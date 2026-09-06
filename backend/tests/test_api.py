"""API tests for the churn prediction backend.

Covers: health, model-info (serves metrics.json verbatim), valid prediction
(typical customer + likely churner), gender/contract/payment required
validation, missing fields, invalid enums, out-of-range numeric, charges
above the old $500 cap, out-of-training-range input warnings, and
production-threshold consistency with metadata.json.

Run from backend/:  pytest -v
"""

import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parent          # backend/tests
PROJECT_ROOT = BACKEND_DIR.parent.parent               # repo root
sys.path.insert(0, str(BACKEND_DIR))

from app.main import app  # noqa: E402

METADATA = json.loads((PROJECT_ROOT / "ml" / "artifacts" / "metadata.json").read_text())
PROD_THRESHOLD = float(METADATA["classification_threshold"])
RISK_THRESHOLDS = METADATA["risk_thresholds"]


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _base_payload(**overrides):
    """A long-tenured, contract-bound customer (historically low churn)."""
    payload = {
        "gender": "Female",
        "SeniorCitizen": 0,
        "Partner": "Yes",
        "Dependents": "Yes",
        "PhoneService": "Yes",
        "MultipleLines": "No",
        "InternetService": "DSL",
        "OnlineSecurity": "Yes",
        "OnlineBackup": "Yes",
        "DeviceProtection": "Yes",
        "TechSupport": "Yes",
        "StreamingTV": "No",
        "StreamingMovies": "No",
        "Contract": "Two year",
        "PaperlessBilling": "No",
        "PaymentMethod": "Credit card (automatic)",
        "tenure": 65,
        "MonthlyCharges": 75.50,
        "TotalCharges": 4800.25,
    }
    payload.update(overrides)
    return payload


# ---------------------------------------------------------------- health


def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["model_loaded"] is True
    assert body["model_name"]


# ---------------------------------------------------------------- model-info


def test_model_info_returns_real_metrics(client):
    r = client.get("/model-info")
    assert r.status_code == 200
    body = r.json()
    assert body["model_name"] == "voting_ensemble"
    tm = body["test_metrics"]
    for key in ("accuracy", "precision", "recall", "f1", "roc_auc"):
        assert key in tm, f"missing metric: {key}"
        assert 0.0 <= tm[key] <= 1.0
    recorded = json.loads(
        (PROJECT_ROOT / "ml" / "artifacts" / "metrics.json").read_text()
    )
    expected = recorded["results"][recorded["selected_model"]]["test"]
    assert tm == expected  # endpoint serves metrics.json verbatim — nothing hardcoded


def test_model_info_includes_components_and_threshold(client):
    body = client.get("/model-info").json()
    assert body["components"] == ["Logistic Regression", "Random Forest",
                                  "Gradient Boosting"]
    assert body["classification_threshold"] == PROD_THRESHOLD


# ---------------------------------------------------------------- valid


def test_predict_typical_customer_low_risk(client):
    r = client.post("/predict", json=_base_payload())
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body["churn_prediction"], bool)
    assert 0.0 <= body["churn_probability"] <= 1.0
    assert body["risk_level"] in {"Low", "Medium", "High"}
    assert body["model_name"] == "voting_ensemble"
    assert isinstance(body["top_factors"], list) and len(body["top_factors"]) > 0
    assert body["churn_prediction"] is False
    assert body["risk_level"] == "Low"
    assert body["input_warnings"] == []


def test_predict_likely_churner_high_risk(client):
    """Month-to-month + fiber + electronic check + low tenure: classic churner."""
    r = client.post("/predict", json=_base_payload(
        gender="Male",
        SeniorCitizen=1,
        Partner="No",
        Dependents="No",
        InternetService="Fiber optic",
        OnlineSecurity="No",
        OnlineBackup="No",
        DeviceProtection="No",
        TechSupport="No",
        Contract="Month-to-month",
        PaperlessBilling="Yes",
        PaymentMethod="Electronic check",
        tenure=2,
        MonthlyCharges=104.9,
        TotalCharges=210.0,
    ))
    assert r.status_code == 200
    body = r.json()
    assert body["churn_prediction"] is True
    assert body["risk_level"] == "High"
    assert body["churn_probability"] >= RISK_THRESHOLDS["high"]


def test_churner_probability_exceeds_safe_customer(client):
    safe = client.post("/predict", json=_base_payload()).json()
    risky = client.post("/predict", json=_base_payload(
        Contract="Month-to-month", tenure=2, InternetService="Fiber optic",
        PaymentMethod="Electronic check", TechSupport="No",
    )).json()
    assert risky["churn_probability"] > safe["churn_probability"]


# ---------------------------------------------------------------- threshold


def test_prediction_uses_production_threshold(client):
    """churn_prediction must equal (probability >= metadata threshold)."""
    body = client.post("/predict", json=_base_payload(
        Contract="Month-to-month", tenure=8, InternetService="Fiber optic",
    )).json()
    assert body["churn_prediction"] == (body["churn_probability"] >= PROD_THRESHOLD)


def test_threshold_matches_metadata():
    """Guard: tests and backend must agree on the production threshold."""
    assert PROD_THRESHOLD == 0.5


# ---------------------------------------------------------------- invalid


def test_missing_gender_rejected(client):
    payload = _base_payload()
    del payload["gender"]
    r = client.post("/predict", json=payload)
    assert r.status_code == 422
    assert "gender" in r.text


def test_missing_field_rejected(client):
    payload = _base_payload()
    del payload["tenure"]
    r = client.post("/predict", json=payload)
    assert r.status_code == 422
    assert "tenure" in r.text


def test_invalid_enum_rejected(client):
    r = client.post("/predict", json=_base_payload(Contract="3 year"))
    assert r.status_code == 422
    assert "Contract" in r.text


def test_out_of_range_tenure_rejected(client):
    r = client.post("/predict", json=_base_payload(tenure=601))
    assert r.status_code == 422


def test_negative_charges_rejected(client):
    r = client.post("/predict", json=_base_payload(MonthlyCharges=-10))
    assert r.status_code == 422


def test_charge_above_old_500_cap_accepted(client):
    """$500 was an arbitrary cap; economically plausible values must pass."""
    r = client.post("/predict", json=_base_payload(MonthlyCharges=850.0,
                                                   TotalCharges=10200.0))
    assert r.status_code == 200
    body = r.json()
    assert 0.0 <= body["churn_probability"] <= 1.0


def test_extreme_charge_still_bounded(client):
    r = client.post("/predict", json=_base_payload(MonthlyCharges=500_000))
    assert r.status_code == 422


def test_non_numeric_charge_rejected(client):
    r = client.post("/predict", json=_base_payload(TotalCharges="expensive"))
    assert r.status_code == 422


def test_total_below_monthly_rejected(client):
    r = client.post("/predict", json=_base_payload(MonthlyCharges=90.0,
                                                   TotalCharges=50.0))
    assert r.status_code == 422
    assert "TotalCharges" in r.text


def test_senior_citizen_must_be_0_or_1(client):
    r = client.post("/predict", json=_base_payload(SeniorCitizen=2))
    assert r.status_code == 422


# ---------------------------------------------------------------- warnings


def test_warning_for_value_far_above_training_range(client):
    """Valid but far outside the training distribution -> warning, not error."""
    r = client.post("/predict", json=_base_payload(MonthlyCharges=850.0,
                                                   TotalCharges=10200.0))
    assert r.status_code == 200
    warnings = {w["field"]: w["message"] for w in r.json()["input_warnings"]}
    assert "MonthlyCharges" in warnings
    assert "less reliable" in warnings["MonthlyCharges"]


def test_no_warning_for_in_range_values(client):
    r = client.post("/predict", json=_base_payload(MonthlyCharges=80.0,
                                                   TotalCharges=2000.0))
    assert r.status_code == 200
    assert r.json()["input_warnings"] == []

"""Degraded-mode tests: behavior when model artifacts are missing.

Runs in a separate module because starting a TestClient without artifacts
clears the app's shared STATE, which would break the other tests if they
shared a session.
"""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))


@pytest.fixture()
def no_model_client(monkeypatch, tmp_path):
    """App instance whose artifact paths point at an empty temp dir."""
    from app import inference, main

    monkeypatch.setattr(inference, "MODEL_PATH", tmp_path / "nope.joblib")
    monkeypatch.setattr(inference, "METADATA_PATH", tmp_path / "nope.json")
    monkeypatch.setattr(inference, "METRICS_PATH", tmp_path / "nope-metrics.json")
    monkeypatch.setattr(inference, "FACTORS_PATH", tmp_path / "nope-factors.json")
    # Fresh STATE so this module is independent of the main test module.
    monkeypatch.setattr(main, "STATE", {})
    with TestClient(main.app) as c:
        yield c


def test_health_degraded_without_model(no_model_client):
    body = no_model_client.get("/health").json()
    assert body["model_loaded"] is False
    assert body["status"] == "degraded"


def test_predict_503_without_model(no_model_client):
    payload = {
        "gender": "Female", "SeniorCitizen": 0, "Partner": "Yes",
        "Dependents": "Yes", "PhoneService": "Yes", "MultipleLines": "No",
        "InternetService": "DSL", "OnlineSecurity": "Yes", "OnlineBackup": "Yes",
        "DeviceProtection": "Yes", "TechSupport": "Yes", "StreamingTV": "No",
        "StreamingMovies": "No", "Contract": "Two year",
        "PaperlessBilling": "No", "PaymentMethod": "Credit card (automatic)",
        "tenure": 65, "MonthlyCharges": 75.5, "TotalCharges": 4800.0,
    }
    r = no_model_client.post("/predict", json=payload)
    assert r.status_code == 503
    assert "python -m ml.train" in r.json()["detail"]


def test_model_info_503_without_model(no_model_client):
    assert no_model_client.get("/model-info").status_code == 503

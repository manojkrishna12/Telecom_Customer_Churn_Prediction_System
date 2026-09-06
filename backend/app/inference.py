"""Model loading and prediction logic for the churn API.

Loads the artifacts produced by `python -m ml.train`:
  ml/artifacts/model.joblib   -> full sklearn Pipeline (preprocessing + model)
  ml/artifacts/metadata.json  -> feature order, enums, risk thresholds
  ml/artifacts/factor_importance.json -> global top factors (test set)

The pipeline applies the exact same preprocessing fitted during training
(scaling, imputation, one-hot encoding), so there is no train/serve skew.
"""

import json
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

HERE = Path(__file__).resolve().parent          # backend/app
BACKEND_DIR = HERE.parent                        # backend
PROJECT_ROOT = BACKEND_DIR.parent
ARTIFACTS_DIR = PROJECT_ROOT / "ml" / "artifacts"

MODEL_PATH = ARTIFACTS_DIR / "model.joblib"
METADATA_PATH = ARTIFACTS_DIR / "metadata.json"
METRICS_PATH = ARTIFACTS_DIR / "metrics.json"
FACTORS_PATH = ARTIFACTS_DIR / "factor_importance.json"


class ModelNotLoadedError(RuntimeError):
    """Raised when the API is asked to predict before artifacts exist."""


def load_bundle() -> dict[str, Any]:
    """Load model + metadata + factors. Raises FileNotFoundError if missing."""
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model artifact not found at {MODEL_PATH}. "
            "Run `python -m ml.train` first."
        )
    model = joblib.load(MODEL_PATH)
    metadata = json.loads(METADATA_PATH.read_text())
    metrics = json.loads(METRICS_PATH.read_text()) if METRICS_PATH.exists() else {}
    factors = json.loads(FACTORS_PATH.read_text()) if FACTORS_PATH.exists() else {}
    return {
        "model": model,
        "metadata": metadata,
        "metrics": metrics,
        "factors": factors.get("factors", []),
    }


def model_info(bundle: dict[str, Any]) -> dict[str, Any]:
    """Model name + held-out test metrics, read straight from metrics.json.

    No values are hardcoded here: everything comes from the training run.
    """
    metadata = bundle["metadata"]
    metrics = bundle["metrics"]
    selected = metadata["selected_model"]
    result = metrics.get("results", {}).get(selected, {})
    return {
        "model_name": selected,
        "components": metadata.get("model_components", []),
        "test_metrics": result.get("test"),
        "cv_metrics": result.get("cv"),
        "selection_criterion": metrics.get("selection_criterion"),
        "dataset": metrics.get("dataset"),
        "classification_threshold": metadata.get("classification_threshold"),
        "trained_at": metadata.get("trained_at"),
        "versions": metadata.get("versions"),
    }


def risk_level(probability: float, thresholds: dict[str, float]) -> str:
    """Map churn probability to Low/Medium/High using metadata thresholds."""
    if probability >= thresholds.get("high", 0.70):
        return "High"
    if probability >= thresholds.get("medium", 0.40):
        return "Medium"
    return "Low"


def input_warnings(payload: dict[str, Any], metadata: dict[str, Any]) -> list[dict[str, str]]:
    """Flag numeric inputs far outside the training distribution.

    Values are still accepted (physical bounds live in schemas.py); this only
    warns that the model has seen little/no similar data, so reliability is
    reduced. Ranges come from metadata.json's training_ranges (train split
    only, so there is no test leakage in the warning logic either).
    """
    ranges = metadata.get("training_ranges", {})
    warnings: list[dict[str, str]] = []
    for field in ("tenure", "MonthlyCharges", "TotalCharges"):
        r = ranges.get(field)
        if not r:
            continue
        value = payload.get(field)
        if value is None:
            continue
        # Warn beyond ~1.5x the training max or well below the observed min
        # (charges below the min are still valid - cheap plans exist - so
        # only absurdly-low *tenure* would matter, and 0 is in-training).
        upper_limit = r["max"] * 1.5
        if value > upper_limit:
            warnings.append({
                "field": field,
                "message": (
                    f"This value is outside the range commonly seen in the "
                    f"training data (observed max {r['max']:,.2f}). The "
                    f"prediction may be less reliable."
                ),
            })
    return warnings


def predict(payload: dict[str, Any], bundle: dict[str, Any]) -> dict[str, Any]:
    """Run one customer through the saved pipeline and build the response.

    payload keys match dataset column names (validated by Pydantic schemas).
    """
    model = bundle["model"]
    metadata = bundle["metadata"]

    row = pd.DataFrame([payload])[metadata["feature_order"]]
    proba = float(model.predict_proba(row)[0, 1])
    # Production classification threshold comes from training-time
    # threshold analysis stored in metadata.json (0.5 unless tuning proves
    # a better operating point).
    threshold = float(metadata.get("classification_threshold", 0.5))
    prediction = bool(proba >= threshold)

    return {
        "churn_prediction": prediction,
        "churn_probability": round(proba, 4),
        "risk_level": risk_level(proba, metadata["risk_thresholds"]),
        "model_name": metadata["selected_model"],
        "top_factors": bundle["factors"],
        "input_warnings": input_warnings(payload, metadata),
    }

"""Data loading and cleaning for the Telco customer churn dataset.

Responsibilities:
- Read the raw CSV (the original dataset at the repository root).
- Drop the identifier column (customerID) - it carries no predictive signal.
- Coerce TotalCharges to numeric; blanks (the 11 customers with tenure == 0)
  become NaN and are handled later by the pipeline's median imputer, fitted
  on training data only.
- Separate features (X) and target (y, encoded Churn Yes -> 1, No -> 0).

No model-specific preprocessing happens here. Scaling and encoding live inside
the sklearn Pipeline in train.py so they are fitted on training data only.
"""

from pathlib import Path

import pandas as pd

TARGET_COL = "Churn"
DROP_COLS = ["customerID"]

# Canonical column order for model input (target excluded).
NUMERIC_FEATURES = ["tenure", "MonthlyCharges", "TotalCharges"]

CATEGORICAL_FEATURES = [
    "gender", "SeniorCitizen", "Partner", "Dependents", "PhoneService",
    "MultipleLines", "InternetService", "OnlineSecurity", "OnlineBackup",
    "DeviceProtection", "TechSupport", "StreamingTV", "StreamingMovies",
    "Contract", "PaperlessBilling", "PaymentMethod",
]

FEATURE_ORDER = CATEGORICAL_FEATURES + NUMERIC_FEATURES

# Allowed values for every categorical feature, straight from the dataset.
# The API validation layer reuses this so users can only send real values.
CATEGORICAL_VALUES = {
    "gender": ["Female", "Male"],
    "SeniorCitizen": [0, 1],
    "Partner": ["Yes", "No"],
    "Dependents": ["Yes", "No"],
    "PhoneService": ["Yes", "No"],
    "MultipleLines": ["No", "Yes", "No phone service"],
    "InternetService": ["DSL", "Fiber optic", "No"],
    "OnlineSecurity": ["No", "Yes", "No internet service"],
    "OnlineBackup": ["Yes", "No", "No internet service"],
    "DeviceProtection": ["Yes", "No", "No internet service"],
    "TechSupport": ["Yes", "No", "No internet service"],
    "StreamingTV": ["Yes", "No", "No internet service"],
    "StreamingMovies": ["Yes", "No", "No internet service"],
    "Contract": ["Month-to-month", "One year", "Two year"],
    "PaperlessBilling": ["Yes", "No"],
    "PaymentMethod": [
        "Electronic check", "Mailed check",
        "Bank transfer (automatic)", "Credit card (automatic)",
    ],
}

RISK_THRESHOLDS = {"medium": 0.40, "high": 0.70}


def find_dataset_path() -> Path:
    """Locate the original dataset at the repository root (data/data.csv)."""
    here = Path(__file__).resolve().parent          # ml/
    for candidate in (here.parent / "data" / "data.csv", here.parent / "data.csv"):
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        "Could not find data/data.csv. Run this from the project checkout."
    )


def load_raw(path: Path | None = None) -> pd.DataFrame:
    path = path or find_dataset_path()
    df = pd.read_csv(path)
    return df


def clean(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Clean the raw frame and return (X, y).

    Steps:
    1. Drop customerID.
    2. Coerce TotalCharges to numeric (blanks -> NaN).
    3. Drop rows with a missing target (never impute the label).
    4. Encode target: Yes -> 1 (churn), No -> 0.
    """
    df = df.drop(columns=[c for c in DROP_COLS if c in df.columns])

    # TotalCharges is stored as object because of blank strings.
    df["TotalCharges"] = pd.to_numeric(df["TotalCharges"], errors="coerce")

    # Never impute the target; drop rows without a label.
    df = df.dropna(subset=[TARGET_COL])

    y = (df[TARGET_COL].astype(str).str.strip().str.lower() == "yes").astype(int)
    X = df[FEATURE_ORDER].copy()
    return X, y


def load_clean(path: Path | None = None) -> tuple[pd.DataFrame, pd.Series]:
    return clean(load_raw(path))

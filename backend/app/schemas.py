"""Pydantic schemas for the churn prediction API.

Validation mirrors ml/prepare_data.py: every categorical feature is an enum
of real dataset values, numeric features get sanity bounds. Invalid or
missing input produces a clear 422 response before any model code runs.

Bounds policy: numeric caps are PHYSICAL sanity limits, not training-range
limits. Values outside the training distribution are accepted and returned
with an `input_warnings` entry (see ChurnResponse) so the UI can tell the
user the prediction may be less reliable - the model never silently rejects
an economically plausible customer.
"""

from enum import Enum
from typing import ClassVar

from pydantic import BaseModel, Field, field_validator


class Gender(str, Enum):
    Female = "Female"
    Male = "Male"


class YesNo(str, Enum):
    Yes = "Yes"
    No = "No"


class MultiLines(str, Enum):
    No = "No"
    Yes = "Yes"
    NoPhoneService = "No phone service"


class InternetService(str, Enum):
    DSL = "DSL"
    Fiber = "Fiber optic"
    No = "No"


class AddonService(str, Enum):
    No = "No"
    Yes = "Yes"
    NoInternetService = "No internet service"


class Contract(str, Enum):
    MonthToMonth = "Month-to-month"
    OneYear = "One year"
    TwoYear = "Two year"


class PaymentMethod(str, Enum):
    ElectronicCheck = "Electronic check"
    MailedCheck = "Mailed check"
    BankTransfer = "Bank transfer (automatic)"
    CreditCard = "Credit card (automatic)"


class SeniorCitizen(int, Enum):
    No = 0
    Yes = 1


class ChurnRequest(BaseModel):
    """One customer's feature values. Field names match the dataset columns."""

    # Physical sanity bounds (not training-distribution limits).
    TENURE_MAX: ClassVar[int] = 600          # 50 years - beyond any telecom tenure
    CHARGE_MAX: ClassVar[int] = 100_000      # generous guard against typos

    gender: Gender
    SeniorCitizen: SeniorCitizen
    Partner: YesNo
    Dependents: YesNo
    PhoneService: YesNo
    MultipleLines: MultiLines
    InternetService: InternetService
    OnlineSecurity: AddonService
    OnlineBackup: AddonService
    DeviceProtection: AddonService
    TechSupport: AddonService
    StreamingTV: AddonService
    StreamingMovies: AddonService
    Contract: Contract
    PaperlessBilling: YesNo
    PaymentMethod: PaymentMethod
    tenure: int = Field(ge=0, le=600)
    MonthlyCharges: float = Field(ge=0, le=100_000)
    TotalCharges: float = Field(ge=0, le=1_000_000)

    @field_validator("TotalCharges")
    @classmethod
    def total_not_below_monthly(cls, v: float, info):
        """Reject TotalCharges < MonthlyCharges (impossible: total accumulates monthly)."""
        monthly = info.data.get("MonthlyCharges")
        if monthly is not None and v < monthly:
            raise ValueError("TotalCharges cannot be lower than MonthlyCharges")
        return v


class Factor(BaseModel):
    feature: str
    importance: float


class InputWarning(BaseModel):
    field: str
    message: str


class ChurnResponse(BaseModel):
    churn_prediction: bool
    churn_probability: float
    risk_level: str
    model_name: str
    top_factors: list[Factor]
    input_warnings: list[InputWarning] = []

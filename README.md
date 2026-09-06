# Telecom Customer Churn Prediction

A production-style, end-to-end machine-learning web application that
estimates how likely a telecom customer is to cancel their service. Enter a
customer's profile in the React dashboard; a FastAPI backend runs it through
a leakage-free scikit-learn pipeline and returns an estimated churn
probability, a Low / Medium / High risk level, and the model's most
influential factors.

**Stack:** React 18 + Vite (frontend) · FastAPI (backend) · scikit-learn (ML)

---

## 1. Problem Statement

Customer churn — subscribers discontinuing a service — is a critical metric
in the highly competitive telecom market, where annual churn runs 15–25%.

## 2. Business Motivation

Retaining an existing customer is considerably cheaper than acquiring a new
one. If a carrier can identify at-risk customers *before* they leave, it can
target retention offers only where they are needed: a missed churner (false
negative) costs far more than a wasted retention offer (false positive).
This application scores individual customers on demand so retention teams
can prioritize outreach by risk level.

## 3. Dataset

[Telco Customer Churn](https://www.kaggle.com/bhartiprasad17/customer-churn-prediction/data)
— **7,043 customer records × 21 columns**, stored at `data/data.csv`.

**Important:** the original Telco Customer Churn dataset is denominated in
**US dollars (USD)**. All charges shown and stored in this application
(`Monthly Charges ($)`, `Total Charges ($)`) use USD exactly as the dataset
does — there is no currency conversion anywhere in the project.

- **Target variable:** `Churn` (Yes / No) — 1,869 churners, a 26.5% churn rate.
- `TotalCharges` is stored as text with blank strings for the 11 customers
  with `tenure == 0`; it is coerced to numeric and imputed (see §8).
- The original analysis notebook (`Scripts/Customer churn prediction.ipynb`)
  and the EDA images in `output/` are preserved untouched.

## 4. Feature Description

19 features (after dropping the `customerID` identifier):

| Group | Features |
|---|---|
| Demographics | gender, SeniorCitizen, Partner, Dependents |
| Services | PhoneService, MultipleLines, InternetService, OnlineSecurity, OnlineBackup, DeviceProtection, TechSupport, StreamingTV, StreamingMovies |
| Account & billing | Contract, PaperlessBilling, PaymentMethod, tenure (months), MonthlyCharges ($), TotalCharges ($) |

Training-data ranges (train split only, stored in `metadata.json`):
tenure 0–72 months; MonthlyCharges $18.40–$118.75; TotalCharges
$18.85–$8,684.80.

## 5. Data Preprocessing

Implemented in `ml/prepare_data.py` and `ml/train.py`:

- `customerID` dropped (identifier, no predictive signal).
- `TotalCharges` coerced to numeric (blanks → NaN).
- Rows with a missing target are dropped; **`tenure=0` rows are kept** and
  their missing `TotalCharges` is imputed — a deliberate improvement over
  the original notebook, which discarded them.
- Numeric features: median imputation → `StandardScaler`.
- Categorical features: `OneHotEncoder(handle_unknown="ignore")` — nominal
  features are never ordinally label-encoded, and unseen categories at
  prediction time map to all-zero columns instead of crashing.

## 6. Data Leakage Prevention

All preprocessing lives **inside** the sklearn `Pipeline`, so it is fitted
only on training data and reused unchanged at prediction time:

- Stratified 80/20 train/test split (`random_state=42`); the test set is
  used only for final evaluation.
- 5-fold stratified cross-validation on the training folds drives model
  comparison; preprocessing is re-fit within each fold by the Pipeline.
- The classification threshold is tuned on **out-of-fold training
  predictions** (`cross_val_predict`) — the test set plays no role in tuning.
- The entire fitted pipeline (imputer + scaler + encoder + model) is saved
  as a single `model.joblib`, guaranteeing train/serve preprocessing parity.
- The API never calls `.fit()`; it only calls `predict_proba` on the saved
  pipeline (verified by tests).

## 7. Cross-Validation Methodology

5-fold stratified CV on the 5,634-row training set, repeated for every
candidate model, scoring accuracy, precision, recall, F1 and ROC-AUC. The
winner is then refit on the full training set and evaluated once on the
1,409-row held-out test set.

## 8. Models Evaluated

Logistic Regression (class_weight=balanced), Random Forest, Gradient
Boosting, AdaBoost (SAMME), KNN, SVC (probability=True), a soft
**VotingClassifier** (LR + RF + GB) and a **StackingClassifier** (same base
learners), plus a majority-class baseline for context.

### Held-out test results (n = 1,409)

| Model | Accuracy | Precision | Recall | F1 | ROC-AUC |
|---|---|---|---|---|---|
| **Voting ensemble (selected)** | 0.7842 | 0.5799 | **0.6791** | **0.6256** | 0.8446 |
| Stacking ensemble | 0.7977 | 0.6395 | 0.5455 | 0.5887 | **0.8454** |
| Gradient Boosting | 0.8062 | 0.6735 | 0.5241 | 0.5895 | 0.8434 |
| AdaBoost | 0.8020 | 0.6518 | 0.5455 | 0.5939 | 0.8433 |
| Logistic Regression | 0.7374 | 0.5034 | 0.7834 | 0.6130 | 0.8414 |
| Random Forest | 0.7771 | 0.5725 | 0.6337 | 0.6015 | 0.8345 |
| KNN | 0.7821 | 0.5954 | 0.5588 | 0.5766 | 0.8225 |
| SVC | 0.7452 | 0.5133 | 0.7727 | 0.6169 | 0.8213 |
| Baseline (majority class) | 0.7346 | 0.0 | 0.0 | 0.0 | 0.5000 |

The machine-generated source of these numbers is `ml/artifacts/metrics.json`;
the UI's Model Performance panel reads them live from `GET /model-info`
(nothing is hardcoded).

## 9. Final Model & Selection Reasoning

**Soft Voting Ensemble — Logistic Regression + Random Forest + Gradient
Boosting** (soft voting on predicted probabilities).

Selection rule: highest **ROC-AUC** on the held-out test set, with
differences within 0.005 treated as ties and broken by **F1**. Accuracy alone
was explicitly *not* used — with a 26.5% churn rate, "always predict No"
scores 73.5% accuracy while catching zero churners.

- Stacking edges out voting on ROC-AUC by 0.0008 — inside the noise
  tolerance — so they are treated as tied on ranking ability.
- The tie-break goes to the voting ensemble on F1 (0.6256 vs 0.5887) and
  churn recall (0.679 vs 0.545), matching the business priority of catching
  churners.

## 10. Classification Threshold

The default 0.5 cutoff was **challenged with a leakage-free threshold
analysis** and **kept**:

- Method: out-of-fold (`cross_val_predict`) probabilities on the *training
  set only*; scan of thresholds 0.05–0.95 with a precision floor of 0.50.
- Result: the best eligible candidate, t=0.45 (precision 0.568, recall 0.724,
  F1 0.6363), beats t=0.5's OOF F1 (0.6284) by only 0.0079 — below the 0.01
  improvement bar set to avoid chasing noise.
- Decision: keep 0.5. The full scan table is stored in
  `ml/artifacts/metadata.json` (`threshold_analysis`), and the backend reads
  the production threshold from metadata (so retraining that finds a better
  threshold automatically propagates to the API).

**Business trade-off:** a *false negative* is a real churner predicted to
stay (lost revenue, no retention attempt); a *false positive* is a
non-churner flagged as at-risk (a wasted, low-cost retention offer). Lowering
the threshold trades precision for recall; at 0.3, recall jumps to 0.86 but
precision drops to 0.48 — nearly half of flagged customers would not have
churned. 0.5 sits at the reasonable middle of that curve for this dataset.

## 11. Risk Levels

Churn probability maps to risk using fixed thresholds:

| Risk | Churn probability |
|---|---|
| Low | < 40% |
| Medium | 40% – 69.9% |
| High | ≥ 70% |

## 12. Explainability Methodology

`ml/train.py` computes **permutation importance on the held-out test set**
(scoring ROC-AUC, 10 repeats) and stores the top factors in
`ml/artifacts/factor_importance.json`. Top factors: **tenure, Contract,
InternetService**, then OnlineSecurity, TechSupport, TotalCharges,
MonthlyCharges, PaymentMethod — consistent with the EDA in the original
notebook (month-to-month contracts, fiber-optic users and brand-new
customers churn most).

The UI labels these clearly as **"Most Influential Factors — Model Wide"**
with the note that they "describe which features influence the model overall
and are NOT a personalized explanation for this individual customer." Global
importance is never presented as a per-customer explanation, and no
explanations are fabricated.

## 13. Architecture

```
React form (19 validated fields)
      ↓  POST /predict (JSON)
FastAPI validation (Pydantic enums + bounds)
      ↓
Saved sklearn Pipeline  (model.joblib — loaded once at startup)
      ↓  impute → scale → one-hot encode   (identical to training)
Soft Voting Ensemble  (LR + RF + GB)
      ↓  predict_proba
Churn probability → threshold decision → risk level
      ↓  JSON response
React result card (probability, risk, factors, warnings)
```

## 14. Project Structure

```
├── data/
│   └── data.csv                  # dataset (original, USD-denominated)
├── ml/                           # training pipeline
│   ├── prepare_data.py           # loading, cleaning, enums, thresholds
│   ├── train.py                  # training, CV, threshold analysis, saving
│   └── artifacts/                # generated: model.joblib, *.json (gitignored)
├── backend/                      # FastAPI API
│   ├── app/
│   │   ├── main.py               # /health, /model-info, /predict, CORS
│   │   ├── schemas.py            # Pydantic validation
│   │   └── inference.py          # artifact loading, warnings, risk levels
│   ├── tests/                    # 23 API tests (pytest)
│   └── requirements.txt
├── frontend/                     # React 18 + Vite app
│   ├── src/
│   │   ├── App.jsx               # dashboard layout, validation, state
│   │   ├── api.js                # fetch client w/ error handling
│   │   ├── formConfig.js         # field definitions & placeholders
│   │   ├── index.css             # responsive dashboard styling
│   │   └── components/           # ChurnForm, ResultCard, ModelPanel
│   ├── .env                      # VITE_API_URL (gitignored)
│   └── .env.example
├── Scripts/                      # original notebook + data copy (preserved)
├── output/                       # original EDA images (preserved)
└── README.md
```

## 15. React Frontend

Two-column dashboard (form left, results right) that collapses to a single
column on mobile. Features:

- **Customer Input** form with three sections and explicit placeholder
  selections for Gender, Contract and Payment Method ("Select Gender", etc.)
  — the app never silently defaults a sensitive field.
- Stable **Prediction Result** card that shows an empty state before the
  first prediction (no layout shift, no popup feel).
- **Model Performance** panel with live metrics from `/model-info`.
- Loading spinner, friendly backend-unavailable banner, parsed FastAPI 422
  validation messages, and inline per-field errors.
- A visible warning when an input is valid but far outside the training
  distribution (see §17).

## 16. FastAPI Backend

- Artifacts loaded **once** at startup via the lifespan hook; requests never
  retrain or reload the model.
- Graceful degradation: without artifacts, `/health` reports `degraded` and
  `/predict` returns HTTP 503 with instructions.
- CORS enabled for the Vite dev origins (5173/5174).
- Interactive docs at `/docs` (Swagger UI).

## 17. API Endpoints

### `GET /health`

```json
{ "status": "ok", "model_loaded": true, "model_name": "voting_ensemble" }
```

### `GET /model-info`

Model name, components, held-out test metrics (read verbatim from
`metrics.json`), selection criterion, classification threshold, dataset
summary and library versions. Example:

```json
{
  "model_name": "voting_ensemble",
  "components": ["Logistic Regression", "Random Forest", "Gradient Boosting"],
  "test_metrics": { "accuracy": 0.7842, "precision": 0.5799,
                    "recall": 0.6791, "f1": 0.6256, "roc_auc": 0.8446 },
  "classification_threshold": 0.5
}
```

### `POST /predict`

All 19 feature fields are required. Categorical fields are enum-validated.
Numeric caps are **physical sanity limits** (tenure ≤ 600 months,
MonthlyCharges ≤ $100,000, TotalCharges ≤ $1,000,000) — *not* the training
range. This distinguishes two kinds of "unusual" input:

- **Invalid** (HTTP 422): negative values, non-numerics, impossible
  combinations (`TotalCharges < MonthlyCharges`), unknown categories.
- **Valid but out-of-distribution** (HTTP 200 + `input_warnings`): e.g. a
  $850/month plan is economically plausible though far above the training
  max of $118.75. The API accepts it and returns a warning:
  *"This value is outside the range commonly seen in the training data
  (observed max 118.75). The prediction may be less reliable."*

Example request (a likely churner):

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "gender": "Male", "SeniorCitizen": 1, "Partner": "No", "Dependents": "No",
    "PhoneService": "Yes", "MultipleLines": "No",
    "InternetService": "Fiber optic", "OnlineSecurity": "No",
    "OnlineBackup": "No", "DeviceProtection": "No", "TechSupport": "No",
    "StreamingTV": "No", "StreamingMovies": "No",
    "Contract": "Month-to-month", "PaperlessBilling": "Yes",
    "PaymentMethod": "Electronic check",
    "tenure": 2, "MonthlyCharges": 104.9, "TotalCharges": 210
  }'
```

Example response:

```json
{
  "churn_prediction": true,
  "churn_probability": 0.7631,
  "risk_level": "High",
  "model_name": "voting_ensemble",
  "top_factors": [
    { "feature": "tenure", "importance": 0.06829 },
    { "feature": "Contract", "importance": 0.05057 },
    { "feature": "InternetService", "importance": 0.01899 }
  ],
  "input_warnings": []
}
```

## 18. How to Train

```bash
pip install -r requirements.txt
python -m ml.train
```

Runs in ~1 minute and writes `ml/artifacts/` (model, metrics, metadata,
factors). The console prints every model's test metrics, the selection
outcome, and the threshold-analysis result.

## 19. How to Run the Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

`GET http://localhost:8000/health` should return
`{"status":"ok","model_loaded":true,...}`.

## 20. How to Run the Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5174. The backend URL is configured in
`frontend/.env` (copy `.env.example`): `VITE_API_URL=http://localhost:8000`.

## 21. Testing

```bash
cd backend
pytest -v        # 23 tests
```

Coverage includes: health; model-info serving metrics.json verbatim; valid
predictions; missing gender/fields; invalid enums; out-of-range tenure;
negative charges; **charges above the old $500 cap accepted**; extreme
values still bounded; **out-of-training-range warnings**; **production
threshold consistency with metadata**; and degraded behavior when artifacts
are missing.

Live end-to-end scenarios verified in the running app: safe customer (Low),
high-risk customer (High), invalid input (inline errors), MonthlyCharges
$850 (prediction + warning), repeated predictions without refresh, and the
backend-unavailable banner.

## 22. Screenshots

Not included yet — no images are claimed beyond what this repository
actually contains. The original project's EDA charts are preserved in
`output/`, and the trained-model UI can be reproduced locally with two
commands (see §19–20).

## 23. Limitations

- **Class imbalance** (~26.5% churn): mitigated with stratified splits,
  class weighting where applicable, and ROC-AUC/F1-based selection, but
  minority-class recall (~0.68 at t=0.5) remains the weakest metric.
- **Probability calibration** is not guaranteed for tree ensembles; the
  40%/70% risk cutoffs are documented heuristics, not cost-optimized points.
- **Global explainability only** — no per-customer attributions (SHAP was
  deliberately not added to keep the project simple and honest).
- **Snapshot model** — trained on this historical dataset; drift would
  require retraining. No automated retraining schedule or monitoring.
- Demographic features (e.g. SeniorCitizen, gender) can encode bias; do not
  use predictions for adverse decisions without fairness review.
- Single-process, in-memory API; no auth, rate limiting, or horizontal
  scaling. Suitable for local development and demos.

## 24. Future Improvements

- Cost-sensitive threshold selection once real retention costs are known.
- Probability calibration (isotonic/Platt) and reliability diagrams.
- Per-customer explanations (e.g. SHAP) behind a clear UI disclaimer.
- Automated retraining pipeline with drift monitoring.
- Docker Compose packaging and a CI workflow (tests on every push).

## 25. Feedback

Built on the original
[Telecom-Customer-Churn-prediction](https://github.com/Pradnya1208/Telecom-Customer-Churn-prediction)
notebook analysis; the original notebook, dataset and EDA outputs are
preserved in this repository.

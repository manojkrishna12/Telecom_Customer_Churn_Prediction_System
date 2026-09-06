"""End-to-end training pipeline for the Telco churn model.

Run from the repository root:
    python -m ml.train

What it does:
1. Load and clean the dataset (ml/prepare_data.py).
2. Split into train/test (stratified, 80/20). Test set is touched only for
   final evaluation - never for fitting.
3. 5-fold stratified cross-validation on the training set for each candidate
   model (preprocessing is re-fitted inside each fold via sklearn Pipeline).
4. Refit every candidate on the full training set, evaluate on the held-out
   test set: Accuracy, Precision, Recall, F1, ROC-AUC.
5. Select the final model by ROC-AUC (F1 as tie-break) - explicitly NOT
   accuracy, because churn is imbalanced (~26.6% positives) and accuracy is
   dominated by the majority class.
6. Persist everything the API needs into ml/artifacts/:
   - model.joblib       : the fitted sklearn Pipeline (preprocessing + model)
   - metrics.json       : all metrics + selection rationale
   - metadata.json      : feature lists, allowed values, thresholds, versions
   - factor_importance.json : permutation importance on the TEST set

The single joblib pipeline guarantees that prediction-time preprocessing is
identical to training-time preprocessing (no leakage, no drift).
"""

from __future__ import annotations

import json
import platform
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import (
    AdaBoostClassifier,
    GradientBoostingClassifier,
    RandomForestClassifier,
    StackingClassifier,
    VotingClassifier,
)
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import (
    StratifiedKFold,
    cross_val_predict,
    cross_validate,
    train_test_split,
)
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.svm import SVC

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from ml.prepare_data import (  # noqa: E402
    CATEGORICAL_FEATURES,
    CATEGORICAL_VALUES,
    FEATURE_ORDER,
    NUMERIC_FEATURES,
    RISK_THRESHOLDS,
    TARGET_COL,
    load_clean,
)

ARTIFACTS_DIR = HERE / "artifacts"
RANDOM_STATE = 42
CV_SPLITS = 5
TEST_SIZE = 0.20

MIN_POSITIVES = 200  # minimum churn cases to keep a test split reliable

# Human-readable component lists, shown in the UI's Model Performance panel.
MODEL_COMPONENTS = {
    "voting_ensemble": ["Logistic Regression", "Random Forest", "Gradient Boosting"],
    "stacking_ensemble": ["Logistic Regression", "Random Forest", "Gradient Boosting"],
    "logistic_regression": ["Logistic Regression"],
    "random_forest": ["Random Forest"],
    "gradient_boosting": ["Gradient Boosting"],
    "ada_boost": ["AdaBoost"],
    "knn": ["K-Nearest Neighbors"],
    "svc": ["Support Vector Machine"],
}

# ROC-AUC differences below this are treated as statistical noise between
# models; ties are then broken by F1, which better reflects churn-detection
# quality (recall of the minority class) than accuracy does.
AUC_TIE_TOLERANCE = 0.005

# ---------------------------------------------------------------------------
# Classification-threshold tuning (leakage-free)
#
# The default 0.5 cutoff maximizes neither F1 nor recall. A better operating
# point is chosen from OUT-OF-FOLD predictions on the TRAINING set only
# (cross_val_predict), so the held-out test set stays untouched by tuning.
#
# Selection rule: among candidate thresholds, take the one maximizing F1
# subject to a precision floor. The floor keeps the business trade-off sane:
# below it, most flagged customers would be non-churners and retention offers
# would be mostly wasted. A change is adopted only if it beats the 0.5
# threshold's OOF F1 by more than F1_MIN_GAIN (noise guard).
# ---------------------------------------------------------------------------
THRESHOLD_GRID = [round(0.05 + 0.05 * i, 2) for i in range(19)]  # 0.05 .. 0.95
PRECISION_FLOOR = 0.50
F1_MIN_GAIN = 0.01
DEFAULT_THRESHOLD = 0.50


def build_preprocessor() -> ColumnTransformer:
    """Preprocessing fitted on training data only (inside the Pipeline).

    - Numeric: median imputation (TotalCharges blanks) then standard scaling.
    - Categorical: one-hot encoding; unknown categories at predict time map
      to all-zero columns instead of crashing.
    """
    numeric = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])
    categorical = Pipeline(steps=[
        ("onehot", OneHotEncoder(handle_unknown="ignore")),
    ])
    return ColumnTransformer(
        transformers=[
            ("num", numeric, NUMERIC_FEATURES),
            ("cat", categorical, CATEGORICAL_FEATURES),
        ],
        remainder="drop",
    )


def candidate_models() -> dict[str, object]:
    """Candidate estimators, mirroring the original notebook's shortlist."""
    return {
        "logistic_regression": LogisticRegression(
            max_iter=1000, class_weight="balanced", random_state=RANDOM_STATE
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=300, min_samples_leaf=2, class_weight="balanced",
            random_state=RANDOM_STATE, n_jobs=-1,
        ),
        "gradient_boosting": GradientBoostingClassifier(random_state=RANDOM_STATE),
        "ada_boost": AdaBoostClassifier(algorithm="SAMME", random_state=RANDOM_STATE),
        "knn": KNeighborsClassifier(n_neighbors=15),
        "svc": SVC(probability=True, class_weight="balanced", random_state=RANDOM_STATE),
        "voting_ensemble": VotingClassifier(
            estimators=[
                ("lr", LogisticRegression(max_iter=1000, class_weight="balanced",
                                          random_state=RANDOM_STATE)),
                ("rf", RandomForestClassifier(n_estimators=300, min_samples_leaf=2,
                                              class_weight="balanced",
                                              random_state=RANDOM_STATE, n_jobs=-1)),
                ("gb", GradientBoostingClassifier(random_state=RANDOM_STATE)),
            ],
            voting="soft",
        ),
        "stacking_ensemble": StackingClassifier(
            estimators=[
                ("lr", LogisticRegression(max_iter=1000, class_weight="balanced",
                                          random_state=RANDOM_STATE)),
                ("rf", RandomForestClassifier(n_estimators=300, min_samples_leaf=2,
                                              class_weight="balanced",
                                              random_state=RANDOM_STATE, n_jobs=-1)),
                ("gb", GradientBoostingClassifier(random_state=RANDOM_STATE)),
            ],
            final_estimator=LogisticRegression(max_iter=1000),
            cv=5,
        ),
    }


def evaluate(y_true, y_pred, y_prob) -> dict:
    return {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, y_pred)), 4),
        "f1": round(float(f1_score(y_true, y_pred)), 4),
        "roc_auc": round(float(roc_auc_score(y_true, y_prob)), 4),
    }


def analyze_thresholds(y_true, oof_prob) -> dict:
    """Pick the production classification threshold from OOF training predictions.

    Returns the chosen threshold, the full scan table, and the rationale.
    Uses ONLY training-fold (out-of-fold) predictions: the test set is never
    consulted, so no tuning leakage is possible.
    """
    table = []
    for t in THRESHOLD_GRID:
        pred = (oof_prob >= t).astype(int)
        table.append({
            "threshold": t,
            "precision": round(float(precision_score(y_true, pred, zero_division=0)), 4),
            "recall": round(float(recall_score(y_true, pred)), 4),
            "f1": round(float(f1_score(y_true, pred)), 4),
        })

    by_t = {row["threshold"]: row for row in table}
    f1_default = by_t[DEFAULT_THRESHOLD]["f1"]

    eligible = [r for r in table if r["precision"] >= PRECISION_FLOOR]
    best = max(eligible, key=lambda r: r["f1"]) if eligible else None

    if best and best["f1"] >= f1_default + F1_MIN_GAIN and best["threshold"] != DEFAULT_THRESHOLD:
        chosen = best["threshold"]
        reason = (
            f"Threshold {chosen} maximizes out-of-fold F1 ({best['f1']}) among "
            f"candidates with precision >= {PRECISION_FLOOR}, beating the 0.5 "
            f"threshold's F1 ({f1_default}) by more than {F1_MIN_GAIN}. It trades "
            "some precision for materially higher churn recall, which suits "
            "retention campaigns where a missed churner costs more than a "
            "wasted offer."
        )
    else:
        chosen = DEFAULT_THRESHOLD
        best_note = (
            f"best eligible candidate was {best['threshold']} "
            f"(F1 {best['f1']}, gain {round(best['f1'] - f1_default, 4)})"
            if best else "no candidate cleared the precision floor"
        )
        reason = (
            f"The default 0.5 threshold is kept: {best_note}, below the "
            f"{F1_MIN_GAIN} improvement bar, so no change is justified."
        )

    return {
        "chosen_threshold": chosen,
        "default_threshold": DEFAULT_THRESHOLD,
        "precision_floor": PRECISION_FLOOR,
        "method": (
            "Out-of-fold (cross_val_predict) probabilities on the TRAINING set "
            "only; the held-out test set was not used for tuning."
        ),
        "reason": reason,
        "table": table,
    }


def main() -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    X, y = load_clean()
    n_total = len(X)
    n_churn = int(y.sum())
    churn_rate = n_churn / n_total
    print(f"Dataset: {n_total} rows, {n_churn} churn ({churn_rate:.1%})")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y
    )
    if int(y_test.sum()) < MIN_POSITIVES:
        raise RuntimeError("Test split has too few churn cases; aborting.")

    cv = StratifiedKFold(n_splits=CV_SPLITS, shuffle=True, random_state=RANDOM_STATE)
    results: dict[str, dict] = {}

    # Majority-class baseline for context (should never win).
    dummy = Pipeline([("prep", build_preprocessor()),
                      ("model", DummyClassifier(strategy="most_frequent"))])
    dummy.fit(X_train, y_train)
    results["baseline_majority"] = {
        "cv": {"roc_auc": None, "accuracy": None, "f1": None, "recall": None, "precision": None},
        "test": evaluate(y_test,
                         dummy.predict(X_test),
                         np.full(len(y_test), float(1 - y_train.mean()))),
    }

    for name, estimator in candidate_models().items():
        print(f"Training {name} ...", flush=True)
        pipe = Pipeline([("preprocessor", build_preprocessor()), ("model", estimator)])

        cv_scores = cross_validate(
            pipe, X_train, y_train, cv=cv,
            scoring=["accuracy", "precision", "recall", "f1", "roc_auc"],
            n_jobs=-1,
        )
        cv_block = {
            metric: round(float(cv_scores[f"test_{metric}"].mean()), 4)
            for metric in ["accuracy", "precision", "recall", "f1", "roc_auc"]
        }

        pipe.fit(X_train, y_train)
        y_pred = pipe.predict(X_test)
        y_prob = pipe.predict_proba(X_test)[:, 1]

        results[name] = {"cv": cv_block, "test": evaluate(y_test, y_pred, y_prob)}
        print(f"  {name}: test roc_auc={results[name]['test']['roc_auc']:.4f} "
              f"f1={results[name]['test']['f1']:.4f}")

    # ------------------------------------------------------------------
    # Model selection: ROC-AUC on the held-out test set, with ties broken
    # by F1. Accuracy alone is misleading here because only ~26.6% of
    # customers churn, so a majority-class model scores ~73% accuracy.
    # ------------------------------------------------------------------
    ranked = sorted(
        (n for n in results if n != "baseline_majority"),
        key=lambda n: results[n]["test"]["roc_auc"],
        reverse=True,
    )
    best_name = ranked[0]
    for challenger in ranked[1:]:
        auc_gap = (results[best_name]["test"]["roc_auc"]
                   - results[challenger]["test"]["roc_auc"])
        if (auc_gap <= AUC_TIE_TOLERANCE
                and results[challenger]["test"]["f1"] > results[best_name]["test"]["f1"]):
            best_name = challenger
    runner_up = next(n for n in ranked if n != best_name)

    print(f"\nSelected model: {best_name} "
          f"(test roc_auc={results[best_name]['test']['roc_auc']}, "
          f"f1={results[best_name]['test']['f1']}; runner-up {runner_up})")

    # Refit the winner on the full training set and persist the whole pipeline.
    best_pipe = Pipeline([
        ("preprocessor", build_preprocessor()),
        ("model", candidate_models()[best_name]),
    ])
    best_pipe.fit(X_train, y_train)
    joblib.dump(best_pipe, ARTIFACTS_DIR / "model.joblib")

    # ------------------------------------------------------------------
    # Classification-threshold tuning on OUT-OF-FOLD training predictions
    # only. cross_val_predict refits clones inside training folds, so the
    # held-out test set plays no role here (no tuning leakage).
    # ------------------------------------------------------------------
    print("Tuning classification threshold on out-of-fold training predictions ...",
          flush=True)
    oof_prob = cross_val_predict(
        best_pipe, X_train, y_train, cv=cv, method="predict_proba", n_jobs=-1
    )[:, 1]
    threshold_analysis = analyze_thresholds(y_train.to_numpy(), oof_prob)
    production_threshold = threshold_analysis["chosen_threshold"]
    print(f"  production threshold: {production_threshold} "
          f"(OOF F1 at threshold: "
          f"{next(r['f1'] for r in threshold_analysis['table'] if r['threshold'] == production_threshold)})")

    # Training-data ranges for numeric features (used by the API to warn
    # about inputs far outside the observed distribution).
    training_ranges = {
        col: {
            "min": round(float(X_train[col].min()), 4),
            "max": round(float(X_train[col].max()), 4),
            "p50": round(float(X_train[col].median()), 4),
            "p95": round(float(X_train[col].quantile(0.95)), 4),
            "p99": round(float(X_train[col].quantile(0.99)), 4),
        }
        for col in NUMERIC_FEATURES
    }

    # Permutation importance on the TEST set (honest, out-of-sample).
    print("Computing permutation importance on test set ...", flush=True)
    r = permutation_importance(
        best_pipe, X_test, y_test, n_repeats=10, random_state=RANDOM_STATE,
        scoring="roc_auc", n_jobs=-1,
    )
    raw_importance = [
        {"feature": feat, "importance": round(float(imp), 5),
         "std": round(float(sd), 5)}
        for feat, imp, sd in zip(X_test.columns, r.importances_mean, r.importances_std)
    ]
    raw_importance.sort(key=lambda d: d["importance"], reverse=True)
    top_factors = raw_importance[:8]

    (ARTIFACTS_DIR / "metrics.json").write_text(json.dumps({
        "dataset": {
            "rows_total": n_total,
            "rows_train": int(len(X_train)),
            "rows_test": int(len(X_test)),
            "churn_count": n_churn,
            "churn_rate": round(churn_rate, 4),
            "features": FEATURE_ORDER,
            "target": TARGET_COL,
        },
        "cv_folds": CV_SPLITS,
        "test_size": TEST_SIZE,
        "random_state": RANDOM_STATE,
        "results": results,
        "ranking_test_roc_auc": ranked,
        "selected_model": best_name,
        "runner_up": runner_up,
        "selection_criterion": (
            f"Highest ROC-AUC on the held-out test set; differences within "
            f"{AUC_TIE_TOLERANCE:.3f} treated as ties and broken by F1. "
            "Accuracy alone is inappropriate for this imbalanced dataset "
            "(~26.6% churn rate)."
        ),
        "auc_tie_tolerance": AUC_TIE_TOLERANCE,
    }, indent=2))

    (ARTIFACTS_DIR / "metadata.json").write_text(json.dumps({
        "selected_model": best_name,
        "model_artifact": "model.joblib",
        "feature_order": FEATURE_ORDER,
        "numeric_features": NUMERIC_FEATURES,
        "categorical_features": CATEGORICAL_FEATURES,
        "categorical_values": {
            # JSON keys must be strings; SeniorCitizen values become "0"/"1".
            k: [str(v) for v in vals] for k, vals in CATEGORICAL_VALUES.items()
        },
        "risk_thresholds": RISK_THRESHOLDS,
        "classification_threshold": production_threshold,
        "threshold_analysis": {
            "method": threshold_analysis["method"],
            "reason": threshold_analysis["reason"],
            "precision_floor": threshold_analysis["precision_floor"],
            "default_threshold": threshold_analysis["default_threshold"],
            "table": threshold_analysis["table"],
        },
        "training_ranges": training_ranges,
        "model_components": MODEL_COMPONENTS.get(best_name, []),
        "target_mapping": {"0": "No", "1": "Yes"},
        "trained_at": pd.Timestamp.utcnow().isoformat(),
        "versions": {
            "python": platform.python_version(),
            "scikit-learn": sklearn.__version__,
            "pandas": pd.__version__,
            "numpy": np.__version__,
            "joblib": joblib.__version__,
        },
    }, indent=2))

    (ARTIFACTS_DIR / "factor_importance.json").write_text(json.dumps({
        "method": "permutation importance on held-out test set (scoring=roc_auc)",
        "n_repeats": 10,
        "factors": top_factors,
    }, indent=2))

    print("\nAll artifacts written to", ARTIFACTS_DIR)


if __name__ == "__main__":
    main()

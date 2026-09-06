"""Telecom Customer Churn Prediction - FastAPI backend.

Endpoints:
  GET  /health      -> service + model status
  GET  /model-info  -> model name + held-out test metrics (from metrics.json)
  POST /predict     -> churn prediction for one customer

Run from the backend/ directory:
    uvicorn app.main:app --reload --port 8000
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .inference import ModelNotLoadedError, load_bundle, model_info, predict
from .schemas import ChurnRequest, ChurnResponse

STATE: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load model artifacts once at startup; never retrain per request."""
    try:
        STATE["bundle"] = load_bundle()
        STATE["model_loaded"] = True
        print("Model artifacts loaded OK.")
    except FileNotFoundError as exc:
        STATE["bundle"] = None
        STATE["model_loaded"] = False
        print(f"WARNING: {exc}")
    yield
    STATE.clear()


app = FastAPI(
    title="Telecom Customer Churn Prediction API",
    version="1.0.0",
    description="Predicts churn for a telecom customer using a trained "
                "scikit-learn pipeline (VotingClassifier ensemble).",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev server
        "http://127.0.0.1:5173",
        "http://localhost:5174",   # Vite dev server (alternate port)
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {
        "status": "ok" if STATE.get("model_loaded") else "degraded",
        "model_loaded": STATE.get("model_loaded", False),
        "model_name": (STATE.get("bundle") or {}).get("metadata", {}).get("selected_model"),
    }


@app.get("/model-info")
def get_model_info():
    if not STATE.get("model_loaded"):
        raise HTTPException(
            status_code=503,
            detail="Model not loaded. Train it first: python -m ml.train",
        )
    return model_info(STATE["bundle"])


@app.post("/predict", response_model=ChurnResponse)
def predict_churn(request: ChurnRequest) -> ChurnResponse:
    if not STATE.get("model_loaded"):
        raise HTTPException(
            status_code=503,
            detail="Model not loaded. Train it first: python -m ml.train",
        )
    try:
        result = predict(request.model_dump(), STATE["bundle"])
    except ModelNotLoadedError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - surface unexpected model errors cleanly
        raise HTTPException(status_code=500, detail=f"Prediction failed: {exc}") from exc
    return ChurnResponse(**result)

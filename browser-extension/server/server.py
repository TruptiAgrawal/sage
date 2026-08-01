#!/usr/bin/env python3
"""SAGE prediction server.

Loads the trained CatBoost models and exposes a single POST /predict endpoint.
The browser extension sends a prompt string; the server returns predicted
input tokens, output tokens, estimated cost, and quality score (1-10).

Run:
    uv run python browser-extension/server/server.py
    # or:
    python browser-extension/server/server.py

The server listens on http://localhost:5050 by default.
"""

import json
import sys
from pathlib import Path

# Allow importing feature_engineering from the repo root dataset/ folder
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "dataset"))

import numpy as np
import pandas as pd
import uvicorn
from catboost import CatBoostClassifier, CatBoostRegressor
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from feature_engineering import extract_features  # noqa: E402

# ---------------------------------------------------------------------------
# Model paths
# ---------------------------------------------------------------------------
CATBOOST_DIR = REPO_ROOT / "models" / "catboost"

# ---------------------------------------------------------------------------
# Feature schema — must match the training order exactly
# ---------------------------------------------------------------------------
NUMERIC_FEATURES = [
    "char_count",
    "word_count",
    "line_count",
    "sentence_count",
    "unique_words",
    "avg_word_length",
    "prompt_depth",
]
BOOL_FEATURES = [
    "has_code",
    "has_json",
    "has_markdown",
    "has_math",
    "has_xml",
    "reasoning_prompt",
    "creative_prompt",
    "tool_usage_prompt",
    "rag_prompt",
]
FEATURE_ORDER = NUMERIC_FEATURES + BOOL_FEATURES

# ---------------------------------------------------------------------------
# Pricing: $ per 1 000 000 tokens — edit to match current provider rates
# ---------------------------------------------------------------------------
PRICING = {
    "claude-opus-4-8":              {"input": 5.00,  "output": 25.00},
    "Groq-llama-3.3-70b-versatile": {"input": 0.59,  "output": 0.79},
    "DeepSeek V4 Flash":            {"input": 0.14,  "output": 0.28},
    "deepseek-reasoner":            {"input": 0.55,  "output": 2.19},
}

# ---------------------------------------------------------------------------
# Quality label → numeric 1-10 mapping
# Bad → 2  |  Average → 5  |  Good → 7  |  Excellent → 9
# ---------------------------------------------------------------------------
QUALITY_SCORE: dict[str, int] = {
    "Bad":       2,
    "Average":   5,
    "Good":      7,
    "Excellent": 9,
}

# ---------------------------------------------------------------------------
# Load models once at startup
# ---------------------------------------------------------------------------
print("Loading CatBoost models …", flush=True)
_input_model  = CatBoostRegressor()
_input_model.load_model(str(CATBOOST_DIR / "token_predictor_input_tokens.cbm"))

_output_model = CatBoostRegressor()
_output_model.load_model(str(CATBOOST_DIR / "token_predictor_output_tokens.cbm"))

_quality_model = CatBoostClassifier()
_quality_model.load_model(str(CATBOOST_DIR / "quality_predictor.cbm"))

# Derive the model list from the quality classifier's training classes so we
# never hard-code it here and it stays in sync with whatever was trained.
_TRAINED_MODELS: list[str] = list(PRICING.keys())
print(f"Models available: {_TRAINED_MODELS}", flush=True)
print("Server ready.", flush=True)

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(title="SAGE Prediction API", version="1.0.0")

# Allow the browser extension (chrome-extension://*) to call this server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)


class PredictRequest(BaseModel):
    prompt: str
    # Optional: if the user is on a known LLM site the extension can pass the
    # detected model name so we show that model first.
    detected_model: str | None = None


class AnalyzeRequest(BaseModel):
    """Analyze a completed prompt+response pair with real token counts."""
    prompt: str
    response: str
    # Actual token counts measured in the browser (js-tiktoken approximation).
    # If not provided the server falls back to character-based estimation.
    input_tokens: int | None = None
    output_tokens: int | None = None
    detected_model: str | None = None


class ModelPrediction(BaseModel):
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float | None
    quality_label: str
    quality_score: int   # 1-10


class AnalysisResult(BaseModel):
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float | None
    quality_label: str
    quality_score: int
    # token source: "measured" (from browser) or "estimated" (char/4 fallback)
    token_source: str


class PredictResponse(BaseModel):
    predictions: list[ModelPrediction]
    features: dict        # echo the extracted features for transparency


class AnalyzeResponse(BaseModel):
    results: list[AnalysisResult]
    features: dict


def _build_feature_row(prompt: str) -> dict:
    """Extract features from a prompt and convert booleans to 0/1 ints."""
    raw = extract_features(prompt)
    row: dict = {f: raw[f] for f in NUMERIC_FEATURES}
    for f in BOOL_FEATURES:
        row[f] = int(raw[f] == "True")
    return row


def _estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float | None:
    rates = PRICING.get(model)
    if rates is None:
        return None
    return (
        (input_tokens  / 1_000_000) * rates["input"]
        + (output_tokens / 1_000_000) * rates["output"]
    )


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "models": _TRAINED_MODELS}


@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest) -> PredictResponse:
    feature_row = _build_feature_row(req.prompt)

    # Build a DataFrame with one row per trained model (same layout as training)
    X = pd.DataFrame(
        [{**feature_row, "model": m} for m in _TRAINED_MODELS]
    )[["model"] + FEATURE_ORDER]

    input_preds  = np.clip(_input_model.predict(X),  a_min=0, a_max=None)
    output_preds = np.clip(_output_model.predict(X), a_min=0, a_max=None)
    quality_preds = _quality_model.predict(X).ravel()

    predictions: list[ModelPrediction] = []
    for i, model_name in enumerate(_TRAINED_MODELS):
        in_tok  = int(round(float(input_preds[i])))
        out_tok = int(round(float(output_preds[i])))
        qlabel  = str(quality_preds[i])
        qscore  = QUALITY_SCORE.get(qlabel, 5)
        cost    = _estimate_cost(model_name, in_tok, out_tok)

        predictions.append(ModelPrediction(
            model         = model_name,
            input_tokens  = in_tok,
            output_tokens = out_tok,
            cost_usd      = round(cost, 6) if cost is not None else None,
            quality_label = qlabel,
            quality_score = qscore,
        ))

    # Sort: detected model first (if any), then by ascending cost
    if req.detected_model:
        predictions.sort(
            key=lambda p: (0 if p.model == req.detected_model else 1, p.cost_usd or 0)
        )
    else:
        predictions.sort(key=lambda p: p.cost_usd or 0)

    return PredictResponse(
        predictions=predictions,
        features=feature_row,
    )


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest) -> AnalyzeResponse:
    """Analyze a completed exchange using real (browser-measured) token counts.

    The quality predictor is still run from prompt features — quality is a
    property of the prompt, not the response text — but the token counts and
    cost come from what was actually observed in the browser.

    Falls back to a character/4 approximation if the browser did not send
    token counts.
    """
    feature_row = _build_feature_row(req.prompt)

    # Use measured counts when available, else estimate (chars / 4 is a rough
    # but widely-used approximation for English text at ~4 chars/token).
    token_source = "measured"
    if req.input_tokens is not None and req.output_tokens is not None:
        in_tok_base  = req.input_tokens
        out_tok_base = req.output_tokens
    else:
        token_source = "estimated"
        in_tok_base  = max(1, len(req.prompt)   // 4)
        out_tok_base = max(1, len(req.response) // 4)

    # Run quality predictor for each trained model
    X = pd.DataFrame(
        [{**feature_row, "model": m} for m in _TRAINED_MODELS]
    )[["model"] + FEATURE_ORDER]
    quality_preds = _quality_model.predict(X).ravel()

    results: list[AnalysisResult] = []
    for i, model_name in enumerate(_TRAINED_MODELS):
        qlabel = str(quality_preds[i])
        qscore = QUALITY_SCORE.get(qlabel, 5)
        cost   = _estimate_cost(model_name, in_tok_base, out_tok_base)

        results.append(AnalysisResult(
            model        = model_name,
            input_tokens = in_tok_base,
            output_tokens= out_tok_base,
            cost_usd     = round(cost, 6) if cost is not None else None,
            quality_label= qlabel,
            quality_score= qscore,
            token_source = token_source,
        ))

    # Sort: detected model first, then by cost
    if req.detected_model:
        results.sort(
            key=lambda r: (0 if r.model == req.detected_model else 1, r.cost_usd or 0)
        )
    else:
        results.sort(key=lambda r: r.cost_usd or 0)

    return AnalyzeResponse(results=results, features=feature_row)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=5050, log_level="warning")

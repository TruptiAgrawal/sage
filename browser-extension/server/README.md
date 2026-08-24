# SAGE Browser Extension — Server

A minimal FastAPI server that loads the trained CatBoost models and exposes
a `/predict` endpoint for the browser extension.

## Requirements

Dependencies are declared in the root `pyproject.toml` (catboost, fastapi,
uvicorn, numpy, pandas). No extra install needed if you already use `uv` for
the main pipeline.

## Start the server

```bash
# From the repo root:
uv run python browser-extension/server/server.py
```

The server starts on **http://localhost:5050**.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Returns `{"status":"ok","models":[...]}` |
| POST | `/predict` | Returns token/cost/quality predictions |

### POST /predict

Request body (JSON):

```json
{
  "prompt": "Explain quantum computing in simple terms",
  "detected_model": "claude-opus-4-8"
}
```

`detected_model` is optional. When provided the matching row is sorted first
in the response so the extension can highlight it.

Response (JSON):

```json
{
  "predictions": [
    {
      "model": "claude-opus-4-8",
      "input_tokens": 8,
      "output_tokens": 143,
      "cost_usd": 0.003615,
      "quality_label": "Good",
      "quality_score": 7
    },
    ...
  ],
  "features": {
    "char_count": 42,
    "word_count": 7,
    ...
  }
}
```

## Quality score mapping

| Label | Score (1-10) |
|-------|-------------|
| Bad | 2 |
| Average | 5 |
| Good | 7 |
| Excellent | 9 |

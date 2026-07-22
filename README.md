# SAGE — Smart Advisor for Generative modEls

Predicting LLM token usage and response quality from prompt features, and
estimating the token/cost/quality tradeoff across models for a given prompt.

Goal, for any input prompt:

| Model  | Input Tok | Output Tok | Cost  | Quality   |
| ------ | --------- | ---------- | ----- | --------- |
| Claude | 1800      | 300        | $0.60 | Average   |
| llama3 | 1900      | 350        | $2.50 | Good      |
| Groq   | 2000      | 420        | $5.60 | Excellent |

## Pipeline

Each phase reads the previous phase's output and writes its own; earlier
files are never modified in place.

1. **Raw data** — `dataset/raw_datasets/dataset{1..6}.csv`, one file per
   model: `Model Name, Prompt, Input Tokens, Output Tokens, Quality, Feedback`.
2. **Clean** — `dataset/clean_datasets.py` dedupes, drops rows with
   missing/invalid token counts, standardizes labels -> `dataset/cleaned/*.csv`.
3. **Feature engineering** — `dataset/feature_engineering.py` derives
   structural/semantic features from prompt text (length, code/JSON/markdown
   detection, reasoning/creative/tool-use/RAG heuristics, etc.) ->
   `dataset/cleaned/*_features.csv`.
4. **Merge** — `dataset/merge_datasets.py` joins all per-model feature
   files on prompt text -> `dataset/merged/merged_long.csv` (one row per
   prompt+model) and `merged_wide.csv` (one row per prompt, columns per model).
5. **Targets** — `dataset/prepare_targets.py` splits `merged_long.csv` into
   the two prediction tasks -> `dataset/merged/model_a_token_predictor.csv`
   (X: prompt features + model name, y: input/output tokens) and
   `model_b_quality_predictor.csv` (X: same, y: quality label). Rows for
   `llama3` and `opencode/big-pickle` are excluded here — their logged
   token counts don't track prompt length like every other model, pointing
   to a collection bug rather than real signal.
6. **Train** — two model families trained on the same X/y for comparison:
   - `dataset/train_token_predictor.py` / `train_quality_predictor.py` —
     RandomForest baselines (one-hot encoded categoricals), saved to
     `models/*.joblib`.
   - `models/catboost/train_token_predictor_catboost.py` /
     `train_quality_predictor_catboost.py` — CatBoost variants (native
     categorical handling), saved to `models/catboost/*.cbm`.

Run phases in order from `dataset/`:

```bash
python clean_datasets.py
python feature_engineering.py
python merge_datasets.py
python prepare_targets.py
python train_token_predictor.py
python train_quality_predictor.py
python ../models/catboost/train_token_predictor_catboost.py
python ../models/catboost/train_quality_predictor_catboost.py
```

## Layout

```
dataset/            pipeline scripts + data at each phase (raw_datasets -> cleaned -> merged)
models/             trained model artifacts (RandomForest .joblib, CatBoost .cbm) + CatBoost training scripts
prompts/            held-out prompt lists used to generate/test data
experiments/trial1/ early static token-counting + pricing prototype (superseded)
experiments/trial2/ agent-loop token tracer + response/chat analysis prototype (superseded)
```

`experiments/` holds earlier prototypes kept for reference; the active
pipeline is `dataset/` + `models/`.

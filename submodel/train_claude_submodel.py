#!/usr/bin/env python3
"""Train a Claude-only sub-model: token predictor + quality predictor fit
exclusively on dataset/raw_datasets/dataset6.csv (claude-opus-4-8 rows).

Unlike the main pipeline (dataset/*.py, models/*), this never merges in the
other five raw datasets, so there's no "model" categorical column to encode
-- every row is the same model. Trades the cross-model comparison table for
a predictor specialized to Claude's token/quality behavior.

Reuses dataset/clean_datasets.py's cleaning rules and
dataset/feature_engineering.py's prompt feature extraction so the submodel
stays consistent with the main pipeline's definitions; only the training
scope (dataset6 only) differs.

Writes:
  submodel/data/dataset6_prepared.csv  - cleaned rows + engineered features
  submodel/models/token_predictor.joblib
  submodel/models/quality_predictor.joblib
  submodel/results/token_predictor.json
  submodel/results/quality_predictor.json
"""

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    r2_score,
    root_mean_squared_error,
)
from sklearn.model_selection import train_test_split

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "dataset"))
from clean_datasets import standardize_quality  # noqa: E402
from feature_engineering import extract_features  # noqa: E402

RAW_PATH = HERE.parent / "dataset" / "raw_datasets" / "dataset6.csv"
DATA_DIR = HERE / "data"
MODEL_DIR = HERE / "models"
RESULTS_DIR = HERE / "results"

NUMERIC_FEATURES = [
    "char_count", "word_count", "line_count", "sentence_count",
    "unique_words", "avg_word_length", "prompt_depth",
]
BOOL_FEATURES = [
    "has_code", "has_json", "has_markdown", "has_math", "has_xml",
    "reasoning_prompt", "creative_prompt", "tool_usage_prompt", "rag_prompt",
]
X_FIELDS = NUMERIC_FEATURES + BOOL_FEATURES
TOKEN_TARGETS = ["input_tokens", "output_tokens"]
QUALITY_TARGET = "quality"
CLASS_ORDER = ["Bad", "Average", "Good", "Excellent"]


def load_and_clean() -> pd.DataFrame:
    """Same rules as dataset/clean_datasets.py: dedupe, drop bad token
    counts, standardize quality labels. dataset6.csv carries an extra
    'Response' column the other raw datasets don't have; it's unused here."""
    seen = set()
    rows = []
    with open(RAW_PATH, newline="", encoding="utf-8", errors="replace") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            prompt = row["Prompt"].strip()
            input_tokens = row["Input Tokens"].strip()
            output_tokens = row["Output Tokens"].strip()
            quality_raw = row["Quality"]

            key = (prompt, input_tokens, output_tokens, quality_raw.strip())
            if key in seen:
                continue
            seen.add(key)

            if not (input_tokens.isdigit() and output_tokens.isdigit()):
                continue
            if int(input_tokens) <= 0 or int(output_tokens) <= 0:
                continue

            quality = standardize_quality(quality_raw)
            if quality is None:
                continue

            rows.append({
                "prompt": prompt,
                "input_tokens": int(input_tokens),
                "output_tokens": int(output_tokens),
                "quality": quality,
            })

    df = pd.DataFrame(rows)
    features = df["prompt"].apply(extract_features).apply(pd.Series)
    for c in BOOL_FEATURES:
        features[c] = features[c] == "True"
    df = pd.concat([df, features], axis=1)

    DATA_DIR.mkdir(exist_ok=True)
    df.to_csv(DATA_DIR / "dataset6_prepared.csv", index=False)
    return df


def train_token_predictor(df: pd.DataFrame) -> dict:
    X = df[X_FIELDS]
    y = df[TOKEN_TARGETS]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = RandomForestRegressor(n_estimators=300, min_samples_leaf=2, random_state=42, n_jobs=-1)
    model.fit(X_train, y_train)

    preds = np.clip(model.predict(X_test), a_min=0, a_max=None)

    print(f"\n[token predictor] train rows: {len(X_train)}  test rows: {len(X_test)}")
    print(f"{'Target':<15}{'MAE':>10}{'RMSE':>10}{'R2':>10}")
    metrics = {}
    for i, target in enumerate(TOKEN_TARGETS):
        mae = mean_absolute_error(y_test[target], preds[:, i])
        rmse = root_mean_squared_error(y_test[target], preds[:, i])
        r2 = r2_score(y_test[target], preds[:, i])
        print(f"{target:<15}{mae:>10.2f}{rmse:>10.2f}{r2:>10.3f}")
        metrics[target] = {"mae": mae, "rmse": rmse, "r2": r2}

    top = sorted(zip(X_FIELDS, model.feature_importances_), key=lambda t: -t[1])[:8]
    print("Top features:")
    for name, imp in top:
        print(f"  {name:<20}{imp:.3f}")

    MODEL_DIR.mkdir(exist_ok=True)
    joblib.dump(model, MODEL_DIR / "token_predictor.joblib")

    RESULTS_DIR.mkdir(exist_ok=True)
    result = {
        "model_type": "random_forest",
        "task": "token_predictor",
        "scope": "dataset6.csv (claude-opus-4-8 only)",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "train_rows": len(X_train),
        "test_rows": len(X_test),
        "metrics": metrics,
        "top_features": [{"name": n, "importance": float(i)} for n, i in top],
    }
    (RESULTS_DIR / "token_predictor.json").write_text(json.dumps(result, indent=2))
    return result


def train_quality_predictor(df: pd.DataFrame) -> dict:
    X = df[X_FIELDS]
    y = df[QUALITY_TARGET]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = RandomForestClassifier(
        n_estimators=300, min_samples_leaf=2, class_weight="balanced", random_state=42, n_jobs=-1,
    )
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    labels = [c for c in CLASS_ORDER if c in set(y)]

    acc = float((preds == y_test).mean())
    macro_f1 = f1_score(y_test, preds, labels=labels, average="macro", zero_division=0)
    report = classification_report(y_test, preds, labels=labels, zero_division=0, output_dict=True)
    cm = confusion_matrix(y_test, preds, labels=labels)

    print(f"\n[quality predictor] train rows: {len(X_train)}  test rows: {len(X_test)}")
    print(f"Accuracy: {acc:.3f}  Macro-F1: {macro_f1:.3f}")
    print(classification_report(y_test, preds, labels=labels, zero_division=0))

    top = sorted(zip(X_FIELDS, model.feature_importances_), key=lambda t: -t[1])[:8]
    print("Top features:")
    for name, imp in top:
        print(f"  {name:<20}{imp:.3f}")

    MODEL_DIR.mkdir(exist_ok=True)
    joblib.dump(model, MODEL_DIR / "quality_predictor.joblib")

    RESULTS_DIR.mkdir(exist_ok=True)
    result = {
        "model_type": "random_forest",
        "task": "quality_predictor",
        "scope": "dataset6.csv (claude-opus-4-8 only)",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "train_rows": len(X_train),
        "test_rows": len(X_test),
        "accuracy": acc,
        "macro_f1": macro_f1,
        "classification_report": report,
        "confusion_matrix": {"labels": labels, "matrix": cm.tolist()},
        "top_features": [{"name": n, "importance": float(i)} for n, i in top],
    }
    (RESULTS_DIR / "quality_predictor.json").write_text(json.dumps(result, indent=2))
    return result


def main():
    df = load_and_clean()
    print(f"Loaded {len(df)} cleaned rows from {RAW_PATH}")
    print("Quality distribution:")
    print(df["quality"].value_counts().to_string())

    train_token_predictor(df)
    train_quality_predictor(df)

    print(f"\nSaved models to {MODEL_DIR}/")
    print(f"Saved metrics to {RESULTS_DIR}/")


if __name__ == "__main__":
    main()

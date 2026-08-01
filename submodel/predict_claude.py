#!/usr/bin/env python3
"""Predict tokens, cost, and quality for a prompt using the Claude-only
sub-model trained by train_claude_submodel.py.

Usage:
    python submodel/predict_claude.py "Write a poem about the ocean"
"""

import argparse
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "dataset"))
from feature_engineering import extract_features  # noqa: E402

MODEL_DIR = HERE / "models"

NUMERIC_FEATURES = [
    "char_count", "word_count", "line_count", "sentence_count",
    "unique_words", "avg_word_length", "prompt_depth",
]
BOOL_FEATURES = [
    "has_code", "has_json", "has_markdown", "has_math", "has_xml",
    "reasoning_prompt", "creative_prompt", "tool_usage_prompt", "rag_prompt",
]
FEATURE_ORDER = NUMERIC_FEATURES + BOOL_FEATURES

# claude-opus-4-8 pricing, $ per 1M tokens -- edit to match real rates.
PRICING = {"input": 15.00, "output": 75.00}


def build_feature_row(prompt: str) -> dict:
    features = extract_features(prompt)
    row = {f: features[f] for f in NUMERIC_FEATURES}
    for f in BOOL_FEATURES:
        row[f] = int(features[f] == "True")
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("prompt", help="Prompt text to estimate tokens/cost/quality for")
    args = parser.parse_args()

    token_model = joblib.load(MODEL_DIR / "token_predictor.joblib")
    quality_model = joblib.load(MODEL_DIR / "quality_predictor.joblib")

    row = build_feature_row(args.prompt)
    X = pd.DataFrame([row])[FEATURE_ORDER]

    input_tokens, output_tokens = np.clip(token_model.predict(X)[0], a_min=0, a_max=None)
    quality = quality_model.predict(X)[0]

    input_tokens, output_tokens = int(round(input_tokens)), int(round(output_tokens))
    cost = (input_tokens / 1_000_000) * PRICING["input"] + (output_tokens / 1_000_000) * PRICING["output"]

    print(f"{'Model':<20}{'Input Tok':>10}{'Output Tok':>12}{'Cost':>10}{'Quality':>12}")
    print(f"{'claude-opus-4-8':<20}{input_tokens:>10}{output_tokens:>12}{f'${cost:.4f}':>10}{quality:>12}")


if __name__ == "__main__":
    main()

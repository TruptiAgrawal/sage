#!/usr/bin/env python3
"""Phase 3 - Feature Engineering: turn raw prompt text into structured features.

Reads cleaned/dataset1.csv..dataset6.csv (output of clean_datasets.py) and
writes cleaned/dataset*_features.csv with the original columns plus the
engineered feature columns below. Does not modify the cleaned/*.csv inputs.

6.1 Basic:      char_count, word_count, line_count, sentence_count
6.2 Complexity: unique_words, avg_word_length, prompt_depth
6.3 Structural: has_code, has_json, has_markdown, has_math, has_xml
6.4 Semantic:   reasoning_prompt, creative_prompt, tool_usage_prompt, rag_prompt

Embedding features (6.5) are intentionally skipped: at ~1.6k rows they add
API/dependency cost for little benefit. Revisit if the dataset grows or you
need semantic similarity/clustering.
"""

import csv
import re
from pathlib import Path

HERE = Path(__file__).parent
IN_DIR = HERE / "cleaned"
OUT_DIR = HERE / "cleaned"

SOURCE_FILES = [
    "dataset1.csv",
    "dataset2.csv",
    "dataset3.csv",
    "dataset4.csv",
    "dataset5.csv",
    "dataset6.csv",
]

SENTENCE_SPLIT_RE = re.compile(r"[.!?]+(?:\s|$)")
WORD_RE = re.compile(r"[A-Za-z0-9']+")

CODE_RE = re.compile(r"```|`[^`]+`|\bdef \w+\(|\bfunction \w+\(|\bclass \w+[:({]")
JSON_RE = re.compile(r"\{[^{}]*\"[^\"]+\"\s*:")
MARKDOWN_RE = re.compile(r"(^|\n)\s*#{1,6}\s|(^|\n)\s*[-*]\s|\*\*[^*]+\*\*|\[[^\]]+\]\([^)]+\)")
MATH_RE = re.compile(r"\\frac|\$\$|\\sum|\\int|[=+\-*/^]\s*\d|\b\d+\s*[+\-*/^]\s*\d+\b")
XML_RE = re.compile(r"</?[a-zA-Z][\w:-]*\s*/?>")

REASONING_WORDS = re.compile(
    r"\b(why|how|explain|reason|because|analyze|derive|prove|step[- ]by[- ]step|think through|logic)\b",
    re.IGNORECASE,
)
CREATIVE_WORDS = re.compile(
    r"\b(story|poem|imagine|write a|creative|fictional|as if you're|as if you are|narrator|knight|metaphor)\b",
    re.IGNORECASE,
)
TOOL_USAGE_WORDS = re.compile(
    r"\b(call the|use the tool|api|function call|invoke|execute|run the|tool_use|search the web|query the)\b",
    re.IGNORECASE,
)
RAG_WORDS = re.compile(
    r"\b(according to|based on the (document|context|following)|retrieved|given the (context|passage|text)|cite|source[sd]?:)\b",
    re.IGNORECASE,
)


def bool_str(v: bool) -> str:
    return "True" if v else "False"


def prompt_depth(prompt: str) -> int:
    """Max nesting depth across (), [], {} — proxy for structural/logical nesting."""
    pairs = {")": "(", "]": "[", "}": "{"}
    openers = set(pairs.values())
    depth = 0
    max_depth = 0
    for ch in prompt:
        if ch in openers:
            depth += 1
            max_depth = max(max_depth, depth)
        elif ch in pairs:
            depth = max(0, depth - 1)
    return max_depth


def extract_features(prompt: str) -> dict:
    words = WORD_RE.findall(prompt)
    word_count = len(words)
    unique_words = len(set(w.lower() for w in words))
    avg_word_length = round(sum(len(w) for w in words) / word_count, 2) if word_count else 0.0

    lines = prompt.splitlines() or [prompt]
    sentences = [s for s in SENTENCE_SPLIT_RE.split(prompt) if s.strip()]

    return {
        "char_count": len(prompt),
        "word_count": word_count,
        "line_count": len(lines),
        "sentence_count": max(len(sentences), 1 if prompt.strip() else 0),
        "unique_words": unique_words,
        "avg_word_length": avg_word_length,
        "prompt_depth": prompt_depth(prompt),
        "has_code": bool_str(bool(CODE_RE.search(prompt))),
        "has_json": bool_str(bool(JSON_RE.search(prompt))),
        "has_markdown": bool_str(bool(MARKDOWN_RE.search(prompt))),
        "has_math": bool_str(bool(MATH_RE.search(prompt))),
        "has_xml": bool_str(bool(XML_RE.search(prompt))),
        "reasoning_prompt": bool_str(bool(REASONING_WORDS.search(prompt))),
        "creative_prompt": bool_str(bool(CREATIVE_WORDS.search(prompt))),
        "tool_usage_prompt": bool_str(bool(TOOL_USAGE_WORDS.search(prompt))),
        "rag_prompt": bool_str(bool(RAG_WORDS.search(prompt))),
    }


FEATURE_FIELDS = [
    "char_count", "word_count", "line_count", "sentence_count",
    "unique_words", "avg_word_length", "prompt_depth",
    "has_code", "has_json", "has_markdown", "has_math", "has_xml",
    "reasoning_prompt", "creative_prompt", "tool_usage_prompt", "rag_prompt",
]


def process_file(filename: str) -> int:
    in_path = IN_DIR / filename
    with open(in_path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        base_fields = reader.fieldnames
        rows = list(reader)

    out_rows = []
    for row in rows:
        features = extract_features(row["Prompt"])
        merged = dict(row)
        merged.update(features)
        out_rows.append(merged)

    out_path = OUT_DIR / filename.replace(".csv", "_features.csv")
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=base_fields + FEATURE_FIELDS)
        writer.writeheader()
        writer.writerows(out_rows)

    return len(out_rows)


def main():
    total = 0
    for f in SOURCE_FILES:
        n = process_file(f)
        total += n
        print(f"{f} -> {f.replace('.csv', '_features.csv')} ({n} rows, {len(FEATURE_FIELDS)} features added)")
    print(f"\nTotal rows processed: {total}")


if __name__ == "__main__":
    main()

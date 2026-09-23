#!/usr/bin/env python3
"""Ingest 10,000 prompts from ~/Downloads/prompts -> dataset/raw_datasets/dataset10.csv

The prompts file has one prompt per line, optionally prefixed with "N. " numbering.
Since we don't have real LLM responses for these prompts, we:
  1. Estimate input tokens  (~3.46 chars/token, calibrated against existing data)
  2. Assign quality labels  (heuristic based on prompt complexity features,
                             matching the distribution in the existing 1,800-row corpus)
  3. Estimate output tokens (sampled from per-quality distributions observed in data)

This is synthetic annotation — the estimates are principled but not ground truth.
The file is written in the standard SAGE schema:
    Model Name, Prompt, Input Tokens, Output Tokens, Quality, Feedback

We use "GPT-4o" as the synthetic model name so the downstream pipeline
treats this dataset as a new model and it gets its own model coefficient
in the token/quality predictors.
"""

import csv
import math
import re
import random
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

INPUT_FILE   = Path.home() / "Downloads" / "prompts"
OUTPUT_FILE  = Path(__file__).parent / "raw_datasets" / "dataset10.csv"
MODEL_NAME   = "GPT-4o"
RANDOM_SEED  = 42

# Calibrated from existing merged data: avg chars / avg input_tokens
CHARS_PER_TOKEN = 3.46

# Output token distributions per quality bucket (from existing corpus analysis)
# Each tuple is (mean, std_dev, min, max)
OUTPUT_DIST = {
    "Bad":       (241,  300,  10,  800),
    "Average":   (258,  280,  20, 1200),
    "Good":      (257,  290,  20, 1500),
    "Excellent": (131,  120,  25,  600),
}

# ── Feature extraction (mirrors feature_engineering.py) ──────────────────────

SENTENCE_SPLIT_RE = re.compile(r"[.!?]+(?:\s|$)")
WORD_RE = re.compile(r"[A-Za-z0-9']+")

CODE_RE      = re.compile(r"```|`[^`]+`|\bdef \w+\(|\bfunction \w+\(|\bclass \w+[:({]")
JSON_RE      = re.compile(r"\{[^{}]*\"[^\"]+\"\s*:")
MARKDOWN_RE  = re.compile(r"(^|\n)\s*#{1,6}\s|(^|\n)\s*[-*]\s|\*\*[^*]+\*\*|\[[^\]]+\]\([^)]+\)")
MATH_RE      = re.compile(r"\\frac|\$\$|\\sum|\\int|[=+\-*/^]\s*\d|\b\d+\s*[+\-*/^]\s*\d+\b")
XML_RE       = re.compile(r"</?[a-zA-Z][\w:-]*\s*/?>")

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

TYPO_RE = re.compile(
    r"\b(wat |wats |teh |taht |recieve|occured|seperate|definately|accomodate|wierd|"
    r"reccomend|adress|beleive|untill|occurance|independant|payed)\b",
    re.IGNORECASE,
)

VAGUE_SHORT_RE = re.compile(
    r"^(what is|tell me about|explain|describe|define|give me|how does|why is)\s+\w[\w\s]{0,30}[?.]?$",
    re.IGNORECASE,
)


def compute_complexity(prompt: str) -> tuple[float, dict]:
    """Return (complexity_score, feature_dict) for a prompt."""
    words = WORD_RE.findall(prompt)
    word_count = len(words)
    unique_words = len(set(w.lower() for w in words))
    avg_wl = sum(len(w) for w in words) / word_count if word_count else 0.0

    has_code     = bool(CODE_RE.search(prompt))
    has_json     = bool(JSON_RE.search(prompt))
    has_markdown = bool(MARKDOWN_RE.search(prompt))
    has_math     = bool(MATH_RE.search(prompt))
    has_xml      = bool(XML_RE.search(prompt))
    is_reasoning = bool(REASONING_WORDS.search(prompt))
    is_creative  = bool(CREATIVE_WORDS.search(prompt))
    is_tool      = bool(TOOL_USAGE_WORDS.search(prompt))
    is_rag       = bool(RAG_WORDS.search(prompt))
    has_typos    = bool(TYPO_RE.search(prompt))
    is_vague     = bool(VAGUE_SHORT_RE.match(prompt.strip())) and word_count < 10

    complexity = min(len(prompt) / 500.0, 1.0)
    complexity += 0.20 * has_code
    complexity += 0.10 * has_json
    complexity += 0.10 * has_markdown
    complexity += 0.15 * has_math
    complexity += 0.15 * is_reasoning
    complexity += 0.10 * is_creative
    complexity += 0.10 * is_tool
    complexity += 0.10 * is_rag
    # penalise vague/typo-heavy prompts
    complexity -= 0.20 * has_typos
    complexity -= 0.15 * is_vague
    complexity = max(0.0, round(complexity, 4))

    feats = {
        "word_count": word_count,
        "char_count": len(prompt),
        "unique_words": unique_words,
        "avg_word_length": round(avg_wl, 2),
        "has_code": has_code,
        "has_json": has_json,
        "has_markdown": has_markdown,
        "has_math": has_math,
        "has_xml": has_xml,
        "is_reasoning": is_reasoning,
        "is_creative": is_creative,
        "is_tool": is_tool,
        "is_rag": is_rag,
        "has_typos": has_typos,
        "is_vague": is_vague,
    }
    return complexity, feats


def assign_quality(complexity: float, feats: dict) -> str:
    """Heuristic quality assignment targeting this distribution:
        Bad ~15%, Average ~25%, Good ~35%, Excellent ~25%

    Quality is determined primarily by structural/semantic signals (code,
    math, reasoning keywords, constraints, role framing) rather than raw
    length, which inflated the Excellent bucket when using complexity alone.
    """
    char_count   = feats["char_count"]
    word_count   = feats["word_count"]
    has_typos    = feats["has_typos"]
    is_vague     = feats["is_vague"]
    has_code     = feats["has_code"]
    has_math     = feats["has_math"]
    has_json     = feats["has_json"]
    is_reasoning = feats["is_reasoning"]
    is_creative  = feats["is_creative"]
    is_tool      = feats["is_tool"]
    is_rag       = feats["is_rag"]

    # Count semantic/structural signals (independent of length)
    structural_signals = sum([has_code, has_math, has_json, is_reasoning,
                               is_creative, is_tool, is_rag])

    # Bad: typo-heavy, very short/vague, or single-word / near-empty
    if has_typos or is_vague or word_count < 4 or (char_count < 25 and not structural_signals):
        return "Bad"

    # Excellent: needs ≥2 structural/semantic signals regardless of length,
    # OR ≥3 signals alone (e.g. a dense technical prompt that's still short).
    # Raw length without signals is NOT enough for Excellent — it just means Good.
    if structural_signals >= 3 or (structural_signals >= 2 and char_count > 150):
        return "Excellent"

    # Good: one structural signal OR a well-formed medium-length prompt
    if structural_signals >= 1 or (char_count > 80 and word_count > 12):
        return "Good"

    # Average: everything else (short but grammatical, generic questions)
    return "Average"


def estimate_input_tokens(prompt: str) -> int:
    """Estimate input tokens from character count (calibrated ratio 3.46 chars/tok)."""
    tokens = max(1, round(len(prompt) / CHARS_PER_TOKEN))
    return tokens


def estimate_output_tokens(quality: str, rng: random.Random) -> int:
    """Sample output token count from the per-quality normal distribution."""
    mean, std, lo, hi = OUTPUT_DIST[quality]
    val = rng.gauss(mean, std)
    return max(lo, min(hi, round(val)))


def generate_feedback(quality: str, feats: dict) -> str:
    """Generate a brief feedback string matching the quality label."""
    char_count  = feats["char_count"]
    has_code    = feats["has_code"]
    has_math    = feats["has_math"]
    is_reasoning = feats["is_reasoning"]
    has_typos   = feats["has_typos"]
    is_vague    = feats["is_vague"]

    if quality == "Bad":
        if has_typos:
            return "Prompt contains spelling errors and lacks clarity."
        if is_vague:
            return "Prompt is too vague; lacks specificity and context."
        return "Prompt is too short and underspecified."

    if quality == "Average":
        if char_count < 60:
            return "Prompt is functional but brief; adding context would improve results."
        return "Prompt communicates the goal but lacks structure or constraints."

    if quality == "Good":
        if has_code:
            return "Well-structured prompt with code context; clear objective."
        if is_reasoning:
            return "Clear reasoning-oriented prompt with good specificity."
        return "Prompt is clear and well-defined with a specific goal."

    # Excellent
    if has_math:
        return "Highly structured prompt with mathematical precision and clear constraints."
    if has_code:
        return "Excellent technical prompt with full context and detailed requirements."
    return "Comprehensive, well-scoped prompt with clear constraints and expected output format."


# ── Main ──────────────────────────────────────────────────────────────────────

def parse_prompts(path: Path) -> list[str]:
    """Read prompts file and strip leading numbering."""
    NUMBER_RE = re.compile(r"^\d+\.\s*")
    prompts = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            # Strip leading "N. " numbering
            line = NUMBER_RE.sub("", line).strip()
            if line:
                prompts.append(line)
    return prompts


def main():
    rng = random.Random(RANDOM_SEED)

    print(f"Reading prompts from: {INPUT_FILE}")
    prompts = parse_prompts(INPUT_FILE)
    print(f"Parsed {len(prompts):,} prompts")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    quality_counts = {"Bad": 0, "Average": 0, "Good": 0, "Excellent": 0}

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["Model Name", "Prompt", "Input Tokens", "Output Tokens", "Quality", "Feedback"],
        )
        writer.writeheader()

        for prompt in prompts:
            complexity, feats = compute_complexity(prompt)
            quality    = assign_quality(complexity, feats)
            in_tokens  = estimate_input_tokens(prompt)
            out_tokens = estimate_output_tokens(quality, rng)
            feedback   = generate_feedback(quality, feats)

            quality_counts[quality] += 1
            writer.writerow({
                "Model Name":    MODEL_NAME,
                "Prompt":        prompt,
                "Input Tokens":  in_tokens,
                "Output Tokens": out_tokens,
                "Quality":       quality,
                "Feedback":      feedback,
            })

    total = len(prompts)
    print(f"\nWrote {total:,} rows -> {OUTPUT_FILE}")
    print("\nQuality distribution:")
    for q in ["Bad", "Average", "Good", "Excellent"]:
        n = quality_counts[q]
        print(f"  {q:10s}: {n:5d}  ({100*n/total:.1f}%)")


if __name__ == "__main__":
    main()

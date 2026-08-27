#!/usr/bin/env python3
"""Clean per-model CSVs in dataset/raw_datasets/ (dataset1.csv..dataset6.csv).

For each source file, writes a cleaned copy to cleaned/<name>.csv after:
  - Removing exact duplicate rows
  - Dropping rows with missing/invalid token counts (can't be imputed)
  - Standardizing quality labels (title case, trimmed)
  - Standardizing model names (trimmed, consistent form)
  - Ensuring token counts are valid positive integers

Does not modify the source dataset*.csv files. Prints a per-file summary
of what was removed/changed.
"""

import csv
from pathlib import Path

HERE = Path(__file__).parent
RAW_DIR = HERE / "raw_datasets"
OUT_DIR = HERE / "cleaned"

SOURCE_FILES = [
    "dataset1.csv",
    "dataset2.csv",
    "dataset3.csv",
    "dataset4.csv",
    "dataset5.csv",
    "dataset6.csv",
    "dataset7.csv",   # ChatGPT GPT-5.5  (TSV, Quality Category column)
    "dataset8.csv",   # Gemini variants   (CSV, lowercase headers, extra response col)
    "dataset9.csv",   # Perplexity        (CSV, has "Okay" quality label + corrupt rows)
]

FIELDNAMES = ["Model Name", "Prompt", "Input Tokens", "Output Tokens", "Quality", "Feedback"]

VALID_QUALITY = {"bad", "average", "good", "excellent"}

# "Okay" appears in dataset9 as a synonym for Average
QUALITY_ALIAS = {"okay": "average"}

# Canonical spelling for model names seen across files (trim whitespace only;
# no case variants existed in the source data, but this map lets future
# variants be normalized in one place).
MODEL_NAME_MAP = {
    "groq-llama-3.3-70b-versatile": "Groq-llama-3.3-70b-versatile",
    "deepseek-reasoner": "deepseek-reasoner",
    "llama3": "llama3",
    "deepseek v4 flash": "DeepSeek V4 Flash",
    "opencode/big-pickle": "opencode/big-pickle",
    "claude-opus-4-8": "claude-opus-4-8",
    # dataset7
    "chatgpt gpt-5.5": "ChatGPT GPT-5.5",
    # dataset8 (10 gemini variants — normalise to lowercase base names)
    "gemini-1.5-flash": "gemini-1.5-flash",
    "gemini-1.5-pro": "gemini-1.5-pro",
    "gemini-2.0-flash": "gemini-2.0-flash",
    "gemini-2.0-pro": "gemini-2.0-pro",
    "gemini-2.5-flash": "gemini-2.5-flash",
    "gemini-2.5-pro": "gemini-2.5-pro",
    "gemini-3.1-pro": "gemini-3.1-pro",
    "gemini-3.5-flash": "gemini-3.5-flash",
    "gemini-3.5-pro": "gemini-3.5-pro",
    "gemini-3.6-flash": "gemini-3.6-flash",
    # dataset9
    "perplexity": "Perplexity",
}


def standardize_quality(raw: str) -> str | None:
    q = raw.strip().lower()
    # map aliases first (e.g. "okay" -> "average")
    q = QUALITY_ALIAS.get(q, q)
    if q not in VALID_QUALITY:
        return None
    return q.capitalize()


def standardize_model(raw: str) -> str:
    m = raw.strip()
    return MODEL_NAME_MAP.get(m.lower(), m)


def _numeric_quality_to_label(score_str: str) -> str | None:
    """Map a float quality score (dataset6) to a label category.

    Buckets: <4 -> Bad, 4-6 -> Average, 6-8 -> Good, >8 -> Excellent.
    Returns None if the value is not a valid number.
    """
    try:
        score = float(score_str.strip())
    except ValueError:
        return None
    if score < 4.0:
        return "Bad"
    if score < 6.0:
        return "Average"
    if score <= 8.0:
        return "Good"
    return "Excellent"


def _detect_dialect(filename: str, path: Path) -> tuple[str, dict, bool]:
    """Return (separator, column_name_mapping, numeric_quality) for a source file.

    dataset6.csv  — CSV, extra Response column, numeric quality (1-10 float)
    dataset7.csv  — TSV, uses 'Quality Category' instead of 'Quality'
    dataset8.csv  — CSV, all lowercase headers, extra 'response' column
    dataset9.csv  — CSV, uses 'Model' instead of 'Model Name'
    all others    — CSV, standard FIELDNAMES
    """
    if filename == "dataset6.csv":
        return ",", {"Model Name": "Model Name", "Prompt": "Prompt",
                     "Input Tokens": "Input Tokens", "Output Tokens": "Output Tokens",
                     "Quality": "Quality", "Feedback": None}, True
    if filename == "dataset7.csv":
        return "\t", {"Model Name": "Model Name", "Prompt": "Prompt",
                      "Input Tokens": "Input Tokens", "Output Tokens": "Output Tokens",
                      "Quality": "Quality Category", "Feedback": "Feedback"}, False
    if filename == "dataset8.csv":
        return ",", {"Model Name": "model", "Prompt": "prompt",
                     "Input Tokens": "input_tokens", "Output Tokens": "output_tokens",
                     "Quality": "quality", "Feedback": "feedback"}, False
    if filename == "dataset9.csv":
        return ",", {"Model Name": "Model", "Prompt": "Prompt",
                     "Input Tokens": "Input Tokens", "Output Tokens": "Output Tokens",
                     "Quality": "Quality", "Feedback": "Feedback"}, False
    return ",", {"Model Name": "Model Name", "Prompt": "Prompt",
                 "Input Tokens": "Input Tokens", "Output Tokens": "Output Tokens",
                 "Quality": "Quality", "Feedback": "Feedback"}, False


def clean_file(filename: str) -> dict:
    path = RAW_DIR / filename
    sep, col_map, numeric_quality = _detect_dialect(filename, path)

    stats = {
        "total": 0,
        "dup_removed": 0,
        "bad_tokens_removed": 0,
        "bad_quality_removed": 0,
        "feedback_filled": 0,
        "kept": 0,
    }

    seen_rows = set()
    cleaned_rows = []

    with open(path, newline="", encoding="utf-8", errors="replace") as fh:
        reader = csv.DictReader(fh, delimiter=sep)
        for row in reader:
            stats["total"] += 1

            model = standardize_model(row[col_map["Model Name"]])
            prompt = row[col_map["Prompt"]].strip()
            input_tokens = row[col_map["Input Tokens"]].strip()
            output_tokens = row[col_map["Output Tokens"]].strip()
            quality_raw = row[col_map["Quality"]]
            feedback_key = col_map["Feedback"]
            feedback = (row.get(feedback_key, "") or "").strip() if feedback_key else ""

            # Exact duplicate row check (on standardized values)
            dedupe_key = (model, prompt, input_tokens, output_tokens, quality_raw.strip(), feedback)
            if dedupe_key in seen_rows:
                stats["dup_removed"] += 1
                continue
            seen_rows.add(dedupe_key)

            # Valid, positive integer token counts required
            if not (input_tokens.isdigit() and output_tokens.isdigit()):
                stats["bad_tokens_removed"] += 1
                continue
            if int(input_tokens) <= 0 or int(output_tokens) <= 0:
                stats["bad_tokens_removed"] += 1
                continue

            # For datasets with numeric quality scores, convert to label first
            if numeric_quality:
                quality = _numeric_quality_to_label(quality_raw)
            else:
                quality = standardize_quality(quality_raw)
            if quality is None:
                stats["bad_quality_removed"] += 1
                continue

            if not feedback:
                feedback = "N/A"
                stats["feedback_filled"] += 1

            cleaned_rows.append({
                "Model Name": model,
                "Prompt": prompt,
                "Input Tokens": input_tokens,
                "Output Tokens": output_tokens,
                "Quality": quality,
                "Feedback": feedback,
            })

    stats["kept"] = len(cleaned_rows)

    OUT_DIR.mkdir(exist_ok=True)
    out_path = OUT_DIR / filename
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(cleaned_rows)

    return stats


def main():
    grand_total = 0
    grand_kept = 0
    for f in SOURCE_FILES:
        stats = clean_file(f)
        grand_total += stats["total"]
        grand_kept += stats["kept"]
        print(
            f"{f}: {stats['total']} rows -> {stats['kept']} kept "
            f"(dupes removed: {stats['dup_removed']}, "
            f"bad token rows removed: {stats['bad_tokens_removed']}, "
            f"bad quality removed: {stats['bad_quality_removed']}, "
            f"feedback filled: {stats['feedback_filled']})"
        )
    print(f"\nTotal: {grand_total} rows -> {grand_kept} kept, "
          f"{grand_total - grand_kept} removed. Cleaned files written to {OUT_DIR}/")


if __name__ == "__main__":
    main()

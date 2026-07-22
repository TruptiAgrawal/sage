#!/usr/bin/env python3
"""
Simple analyzer - processes all test_prompt_answers files and outputs to team11.csv
No dependencies, no API calls needed.

Usage:
    python3 analyze_all.py
"""

import os
import csv
import re
from pathlib import Path

def estimate_tokens(text: str) -> int:
    """Estimate tokens: roughly 1 token per 4 characters"""
    return max(1, len(text.strip()) // 4)


def parse_response_file(filepath: str):
    """Extract user prompt and assistant response from file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        user_match = re.search(r'^User:\s*(.+?)(?=\n\nAssistant:|$)', content,
                              re.MULTILINE | re.DOTALL)
        asst_match = re.search(r'^Assistant:\s*(.+?)$', content,
                              re.MULTILINE | re.DOTALL)

        if user_match and asst_match:
            return user_match.group(1).strip(), asst_match.group(1).strip()

        return None, None
    except:
        return None, None


def rate_quality(user_prompt: str, response: str) -> tuple:
    """Rate response quality: Good/Average/Bad with detailed feedback."""
    score = 0
    feedback_parts = []

    # Length assessment
    length = len(response)
    if length < 50:
        score -= 2
        feedback_parts.append("Response is too brief and lacks depth")
    elif length < 200:
        score += 1
        feedback_parts.append("Response has adequate length for the topic")
    elif length < 500:
        score += 2
        feedback_parts.append("Response provides good depth and comprehensive coverage")
    else:
        score += 3
        feedback_parts.append("Response is thorough and comprehensive with substantial detail")

    # Structure check
    sentences = len(re.split(r'[.!?]+', response.strip()))
    if sentences >= 3:
        score += 1
        feedback_parts.append("Well-structured with multiple logical sections")
    else:
        feedback_parts.append("Could benefit from better structure")

    # Specificity check
    has_examples = bool(re.search(
        r'\b(example|e\.g\.|for instance|such as|specifically|1st|2nd|3rd)\b',
        response, re.IGNORECASE
    ))
    has_numbers = bool(re.search(r'\d+', response))

    if has_examples and has_numbers:
        score += 2
        feedback_parts.append("Uses concrete examples and numerical data to support claims")
    elif has_examples or has_numbers:
        score += 1
        feedback_parts.append("Includes specific examples or data points")
    else:
        feedback_parts.append("Could benefit from concrete examples or numerical support")

    # Clarity check
    if response and response[0].isupper() and len(re.findall(r'[.!?]', response)) >= 1:
        score += 1
        feedback_parts.append("Clear and proper grammar throughout")

    # Relevance check
    prompt_words = set(user_prompt.lower().split())
    response_words = set(response.lower().split())
    overlap = len(prompt_words & response_words) / max(len(prompt_words), 1)

    if overlap > 0.3:
        score += 2
        feedback_parts.append("Directly and thoroughly addresses the user's question")
    elif overlap > 0.1:
        score += 1
        feedback_parts.append("Addresses the question but could be more focused")
    else:
        feedback_parts.append("Response relevance to the question could be improved")

    # Categorize
    if score >= 6:
        category = "Good"
    elif score >= 2:
        category = "Average"
    else:
        category = "Bad"

    # Build feedback
    feedback = "; ".join(feedback_parts[:3]) if feedback_parts else "Response requires improvement"

    return category, feedback


def main():
    input_dir = "test_prompt_answers"
    output_file = "team11.csv"

    print(f"\n🚀 Starting analysis of {input_dir}/...\n")

    # Get all response files
    response_files = sorted(
        Path(input_dir).glob("prompt*response.txt"),
        key=lambda x: int(re.search(r'\d+', x.name).group())
                     if re.search(r'\d+', x.name) else 0
    )

    if not response_files:
        print(f"❌ No prompt*response.txt files found in {input_dir}")
        return

    print(f"📄 Found {len(response_files)} files to analyze...\n")

    # Process files
    rows = []
    for idx, filepath in enumerate(response_files, 1):
        user_prompt, response = parse_response_file(str(filepath))

        if not user_prompt or not response:
            print(f"[{idx:3d}] ⚠️  Skipped {filepath.name}")
            continue

        input_tokens = estimate_tokens(user_prompt)
        output_tokens = estimate_tokens(response)
        quality, feedback = rate_quality(user_prompt, response)

        rows.append({
            'Model Name': 'claude-opus-4-8',
            'Prompt': user_prompt[:150],
            'Input Tokens': input_tokens,
            'Output Tokens': output_tokens,
            'Quality Category': quality,
            'Feedback': feedback
        })

        if idx % 20 == 0:
            print(f"[{idx:3d}] ✓ Processed {filepath.name}")

    # Write CSV
    if rows:
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'Model Name', 'Prompt', 'Input Tokens', 'Output Tokens',
                'Quality Category', 'Feedback'
            ])
            writer.writeheader()
            writer.writerows(rows)

        print(f"\n✅ Analysis complete!")
        print(f"   Total rows: {len(rows)}")
        print(f"   Output file: {output_file}")

        # Show stats
        good = sum(1 for r in rows if r['Quality Category'] == 'Good')
        avg = sum(1 for r in rows if r['Quality Category'] == 'Average')
        bad = sum(1 for r in rows if r['Quality Category'] == 'Bad')

        print(f"\n   Good:    {good:3d} ({good/len(rows)*100:5.1f}%)")
        print(f"   Average: {avg:3d} ({avg/len(rows)*100:5.1f}%)")
        print(f"   Bad:     {bad:3d} ({bad/len(rows)*100:5.1f}%)\n")


if __name__ == "__main__":
    main()

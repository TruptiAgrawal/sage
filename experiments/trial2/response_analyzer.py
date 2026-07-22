#!/usr/bin/env python3
"""
Response Analyzer Tool (No API Required)

Analyzes test prompt responses from test_prompt_answers folder.
Generates CSV with: Model | Prompt | Input Tokens | Output Tokens | Quality Category | Feedback

Uses local heuristics for quality assessment (no API calls needed).

Usage:
    python3 response_analyzer.py --input-dir test_prompt_answers --output output.csv --model claude-opus-4-8
"""

import os
import sys
import csv
import json
import re
from pathlib import Path
from dataclasses import dataclass
from typing import List, Tuple, Optional
from datetime import datetime


@dataclass
class ResponseAnalysis:
    model: str
    prompt: str
    input_tokens: int
    output_tokens: int
    quality_category: str
    feedback: str


class ResponseAnalyzer:
    """Analyze test prompt responses and generate quality metrics."""

    def __init__(self, model_name: str = "claude-opus-4-8"):
        self.model_name = model_name
        self.analyses: List[ResponseAnalysis] = []

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Estimate tokens: roughly 1 token per 4 characters"""
        return max(1, len(text.strip()) // 4)

    @staticmethod
    def parse_response_file(filepath: str) -> Tuple[Optional[str], Optional[str]]:
        """Parse response file to extract user prompt and assistant response."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            # Try to find User: and Assistant: sections
            user_match = re.search(r'^User:\s*(.+?)(?=\n\nAssistant:|$)', content,
                                  re.MULTILINE | re.DOTALL)
            asst_match = re.search(r'^Assistant:\s*(.+?)$', content,
                                  re.MULTILINE | re.DOTALL)

            if user_match and asst_match:
                user_prompt = user_match.group(1).strip()
                assistant_response = asst_match.group(1).strip()
                return user_prompt, assistant_response

            # Fallback: first line is user, rest is assistant
            lines = content.strip().split('\n')
            if len(lines) >= 2:
                # Skip lines that are just metadata/formatting
                user_line = next((l for l in lines if l.startswith('User:')), None)
                if user_line:
                    user_prompt = user_line.replace('User:', '').strip()
                    assistant_start_idx = next((i for i, l in enumerate(lines)
                                              if l.startswith('Assistant:')), 1)
                    assistant_response = '\n'.join(lines[assistant_start_idx+1:]).strip()
                    if assistant_response:
                        return user_prompt, assistant_response

            return None, None

        except Exception as e:
            print(f"⚠️  Error parsing {filepath}: {e}")
            return None, None

    def rate_quality(self, user_prompt: str, assistant_response: str) -> Tuple[str, str]:
        """Rate response quality using local heuristics (no API calls)."""
        score = 0
        feedback_parts = []

        # Length heuristic: Good responses are substantial
        response_length = len(assistant_response)
        if response_length < 50:
            score -= 2
            feedback_parts.append("Response is too brief and lacks depth")
        elif response_length < 200:
            score += 1
            feedback_parts.append("Response has adequate length for the topic")
        elif response_length < 500:
            score += 2
            feedback_parts.append("Response provides good depth and comprehensive coverage")
        else:
            score += 3
            feedback_parts.append("Response is thorough and comprehensive with substantial detail")

        # Complexity heuristic: Multiple sentences suggest structure
        sentence_count = len(re.split(r'[.!?]+', assistant_response.strip()))
        if sentence_count >= 3:
            score += 1
            feedback_parts.append("Well-structured with multiple logical sections")
        else:
            feedback_parts.append("Could benefit from better structure")

        # Specificity: Contains examples, numbers, or technical terms
        has_examples = re.search(r'\b(example|e\.g\.|for instance|such as|namely|specifically|1st|2nd|3rd|e\.g|i\.e|circa)\b',
                                 assistant_response, re.IGNORECASE)
        has_numbers = re.search(r'\d+', assistant_response)

        if has_examples and has_numbers:
            score += 2
            feedback_parts.append("Uses concrete examples and numerical data to support claims")
        elif has_examples or has_numbers:
            score += 1
            feedback_parts.append("Includes specific examples or data points")
        else:
            feedback_parts.append("Could benefit from concrete examples or numerical support")

        # Clarity: Proper punctuation and capitalization
        has_proper_caps = assistant_response[0].isupper() if assistant_response else False
        has_proper_punctuation = len(re.findall(r'[.!?]', assistant_response)) >= 1

        if has_proper_caps and has_proper_punctuation:
            score += 1
            feedback_parts.append("Clear and proper grammar throughout")

        # Relevance: Check if response addresses key concepts from prompt
        prompt_words = set(user_prompt.lower().split())
        response_words = set(assistant_response.lower().split())
        overlap = len(prompt_words & response_words) / max(len(prompt_words), 1)

        if overlap > 0.3:
            score += 2
            feedback_parts.append("Directly and thoroughly addresses the user's question")
        elif overlap > 0.1:
            score += 1
            feedback_parts.append("Addresses the question but could be more focused")
        else:
            feedback_parts.append("Response relevance to the question could be improved")

        # Categorize based on score - only 3 categories: Good/Average/Bad
        if score >= 6:
            category = "Good"
        elif score >= 2:
            category = "Average"
        else:
            category = "Bad"

        # Build comprehensive feedback - combine all relevant parts
        relevant_feedback = [f for f in feedback_parts if f]
        if len(relevant_feedback) > 3:
            feedback = "; ".join(relevant_feedback[:3])
        else:
            feedback = "; ".join(relevant_feedback) if relevant_feedback else "Response requires improvement"

        return category, feedback

    def analyze_directory(self, input_dir: str) -> None:
        """Analyze all prompt response files in directory."""
        if not os.path.isdir(input_dir):
            raise ValueError(f"Directory not found: {input_dir}")

        # Get all prompt*response.txt files
        response_files = sorted(
            Path(input_dir).glob("prompt*response.txt"),
            key=lambda x: int(re.search(r'\d+', x.name).group())
                          if re.search(r'\d+', x.name) else 0
        )

        if not response_files:
            raise ValueError(f"No prompt*response.txt files found in {input_dir}")

        print(f"\n📊 Analyzing {len(response_files)} response files...")
        print("-" * 80)

        for idx, filepath in enumerate(response_files, 1):
            user_prompt, assistant_response = self.parse_response_file(str(filepath))

            if not user_prompt or not assistant_response:
                print(f"[{idx}] ⚠️  Skipping {filepath.name} - couldn't parse")
                continue

            input_tokens = self.estimate_tokens(user_prompt)
            output_tokens = self.estimate_tokens(assistant_response)

            print(f"[{idx}] Analyzing {filepath.name}...", end=" ")
            quality_category, feedback = self.rate_quality(user_prompt, assistant_response)
            print(f"Category: {quality_category}")

            analysis = ResponseAnalysis(
                model=self.model_name,
                prompt=user_prompt[:200],  # Truncate for CSV readability
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                quality_category=quality_category,
                feedback=feedback
            )
            self.analyses.append(analysis)

        print("-" * 80)
        print(f"✓ Analyzed {len(self.analyses)} responses\n")

    def export_csv(self, output_path: str) -> None:
        """Export analyses to CSV."""
        if not self.analyses:
            print("❌ No analyses to export")
            return

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    'Model Name',
                    'Prompt',
                    'Input Tokens',
                    'Output Tokens',
                    'Quality Category',
                    'Feedback'
                ]
            )
            writer.writeheader()

            for analysis in self.analyses:
                writer.writerow({
                    'Model Name': analysis.model,
                    'Prompt': analysis.prompt,
                    'Input Tokens': analysis.input_tokens,
                    'Output Tokens': analysis.output_tokens,
                    'Quality Category': analysis.quality_category,
                    'Feedback': analysis.feedback
                })

        print(f"✓ Exported CSV: {output_path}")

    def export_json(self, output_path: str) -> None:
        """Export analyses to JSON."""
        if not self.analyses:
            print("❌ No analyses to export")
            return

        data = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "model": self.model_name,
                "total_analyzed": len(self.analyses),
                "analysis_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            },
            "analyses": [
                {
                    "model": a.model,
                    "prompt": a.prompt,
                    "input_tokens": a.input_tokens,
                    "output_tokens": a.output_tokens,
                    "quality_category": a.quality_category,
                    "feedback": a.feedback
                }
                for a in self.analyses
            ]
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"✓ Exported JSON: {output_path}")

    def print_summary(self) -> None:
        """Print analysis summary."""
        if not self.analyses:
            print("❌ No analyses to summarize")
            return

        quality_counts = {}
        for analysis in self.analyses:
            quality_counts[analysis.quality_category] = quality_counts.get(
                analysis.quality_category, 0
            ) + 1

        total_input = sum(a.input_tokens for a in self.analyses)
        total_output = sum(a.output_tokens for a in self.analyses)
        avg_input = total_input / len(self.analyses) if self.analyses else 0
        avg_output = total_output / len(self.analyses) if self.analyses else 0

        print("\n" + "=" * 80)
        print("RESPONSE ANALYSIS SUMMARY")
        print("=" * 80)
        print(f"Model:                  {self.model_name}")
        print(f"Total Responses:        {len(self.analyses)}")
        print(f"\nQuality Distribution:")
        for quality, count in sorted(quality_counts.items()):
            percentage = (count / len(self.analyses)) * 100
            print(f"  {quality:<12} {count:>4} ({percentage:>5.1f}%)")
        print(f"\nToken Usage:")
        print(f"  Total Input:           {total_input:,}")
        print(f"  Total Output:          {total_output:,}")
        print(f"  Total:                 {total_input + total_output:,}")
        print(f"  Avg Input/Response:    {avg_input:.0f}")
        print(f"  Avg Output/Response:   {avg_output:.0f}")
        print("=" * 80 + "\n")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Analyze test prompt responses and generate quality metrics"
    )
    parser.add_argument(
        "--input-dir",
        default="test_prompt_answers",
        help="Input directory with prompt*response.txt files (default: test_prompt_answers)"
    )
    parser.add_argument(
        "--output",
        default="responses_analysis.csv",
        help="Output CSV file (default: responses_analysis.csv)"
    )
    parser.add_argument(
        "--model",
        default="claude-opus-4-8",
        help="Claude model to use for quality rating (default: claude-opus-4-8)"
    )
    parser.add_argument(
        "--format",
        choices=["csv", "json", "both"],
        default="csv",
        help="Output format (default: csv)"
    )

    args = parser.parse_args()

    try:
        analyzer = ResponseAnalyzer(args.model)
        analyzer.analyze_directory(args.input_dir)
        analyzer.print_summary()

        base_output = args.output.rsplit('.', 1)[0]

        if args.format in ["csv", "both"]:
            csv_path = f"{base_output}.csv" if args.format == "csv" else f"{base_output}.csv"
            analyzer.export_csv(csv_path)

        if args.format in ["json", "both"]:
            json_path = f"{base_output}.json"
            analyzer.export_json(json_path)

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

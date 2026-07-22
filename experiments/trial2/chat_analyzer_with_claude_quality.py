#!/usr/bin/env python3
"""
Chat Analyzer with Claude Quality Ratings

Reads chat transcripts and uses Claude API to rate response quality.
Outputs: Model name | Prompt | Input tokens | Output tokens | Quality (1-10)

Usage:
    export ANTHROPIC_API_KEY="sk-ant-..."
    python3 chat_analyzer_with_claude_quality.py your_chat.txt --model claude-opus-4-8 --export json
"""

import json
import csv
import sys
from dataclasses import dataclass
from typing import List
from datetime import datetime

try:
    from anthropic import Anthropic
except ImportError:
    print("❌ anthropic library not installed")
    print("   Install with: pip install anthropic")
    sys.exit(1)


@dataclass
class Message:
    index: int
    role: str
    content: str
    tokens: int
    model: str = "unknown"
    quality: float = 0.0

    @property
    def efficiency(self) -> float:
        """Quality per token"""
        return self.quality / max(1, self.tokens)


class ChatAnalyzerWithQuality:
    """Analyze chat and use Claude to rate response quality."""

    def __init__(self, model_name: str = "claude-opus-4-8"):
        self.model_name = model_name
        self.messages: List[Message] = []
        self.client = Anthropic()

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Estimate tokens: ~1 per 4 characters"""
        return max(1, len(text.strip()) // 4)

    def parse_chat(self, text: str) -> List[dict]:
        """Parse generic format: User: ... Assistant: ..."""
        messages = []
        lines = text.split('\n')
        current = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if line.startswith('User:'):
                if current:
                    messages.append(current)
                current = {'role': 'user', 'content': line[5:].strip()}
            elif line.startswith('Assistant:'):
                if current:
                    messages.append(current)
                current = {'role': 'assistant', 'content': line[10:].strip()}
            elif current and not any(line.startswith(x) for x in ['User:', 'Assistant:', 'Quality:', 'Model:']):
                current['content'] += ' ' + line

        if current:
            messages.append(current)

        return messages

    def rate_response_quality(self, user_prompt: str, assistant_response: str) -> float:
        """Use Claude to rate response quality 1-10."""
        try:
            response = self.client.messages.create(
                model=self.model_name,
                max_tokens=100,
                messages=[{
                    "role": "user",
                    "content": f"""Rate this assistant response on a scale of 1-10 based on:
- Accuracy and correctness
- Clarity and readability
- Completeness and helpfulness
- Relevance to the question

User Question: {user_prompt}

Assistant Response: {assistant_response}

Respond with ONLY a number 1-10, nothing else."""
                }]
            )

            rating_text = response.content[0].text.strip()
            rating = float(rating_text.split()[0])
            return min(10, max(1, rating))  # Clamp to 1-10
        except Exception as e:
            print(f"⚠️  Error rating response: {e}")
            return 5.0  # Default neutral rating

    def analyze(self, text: str, model: str = None) -> None:
        """Analyze chat and rate responses."""
        if model:
            self.model_name = model

        messages_data = self.parse_chat(text)
        if not messages_data:
            raise ValueError("No messages found")

        self.messages = []
        user_prompt = ""
        msg_idx = 1

        print("\n📊 Analyzing chat and rating responses...")
        print("-" * 60)

        for msg in messages_data:
            role = msg['role'].lower()
            content = msg['content']
            tokens = self.estimate_tokens(content)

            if role == 'user':
                user_prompt = content
                quality = 0.0  # User messages don't get rated
                print(f"[{msg_idx}] User prompt: {content[:50]}...")
            else:  # assistant
                print(f"[{msg_idx}] Rating assistant response...", end=" ")
                quality = self.rate_response_quality(user_prompt, content)
                print(f"Quality: {quality}/10")

            self.messages.append(Message(
                index=msg_idx,
                role=role,
                content=content,
                tokens=tokens,
                model=self.model_name,
                quality=quality
            ))
            msg_idx += 1

        print("-" * 60)

    def get_stats(self) -> dict:
        """Get analysis statistics."""
        user_msgs = [m for m in self.messages if m.role == 'user']
        asst_msgs = [m for m in self.messages if m.role == 'assistant']

        input_tokens = sum(m.tokens for m in user_msgs)
        output_tokens = sum(m.tokens for m in asst_msgs)

        avg_quality = sum(m.quality for m in asst_msgs) / len(asst_msgs) if asst_msgs else 0

        return {
            'model': self.model_name,
            'total_messages': len(self.messages),
            'total_tokens': input_tokens + output_tokens,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'user_messages': len(user_msgs),
            'assistant_messages': len(asst_msgs),
            'avg_user_tokens': input_tokens // len(user_msgs) if user_msgs else 0,
            'avg_output_tokens': output_tokens // len(asst_msgs) if asst_msgs else 0,
            'avg_response_quality': round(avg_quality, 2),
        }

    def print_summary(self) -> None:
        """Print analysis summary."""
        stats = self.get_stats()

        print("\n" + "=" * 80)
        print("CHAT ANALYSIS WITH CLAUDE QUALITY RATINGS")
        print("=" * 80)
        print(f"Model:                       {stats['model']}")
        print(f"Total Messages:              {stats['total_messages']}")
        print(f"  User Messages:             {stats['user_messages']}")
        print(f"  Assistant Messages:        {stats['assistant_messages']}")
        print(f"\nToken Usage:")
        print(f"  Total:                     {stats['total_tokens']:,}")
        print(f"  Input (User):              {stats['input_tokens']:,}")
        print(f"  Output (Assistant):        {stats['output_tokens']:,}")
        print(f"\nAverage per Message:")
        print(f"  User Tokens:               {stats['avg_user_tokens']}")
        print(f"  Assistant Tokens:          {stats['avg_output_tokens']}")
        print(f"\nQuality Metrics:")
        print(f"  Avg Response Quality:      {stats['avg_response_quality']}/10")
        print("=" * 80 + "\n")

    def print_table(self) -> None:
        """Print detailed breakdown."""
        print("MESSAGE BREAKDOWN")
        print("-" * 130)
        print(f"{'#':<4} {'Model':<20} {'Role':<12} {'Quality':<10} {'Tokens':<10} {'Preview':<60}")
        print("-" * 130)

        for msg in self.messages:
            quality_str = f"{msg.quality}/10" if msg.role == 'assistant' else "N/A"
            preview = msg.content[:60]
            print(f"{msg.index:<4} {msg.model:<20} {msg.role.upper():<12} {quality_str:<10} {msg.tokens:<10} {preview:<60}")

        print("-" * 130 + "\n")

    def export_json(self, filepath: str) -> None:
        """Export with quality ratings."""
        data = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                **self.get_stats()
            },
            "messages": [
                {
                    "index": m.index,
                    "model": m.model,
                    "role": m.role,
                    "tokens": m.tokens,
                    "quality": round(m.quality, 2) if m.role == 'assistant' else None,
                    "efficiency": round(m.efficiency, 3) if m.role == 'assistant' else None,
                    "content_length": len(m.content),
                    "preview": m.content[:100]
                }
                for m in self.messages
            ]
        }

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"✓ Exported JSON: {filepath}")

    def export_csv(self, filepath: str) -> None:
        """Export as CSV: Model | Role | Tokens | Quality | Efficiency"""
        with open(filepath, 'w', newline='') as f:
            writer = csv.DictWriter(
                f,
                fieldnames=['Index', 'Model', 'Role', 'Tokens', 'Quality', 'Efficiency', 'Preview']
            )
            writer.writeheader()

            for msg in self.messages:
                writer.writerow({
                    'Index': msg.index,
                    'Model': msg.model,
                    'Role': msg.role.upper(),
                    'Tokens': msg.tokens,
                    'Quality': round(msg.quality, 2) if msg.role == 'assistant' else 'N/A',
                    'Efficiency': round(msg.efficiency, 3) if msg.role == 'assistant' else 'N/A',
                    'Preview': msg.content[:100]
                })

        print(f"✓ Exported CSV: {filepath}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    input_file = sys.argv[1]
    model = "claude-opus-4-8"
    export_fmt = None

    for i, arg in enumerate(sys.argv[2:], 2):
        if arg == "--model" and i + 1 < len(sys.argv):
            model = sys.argv[i + 1]
        elif arg == "--export" and i + 1 < len(sys.argv):
            export_fmt = sys.argv[i + 1]

    try:
        with open(input_file, 'r') as f:
            text = f.read()

        analyzer = ChatAnalyzerWithQuality(model)
        analyzer.analyze(text, model)
        analyzer.print_summary()
        analyzer.print_table()

        if export_fmt:
            base = input_file.rsplit('.', 1)[0]
            if export_fmt == "json":
                analyzer.export_json(f"{base}-quality.json")
            elif export_fmt == "csv":
                analyzer.export_csv(f"{base}-quality.csv")

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

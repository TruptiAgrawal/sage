#!/usr/bin/env python3
"""
Chat Analyzer PRO - With model name and prompt quality tracking.

Extends the basic analyzer to track:
- Model used
- Prompt quality rating (1-10)
- Input tokens
- Output tokens
- Token efficiency

Format:
    User: [message]
    Quality: [1-10]
    Model: [model-name]

    Assistant: [response]
    Quality: [1-10]
"""

import json
import csv
from dataclasses import dataclass
from typing import List
from datetime import datetime


@dataclass
class EnhancedMessage:
    index: int
    role: str
    model: str = "unknown"
    quality: float = 0.0
    content: str = ""
    tokens: int = 0

    @property
    def efficiency(self) -> float:
        """Token efficiency (quality per token)"""
        return self.quality / max(1, self.tokens)


class ChatAnalyzerPro:
    """Enhanced analyzer with quality tracking."""

    def __init__(self, model_name: str = "claude-opus-4-8"):
        self.model_name = model_name
        self.messages: List[EnhancedMessage] = []

    @staticmethod
    def estimate_tokens(text: str) -> int:
        return max(1, len(text.strip()) // 4)

    def parse_enhanced_format(self, text: str) -> List[dict]:
        """Parse format with metadata (Quality, Model)."""
        messages = []
        lines = text.split('\n')
        current = {
            'role': None,
            'content': '',
            'model': self.model_name,
            'quality': 0.0
        }

        for line in lines:
            line = line.strip()

            if line.startswith('User:'):
                if current['role']:
                    messages.append(current)
                current = {
                    'role': 'user',
                    'content': line[5:].strip(),
                    'model': self.model_name,
                    'quality': 0.0
                }
            elif line.startswith('Assistant:'):
                if current['role']:
                    messages.append(current)
                current = {
                    'role': 'assistant',
                    'content': line[10:].strip(),
                    'model': self.model_name,
                    'quality': 0.0
                }
            elif line.startswith('Quality:'):
                try:
                    current['quality'] = float(line[8:].strip().split('/')[0])
                except:
                    pass
            elif line.startswith('Model:'):
                current['model'] = line[6:].strip()
            elif line and current['role']:
                current['content'] += ' ' + line

        if current['role']:
            messages.append(current)

        return messages

    def analyze(self, text: str, model: str = None) -> None:
        """Analyze chat with quality tracking."""
        if model:
            self.model_name = model

        messages_data = self.parse_enhanced_format(text)

        if not messages_data:
            raise ValueError("No messages found")

        self.messages = []
        for i, msg in enumerate(messages_data, 1):
            role = msg['role'].lower()
            content = msg['content']
            tokens = self.estimate_tokens(content)
            quality = msg.get('quality', 0.0)
            model = msg.get('model', self.model_name)

            self.messages.append(EnhancedMessage(
                index=i,
                role=role,
                model=model,
                quality=quality,
                content=content,
                tokens=tokens
            ))

    def get_stats(self) -> dict:
        user_msgs = [m for m in self.messages if m.role == 'user']
        asst_msgs = [m for m in self.messages if m.role == 'assistant']

        input_tokens = sum(m.tokens for m in user_msgs)
        output_tokens = sum(m.tokens for m in asst_msgs)
        total_tokens = input_tokens + output_tokens

        avg_user_quality = sum(m.quality for m in user_msgs) / len(user_msgs) if user_msgs else 0
        avg_asst_quality = sum(m.quality for m in asst_msgs) / len(asst_msgs) if asst_msgs else 0

        return {
            'total_messages': len(self.messages),
            'total_tokens': total_tokens,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'user_messages': len(user_msgs),
            'assistant_messages': len(asst_msgs),
            'avg_input_tokens': input_tokens // len(user_msgs) if user_msgs else 0,
            'avg_output_tokens': output_tokens // len(asst_msgs) if asst_msgs else 0,
            'avg_user_quality': round(avg_user_quality, 2),
            'avg_assistant_quality': round(avg_asst_quality, 2),
            'model': self.model_name
        }

    def print_summary(self) -> None:
        stats = self.get_stats()
        print("\n" + "=" * 80)
        print("CHAT ANALYSIS WITH QUALITY METRICS")
        print("=" * 80)
        print(f"Model:                       {stats['model']}")
        print(f"Total Messages:              {stats['total_messages']}")
        print(f"User Messages:               {stats['user_messages']}")
        print(f"Assistant Messages:          {stats['assistant_messages']}")
        print(f"\nTotal Tokens:                {stats['total_tokens']:,}")
        print(f"  Input (User):              {stats['input_tokens']:,}")
        print(f"  Output (Assistant):        {stats['output_tokens']:,}")
        print(f"\nAverage Tokens per Message:")
        print(f"  User:                      {stats['avg_input_tokens']}")
        print(f"  Assistant:                 {stats['avg_output_tokens']}")
        print(f"\nAverage Quality Rating (1-10):")
        print(f"  User Prompts:              {stats['avg_user_quality']}")
        print(f"  Assistant Responses:       {stats['avg_assistant_quality']}")
        print("=" * 80 + "\n")

    def print_table(self) -> None:
        print("MESSAGE BREAKDOWN")
        print("-" * 120)
        print(f"{'#':<4} {'Role':<12} {'Model':<20} {'Quality':<10} {'Tokens':<10} {'Preview':<60}")
        print("-" * 120)

        for msg in self.messages:
            quality_str = f"{msg.quality}/10" if msg.quality > 0 else "N/A"
            print(f"{msg.index:<4} {msg.role.upper():<12} {msg.model:<20} {quality_str:<10} {msg.tokens:<10} {msg.content[:60]:<60}")

        print("-" * 120 + "\n")

    def export_json(self, filepath: str) -> None:
        """Export with quality metrics."""
        data = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                **self.get_stats()
            },
            "messages": [
                {
                    "index": m.index,
                    "role": m.role,
                    "model": m.model,
                    "quality": m.quality,
                    "tokens": m.tokens,
                    "length": len(m.content),
                    "efficiency": round(m.efficiency, 3)
                }
                for m in self.messages
            ]
        }

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"✓ Exported to {filepath}")

    def export_csv(self, filepath: str) -> None:
        """Export as: Model | Prompt | Input/Output Tokens | Quality"""
        with open(filepath, 'w', newline='') as f:
            writer = csv.DictWriter(
                f,
                fieldnames=['Index', 'Model', 'Role', 'Prompt', 'Tokens', 'Quality', 'Efficiency']
            )
            writer.writeheader()

            for msg in self.messages:
                writer.writerow({
                    'Index': msg.index,
                    'Model': msg.model,
                    'Role': msg.role,
                    'Prompt': msg.content[:100],
                    'Tokens': msg.tokens,
                    'Quality': msg.quality if msg.quality > 0 else 'N/A',
                    'Efficiency': round(msg.efficiency, 3)
                })

        print(f"✓ Exported to {filepath}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python3 chat_analyzer_pro.py <file.txt> [--model MODEL] [--export FORMAT]")
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

        analyzer = ChatAnalyzerPro(model)
        analyzer.analyze(text, model)
        analyzer.print_summary()
        analyzer.print_table()

        if export_fmt == "json":
            base = input_file.rsplit('.', 1)[0]
            analyzer.export_json(f"{base}-pro.json")
        elif export_fmt == "csv":
            base = input_file.rsplit('.', 1)[0]
            analyzer.export_csv(f"{base}-pro.csv")

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

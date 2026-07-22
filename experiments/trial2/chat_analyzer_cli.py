#!/usr/bin/env python3
"""
Chat Token Analyzer CLI - Analyze token usage in chat transcripts.

Usage:
    python3 chat_analyzer_cli.py input.txt               # Analyze from file
    python3 chat_analyzer_cli.py input.txt --format json # Specify format
    python3 chat_analyzer_cli.py input.txt --export json # Export to JSON
    python3 chat_analyzer_cli.py input.txt --export csv  # Export to CSV
"""

import json
import csv
import sys
import re
from pathlib import Path
from dataclasses import dataclass
from typing import List, Tuple
from datetime import datetime


@dataclass
class Message:
    """A single message in the chat."""
    index: int
    role: str
    content: str
    tokens: int

    @property
    def preview(self) -> str:
        return self.content[:50] + ("..." if len(self.content) > 50 else "")


class ChatAnalyzer:
    """Analyze token usage in chat transcripts."""

    def __init__(self):
        self.messages: List[Message] = []

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Estimate tokens: roughly 1 token per 4 characters."""
        return max(1, len(text.strip()) // 4)

    def parse_generic_format(self, text: str) -> List[dict]:
        """Parse generic format: User: ...\n\nAssistant: ..."""
        messages = []
        # Split by User: or Assistant: at start of line
        pattern = r'^(User|Assistant|user|assistant):\s*([\s\S]*?)(?=^(?:User|Assistant|user|assistant):|$)'
        for match in re.finditer(pattern, text, re.MULTILINE):
            role = match.group(1).lower()
            content = match.group(2).strip()
            if content:
                messages.append({"role": role, "content": content})
        return messages

    def parse_json_format(self, text: str) -> List[dict]:
        """Parse JSON format: [{role: "user", content: "..."}, ...]"""
        try:
            data = json.loads(text)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and "messages" in data:
                return data["messages"]
            return []
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}")

    def parse_markdown_format(self, text: str) -> List[dict]:
        """Parse markdown format: ## User\n...\n## Assistant\n..."""
        messages = []
        sections = re.split(r'^##\s+(User|Assistant|user|assistant)', text, flags=re.MULTILINE)

        for i in range(1, len(sections), 2):
            if i + 1 < len(sections):
                role = sections[i].lower().strip()
                content = sections[i + 1].strip()
                if content and role in ['user', 'assistant']:
                    messages.append({"role": role, "content": content})
        return messages

    def parse_chat(self, text: str, format: str = "generic") -> List[dict]:
        """Parse chat in specified format."""
        if format == "generic":
            return self.parse_generic_format(text)
        elif format == "json":
            return self.parse_json_format(text)
        elif format == "markdown":
            return self.parse_markdown_format(text)
        else:
            raise ValueError(f"Unknown format: {format}")

    def analyze(self, text: str, format: str = "generic") -> None:
        """Analyze chat text."""
        messages_data = self.parse_chat(text, format)

        if not messages_data:
            raise ValueError("No messages found in chat")

        self.messages = []
        for i, msg in enumerate(messages_data, 1):
            role = msg.get("role", "unknown").lower()
            content = msg.get("content", "")
            tokens = self.estimate_tokens(content)
            self.messages.append(Message(
                index=i,
                role=role,
                content=content,
                tokens=tokens
            ))

    def get_stats(self) -> dict:
        """Get analysis statistics."""
        user_msgs = [m for m in self.messages if m.role == "user"]
        assistant_msgs = [m for m in self.messages if m.role == "assistant"]

        input_tokens = sum(m.tokens for m in user_msgs)
        output_tokens = sum(m.tokens for m in assistant_msgs)
        total_tokens = input_tokens + output_tokens

        return {
            "total_messages": len(self.messages),
            "total_tokens": total_tokens,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "user_messages": len(user_msgs),
            "assistant_messages": len(assistant_msgs),
            "avg_input_per_msg": input_tokens // len(user_msgs) if user_msgs else 0,
            "avg_output_per_msg": output_tokens // len(assistant_msgs) if assistant_msgs else 0,
        }

    def print_summary(self) -> None:
        """Print analysis summary to console."""
        stats = self.get_stats()

        print("\n" + "=" * 70)
        print("CHAT TOKEN ANALYSIS SUMMARY")
        print("=" * 70)
        print(f"Total Messages:          {stats['total_messages']}")
        print(f"User Messages:           {stats['user_messages']}")
        print(f"Assistant Messages:      {stats['assistant_messages']}")
        print(f"\nTotal Tokens:            {stats['total_tokens']:,}")
        print(f"  Input (User):          {stats['input_tokens']:,}")
        print(f"  Output (Assistant):    {stats['output_tokens']:,}")
        print(f"\nAverage per Message:")
        print(f"  User:                  {stats['avg_input_per_msg']} tokens")
        print(f"  Assistant:             {stats['avg_output_per_msg']} tokens")
        print("=" * 70 + "\n")

    def print_table(self) -> None:
        """Print detailed message table."""
        print("\nMESSAGE BREAKDOWN")
        print("-" * 100)
        print(f"{'#':<4} {'Role':<12} {'Preview':<60} {'Tokens':>10}")
        print("-" * 100)

        for msg in self.messages:
            role_display = msg.role.upper()
            print(f"{msg.index:<4} {role_display:<12} {msg.preview:<60} {msg.tokens:>10}")

        print("-" * 100 + "\n")

    def export_json(self, filepath: str) -> None:
        """Export analysis to JSON."""
        data = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "format": "messages",
                **self.get_stats()
            },
            "messages": [
                {
                    "index": m.index,
                    "role": m.role,
                    "tokens": m.tokens,
                    "length": len(m.content),
                    "preview": m.preview
                }
                for m in self.messages
            ]
        }

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"✓ Exported to {filepath}")

    def export_csv(self, filepath: str) -> None:
        """Export analysis to CSV."""
        with open(filepath, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['Index', 'Role', 'Tokens', 'Length'])
            writer.writeheader()
            for msg in self.messages:
                writer.writerow({
                    'Index': msg.index,
                    'Role': msg.role,
                    'Tokens': msg.tokens,
                    'Length': len(msg.content)
                })

        print(f"✓ Exported to {filepath}")

    def export_database_schema(self, filepath: str) -> None:
        """Export schema for database creation."""
        schema = {
            "database": "chat_analysis",
            "tables": {
                "chats": {
                    "columns": [
                        {"name": "chat_id", "type": "INTEGER PRIMARY KEY"},
                        {"name": "analyzed_at", "type": "TIMESTAMP"},
                        {"name": "total_messages", "type": "INTEGER"},
                        {"name": "total_tokens", "type": "INTEGER"},
                        {"name": "input_tokens", "type": "INTEGER"},
                        {"name": "output_tokens", "type": "INTEGER"},
                    ]
                },
                "messages": {
                    "columns": [
                        {"name": "message_id", "type": "INTEGER PRIMARY KEY"},
                        {"name": "chat_id", "type": "INTEGER FOREIGN KEY"},
                        {"name": "index", "type": "INTEGER"},
                        {"name": "role", "type": "TEXT"},
                        {"name": "tokens", "type": "INTEGER"},
                        {"name": "length", "type": "INTEGER"},
                        {"name": "preview", "type": "TEXT"},
                    ]
                }
            }
        }

        with open(filepath, 'w') as f:
            json.dump(schema, f, indent=2)

        print(f"✓ Database schema exported to {filepath}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    input_file = sys.argv[1]
    format_type = "generic"
    export_format = None

    # Parse arguments
    for i, arg in enumerate(sys.argv[2:], 2):
        if arg == "--format" and i + 1 < len(sys.argv):
            format_type = sys.argv[i + 1]
        elif arg == "--export" and i + 1 < len(sys.argv):
            export_format = sys.argv[i + 1]

    # Read file
    try:
        with open(input_file, 'r') as f:
            text = f.read()
    except FileNotFoundError:
        print(f"❌ File not found: {input_file}")
        sys.exit(1)

    # Analyze
    try:
        analyzer = ChatAnalyzer()
        analyzer.analyze(text, format_type)

        # Display results
        analyzer.print_summary()
        analyzer.print_table()

        # Export if requested
        if export_format:
            base_name = Path(input_file).stem
            if export_format == "json":
                analyzer.export_json(f"{base_name}-analysis.json")
            elif export_format == "csv":
                analyzer.export_csv(f"{base_name}-analysis.csv")
            elif export_format == "schema":
                analyzer.export_database_schema(f"{base_name}-schema.json")

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

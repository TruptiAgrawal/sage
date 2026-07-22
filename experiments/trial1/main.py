#!/usr/bin/env python3
"""Main entry point for token cost calculator."""

import sys
from src.tokenizer import tokenize
from src.calculator import calculate_costs
from src.display import display_tokens, display_cost_breakdown


def get_int_input(prompt: str, default: int = 0) -> int:
    """Get integer input from user with a default."""
    try:
        value = input(prompt).strip()
        return int(value) if value else default
    except ValueError:
        print(f"Invalid input, using default: {default}")
        return default


def main():
    """Main flow: tokenize → ask for other token types → calculate → display."""
    # Get prompt from args or stdin
    from_args = len(sys.argv) > 1
    if from_args:
        prompt = " ".join(sys.argv[1:])
    else:
        print("Enter your prompt (press Enter twice to submit):")
        lines = []
        while True:
            line = input()
            if line:
                lines.append(line)
            else:
                if lines:
                    break
        prompt = "\n".join(lines)

    if not prompt.strip():
        print("No prompt provided.")
        return

    # Step 1: Tokenize the prompt
    print("\n→ Tokenizing prompt...")
    token_data = tokenize(prompt)
    input_token_count = token_data["token_count"]
    print(f"  Found {input_token_count} tokens")

    # Display the actual tokens
    display_tokens(token_data)

    # Step 2: Ask for other token types (only if input from stdin)
    if from_args:
        output_tokens = 0
        reasoning_tokens = 0
        cache_tokens = 0
    else:
        print("Enter additional token counts (press Enter to skip/use 0):\n")
        output_tokens = get_int_input("  Output tokens: ", 0)
        reasoning_tokens = get_int_input("  Reasoning tokens (extended thinking): ", 0)
        cache_tokens = get_int_input("  Cache tokens (cached from previous): ", 0)

    # Step 3: Calculate costs
    print("\n→ Calculating costs...")
    cost_breakdown = calculate_costs(
        input_tokens=input_token_count,
        output_tokens=output_tokens,
        reasoning_tokens=reasoning_tokens,
        cache_tokens=cache_tokens,
        model="sonnet",
    )

    # Step 4: Display results
    print("→ Displaying breakdown...\n")
    display_cost_breakdown(cost_breakdown)


if __name__ == "__main__":
    main()

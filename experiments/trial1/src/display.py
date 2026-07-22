"""Display formatting for cost breakdown."""


def display_tokens(token_data: dict, max_display: int = 50) -> None:
    """Display the actual tokens from tokenization.

    Args:
        token_data: Dictionary from tokenizer.tokenize()
        max_display: Maximum tokens to display (long prompts get truncated)
    """
    tokens = token_data["tokens"]
    total = len(tokens)

    print("\n" + "=" * 80)
    print(f"Tokens ({total} total)")
    print("=" * 80)

    display_count = min(max_display, total)
    displayed_tokens = [f'"{t}"' for t in tokens[:display_count]]
    token_str = " | ".join(displayed_tokens)
    print(token_str)

    if total > max_display:
        remaining = total - max_display
        print(f"\n... and {remaining} more tokens (not shown)")

    print("=" * 80 + "\n")


def display_cost_breakdown(cost_data: dict) -> None:
    """Display token cost breakdown as a formatted table.

    Args:
        cost_data: Dictionary from calculator.calculate_costs()
    """
    model_name = cost_data["model_name"]
    input_tokens = cost_data["input"]["tokens"]
    output_tokens = cost_data["output"]["tokens"]
    reasoning_tokens = cost_data["reasoning"]["tokens"]
    total_tokens = cost_data["total_tokens"]
    total_cost = cost_data["total_cost"]

    print("\n" + "=" * 80)
    print(f"Token Cost Breakdown ({model_name})")
    print("=" * 80)
    print(f"{'Token Type':<20} {'Count':>12} {'Rate (per 1M)':>18} {'Cost':>18}")
    print("-" * 80)

    # Input tokens
    print(
        f"{'Input':<20} {input_tokens:>12} "
        f"${cost_data['input']['rate']:>17.2f} "
        f"${cost_data['input']['cost']:>17.6f}"
    )

    # Output tokens
    print(
        f"{'Output':<20} {output_tokens:>12} "
        f"${cost_data['output']['rate']:>17.2f} "
        f"${cost_data['output']['cost']:>17.6f}"
    )

    # Reasoning tokens
    print(
        f"{'Reasoning':<20} {reasoning_tokens:>12} "
        f"${cost_data['reasoning']['rate']:>17.2f} "
        f"${cost_data['reasoning']['cost']:>17.6f}"
    )

    # Cache tokens
    print(
        f"{'Cache':<20} {cost_data['cache']['tokens']:>12} "
        f"${cost_data['cache']['rate']:>17.2f} "
        f"${cost_data['cache']['cost']:>17.6f}"
    )

    # Total
    print("-" * 80)
    print(
        f"{'TOTAL':<20} {total_tokens:>12} "
        f"{' ':>18} "
        f"${total_cost:>17.6f}"
    )
    print("=" * 80 + "\n")

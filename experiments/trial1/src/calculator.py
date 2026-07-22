"""Cost calculation module."""

from src.pricing import get_model, get_cost


def calculate_costs(
    input_tokens: int,
    output_tokens: int = 0,
    reasoning_tokens: int = 0,
    cache_tokens: int = 0,
    model: str = "sonnet",
) -> dict:
    """Calculate costs for token usage.

    Args:
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        reasoning_tokens: Number of reasoning tokens (extended thinking)
        cache_tokens: Number of cache read tokens
        model: Model name (sonnet, opus, haiku)

    Returns:
        Dictionary with cost breakdown
    """
    pricing = get_model(model)

    input_cost = get_cost(input_tokens, pricing["input"])
    output_cost = get_cost(output_tokens, pricing["output"])
    reasoning_cost = get_cost(reasoning_tokens, pricing["reasoning"])
    cache_cost = get_cost(cache_tokens, pricing["cache_read"])

    total_cost = input_cost + output_cost + reasoning_cost + cache_cost

    return {
        "model": model,
        "model_name": pricing["name"],
        "input": {
            "tokens": input_tokens,
            "rate": pricing["input"],
            "cost": input_cost,
        },
        "output": {
            "tokens": output_tokens,
            "rate": pricing["output"],
            "cost": output_cost,
        },
        "reasoning": {
            "tokens": reasoning_tokens,
            "rate": pricing["reasoning"],
            "cost": reasoning_cost,
        },
        "cache": {
            "tokens": cache_tokens,
            "rate": pricing["cache_read"],
            "cost": cache_cost,
        },
        "total_tokens": input_tokens + output_tokens + reasoning_tokens + cache_tokens,
        "total_cost": total_cost,
    }

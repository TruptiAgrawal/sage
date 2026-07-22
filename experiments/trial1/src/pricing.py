"""Claude pricing data for different models."""

# Pricing per million tokens
MODELS = {
    "sonnet": {
        "name": "Claude 3.5 Sonnet",
        "input": 3.00,        # $3 per 1M input tokens
        "output": 15.00,      # $15 per 1M output tokens
        "reasoning": 15.00,   # $15 per 1M reasoning tokens (extended thinking)
        "cache_creation": 3.75,  # $3.75 per 1M (25% surcharge)
        "cache_read": 0.30,   # $0.30 per 1M (90% discount)
    },
    "opus": {
        "name": "Claude 3 Opus",
        "input": 15.00,       # $15 per 1M input tokens
        "output": 75.00,      # $75 per 1M output tokens
        "reasoning": 75.00,   # $75 per 1M reasoning tokens
        "cache_creation": 18.75,  # 25% surcharge
        "cache_read": 1.50,   # 90% discount
    },
    "haiku": {
        "name": "Claude 3 Haiku",
        "input": 0.25,        # $0.25 per 1M input tokens
        "output": 1.25,       # $1.25 per 1M output tokens
        "reasoning": 1.25,    # $1.25 per 1M reasoning tokens
        "cache_creation": 0.3125,  # 25% surcharge
        "cache_read": 0.0125, # 90% discount
    },
}


def get_model(model_name: str) -> dict:
    """Get pricing info for a model."""
    if model_name not in MODELS:
        raise ValueError(f"Unknown model: {model_name}. Available: {list(MODELS.keys())}")
    return MODELS[model_name]


def get_cost(tokens: int, price_per_million: float) -> float:
    """Calculate cost for given token count.

    Args:
        tokens: Number of tokens
        price_per_million: Price per 1 million tokens

    Returns:
        Cost in dollars
    """
    return (tokens / 1_000_000) * price_per_million

"""
Demo: TokenTracer with Mock Client (No API Keys Needed)

This demonstrates the TokenTracer with a simulated Anthropic client.
Perfect for testing token accounting without API authentication.

Usage:
    python demo_mock.py
"""

from token_tracer import TokenTracer
from mock_client import (
    MockAnthropicClient,
    CacheStrategy,
    SCENARIO_3_TURN_NO_CACHE,
    SCENARIO_3_TURN_WITH_CACHE,
    SCENARIO_5_TURN_LONG_LOOP,
    SCENARIO_TOOL_USE,
)


def demo_basic_3_turn():
    """Demo 1: Basic 3-turn loop without caching."""
    print("\n" + "="*80)
    print("DEMO 1: 3-TURN LOOP WITHOUT CACHING")
    print("="*80 + "\n")

    mock_client = MockAnthropicClient(
        cache_strategy=CacheStrategy.NO_CACHE,
        system_prefix_tokens=900
    )
    tracer = TokenTracer(mock_client, verbose=True)

    # Queue responses
    mock_client.queue_scenario(SCENARIO_3_TURN_NO_CACHE)

    # Simulate agent loop
    messages = [{"role": "user", "content": "What is Python?"}]

    for turn in range(3):
        response = tracer.create_message(
            model="mock-model",
            max_tokens=1024,
            system=[{"type": "text", "text": "You are a helpful assistant.", "cache_control": {"type": "ephemeral"}}],
            messages=messages
        )

        # Add to conversation
        messages.append({"role": "assistant", "content": response.content[0].text})
        if turn < 2:
            messages.append({"role": "user", "content": f"Follow-up question {turn + 1}"})

    tracer.table()
    tracer.summary()


def demo_with_caching():
    """Demo 2: Same 3-turn loop WITH caching enabled."""
    print("\n" + "="*80)
    print("DEMO 2: SAME 3-TURN LOOP WITH CACHING ENABLED")
    print("="*80 + "\n")

    mock_client = MockAnthropicClient(
        cache_strategy=CacheStrategy.FULL,
        system_prefix_tokens=900
    )
    tracer = TokenTracer(mock_client, verbose=True)

    # Queue same responses but with cache simulation
    mock_client.queue_scenario(SCENARIO_3_TURN_WITH_CACHE)

    messages = [{"role": "user", "content": "What is Python?"}]

    for turn in range(3):
        response = tracer.create_message(
            model="mock-model",
            max_tokens=1024,
            system=[{"type": "text", "text": "You are a helpful assistant.", "cache_control": {"type": "ephemeral"}}],
            messages=messages
        )

        messages.append({"role": "assistant", "content": response.content[0].text})
        if turn < 2:
            messages.append({"role": "user", "content": f"Follow-up question {turn + 1}"})

    tracer.table()
    tracer.summary()


def demo_long_loop():
    """Demo 3: Longer 5-turn loop to see compounding costs."""
    print("\n" + "="*80)
    print("DEMO 3: 5-TURN LOOP WITH CACHING (SHOWS COMPOUNDING)")
    print("="*80 + "\n")

    mock_client = MockAnthropicClient(
        cache_strategy=CacheStrategy.FULL,
        system_prefix_tokens=900
    )
    tracer = TokenTracer(mock_client, verbose=True)

    mock_client.queue_scenario(SCENARIO_5_TURN_LONG_LOOP)

    messages = [{"role": "user", "content": "Complex multi-turn task"}]

    for turn in range(5):
        response = tracer.create_message(
            model="mock-model",
            max_tokens=1024,
            system=[{"type": "text", "text": "You are expert problem solver.", "cache_control": {"type": "ephemeral"}}],
            messages=messages
        )

        messages.append({"role": "assistant", "content": response.content[0].text})
        if turn < 4:
            messages.append({"role": "user", "content": f"Continue working on this task"})

    tracer.table()
    tracer.summary()


def demo_comparison():
    """Demo 4: Side-by-side comparison of WITH vs WITHOUT caching."""
    print("\n" + "="*80)
    print("DEMO 4: SIDE-BY-SIDE COMPARISON: NO CACHE vs WITH CACHE")
    print("="*80 + "\n")

    # WITHOUT caching
    print("\n--- Without Caching ---\n")
    client_no_cache = MockAnthropicClient(
        cache_strategy=CacheStrategy.NO_CACHE,
        system_prefix_tokens=900
    )
    tracer_no_cache = TokenTracer(client_no_cache, verbose=False)
    client_no_cache.queue_scenario(SCENARIO_3_TURN_NO_CACHE)

    messages = [{"role": "user", "content": "Question"}]
    for turn in range(3):
        response = tracer_no_cache.create_message(
            model="mock",
            messages=messages
        )
        messages.append({"role": "assistant", "content": response.content[0].text})
        if turn < 2:
            messages.append({"role": "user", "content": "Follow-up"})

    tracer_no_cache.summary()
    no_cache_cost = tracer_no_cache.get_cumulative_cost()

    # WITH caching
    print("\n--- With Caching ---\n")
    client_with_cache = MockAnthropicClient(
        cache_strategy=CacheStrategy.FULL,
        system_prefix_tokens=900
    )
    tracer_with_cache = TokenTracer(client_with_cache, verbose=False)
    client_with_cache.queue_scenario(SCENARIO_3_TURN_WITH_CACHE)

    messages = [{"role": "user", "content": "Question"}]
    for turn in range(3):
        response = tracer_with_cache.create_message(
            model="mock",
            messages=messages
        )
        messages.append({"role": "assistant", "content": response.content[0].text})
        if turn < 2:
            messages.append({"role": "user", "content": "Follow-up"})

    tracer_with_cache.summary()
    with_cache_cost = tracer_with_cache.get_cumulative_cost()

    # Comparison
    print("\n" + "="*70)
    print("COMPARISON")
    print("="*70)
    print(f"Without caching: {no_cache_cost:.0f}t")
    print(f"With caching:    {with_cache_cost:.0f}t")
    print(f"Savings:         {no_cache_cost - with_cache_cost:.0f}t ({(1 - with_cache_cost/no_cache_cost)*100:.1f}%)")
    print("="*70)


def demo_custom_scenario():
    """Demo 5: Create a custom scenario and analyze it."""
    print("\n" + "="*80)
    print("DEMO 5: CUSTOM SCENARIO - TOOL USE AGENT")
    print("="*80 + "\n")

    # Create custom scenario: agent that uses tools
    client = MockAnthropicClient(
        cache_strategy=CacheStrategy.FULL,
        system_prefix_tokens=1200  # Larger system (system + tools)
    )
    tracer = TokenTracer(client, verbose=True)

    # Tool use scenario: query -> tool call -> result -> answer
    custom_scenario = [
        ("I'll search for this information.", 1200, 50),  # Turn 1: tool call
        ("Based on the search results...", 2500, 80),     # Turn 2: process result
        ("Here's the answer.", 2800, 120),                # Turn 3: final answer
    ]

    client.queue_scenario(custom_scenario)

    messages = [{"role": "user", "content": "Find information about X"}]

    for turn in range(3):
        response = tracer.create_message(
            model="mock",
            max_tokens=2048,
            system=[
                {
                    "type": "text",
                    "text": "You are a research assistant with tools: search, fetch, analyze",
                    "cache_control": {"type": "ephemeral"}
                }
            ],
            messages=messages
        )

        messages.append({"role": "assistant", "content": response.content[0].text})
        if turn < 2:
            messages.append({"role": "user", "content": "Continue..."})

    tracer.table()
    tracer.summary()


if __name__ == "__main__":
    # Run all demos
    demo_basic_3_turn()
    demo_with_caching()
    demo_long_loop()
    demo_comparison()
    demo_custom_scenario()

    print("\n" + "="*80)
    print("ALL DEMOS COMPLETE")
    print("="*80)
    print("""
Key Takeaways:

1. WITHOUT Caching: Full token cost for entire history on every turn
   - Turn 3 costs the most (largest history)
   - Linear growth in per-turn cost

2. WITH Caching: System/tools cached at 1.25x, read at 0.1x
   - Turn 1 has cache write premium
   - Turns 2+ benefit from cheap cache reads
   - Savings accumulate across more turns

3. Caching is worth it when:
   - Same system prompt + tools used multiple times
   - Break-even is ~2-3 turns
   - Savings increase with loop depth

4. Custom Scenarios:
   - Use MockAnthropicClient to test your own token patterns
   - Queue responses with realistic token counts
   - Analyze results without API costs
""")

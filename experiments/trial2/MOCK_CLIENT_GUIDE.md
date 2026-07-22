# Mock Client Guide: Test Without API Keys

The `MockAnthropicClient` lets you test and analyze token usage patterns **without needing any API keys or authentication**. It simulates the Anthropic API behavior with configurable token counts and caching.

## Why Use Mock Client?

✅ **No API keys needed** — Runs completely offline  
✅ **No API costs** — Full control, zero billing  
✅ **Deterministic** — Same results every time  
✅ **Scenario testing** — Test edge cases easily  
✅ **Fast feedback** — Instant responses  
✅ **Educational** — Learn token accounting without real calls  

## Quick Start

```bash
python3 demo_mock.py
```

This runs 5 different demos showing token accounting with and without caching.

## Basic Usage

```python
from token_tracer import TokenTracer
from mock_client import MockAnthropicClient, CacheStrategy

# Create mock client with caching enabled
mock_client = MockAnthropicClient(
    cache_strategy=CacheStrategy.FULL,
    system_prefix_tokens=900
)

# Wrap with tracer
tracer = TokenTracer(mock_client, verbose=True)

# Queue responses you want to get back
mock_client.queue_response(
    text="Here's the answer to turn 1",
    input_tokens=900,
    output_tokens=30
)

# Use like normal client.messages.create()
response = tracer.create_message(
    model="mock-model",
    messages=[{"role": "user", "content": "Hello"}]
)

# Get reports
tracer.table()
tracer.summary()
```

## Cache Strategies

### NO_CACHE
No caching simulation—all tokens billed at full rate every turn.

```python
mock_client = MockAnthropicClient(
    cache_strategy=CacheStrategy.NO_CACHE,
    system_prefix_tokens=900
)
```

**Output:** Every turn costs full price, no cache reads.

### SIMPLE  
Basic caching—50% of system prompt cached.

```python
mock_client = MockAnthropicClient(
    cache_strategy=CacheStrategy.SIMPLE,
    system_prefix_tokens=900
)
```

**Output:** Turn 1 caches 450t, turns 2+ read it at 0.1x.

### FULL (Recommended)
Full caching simulation—entire system prefix cached on turn 1, read from cache on turns 2+.

```python
mock_client = MockAnthropicClient(
    cache_strategy=CacheStrategy.FULL,
    system_prefix_tokens=900
)
```

**Output:** Turn 1 writes 900t at 1.25x, turns 2+ read 900t at 0.1x.

## Queueing Responses

### Single Response
```python
mock_client.queue_response(
    text="Response text here",
    input_tokens=1000,
    output_tokens=50
)
```

### Multiple Responses at Once
```python
mock_client.queue_scenario([
    ("Response 1", 900, 30),
    ("Response 2", 1200, 40),
    ("Response 3", 1500, 100),
])
```

### Pre-built Scenarios
```python
from mock_client import (
    SCENARIO_3_TURN_NO_CACHE,
    SCENARIO_3_TURN_WITH_CACHE,
    SCENARIO_5_TURN_LONG_LOOP,
    SCENARIO_TOOL_USE,
)

mock_client.queue_scenario(SCENARIO_3_TURN_WITH_CACHE)
```

## Example: Custom Scenario

Test a custom agent workflow without any API keys:

```python
from token_tracer import TokenTracer
from mock_client import MockAnthropicClient, CacheStrategy

def test_my_agent():
    # Setup
    mock_client = MockAnthropicClient(
        cache_strategy=CacheStrategy.FULL,
        system_prefix_tokens=1500  # system + tools
    )
    tracer = TokenTracer(mock_client, verbose=False)
    
    # Define your scenario
    # (text, input_tokens, output_tokens)
    scenario = [
        ("Searching...", 1500, 40),    # Turn 1: tool call
        ("Found results!", 3000, 60),   # Turn 2: process results
        ("Final answer.", 3500, 150),   # Turn 3: response
    ]
    mock_client.queue_scenario(scenario)
    
    # Simulate agent loop
    messages = [{"role": "user", "content": "Question"}]
    for turn in range(3):
        response = tracer.create_message(
            model="mock",
            messages=messages
        )
        messages.append({"role": "assistant", "content": response.content[0].text})
        if turn < 2:
            messages.append({"role": "user", "content": "Continue"})
    
    # Analyze
    tracer.table()
    tracer.summary()
```

**Output will show:**
- Turn 1: Cache write (1.25x premium on 1500t)
- Turns 2-3: Cache reads (0.1x savings on 1500t each)
- Total savings: ~35% compared to no caching

## Real-World Example: Comparing Strategies

```python
from token_tracer import TokenTracer
from mock_client import MockAnthropicClient, CacheStrategy

def compare_caching_strategies():
    scenarios = [
        ("No Cache", CacheStrategy.NO_CACHE),
        ("Simple (50%)", CacheStrategy.SIMPLE),
        ("Full Cache", CacheStrategy.FULL),
    ]
    
    for name, strategy in scenarios:
        print(f"\n=== {name} ===\n")
        
        mock_client = MockAnthropicClient(
            cache_strategy=strategy,
            system_prefix_tokens=1000
        )
        tracer = TokenTracer(mock_client, verbose=False)
        
        # Same scenario for all
        mock_client.queue_scenario([
            ("Turn 1", 1000, 50),
            ("Turn 2", 1500, 60),
            ("Turn 3", 2000, 80),
            ("Turn 4", 2500, 100),
        ])
        
        # Run loop
        messages = [{"role": "user", "content": "Q"}]
        for i in range(4):
            r = tracer.create_message(model="m", messages=messages)
            messages.append({"role": "assistant", "content": r.content[0].text})
            if i < 3:
                messages.append({"role": "user", "content": "Q"})
        
        # Show results
        tracer.summary()
```

## Advanced: Testing Thinking Blocks

Thinking blocks are reprocessed as input on downstream turns, multiplying cost:

```python
mock_client = MockAnthropicClient(
    cache_strategy=CacheStrategy.FULL,
    system_prefix_tokens=900
)
tracer = TokenTracer(mock_client)

# Turn 1: Extended thinking (5000t thinking tokens in output)
mock_client.queue_response(
    text="Thinking...",
    input_tokens=900,    # system
    output_tokens=5050   # 5000 thinking + 50 text
)

# Turn 2: That thinking becomes input (reprocessed)
mock_client.queue_response(
    text="Result...",
    input_tokens=6000,   # system (900) + prior thinking (5050)
    output_tokens=100
)

# Tracer will show how thinking multiplies cost
tracer.table()
tracer.summary()
```

## Pre-built Scenarios Reference

### SCENARIO_3_TURN_NO_CACHE
Basic 3-turn loop without any caching.
- Turn 1: 900t input, 30t output
- Turn 2: 1400t input, 40t output  
- Turn 3: 1700t input, 200t output
- **Total: 4,270t** (no savings)

### SCENARIO_3_TURN_WITH_CACHE
Same loop but with 900t prefix cached.
- Turn 1: 900t → 1.25x (write), 30t output
- Turn 2: 1400t (900 cached @ 0.1x + 500 new), 40t output
- Turn 3: 1700t (900 cached @ 0.1x + 800 new), 200t output
- **Total: 2,875t** (35% savings)

### SCENARIO_5_TURN_LONG_LOOP
Longer loop showing cache benefit increasing with depth.
- Turns 1-5 with growing input/output
- **Shows: Savings increase from 35% (3 turns) to 41% (5 turns)**

### SCENARIO_TOOL_USE
Agent that calls tools (simulated).
- Turn 1: Initial query → tool call
- Turn 2: Process tool result
- Turn 3: Generate final answer
- **Shows: Tool results inflate input tokens on next turn**

## Connecting to Real API (When You Have Keys)

Switch from mock to real client seamlessly:

```python
# Option 1: Use real client
from anthropic import Anthropic
from token_tracer import TokenTracer

client = Anthropic()  # Real API
tracer = TokenTracer(client)
response = tracer.create_message(model="claude-opus-4-8", ...)

# Option 2: Use mock client (no keys needed)
from mock_client import MockAnthropicClient

client = MockAnthropicClient()  # Offline simulation
tracer = TokenTracer(client)
response = tracer.create_message(model="mock", ...)

# Same tracer code works with both!
```

## Understanding Mock Output

When you run the demo, you'll see:

```
[Turn 1] Input: 900t (pred: 912t) | cache_write: 900t | Output: 30t | Turn cost: 1155t
[Turn 2] Input: 1400t (pred: 936t) | cache_read: 900t | Output: 40t | Turn cost: 630t
[Turn 3] Input: 1700t (pred: 964t) | cache_read: 900t | Output: 200t | Turn cost: 1090t
```

- **pred: 912t** — count_tokens predicted before sending
- **actual: 900t** — what mock returned (matches queued input)
- **cache_write: 900t** — Turn 1 writes system prompt to cache
- **cache_read: 900t** — Turns 2-3 read it back at 0.1x cost
- **Turn cost** — Actual amount billed this turn

## Creating Your Own Test

```python
def test_my_scenario():
    from token_tracer import TokenTracer
    from mock_client import MockAnthropicClient, CacheStrategy
    
    # 1. Create mock client
    mock_client = MockAnthropicClient(
        cache_strategy=CacheStrategy.FULL,
        system_prefix_tokens=1200
    )
    
    # 2. Queue realistic responses (your token estimates)
    mock_client.queue_scenario([
        ("Initial response", 1200, 50),
        ("Second response", 2000, 75),
        ("Final response", 2800, 150),
    ])
    
    # 3. Wrap with tracer
    tracer = TokenTracer(mock_client)
    
    # 4. Run agent loop
    messages = [{"role": "user", "content": "Start"}]
    for i in range(3):
        response = tracer.create_message(model="m", messages=messages)
        messages.append({"role": "assistant", "content": response.content[0].text})
        if i < 2:
            messages.append({"role": "user", "content": "Continue"})
    
    # 5. Analyze
    print(f"Total cost: {tracer.get_cumulative_cost():.0f}t")
    print(f"Savings: {tracer.get_cache_savings():.0f}t")
    tracer.summary()
```

## No Dependencies Required

The mock client has **zero dependencies**—only Python 3.7+.

```bash
# No pip install needed!
python3 demo_mock.py
```

When you get API keys and want to try the real thing, just:

```bash
pip install anthropic
python3 demo_agent.py
```

Both demos use the same `TokenTracer` class—the only difference is the client.

## FAQs

**Q: Can I test the same scenario with real API later?**  
A: Yes! Just queue realistic token estimates now, then swap in the real client when ready.

**Q: How do I know what token counts to use?**  
A: Use `claude.ai/tokens` or the `count_tokens()` API on real responses, then use those numbers in your mock scenarios.

**Q: What if my scenario doesn't match reality?**  
A: The math stays the same. The tracer proves token accounting logic; real counts just change the absolute numbers.

**Q: Can I use mock with multiple turns/loops?**  
A: Yes. Queue as many responses as you need, and the mock will serve them in order.

---

## Next Steps

1. **Run the demo:** `python3 demo_mock.py`
2. **Study the output:** See how cache affects each turn
3. **Modify a scenario:** Change token counts and rerun
4. **Test your own workflow:** Copy demo_mock.py and customize
5. **Get API keys when ready:** Switch to real client (same code works!)

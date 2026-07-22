# Trial 2: Agent Loop Token Tracer

A lightweight wrapper around the Anthropic client that intercepts API calls to track and analyze token usage in agentic LLM workflows.

## What's Inside

- **`token_tracer.py`** — The core `TokenTracer` class that wraps `client.messages.create()` and logs token usage at each turn
- **`demo_agent.py`** — Example agent loop showing how to use the tracer in a multi-turn conversation
- **`requirements.txt`** — Dependencies (just `anthropic`)

## Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Set your API key
```bash
export ANTHROPIC_API_KEY="your-key-here"
```

### 3. Run the demo
```bash
python demo_agent.py
```

## How It Works

### Basic Usage

```python
from anthropic import Anthropic
from token_tracer import TokenTracer

# Create client and tracer
client = Anthropic()
tracer = TokenTracer(client, verbose=True)

# Use tracer.create_message() instead of client.messages.create()
response = tracer.create_message(
    model="claude-opus-4-8",
    max_tokens=1024,
    system=[{"type": "text", "text": "You are helpful.", "cache_control": {"type": "ephemeral"}}],
    messages=[{"role": "user", "content": "Hello"}]
)

# Get reports
tracer.table()      # Detailed table of each turn
tracer.summary()    # High-level cost summary
```

### What It Tracks

Each turn logs:
- **predicted_input** — Tokens estimated before sending (via `count_tokens()`)
- **actual_input** — Tokens the API actually processed
- **cache_read** — Tokens served from cache at 0.1× cost
- **cache_write** — Tokens written to cache at 1.25× cost
- **output** — Tokens the model generated (always full price)
- **turn_cost** — What you paid this turn accounting for cache
- **cumulative** — Running total across all turns

## Example Output

```
[Turn 1] Input: 900t (pred: 900t) | cache_write: 900t | Output: 30t | Turn cost: 1155t
[Turn 2] Input: 1400t (pred: 1400t) | cache_read: 900t | Output: 40t | Turn cost: 630t
[Turn 3] Input: 1700t (pred: 1700t) | cache_read: 900t | Output: 200t | Turn cost: 990t

==============================================================================================================================
TOKEN USAGE BY TURN
==============================================================================================================================
Turn   Pred Input   Actual Input    Cache Read   Cache Write   Output     Turn Cost    Cumulative  
----------------------------------------------------------------------------------------------------------------------
1      900          900             0            900            30         1155         1155        
2      1400         1400            900          0              40         630          1785        
3      1700         1700            900          0              200        990          2775        
==============================================================================================================================

==============================================================
SUMMARY
==============================================================
Total turns:              3
Total input tokens:       4,000
Total output tokens:      270
Total cache reads:        1,800 (cost: 180t @ 0.1x)
Total cache writes:       900 (cost: 1125t @ 1.25x)
Uncached input:           1,300 (cost: 1300t @ 1.0x)

Actual total cost:        2775t
Without caching:          4270t
Savings from caching:     1495t (35.0%)
==============================================================
```

## Key Insights

1. **Cache is worth it** — Even a small 900-token prefix saves ~1,500 tokens over 3 turns (35% savings)
2. **Prefix match matters** — Any byte difference in the cached portion invalidates the whole cache
3. **Break-even is fast** — At 2-3 turns, caching pays for the 1.25x write premium
4. **Thinking amplifies costs** — Extended thinking blocks are reprocessed as input on every downstream turn

## Testing with Different Models

The tracer works with any model, but caching is only available on certain models:

```python
# Caching supported on:
tracer.create_message(model="claude-opus-4-8", ...)  # ✅ supports caching
tracer.create_message(model="claude-sonnet-5", ...)  # ✅ supports caching
tracer.create_message(model="claude-haiku-4-5", ...) # ❌ no caching
```

## Common Use Cases

### 1. Measure agent loop efficiency
```python
tracer = TokenTracer(client)
# Run multi-turn loop...
tracer.summary()  # See total cost and savings
```

### 2. Optimize caching strategy
Move `cache_control` to different parts of the prompt and run the tracer to see which placement saves the most tokens.

### 3. Compare with/without caching
Run the same agent loop twice — once with `cache_control` and once without — and compare `tracer.summary()` output.

### 4. Budget tracking
```python
for turn in tracer.turns:
    print(f"Turn {turn.turn_num}: {turn.total_this_turn:.0f}t")

# Stop if cumulative cost exceeds budget
if tracer.get_cumulative_cost() > budget:
    break
```

## API Reference

### TokenTracer

```python
class TokenTracer:
    def __init__(self, client: Anthropic, verbose: bool = True)
    def create_message(self, **kwargs) -> dict  # Drop-in for client.messages.create()
    def table(self) -> None                     # Print detailed turn-by-turn table
    def summary(self) -> None                   # Print high-level cost summary
    def get_cumulative_cost(self) -> float      # Total cost across all turns
    def get_cache_savings(self) -> float        # Total tokens saved by caching
    @property
    def turns: list[TokenTurn]                  # Access raw turn data
```

### TokenTurn (dataclass)

```python
@dataclass
class TokenTurn:
    turn_num: int              # Turn number (1-indexed)
    predicted_input: int       # Tokens predicted via count_tokens()
    actual_input: int          # Tokens actually billed
    cache_read: int            # Tokens from cache (0.1x cost)
    cache_write: int           # Tokens to cache (1.25x cost)
    output: int                # Model output tokens (1.0x cost)
    thinking: int = 0          # Extended thinking tokens (if enabled)
    
    @property
    def total_this_turn(self) -> float         # Actual cost this turn
    @property
    def cumulative_savings(self) -> float      # Savings vs if nothing cached
```

## Notes

- The tracer calls `count_tokens()` before each request, which may add slight latency
- Cache hit/write info is available only on models that support prompt caching
- Output tokens are never cached (always full price)
- Thinking blocks are reprocessed as input on downstream turns (costs accumulate)

## Next Steps

- See the learning document at `/home/trupti/.claude/projects/-home-trupti-Projects-tokenCostGen/memory/agentic_token_lifecycle.md` for deep context on token accounting
- Run `demo_agent.py` to see caching in action
- Integrate the tracer into your own agent workflow to track real costs

# Token Cost Generation - Project Structure

## Overview

This project explores how tokens accumulate in LLM agentic workflows and provides tools to analyze token usage at each step.

**Primary Research Document:** See `/home/trupti/.claude/projects/-home-trupti-Projects-tokenCostGen/memory/agentic_token_lifecycle.md` for a comprehensive explanation of token accounting concepts.

---

## Trial 1: Existing Token Analysis

**Location:** `/trial1/`

This is the original project code that likely does basic token counting and cost calculation.

### Files

- `main.py` — Entry point
- `tokenizer.py` — Token utilities
- `src/` — Modular components
  - `calculator.py` — Token calculations
  - `display.py` — Output formatting
  - `pricing.py` — Model pricing data
  - `tokenizer.py` — Tokenization logic
- `README.md` — Original project documentation
- `requirements.txt` — Dependencies

### Purpose

Static token analysis—likely takes a prompt/conversation and calculates total tokens without tracking the accumulation across multiple turns or caching effects.

---

## Trial 2: Agent Loop Token Tracer (New)

**Location:** `/trial2/`

A new implementation focused on **dynamic token tracking** throughout an agentic workflow—the heart of the learning request.

### Files

- **`token_tracer.py`** — Core implementation
  - `TokenTurn` dataclass — Tracks a single turn's metrics
  - `TokenTracer` wrapper class — Intercepts API calls, predicts, logs actual usage
  - Methods: `create_message()`, `table()`, `summary()`, `get_cumulative_cost()`, `get_cache_savings()`

- **`demo_agent.py`** — Working example
  - 3-turn agent loop with system prompt and tools
  - Shows real API calls with caching enabled
  - Prints live feedback after each turn + detailed reports

- **`requirements.txt`** — Just `anthropic` SDK

- **`README.md`** — Complete usage guide with examples

### What It Does

1. **Intercepts** each `client.messages.create()` call
2. **Predicts** input tokens via `count_tokens()` before sending
3. **Executes** the actual API call
4. **Captures** actual usage from response (input, cache_read, cache_write, output)
5. **Logs** the turn with all metrics
6. **Reports** via:
   - Live per-turn feedback (if `verbose=True`)
   - `table()` — Formatted turn-by-turn breakdown
   - `summary()` — Total costs, cache impact, savings percentage

### Key Insights It Captures

- **Token Accumulation** — How history is reprocessed on every turn
- **Cache Effectiveness** — Cache reads at 0.1x, writes at 1.25x
- **Break-Even Analysis** — When caching pays off (~2-3 turns)
- **Thinking Block Impact** — How extended thinking multiplies costs across turns
- **Cumulative Cost** — Total spend across entire agent loop

---

## How They Work Together

```
User Request
    ↓
Trial 1: Static analysis        Trial 2: Dynamic tracking
├─ Tokenize text                ├─ Wrap client
├─ Count tokens                 ├─ Predict tokens (count_tokens API)
├─ Apply pricing                ├─ Execute API call
├─ Show total                   ├─ Capture actual usage
└─ Fixed output                 ├─ Track cache effects
                                ├─ Log per-turn metrics
                                ├─ Report cumulative costs
                                └─ Show savings %, break-even
```

**Use Trial 1 when:** You have a single prompt/conversation and want quick cost estimates.

**Use Trial 2 when:** You want to understand how tokens flow through a multi-turn agent loop and optimize for cache hits.

---

## Quick Start

### Setup Environment

```bash
# Install anthropic SDK
pip install anthropic

# Export API key
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Try Trial 2 (Recommended First)

```bash
cd trial2
python demo_agent.py
```

This will show:
- 3 turns of an agent loop
- Live token counts after each turn
- Detailed table of metrics
- Summary with cache savings %

### Integrate Into Your Workflow

```python
from trial2.token_tracer import TokenTracer
from anthropic import Anthropic

client = Anthropic()
tracer = TokenTracer(client)

# Use tracer.create_message() anywhere you'd use client.messages.create()
response = tracer.create_message(
    model="claude-opus-4-8",
    max_tokens=1024,
    system=[{"type": "text", "text": "You are helpful.", "cache_control": {"type": "ephemeral"}}],
    messages=[{"role": "user", "content": "Hello"}]
)

tracer.table()
tracer.summary()
```

---

## Learning Resources

### Theory (Recommended First)

**File:** `/home/trupti/.claude/projects/-home-trupti-Projects-tokenCostGen/memory/agentic_token_lifecycle.md`

Covers:
- Token accounting at each stage
- 3-turn example with/without caching
- Token flow mechanics
- Cost formulas
- Practical implications
- How to analyze your own agent

**Key Formulas:**
```
Total cost (no cache) = Σ(input[i] + output[i]) for i=1..N
Cached prefix cost    = prefix_tokens × 1.25 (write) + prefix_tokens × (N-1) × 0.1 (reads) + output
Break-even:           N > ~2.78 turns for 5-min TTL cache
```

### Implementation

**File:** `trial2/README.md`

Practical guide with:
- Usage examples
- API reference
- Common use cases
- Output interpretation

---

## Token Accounting Quick Reference

| Concept | Behavior |
|---------|----------|
| **Input Tokens** | Full conversation history billed on every turn |
| **Output Tokens** | One-time cost per response (never cached) |
| **Cache Write** | 1.25× cost for marked content first turn |
| **Cache Read** | 0.1× cost for reused cached content |
| **Break-Even** | 2-3 turns before cache premium is paid back |
| **Thinking** | Reprocessed as input on downstream turns = multiplied cost |

---

## File Tree

```
tokenCostGen/
├── trial1/                           # Original project (static analysis)
│   ├── main.py
│   ├── tokenizer.py
│   ├── requirements.txt
│   ├── README.md
│   └── src/
│       ├── __init__.py
│       ├── calculator.py
│       ├── display.py
│       ├── pricing.py
│       └── tokenizer.py
│
├── trial2/                           # New implementation (dynamic tracing)
│   ├── token_tracer.py              ✓ Core TokenTracer class
│   ├── demo_agent.py                ✓ Working 3-turn example
│   ├── requirements.txt
│   └── README.md
│
├── PROJECT_STRUCTURE.md              # This file
├── req.md                            # Original requirements
└── .venv/                            # Virtual environment
```

---

## Next Steps

1. **Read the theory:** Open `/home/trupti/.claude/projects/-home-trupti-Projects-tokenCostGen/memory/agentic_token_lifecycle.md`
2. **Run the demo:** `cd trial2 && python demo_agent.py`
3. **Integrate:** Copy `trial2/token_tracer.py` into your agent
4. **Experiment:** Try different cache strategies and compare savings

---

## Questions?

- **How do tokens accumulate?** → See agentic_token_lifecycle.md
- **How does caching work?** → See trial2/README.md
- **How do I use the tracer?** → See demo_agent.py
- **What's the break-even point?** → Run demo and check "Savings" line

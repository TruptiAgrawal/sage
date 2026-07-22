# Trial 2: Complete Contents

All files in trial2/ with their purpose and how to use them.

## Core Implementation

### `token_tracer.py` (190 lines)
**Purpose:** Production-ready wrapper around Anthropic client (or mock client).

**Contains:**
- `TokenTurn` dataclass — Tracks metrics for a single turn
- `TokenTracer` class — Intercepts API calls, predicts tokens, logs actual usage

**Key Methods:**
- `create_message(**kwargs)` — Drop-in replacement for `client.messages.create()`
- `table()` — Print formatted turn-by-turn breakdown
- `summary()` — Print cost summary and cache savings
- `get_cumulative_cost()` — Total tokens spent
- `get_cache_savings()` — Total tokens saved by caching

**Usage:**
```python
from token_tracer import TokenTracer
tracer = TokenTracer(client)  # client = Anthropic() or MockAnthropicClient()
response = tracer.create_message(model="...", messages=[...])
tracer.summary()
```

**Works with:**
- Real Anthropic client (requires `pip install anthropic`)
- Mock client (requires nothing)

---

### `mock_client.py` (260 lines)
**Purpose:** Simulates Anthropic API for testing without API keys.

**Contains:**
- `MockUsage` — Simulates response.usage
- `MockResponse` — Simulates API response structure
- `CacheStrategy` enum — NO_CACHE, SIMPLE, FULL
- `MockAnthropicClient` — Drop-in mock for Anthropic()
- Pre-built scenarios: SCENARIO_3_TURN_*, SCENARIO_5_TURN_*, SCENARIO_TOOL_USE

**Key Methods:**
- `queue_response(text, input_tokens, output_tokens)` — Add single response
- `queue_scenario(list)` — Add multiple responses
- `messages.count_tokens(**kwargs)` — Predict tokens before sending
- `messages.create(**kwargs)` — Return simulated response
- `reset()` — Clear for new scenario

**Usage:**
```python
from mock_client import MockAnthropicClient, CacheStrategy

mock = MockAnthropicClient(
    cache_strategy=CacheStrategy.FULL,
    system_prefix_tokens=900
)
mock.queue_scenario([
    ("Response 1", 900, 30),
    ("Response 2", 1400, 40),
    ("Response 3", 1700, 200),
])
```

**Simulation Behavior:**
- **NO_CACHE:** Every turn billed at full rate
- **SIMPLE:** ~50% of system cached
- **FULL:** Entire system prefix cached on turn 1, read at 0.1x on turns 2+

---

## Demo & Examples

### `demo_agent.py` (230 lines)
**Purpose:** Real 3-turn agent loop with Anthropic API (requires API key).

**What It Does:**
1. Creates system prompt with cache control
2. Defines mock tools (search_documents, fetch_page)
3. Runs 3-turn conversation
4. Tracks tokens with TokenTracer
5. Prints reports

**Usage:**
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
python3 demo_agent.py
```

**Output:**
- Live feedback after each turn
- Detailed token table
- Summary with cache savings percentage

**Best For:**
- Understanding how TokenTracer works with real API
- Seeing actual token counts from Claude
- Validating caching in practice

---

### `demo_mock.py` (230 lines)
**Purpose:** 5 complete demos using mock client (NO API KEY NEEDED).

**Included Demos:**

1. **DEMO 1: 3-Turn Without Caching**
   - Shows baseline costs
   - Every turn bills full history
   - Total: 4,270t

2. **DEMO 2: Same 3-Turn WITH Caching**
   - Turn 1: Write cache (1.25x)
   - Turns 2-3: Read cache (0.1x)
   - Total: 2,875t (35% savings)

3. **DEMO 3: 5-Turn Long Loop**
   - Shows cache benefit increases with loop depth
   - Savings grow to 41% with 5 turns

4. **DEMO 4: Direct Comparison**
   - Side-by-side without vs with caching
   - Shows exact savings calculation

5. **DEMO 5: Tool Use Scenario**
   - Simulates agent calling tools
   - Shows how tool results inflate input on next turn

**Usage:**
```bash
python3 demo_mock.py
```

**No installation needed.** Pure Python with standard library.

**Output:** 
- All 5 demos run automatically
- ~350 lines of formatted output
- Shows token accounting at each step
- Demonstrates cache effectiveness

---

## Documentation

### `README.md` (230 lines)
**Purpose:** Complete usage guide for trial2.

**Covers:**
- Quick start (setup, installation, running)
- How TokenTracer works
- What it tracks (predicted, actual, cache_read, cache_write, output, cost)
- Example output
- Key insights about caching
- Testing with different models
- Common use cases
- Full API reference
- Notes and limitations

**Use:** Reference for understanding the implementation.

---

### `MOCK_CLIENT_GUIDE.md` (400+ lines)
**Purpose:** In-depth guide for using MockAnthropicClient.

**Covers:**
- Why use mock client (no keys, no costs, deterministic)
- Quick start example
- Cache strategies explained
- How to queue responses
- Pre-built scenarios
- Real-world example (comparing strategies)
- Advanced testing (thinking blocks)
- Scenario reference
- Custom test creation
- FAQs

**Use:** Go-to reference for offline testing.

---

### `TRIAL2_CONTENTS.md` (This File)
**Purpose:** Index of all files in trial2/.

**Shows:**
- What each file does
- Key classes and methods
- Usage examples
- When to use each file

---

## File Tree

```
trial2/
├── token_tracer.py              ✓ Core implementation
├── mock_client.py               ✓ Offline testing
├── demo_agent.py                ✓ Real API demo (needs key)
├── demo_mock.py                 ✓ Mock demo (run now!)
├── requirements.txt             ✓ Dependencies for real API
├── README.md                    ✓ Main guide
├── MOCK_CLIENT_GUIDE.md         ✓ Mock client deep dive
└── TRIAL2_CONTENTS.md           ✓ This file
```

---

## Quick Start Paths

### Path 1: I Don't Have API Keys (START HERE)
```bash
cd trial2
python3 demo_mock.py
```
Takes 10 seconds, shows all 5 demos, no installation needed.

### Path 2: I Have API Keys
```bash
cd trial2
pip install -r requirements.txt
export ANTHROPIC_API_KEY="sk-ant-..."
python3 demo_agent.py
```
Real API calls with actual token tracking.

### Path 3: I Want to Test My Own Scenario
```python
from token_tracer import TokenTracer
from mock_client import MockAnthropicClient

# Use mock (no keys) or real (with keys)
client = MockAnthropicClient()  # or Anthropic()
tracer = TokenTracer(client)

# Queue your scenario
client.queue_scenario([
    ("Response 1", 900, 30),
    ("Response 2", 1400, 40),
])

# Run loop and analyze
messages = [{"role": "user", "content": "Question"}]
for i in range(2):
    response = tracer.create_message(model="m", messages=messages)
    messages.append({"role": "assistant", "content": response.content[0].text})
    if i < 1:
        messages.append({"role": "user", "content": "Follow-up"})

tracer.summary()
```

---

## Key Concepts Demonstrated

### Token Accumulation
Every turn in an agent loop reprocesses the entire prior conversation history:
- Turn 1: 900t (system + message)
- Turn 2: 900t reprocessed + 500t new = 1,400t
- Turn 3: 1,400t reprocessed + 300t new = 1,700t

### Cache Pricing
- **Cache Write:** 1.25x per token (first time)
- **Cache Read:** 0.1x per token (subsequent times)
- **Output:** Always 1.0x (never cached)

### Break-Even
Caching pays for itself in 2-3 turns:
```
Without cache: 900 + 1,400 + 1,700 = 4,000t (full price)
With cache:    1,125 + 630 + 1,090 = 2,845t (35% savings)
```

### Cost Formula
```
turn_cost = (cache_write × 1.25) + (cache_read × 0.1) + (uncached × 1.0) + output
```

---

## Dependencies

### For mock client (recommended first):
None. Pure Python.

### For real Anthropic client:
```bash
pip install -r requirements.txt
# or
pip install anthropic>=0.28.0
```

---

## Common Questions

**Q: Which demo should I run first?**  
A: `python3 demo_mock.py` — Works immediately, no setup.

**Q: Can I switch between mock and real client?**  
A: Yes! TokenTracer works with both. Just change the client.

**Q: What if I want to test a different scenario?**  
A: Copy `demo_mock.py`, modify `queue_scenario()` calls, run it.

**Q: How do I know what token counts to use?**  
A: Use `count_tokens()` on real responses, then feed those into mock scenarios.

**Q: Is this production-ready?**  
A: TokenTracer is. MockAnthropicClient is for testing/learning.

**Q: Can I use this in a real agent?**  
A: Yes! TokenTracer is designed to wrap real clients. Just install anthropic and swap clients.

---

## Next Steps

1. **Run the mock demo:** `python3 demo_mock.py`
2. **Read the learning doc:** See agentic_token_lifecycle.md in memory folder
3. **Try your own scenario:** Modify demo_mock.py with your token estimates
4. **Get API keys later:** Everything works with real client too

---

## Related Files

- **Learning Doc:** `/home/trupti/.claude/projects/-home-trupti-Projects-tokenCostGen/memory/agentic_token_lifecycle.md`
- **Project Overview:** `../PROJECT_STRUCTURE.md`
- **Original Code:** `../trial1/`

---

## Summary Table

| File | Purpose | Run Without Keys | Real API |
|------|---------|-----------------|----------|
| `token_tracer.py` | Core tracer | ✅ (with mock) | ✅ |
| `mock_client.py` | Offline simulation | ✅ | N/A |
| `demo_mock.py` | 5 demo scenarios | ✅ | N/A |
| `demo_agent.py` | Real agent loop | ❌ | ✅ |
| README | Main guide | ✅ | ✅ |
| MOCK_CLIENT_GUIDE | Mock deep dive | ✅ | N/A |

**Start here:** `python3 demo_mock.py` (no setup required)

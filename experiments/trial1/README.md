# Token Cost Calculator

A learning tool to understand how Claude tokenizes prompts and calculates API costs.

Built with modular components so you can see how each piece connects.

## Setup

```bash
uv sync
```

## Usage

Pass your prompt as an argument:
```bash
uv run main.py "Your prompt here"
```

Or run interactively (press Enter twice to submit):
```bash
uv run main.py
```

## How It Works

The tool breaks down into 4 independent modules:

1. **`src/tokenizer.py`** - Tokenizes text using tiktoken (o200k_base encoding)
2. **`src/calculator.py`** - Calculates costs based on token count & pricing
3. **`src/pricing.py`** - Holds Claude model pricing data
4. **`src/display.py`** - Formats results as a nice table

Flow: **Prompt → Tokenize → Calculate → Display**

## Example Output

```
================================================================================
Token Cost Breakdown (Claude 3.5 Sonnet)
================================================================================
Token Type           Count       Rate (per 1M)             Cost
--------------------------------------------------------------------------------
Input                   15              $3.00        $0.000045
Output                    0             $15.00        $0.000000
Reasoning                 0                  —        $0.000000
Cache                     0                  —        $0.000000
--------------------------------------------------------------------------------
TOTAL                    15                         $0.000045
================================================================================
```

## Models Supported

- `sonnet` - Claude 3.5 Sonnet (default)
- `opus` - Claude 3 Opus
- `haiku` - Claude 3 Haiku

## Learning Notes

- **Tokens**: Text broken into small chunks. ~1 token ≈ 4 characters
- **Input tokens**: Tokens in your prompt
- **Output tokens**: Tokens the model generates (not counted in learning mode)
- **Pricing**: Per 1 million tokens, varies by model

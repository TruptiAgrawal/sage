# Response Analyzer Tool

Analyzes test prompt responses from the `test_prompt_answers/` folder and generates a comprehensive CSV with quality metrics.

## Output Columns

- **Model Name**: Claude model used (e.g., claude-opus-4-8)
- **Prompt**: The user's question/prompt (first 200 chars)
- **Input Tokens**: Estimated tokens in the user prompt
- **Output Tokens**: Estimated tokens in the assistant response
- **Quality Category**: Rating category (Excellent, Good, Fair, Poor)
- **Feedback**: Brief feedback on accuracy, clarity, and helpfulness

## Installation

```bash
# Install Anthropic SDK
pip install anthropic
```

## Setup

Set your Anthropic API key:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

## Usage

### Basic Usage (Default Settings)

```bash
python3 response_analyzer.py
```

This will:
- Read all `prompt*response.txt` files from `test_prompt_answers/`
- Use `claude-opus-4-8` for quality ratings
- Output to `responses_analysis.csv`

### Custom Model

```bash
python3 response_analyzer.py --model claude-sonnet-4-20250514
```

### Custom Input/Output Paths

```bash
python3 response_analyzer.py \
  --input-dir test_prompt_answers \
  --output my_analysis.csv \
  --model claude-opus-4-8
```

### Export as JSON

```bash
python3 response_analyzer.py --format json
```

### Export Both CSV and JSON

```bash
python3 response_analyzer.py --format both
```

## Output Example

```csv
Model Name,Prompt,Input Tokens,Output Tokens,Quality Category,Feedback
claude-opus-4-8,What is machine learning?,13,95,Excellent,Accurate and comprehensive explanation with good examples.
claude-opus-4-8,What does AI stand for?,11,120,Excellent,Well-structured answer covering multiple AI approaches.
claude-opus-4-8,Give me an example,9,98,Good,Practical example provided but could be more detailed.
```

## Key Features

✅ **Automatic Token Estimation** - Estimates tokens based on character count
✅ **Claude Quality Rating** - Uses Claude API to rate response quality
✅ **Batch Processing** - Analyzes all 200+ responses automatically
✅ **Multiple Export Formats** - CSV, JSON, or both
✅ **Summary Statistics** - Quality distribution and token usage stats
✅ **Error Handling** - Graceful handling of malformed files

## Quality Categories

- **Good**: Comprehensive, well-structured response with specific examples, directly addresses the question, and demonstrates depth
- **Average**: Adequate response with some good elements but lacks depth, specificity, or structure in some areas
- **Bad**: Insufficient response that is too brief, unclear, lacks relevance, or fails to adequately address the question

## Token Estimation

The tool estimates tokens using a rough ratio of 1 token per 4 characters. This is an approximation; actual token counts may vary based on the Claude model's tokenizer.

## Advanced Options

```bash
# Show help
python3 response_analyzer.py --help

# Combine all options
python3 response_analyzer.py \
  --input-dir test_prompt_answers \
  --output quality_report.csv \
  --model claude-opus-4-8 \
  --format both
```

## Troubleshooting

### No API Key Error
```
❌ anthropic library not installed
```
**Solution**: `pip install anthropic`

### API Key Not Found
```
Error: Anthropic API key not found
```
**Solution**: `export ANTHROPIC_API_KEY="your-key-here"`

### Directory Not Found
```
❌ Error: Directory not found: test_prompt_answers
```
**Solution**: Ensure the directory exists and use correct path with `--input-dir`

### Parse Errors
Some files may be skipped if they don't follow the standard format. The tool will report skipped files.

## Performance

- Processing time depends on file count and Claude API response time
- With 200 responses: ~10-15 minutes (depending on API latency)
- Each response requires one API call for quality rating

## Output Files

- `responses_analysis.csv` - Quality metrics in CSV format
- `responses_analysis.json` - Full analysis with metadata in JSON format (if using `--format json` or `--format both`)

## Supported Model Names

- `claude-opus-4-8` (default)
- `claude-sonnet-4-20250514`
- `claude-haiku-4-5-20251001`
- Other Claude models available through Anthropic API

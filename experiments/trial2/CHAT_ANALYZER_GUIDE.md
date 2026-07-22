# Chat Analyzer: Extract Token Usage from Chat Transcripts

A complete tool to analyze token usage in any chat transcript, then export and build a database from the results.

## Features

✅ **Multiple input formats** — Generic text, JSON, Markdown  
✅ **Token estimation** — ~1 token per 4 characters  
✅ **Detailed breakdown** — Per-message token counts  
✅ **Export formats** — JSON, CSV for database ingestion  
✅ **Database ready** — JSON schema for SQL/NoSQL setup  
✅ **No dependencies** — Pure Python, runs offline  

## Quick Start

### 1. Analyze a Chat

```bash
python3 chat_analyzer_cli.py your_chat.txt
```

**Output:**
```
======================================================================
CHAT TOKEN ANALYSIS SUMMARY
======================================================================
Total Messages:          42
User Messages:           21
Assistant Messages:      21

Total Tokens:            45,230
  Input (User):          18,500
  Output (Assistant):    26,730

Average per Message:
  User:                  881 tokens
  Assistant:             1,272 tokens
======================================================================

MESSAGE BREAKDOWN
─────────────────────────────────────────────────────────
#    Role         Preview                         Tokens
─────────────────────────────────────────────────────────
1    USER         Hello, can you help me...       125
2    ASSISTANT    Of course! I'd be happy t...    342
3    USER         Great. I need help with...      89
...
```

### 2. Export to JSON (for database)

```bash
python3 chat_analyzer_cli.py your_chat.txt --export json
```

**Creates:** `your_chat-analysis.json`

```json
{
  "metadata": {
    "timestamp": "2026-07-21T15:30:45.123456",
    "total_messages": 42,
    "total_tokens": 45230,
    "input_tokens": 18500,
    "output_tokens": 26730,
    "user_messages": 21,
    "assistant_messages": 21
  },
  "messages": [
    {
      "index": 1,
      "role": "user",
      "tokens": 125,
      "length": 487,
      "preview": "Hello, can you help me with..."
    },
    ...
  ]
}
```

### 3. Export to CSV (for spreadsheets/databases)

```bash
python3 chat_analyzer_cli.py your_chat.txt --export csv
```

**Creates:** `your_chat-analysis.csv`

```csv
Index,Role,Tokens,Length
1,user,125,487
2,assistant,342,1283
3,user,89,316
...
```

### 4. Generate Database Schema

```bash
python3 chat_analyzer_cli.py your_chat.txt --export schema
```

**Creates:** `your_chat-schema.json` with SQL table definitions.

## Input Formats

### Generic Format (Default)

```
User: What is Python?
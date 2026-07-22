# Chat Token Analyzer - Quick Start Guide

## Your New Tool: Chat Analyzer CLI

You now have a complete tool that analyzes token usage from ANY chat transcript and exports data for database building.

### What It Does

1. **Reads** chat transcripts (paste from any LLM chat interface)
2. **Counts** tokens per message (user input vs assistant output)
3. **Summarizes** total tokens and costs
4. **Exports** to JSON/CSV for database ingestion
5. **Generates** database schema

### The Command

```bash
python3 chat_analyzer_cli.py <chat_file.txt> [--format FORMAT] [--export FORMAT]
```

## Usage Examples

### Example 1: Quick Analysis

```bash
# Paste your entire chat transcript into a text file
echo "User: Hello, how are you?
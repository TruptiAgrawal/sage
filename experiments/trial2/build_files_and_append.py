#!/usr/bin/env python3
"""Combine response batches, write individual prompt/response files, run analyzer, append to master CSV."""
import json
import csv
import subprocess
from pathlib import Path

base = Path("/home/trupti/Projects/tokenCostGen/trial2")
answers_dir = base / "test_prompt_answers"

with open(base / "parsed_prompts2.json", encoding="utf-8") as f:
    prompts = json.load(f)

# Load and merge all batches into a single {prompt: response} map
response_map = {}
for i in range(1, 7):
    with open(base / f"responses_batch{i}.json", encoding="utf-8") as f:
        batch = json.load(f)
    for item in batch:
        response_map[item["prompt"]] = item["response"]

print(f"Total prompts parsed: {len(prompts)}")
print(f"Total responses collected: {len(response_map)}")

missing = [p for p in prompts if p not in response_map]
print(f"Missing responses: {len(missing)}")
if missing:
    for m in missing[:10]:
        print(" -", m[:80])

# Write individual files starting at prompt201
start_num = 201
written = 0
for idx, prompt in enumerate(prompts):
    if prompt not in response_map:
        continue
    num = start_num + written
    response = response_map[prompt]
    filepath = answers_dir / f"prompt{num}response.txt"
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"User: {prompt}\n\nAssistant: {response}")
    written += 1

print(f"Wrote {written} response files (prompt{start_num} to prompt{start_num+written-1})")

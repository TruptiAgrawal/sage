#!/usr/bin/env python3
"""
Generate responses for test_prompts_2.txt and append analysis to CSV
"""

import os
import re
from pathlib import Path
from anthropic import Anthropic
import subprocess
import sys

client = Anthropic()

# Read prompts from test_prompts_2.txt
prompts_file = Path("/home/trupti/Projects/tokenCostGen/test_prompts_2.txt")
response_dir = Path("/home/trupti/Projects/tokenCostGen/trial2/test_prompt_answers")
base_prompt_num = 201

print(f"📝 Reading prompts from {prompts_file}...")

prompts = []
with open(prompts_file, 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if line:
            match = re.match(r'^\d+\.\s+(.+)$', line)
            if match:
                prompts.append(match.group(1))

print(f"✓ Found {len(prompts)} prompts\n")

# Generate responses and save files
print(f"🔄 Generating {len(prompts)} responses...\n")

for idx, prompt in enumerate(prompts, 1):
    prompt_num = base_prompt_num + idx - 1

    try:
        message = client.messages.create(
            model="claude-opus-4-8",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )
        response = message.content[0].text

        # Save response file
        response_file = response_dir / f"prompt{prompt_num}response.txt"
        with open(response_file, 'w', encoding='utf-8') as f:
            f.write(f"User: {prompt}\n\nAssistant: {response}")

        print(f"[{idx}/{len(prompts)}] ✓ Prompt {prompt_num}: {prompt[:50]}...")

    except Exception as e:
        print(f"[{idx}/{len(prompts)}] ✗ Prompt {prompt_num} failed: {e}")

print(f"\n✓ Generated {len(prompts)} response files\n")

# Run analyzer on new files
print("📊 Analyzing new responses...\n")
subprocess.run([
    "python3",
    "/home/trupti/Projects/tokenCostGen/trial2/response_analyzer.py",
    "--input-dir", str(response_dir),
    "--output", "/home/trupti/Projects/tokenCostGen/trial2/modelWiseDs/new_responses.csv",
    "--model", "claude-opus-4-8",
    "--format", "csv"
])

print("\n✅ Done! New responses saved and analyzed.")
print("📄 Analysis saved to: /home/trupti/Projects/tokenCostGen/trial2/modelWiseDs/new_responses.csv")

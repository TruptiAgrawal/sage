#!/usr/bin/env python3
"""Parse test_prompts_2.txt into a clean list of distinct prompts (handles multi-line entries and numbering resets)."""
import re
import json

with open("/home/trupti/Projects/tokenCostGen/test_prompts_2.txt", "r", encoding="utf-8") as f:
    lines = f.readlines()

# An entry starts with "<int>. " at the start of the line (after stripping leading whitespace)
entry_start = re.compile(r'^\s*(\d+)\.\s?(.*)$')

entries = []  # list of (orig_num, text)
current_text = []
current_num = None

def flush():
    global current_text, current_num
    if current_num is not None:
        text = "\n".join(current_text).strip()
        if text:
            entries.append((current_num, text))
    current_text = []

for line in lines:
    raw = line.rstrip("\n")
    m = entry_start.match(raw)
    if m:
        flush()
        current_num = int(m.group(1))
        current_text = [m.group(2)]
    else:
        if current_num is not None:
            current_text.append(raw)
flush()

print(f"Total raw entries parsed: {len(entries)}")

# Filter out empty/near-empty entries (just whitespace or single char artifacts)
clean = []
for num, text in entries:
    t = text.strip()
    if len(t) < 2:
        continue
    clean.append(t)

print(f"Total non-empty entries: {len(clean)}")

with open("/home/trupti/Projects/tokenCostGen/trial2/parsed_prompts2.json", "w", encoding="utf-8") as f:
    json.dump(clean, f, indent=2, ensure_ascii=False)

print("Saved to trial2/parsed_prompts2.json")

# SAGE Browser Extension

Predicts **input tokens, output tokens, estimated cost, and quality (1-10)**
for any prompt you type on a supported LLM web UI — before you hit Send.

---

## How it works

```
You type a prompt on Claude / ChatGPT / Gemini / etc.
          ↓  (debounced, 600 ms after you stop typing)
Content script sends the prompt text to the local SAGE server
          ↓
server.py loads the trained CatBoost models and returns predictions
          ↓
A floating overlay shows the results in real time
```

The prediction runs **locally** — your prompt never leaves your machine.

---

## Supported LLM sites

| Site | Detected model |
|------|----------------|
| claude.ai | claude-opus-4-8 |
| chat.openai.com / chatgpt.com | Llama 3.3 70B (closest in dataset) |
| gemini.google.com | DeepSeek V4 Flash (closest general) |
| chat.deepseek.com / deepseek.com | deepseek-reasoner |
| groq.com | Groq Llama 3.3 70B |
| perplexity.ai | Groq Llama 3.3 70B |

Predictions for **all four trained models** are always shown; the detected
model is highlighted with a ★.

---

## Quality score (1-10)

| Label | Score |
|-------|-------|
| Bad | 2 |
| Average | 5 |
| Good | 7 |
| Excellent | 9 |

---

## Setup

### 1 — Start the prediction server

```bash
# From the repo root:
uv run python browser-extension/server/server.py
```

The server starts on **http://localhost:5050** and must be running whenever
you use the extension.

### 2 — Load the extension in Chrome

1. Open Chrome and go to `chrome://extensions/`
2. Enable **Developer mode** (toggle, top-right)
3. Click **Load unpacked**
4. Select the `browser-extension/extension/` folder
5. The ⚡ SAGE icon appears in your toolbar

### 3 — Open any supported LLM site and start typing

The overlay appears automatically as soon as you type 10+ characters.

---

## Project layout

```
browser-extension/
├── server/
│   ├── server.py       FastAPI prediction server (loads CatBoost models)
│   └── README.md       Server-specific docs
└── extension/
    ├── manifest.json   Chrome extension manifest v3
    ├── content.js      Content script — detects textarea, calls server, renders overlay
    ├── overlay.css     Floating overlay styles
    ├── popup.html      Toolbar popup UI
    ├── popup.css       Popup styles
    ├── popup.js        Popup logic (health check + manual predict)
    └── icons/          Extension icons (16×16, 48×48, 128×128)
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Overlay shows "Server not running" | Run `server.py` first |
| No overlay appears | Check the site is in `manifest.json` host_permissions; reload extension after changes |
| Predictions seem off | The model was trained on ~1 000 prompts; accuracy improves with more data |
| Extension not loading | Ensure `Developer mode` is on in `chrome://extensions/` |

"use strict";

/**
 * popup.js
 *
 * When the user clicks the SAGE toolbar icon:
 *   1. Check the server is alive
 *   2. Ask the active tab's content script for the current prompt text
 *   3. Show the prompt in the preview box
 *   4. On "Predict" click → POST to /predict → render result card
 *
 * The popup also polls the active tab every second so the preview stays
 * in sync as the user types.
 */

const BASE = "http://localhost:5050";

const SITE_META = {
  "chatgpt.com":       { label: "ChatGPT",    cls: "site-chatgpt"    },
  "chat.openai.com":   { label: "ChatGPT",    cls: "site-chatgpt"    },
  "claude.ai":         { label: "Claude",     cls: "site-claude"     },
  "gemini.google.com": { label: "Gemini",     cls: "site-gemini"     },
  "perplexity.ai":     { label: "Perplexity", cls: "site-perplexity" },
};

const MODEL_DISPLAY = {
  "claude-opus-4-8":              "Claude Opus 4",
  "Groq-llama-3.3-70b-versatile": "Llama 3.3 70B",
  "DeepSeek V4 Flash":            "DeepSeek V4 Flash",
  "deepseek-reasoner":            "DeepSeek Reasoner",
};

// ── state ──────────────────────────────────────────────────────────────────
let currentPrompt  = "";
let detectedModel  = null;
let pollTimer      = null;

// ── helpers ────────────────────────────────────────────────────────────────
function qColor(s) {
  return s >= 8 ? "#22c55e" : s >= 6 ? "#84cc16" : s >= 4 ? "#f59e0b" : "#ef4444";
}
function esc(s) {
  return String(s)
    .replace(/&/g,"&amp;").replace(/</g,"&lt;")
    .replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}

// ── server health ──────────────────────────────────────────────────────────
async function checkServer() {
  const dot = document.getElementById("server-dot");
  try {
    const r = await fetch(`${BASE}/health`, { signal: AbortSignal.timeout(2000) });
    dot.className = r.ok ? "dot-green" : "dot-red";
  } catch {
    dot.className = "dot-red";
  }
}

// ── site detection from active tab URL ────────────────────────────────────
function getSiteMeta(url) {
  if (!url) return null;
  for (const [host, meta] of Object.entries(SITE_META)) {
    if (url.includes(host)) return meta;
  }
  return null;
}

function updateSiteBadge(url) {
  const badge = document.getElementById("site-badge");
  const meta  = getSiteMeta(url);
  if (meta) {
    badge.textContent = meta.label;
    badge.className   = `site-badge ${meta.cls}`;
  } else {
    badge.textContent = "Not an LLM page";
    badge.className   = "site-badge site-unknown";
  }
}

// ── read prompt from the active tab via content script ────────────────────
function readPromptFromTab(tabId, callback) {
  chrome.scripting.executeScript(
    {
      target: { tabId },
      func: () => {
        // Try every selector used in content.js
        const SELECTORS = [
          "#prompt-textarea",                          // ChatGPT
          ".ProseMirror[contenteditable='true']",      // Claude
          ".ql-editor[contenteditable='true']",        // Gemini
          "rich-textarea .ql-editor",                  // Gemini alt
          "textarea[placeholder]",                     // Perplexity
          "div[contenteditable='true']",               // generic fallback
          "textarea",                                  // generic fallback
        ];
        for (const sel of SELECTORS) {
          const el = document.querySelector(sel);
          if (!el) continue;
          const txt = el.tagName === "TEXTAREA" ? el.value : el.innerText;
          if (txt && txt.trim().length > 0) return txt.trim();
        }
        return "";
      },
    },
    (results) => {
      if (chrome.runtime.lastError) { callback(""); return; }
      callback((results && results[0] && results[0].result) || "");
    }
  );
}

// ── update the preview box ─────────────────────────────────────────────────
function updatePreview(text) {
  currentPrompt = text;
  const el  = document.getElementById("prompt-preview");
  const btn = document.getElementById("predict-btn");

  if (!text) {
    el.textContent = "No prompt detected yet — start typing on the LLM page…";
    el.className   = "prompt-preview prompt-empty";
    btn.disabled   = true;
  } else {
    el.textContent = text;
    el.className   = "prompt-preview";
    btn.disabled   = false;
  }
}

// ── poll the active tab every 1 s so preview stays live ───────────────────
function startPolling(tabId) {
  clearInterval(pollTimer);
  pollTimer = setInterval(() => {
    readPromptFromTab(tabId, updatePreview);
  }, 1000);
}

// ── render prediction card ─────────────────────────────────────────────────
function renderCard(p, note) {
  const cost  = p.cost_usd != null ? `$${p.cost_usd.toFixed(6)}` : "n/a";
  const pct   = Math.round((p.quality_score / 10) * 100);
  const color = qColor(p.quality_score);
  const name  = MODEL_DISPLAY[p.model] || p.model;

  return `
    <div class="r-card">
      <div class="r-model">${esc(name)}</div>
      <div class="r-grid">
        <div class="r-item">
          <span class="r-key">Input Tokens</span>
          <span class="r-val">${p.input_tokens.toLocaleString()}</span>
        </div>
        <div class="r-item">
          <span class="r-key">Output Tokens</span>
          <span class="r-val">${p.output_tokens.toLocaleString()}</span>
        </div>
        <div class="r-item">
          <span class="r-key">Estimated Cost</span>
          <span class="r-val">${cost}</span>
        </div>
        <div class="r-item">
          <span class="r-key">Quality</span>
          <span class="r-val">${esc(p.quality_label)}</span>
        </div>
      </div>
      <div class="r-qrow">
        <div class="r-track">
          <div class="r-fill" style="width:${pct}%;background:${color}"></div>
        </div>
        <span class="r-qtext">${p.quality_score} / 10</span>
      </div>
      <div class="r-note">${esc(note)}</div>
    </div>`;
}

// ── predict button click ───────────────────────────────────────────────────
async function onPredict() {
  if (!currentPrompt) return;

  const btn  = document.getElementById("predict-btn");
  const area = document.getElementById("result-area");
  btn.disabled    = true;
  btn.textContent = "Predicting…";
  area.innerHTML  = "";

  try {
    const r = await fetch(`${BASE}/predict`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({
        prompt:         currentPrompt,
        detected_model: detectedModel,
      }),
    });

    if (!r.ok) throw new Error(`Server returned ${r.status}`);
    const data = await r.json();

    // Show only the detected model row first, then the rest
    const preds = data.predictions || [];
    if (preds.length === 0) throw new Error("No predictions returned.");

    // detected model card first, then others
    const primary   = preds.find((p) => p.model === detectedModel);
    const secondary = preds.filter((p) => p.model !== detectedModel);
    const ordered   = primary ? [primary, ...secondary] : preds;

    area.innerHTML = ordered.map((p, i) =>
      renderCard(p, i === 0 ? "Detected model for this site" : "Other trained model")
    ).join("");

  } catch (err) {
    const msg = /fetch|network/i.test(err.message)
      ? "Cannot reach SAGE server.\nMake sure server.py is running."
      : err.message;
    document.getElementById("result-area").innerHTML =
      `<div class="r-error">⚠ ${esc(msg)}</div>`;
  } finally {
    btn.disabled    = false;
    btn.textContent = "Predict";
  }
}

// ── boot ───────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", async () => {
  checkServer();

  // Get the active tab
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab) return;

  const url  = tab.url || "";
  updateSiteBadge(url);

  // Set detected model from site
  const meta = getSiteMeta(url);
  const MODEL_FOR_SITE = {
    "chatgpt.com":       "Groq-llama-3.3-70b-versatile",
    "chat.openai.com":   "Groq-llama-3.3-70b-versatile",
    "claude.ai":         "claude-opus-4-8",
    "gemini.google.com": "DeepSeek V4 Flash",
    "perplexity.ai":     "Groq-llama-3.3-70b-versatile",
  };
  for (const [host, model] of Object.entries(MODEL_FOR_SITE)) {
    if (url.includes(host)) { detectedModel = model; break; }
  }

  // Read prompt immediately, then start polling
  readPromptFromTab(tab.id, updatePreview);
  startPolling(tab.id);

  document.getElementById("predict-btn").addEventListener("click", onPredict);
});

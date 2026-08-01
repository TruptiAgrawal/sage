/**
 * SAGE content.js v3.0.0
 *
 * The toolbar icon click sends a "toggle" message to this script.
 * The panel appears beside the prompt input box on the page.
 * It shows live predictions while the user types (debounced).
 * After the user sends the prompt and the LLM responds, it shows actual token counts.
 */

(function () {
  "use strict";

  const PREDICT_URL = "http://localhost:5050/predict";
  const ANALYZE_URL = "http://localhost:5050/analyze";
  const DEBOUNCE_MS   = 600;
  const MIN_CHARS     = 10;
  const STREAM_SETTLE = 1800;
  const MAX_WAIT_MS   = 90000;

  // ── site config ───────────────────────────────────────────────────────────
  // `model`        — the training-set model used to call /predict (closest match)
  // `displayModel` — the real model name shown to the user in the panel
  const SITES = [
    {
      host:         "chatgpt.com",
      inputSel:     "#prompt-textarea",
      submitSel:    "button[data-testid='send-button']",
      responseSel:  "[data-message-author-role='assistant'] .markdown",
      model:        "Groq-llama-3.3-70b-versatile",  // closest in training set
      displayModel: "GPT-4o",
      label:        "ChatGPT",
      color:        "#a6e3a1",
    },
    {
      host:         "chat.openai.com",
      inputSel:     "#prompt-textarea",
      submitSel:    "button[data-testid='send-button']",
      responseSel:  "[data-message-author-role='assistant'] .markdown",
      model:        "Groq-llama-3.3-70b-versatile",
      displayModel: "GPT-4o",
      label:        "ChatGPT",
      color:        "#a6e3a1",
    },
    {
      host:         "claude.ai",
      inputSel:     ".ProseMirror[contenteditable='true']",
      submitSel:    "button[aria-label='Send Message']",
      responseSel:  "[data-testid='chat-message-content']:last-of-type",
      model:        "claude-opus-4-8",
      displayModel: "Claude",
      label:        "Claude",
      color:        "#fab387",
    },
    {
      host:         "gemini.google.com",
      inputSel:     ".ql-editor[contenteditable='true'], rich-textarea .ql-editor",
      submitSel:    "button.send-button, button[aria-label='Send message']",
      responseSel:  "model-response:last-of-type .response-container, message-content:last-of-type",
      model:        "DeepSeek V4 Flash",             // closest general model in training set
      displayModel: "Gemini",
      label:        "Gemini",
      color:        "#89b4fa",
    },
    {
      host:         "perplexity.ai",
      inputSel:     "textarea[placeholder]",
      submitSel:    "button[aria-label='Submit']",
      responseSel:  ".prose:last-of-type",
      model:        "Groq-llama-3.3-70b-versatile",
      displayModel: "Perplexity AI",
      label:        "Perplexity",
      color:        "#cba6f7",
    },
  ];

  function detectSite() {
    return SITES.find((s) => location.hostname.includes(s.host)) || null;
  }

  function getInputEl(site) {
    for (const sel of site.inputSel.split(",").map((s) => s.trim())) {
      const el = document.querySelector(sel);
      if (el) return el;
    }
    return null;
  }

  // ── token estimator ───────────────────────────────────────────────────────
  function estimateTokens(text) {
    let n = 0;
    for (const w of (text.match(/\S+/g) || [])) n += Math.max(1, Math.ceil(w.length / 4));
    return n;
  }

  // ── utilities ─────────────────────────────────────────────────────────────
  function esc(s) {
    return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
  }
  function qColor(s) {
    return s >= 8 ? "#22c55e" : s >= 6 ? "#84cc16" : s >= 4 ? "#f59e0b" : "#ef4444";
  }
  function debounce(fn, ms) {
    let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); };
  }
  function getInputText(el) {
    if (!el) return "";
    return (el.tagName === "TEXTAREA" ? el.value : el.innerText).trim();
  }

  const MODEL_DISPLAY = {
    "claude-opus-4-8":              "Claude Opus 4",
    "Groq-llama-3.3-70b-versatile": "Llama 3.3 70B",
    "DeepSeek V4 Flash":            "DeepSeek V4 Flash",
    "deepseek-reasoner":            "DeepSeek Reasoner",
  };

  // ── panel ─────────────────────────────────────────────────────────────────
  let panel     = null;
  let panelOpen = false;

  function buildPanel(site) {
    if (panel) return panel;

    const el = document.createElement("div");
    el.id = "sage-panel";
    el.innerHTML = `
      <div id="sage-panel-header">
        <span id="sage-panel-title">⚡ SAGE</span>
        <span id="sage-panel-site" style="color:${site.color}">${site.label}</span>
        <span id="sage-panel-badge" class="sp-badge sp-badge-idle">IDLE</span>
        <button id="sage-panel-close">×</button>
      </div>
      <div id="sage-panel-body">
        <span class="sp-hint">Start typing your prompt…</span>
      </div>
    `;
    document.body.appendChild(el);

    document.getElementById("sage-panel-close").addEventListener("click", hidePanel);

    // ── drag to move ────────────────────────────────────────────────────────
    const hdr = document.getElementById("sage-panel-header");
    let dragging = false, startX, startY, startLeft, startTop;

    hdr.addEventListener("mousedown", (e) => {
      // don't drag when clicking the close button
      if (e.target.id === "sage-panel-close") return;
      dragging = true;

      // normalise position to fixed left/top (remove right/bottom)
      const rect   = el.getBoundingClientRect();
      startLeft    = rect.left;
      startTop     = rect.top;
      el.style.setProperty("left",   `${startLeft}px`,  "important");
      el.style.setProperty("top",    `${startTop}px`,   "important");
      el.style.setProperty("right",  "auto",             "important");
      el.style.setProperty("bottom", "auto",             "important");

      startX = e.clientX;
      startY = e.clientY;
      e.preventDefault();
    });

    document.addEventListener("mousemove", (e) => {
      if (!dragging) return;
      const dx  = e.clientX - startX;
      const dy  = e.clientY - startY;
      const newLeft = Math.max(0, Math.min(window.innerWidth  - el.offsetWidth,  startLeft + dx));
      const newTop  = Math.max(0, Math.min(window.innerHeight - el.offsetHeight, startTop  + dy));
      el.style.setProperty("left", `${newLeft}px`, "important");
      el.style.setProperty("top",  `${newTop}px`,  "important");
    });

    document.addEventListener("mouseup", () => { dragging = false; });

    panel = el;
    return el;
  }

  function positionPanel(site) {
    if (!panel) return;
    const inputEl = getInputEl(site);
    if (!inputEl) {
      // fallback: bottom-right corner
      panel.style.position = "fixed";
      panel.style.bottom   = "20px";
      panel.style.right    = "20px";
      panel.style.top      = "auto";
      panel.style.left     = "auto";
      return;
    }

    const rect = inputEl.getBoundingClientRect();
    const panelW = 320;

    // Try to place it to the right of the input box
    const spaceRight = window.innerWidth - rect.right;
    const spaceLeft  = rect.left;

    panel.style.position = "fixed";
    panel.style.top      = `${Math.max(10, rect.top)}px`;
    panel.style.bottom   = "auto";

    if (spaceRight >= panelW + 16) {
      // enough room on the right
      panel.style.left  = `${rect.right + 12}px`;
      panel.style.right = "auto";
    } else if (spaceLeft >= panelW + 16) {
      // enough room on the left
      panel.style.left  = `${rect.left - panelW - 12}px`;
      panel.style.right = "auto";
    } else {
      // not enough room either side — float above the input box
      panel.style.left   = `${Math.max(10, rect.left)}px`;
      panel.style.top    = `${Math.max(10, rect.top - 300)}px`;
      panel.style.right  = "auto";
      panel.style.bottom = "auto";
    }
  }

  function showPanel(site) {
    buildPanel(site);
    positionPanel(site);
    panel.style.setProperty("display", "block", "important");
    panelOpen = true;
  }

  function hidePanel() {
    if (panel) panel.style.setProperty("display", "none", "important");
    panelOpen = false;
  }

  function togglePanel(site) {
    if (panelOpen) { hidePanel(); } else { showPanel(site); }
  }

  function setBody(html) {
    const b = document.getElementById("sage-panel-body");
    if (b) b.innerHTML = html;
  }

  function setBadge(mode) {
    const b = document.getElementById("sage-panel-badge");
    if (!b) return;
    const MAP = {
      idle:    ["sp-badge-idle",    "IDLE"],
      predict: ["sp-badge-predict", "PREDICTING"],
      waiting: ["sp-badge-waiting", "WAITING"],
      actual:  ["sp-badge-actual",  "ACTUAL"],
    };
    const [cls, txt] = MAP[mode] || MAP.idle;
    b.className   = `sp-badge ${cls}`;
    b.textContent = txt;
  }

  // ── prompt quality tip ────────────────────────────────────────────────────
  // Shown below the card when the score is low, explaining why and what to do.
  function promptTip(score, charCount) {
    if (score >= 7) return ""; // good enough — no tip needed

    const tips = [];

    if (charCount < 50) {
      tips.push("Your prompt is very short. Short prompts score lower on average — the model has less context to work with.");
    } else if (charCount < 100) {
      tips.push("Adding more detail or context usually improves quality.");
    }

    if (score <= 2) {
      tips.push("Try being more specific: describe what you want, who it's for, and what format you expect.");
    } else if (score <= 5) {
      tips.push("Consider adding context, examples, or a clear goal to your prompt.");
    }

    if (tips.length === 0) return "";

    return `
      <div class="sp-tip">
        <span class="sp-tip-icon">💡</span>
        <span>${tips.join(" ")}</span>
      </div>`;
  }

  // ── render a result card ──────────────────────────────────────────────────
  function renderCard(p, noteText, displayModel, charCount) {
    const cost  = p.cost_usd != null ? `$${p.cost_usd.toFixed(6)}` : "n/a";
    const pct   = Math.round((p.quality_score / 10) * 100);
    const color = qColor(p.quality_score);
    // Always show the real site model name, not the training proxy
    const name  = displayModel || MODEL_DISPLAY[p.model] || p.model;

    return `
      <div class="sp-card">
        <div class="sp-model">${esc(name)}</div>
        <div class="sp-grid">
          <div class="sp-stat">
            <span class="sp-label">Input Tokens</span>
            <span class="sp-val">${p.input_tokens.toLocaleString()}</span>
          </div>
          <div class="sp-stat">
            <span class="sp-label">Output Tokens</span>
            <span class="sp-val">${p.output_tokens.toLocaleString()}</span>
          </div>
          <div class="sp-stat">
            <span class="sp-label">Est. Cost</span>
            <span class="sp-val">${cost}</span>
          </div>
          <div class="sp-stat">
            <span class="sp-label">Quality</span>
            <span class="sp-val">${esc(p.quality_label)}</span>
          </div>
        </div>
        <div class="sp-qrow">
          <div class="sp-qtrack">
            <div class="sp-qfill" style="width:${pct}%;background:${color}"></div>
          </div>
          <span class="sp-qtext">${p.quality_score}/10</span>
        </div>
        <div class="sp-note">${esc(noteText)}</div>
        ${promptTip(p.quality_score, charCount)}
      </div>`;
  }

  // ── API calls ─────────────────────────────────────────────────────────────
  async function apiPredict(prompt, model) {
    const r = await fetch(PREDICT_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt, detected_model: model }),
    });
    if (!r.ok) throw new Error(`Server ${r.status}`);
    return r.json();
  }

  async function apiAnalyze(prompt, response, inTok, outTok, model) {
    const r = await fetch(ANALYZE_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt, response, input_tokens: inTok, output_tokens: outTok, detected_model: model }),
    });
    if (!r.ok) throw new Error(`Server ${r.status}`);
    return r.json();
  }

  function networkError(err) {
    const msg = /fetch|network/i.test(err.message)
      ? "SAGE server not running.\nStart: uv run python browser-extension/server/server.py"
      : err.message;
    setBody(`<span class="sp-error">⚠ ${esc(msg)}</span>`);
    setBadge("idle");
  }

  function pickRow(data, model, key) {
    const rows = data[key] || [];
    return rows.find((r) => r.model === model) || rows[0] || null;
  }

  // ── wait for LLM response to finish, then analyze ─────────────────────────
  function getResponseText(site) {
    for (const sel of site.responseSel.split(",").map((s) => s.trim())) {
      const nodes = document.querySelectorAll(sel);
      if (nodes.length) {
        const txt = nodes[nodes.length - 1].innerText.trim();
        if (txt.length > 20) return txt;
      }
    }
    return "";
  }

  function waitAndAnalyze(site, promptText) {
    setBadge("waiting");
    setBody(`<span class="sp-hint">Waiting for ${site.label} to respond…</span>`);

    let settled; let retries = 0;
    const obs = new MutationObserver(() => {
      clearTimeout(settled);
      settled = setTimeout(onSettled, STREAM_SETTLE);
    });
    obs.observe(document.body, { childList: true, subtree: true, characterData: true });
    const hard = setTimeout(() => { obs.disconnect(); onSettled(); }, MAX_WAIT_MS);

    async function onSettled() {
      obs.disconnect(); clearTimeout(hard); clearTimeout(settled);
      const responseText = getResponseText(site);
      if (!responseText) {
        retries++;
        if (retries < 3) { setTimeout(() => waitAndAnalyze(site, promptText), 2500); return; }
        setBody(`<span class="sp-error">Could not read response from page.</span>`);
        setBadge("idle");
        return;
      }
      try {
        const inTok = estimateTokens(promptText);
        const outTok = estimateTokens(responseText);
        const data = await apiAnalyze(promptText, responseText, inTok, outTok, site.model);
        const row  = pickRow(data, site.model, "results");
        if (row) {
          setBody(renderCard(row, "Measured from page after response", site.displayModel, promptText.length));
          setBadge("actual");
        }
      } catch (err) { networkError(err); }
    }
  }

  // ── attach input listeners ────────────────────────────────────────────────
  function attachListeners(site) {
    const inputEl = getInputEl(site);
    if (!inputEl || inputEl.__sageAttached) return;
    inputEl.__sageAttached = true;

    let lastPrompt = "";

    // typing → predict (only when panel is open)
    const onType = debounce(async () => {
      if (!panelOpen) return;
      const text = getInputText(inputEl);
      if (text.length < MIN_CHARS) {
        setBody(`<span class="sp-hint">Keep typing… (${text.length}/${MIN_CHARS} chars min)</span>`);
        setBadge("idle");
        return;
      }
      lastPrompt = text;
      setBadge("predict");
      setBody(`<span class="sp-hint">Predicting…</span>`);
      try {
        const data = await apiPredict(text, site.model);
        const row  = pickRow(data, site.model, "predictions");
        if (row && panelOpen) {
          setBody(renderCard(row, "ML prediction — before sending", site.displayModel, text.length));
          setBadge("predict");
        }
      } catch (err) { if (panelOpen) networkError(err); }
    }, DEBOUNCE_MS);

    inputEl.addEventListener("input",   onType, { passive: true });
    inputEl.addEventListener("keydown", onType, { passive: true });

    // submit → analyze
    function onSubmit() {
      const text = getInputText(inputEl);
      if (text.length < MIN_CHARS) return;
      lastPrompt = text;
      setTimeout(() => waitAndAnalyze(site, lastPrompt), 600);
    }

    inputEl.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) onSubmit();
    }, { passive: true });

    // hook send button
    function hookBtn() {
      for (const sel of site.submitSel.split(",").map((s) => s.trim())) {
        const btn = document.querySelector(sel);
        if (btn && !btn.__sageDone) {
          btn.__sageDone = true;
          btn.addEventListener("click", onSubmit, { passive: true });
          return true;
        }
      }
      return false;
    }
    if (!hookBtn()) {
      const bo = new MutationObserver(() => { if (hookBtn()) bo.disconnect(); });
      bo.observe(document.body, { childList: true, subtree: true });
    }
  }

  // ── watch for input element to appear (SPA lazy render) ──────────────────
  function watchForInput(site) {
    function tryFind() {
      const el = getInputEl(site);
      if (el) { attachListeners(site); return true; }
      return false;
    }
    if (!tryFind()) {
      const o = new MutationObserver(() => { if (tryFind()) o.disconnect(); });
      o.observe(document.body, { childList: true, subtree: true });
    }
  }

  // ── listen for toolbar icon click (message from background) ──────────────
  chrome.runtime.onMessage.addListener((msg) => {
    if (msg.type === "SAGE_TOGGLE") {
      const site = detectSite();
      if (!site) return;
      togglePanel(site);
      if (panelOpen) {
        // reposition in case page layout changed
        positionPanel(site);
        // immediately show current prompt if any
        const inputEl = getInputEl(site);
        const text    = getInputText(inputEl);
        if (text.length >= MIN_CHARS) {
          setBody(`<span class="sp-hint">Predicting…</span>`);
          setBadge("predict");
          apiPredict(text, site.model)
            .then((data) => {
              const row = pickRow(data, site.model, "predictions");
              if (row && panelOpen) {
                setBody(renderCard(row, "ML prediction — before sending", site.displayModel, text.length));
                setBadge("predict");
              }
            })
            .catch(networkError);
        }
      }
    }
  });

  // ── boot ──────────────────────────────────────────────────────────────────
  const site = detectSite();
  if (!site) return;
  watchForInput(site);

})();

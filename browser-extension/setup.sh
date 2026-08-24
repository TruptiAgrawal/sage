#!/usr/bin/env bash
# =============================================================================
# SAGE — one-command setup
# Run this from the repo root:
#   bash browser-extension/setup.sh
# =============================================================================

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXTENSION_DIR="$REPO_ROOT/browser-extension/extension"
SERVER_SCRIPT="$REPO_ROOT/browser-extension/server/server.py"

# ── colours ──────────────────────────────────────────────────────────────────
BOLD="\033[1m"
GREEN="\033[1;32m"
CYAN="\033[1;36m"
YELLOW="\033[1;33m"
RESET="\033[0m"

echo ""
echo -e "${BOLD}⚡ SAGE — Prompt Advisor Setup${RESET}"
echo "────────────────────────────────────────"

# ── step 1: install uv if missing ────────────────────────────────────────────
if ! command -v uv &>/dev/null; then
  # check ~/.local/bin too (uv installs there by default)
  if [ -f "$HOME/.local/bin/uv" ]; then
    export PATH="$HOME/.local/bin:$PATH"
  else
    echo -e "\n${CYAN}[1/3] Installing uv (Python package manager)…${RESET}"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
    echo -e "${GREEN}  ✓ uv installed${RESET}"
  fi
else
  echo -e "${GREEN}[1/3] uv already installed${RESET}"
fi

export PATH="$HOME/.local/bin:$PATH"

# ── step 2: sync dependencies ─────────────────────────────────────────────────
echo -e "\n${CYAN}[2/3] Installing Python dependencies…${RESET}"
cd "$REPO_ROOT"
uv sync --quiet
echo -e "${GREEN}  ✓ Dependencies ready${RESET}"

# ── step 3: print extension load instructions ────────────────────────────────
echo ""
echo -e "${CYAN}[3/3] Load the Chrome extension:${RESET}"
echo ""
echo -e "  1. Open Chrome and go to:  ${BOLD}chrome://extensions/${RESET}"
echo -e "  2. Turn on ${BOLD}Developer mode${RESET} (top-right toggle)"
echo -e "  3. Click ${BOLD}Load unpacked${RESET}"
echo -e "  4. Select this folder:"
echo ""
echo -e "     ${YELLOW}${EXTENSION_DIR}${RESET}"
echo ""
echo -e "  5. The ${BOLD}⚡ SAGE${RESET} icon will appear in your toolbar"
echo ""
echo "────────────────────────────────────────"
echo -e "${GREEN}  ✓ Setup complete — starting server…${RESET}"
echo ""
echo -e "  Server running at: ${BOLD}http://localhost:5050${RESET}"
echo -e "  Open any LLM site, click the ${BOLD}⚡ SAGE${RESET} icon to start"
echo -e "  Press ${BOLD}Ctrl+C${RESET} to stop the server"
echo ""

# ── start server (foreground so Ctrl+C kills it cleanly) ─────────────────────
exec uv run python "$SERVER_SCRIPT"

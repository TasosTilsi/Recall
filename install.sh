#!/usr/bin/env bash
# install.sh — set up graphiti-knowledge-graph and add 'graphiti'/'gk' to PATH
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$PROJECT_ROOT/.venv"
LOCAL_BIN="$HOME/.local/bin"

echo "==> graphiti-knowledge-graph installer"
echo "    Project: $PROJECT_ROOT"

# ── 1. Virtual environment ────────────────────────────────────────────────────
if [ ! -d "$VENV" ]; then
    echo "==> Creating virtual environment..."
    python3 -m venv "$VENV"
fi

# ── 2. Install package ────────────────────────────────────────────────────────
echo "==> Installing package (editable)..."
"$VENV/bin/pip" install --quiet -e "$PROJECT_ROOT"

# ── 3. Symlink commands into ~/.local/bin ─────────────────────────────────────
mkdir -p "$LOCAL_BIN"
for cmd in graphiti gk; do
    src="$VENV/bin/$cmd"
    dest="$LOCAL_BIN/$cmd"
    if [ ! -f "$src" ]; then
        echo "    WARNING: $src not found, skipping"
        continue
    fi
    # Remove stale symlink or file
    [ -e "$dest" ] || [ -L "$dest" ] && rm -f "$dest"
    ln -s "$src" "$dest"
    echo "    Linked: $dest -> $src"
done

# ── 4. Ensure ~/.local/bin is in PATH ─────────────────────────────────────────
PATH_LINE='export PATH="$HOME/.local/bin:$PATH"'

_add_to_rc() {
    local rc="$1"
    if [ -f "$rc" ] && grep -qF '.local/bin' "$rc" 2>/dev/null; then
        return 0  # already present
    fi
    printf '\n# Added by graphiti install\n%s\n' "$PATH_LINE" >> "$rc"
    echo "    Added PATH entry to $rc"
    NEEDS_RELOAD=1
}

NEEDS_RELOAD=0
if ! printf ':%s:' "$PATH" | grep -q ":$HOME/.local/bin:"; then
    SHELL_NAME="$(basename "${SHELL:-bash}")"
    case "$SHELL_NAME" in
        zsh)  _add_to_rc "$HOME/.zshrc" ;;
        fish)
            mkdir -p "$HOME/.config/fish"
            grep -qF '.local/bin' "$HOME/.config/fish/config.fish" 2>/dev/null \
                || printf '\nfish_add_path ~/.local/bin\n' >> "$HOME/.config/fish/config.fish"
            echo "    Added PATH entry to ~/.config/fish/config.fish"
            NEEDS_RELOAD=1
            ;;
        *)    _add_to_rc "$HOME/.bashrc" ;;
    esac
fi

# ── 5. Done ───────────────────────────────────────────────────────────────────
echo ""
echo "==> Done!"
if [ "$NEEDS_RELOAD" -eq 1 ]; then
    echo "    PATH updated — reload your shell or run:"
    echo "      source ~/.${SHELL_NAME}rc"
    echo ""
fi
echo "    Usage: graphiti --help"

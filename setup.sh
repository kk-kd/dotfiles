#!/usr/bin/env zsh
set -euo pipefail

DOTFILES="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_HOME="$HOME/.claude"
CLAUDE_DOTFILES="$DOTFILES/.claude"

symlink() {
    local src="$1" dst="$2"

    if [[ -L "$dst" ]]; then
        local current
        current="$(readlink "$dst")"
        if [[ "$current" == "$src" ]]; then
            echo "  skip: $dst (already linked)"
            return
        fi
        echo "  relink: $dst -> $src (was $current)"
        rm "$dst"
    elif [[ -e "$dst" ]]; then
        echo "  backup: $dst -> ${dst}.bak"
        mv "$dst" "${dst}.bak"
    else
        echo "  link: $dst -> $src"
    fi

    ln -s "$src" "$dst"
}

echo "Claude Code"
mkdir -p "$CLAUDE_HOME"
symlink "$CLAUDE_DOTFILES/settings.json" "$CLAUDE_HOME/settings.json"
symlink "$CLAUDE_DOTFILES/commands" "$CLAUDE_HOME/commands"
symlink "$CLAUDE_DOTFILES/CLAUDE.md" "$CLAUDE_HOME/CLAUDE.md"
symlink "$CLAUDE_DOTFILES/scripts" "$CLAUDE_HOME/scripts"
symlink "$DOTFILES/skills" "$CLAUDE_HOME/skills"

echo "Tmux"
symlink "$DOTFILES/tmux.conf" "$HOME/.tmux.conf"

echo "Done."

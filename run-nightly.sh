#!/usr/bin/env bash
set -euo pipefail
export XDG_RUNTIME_DIR="/run/user/$(id -u)"
PROMPT="$(cat "$HOME/.openclaw/workspace/job-search/nightly-prompt.txt")"
exec openclaw agent --agent main --channel telegram --deliver --reply-to <TELEGRAM_CHAT_ID> \
     --timeout 900 --message "$PROMPT"

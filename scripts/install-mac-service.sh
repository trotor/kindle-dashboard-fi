#!/usr/bin/env bash
# Asentaa Mac-palvelun launchd-agentiksi (käynnistyy kirjautuessa, pysyy päällä).
# Installs the Mac service as a launchd agent (starts at login, kept alive).
#   scripts/install-mac-service.sh          asenna ja käynnistä / install and start
#   scripts/install-mac-service.sh --print  tulosta plist / print the plist only
set -euo pipefail

LABEL=fi.ronkko.saasahko
REPO="$(cd "$(dirname "$0")/.." && pwd)"
UV="${UV:-$(command -v uv || true)}"
LOG="$HOME/Library/Logs/saasahko.log"
DEST="$HOME/Library/LaunchAgents/$LABEL.plist"

if [ -z "$UV" ]; then
    echo "virhe / error: uv puuttuu / not found (https://docs.astral.sh/uv/)" >&2
    exit 1
fi

plist() {
    sed -e "s|__UV__|$UV|g" -e "s|__REPO__|$REPO|g" -e "s|__LOG__|$LOG|g" \
        "$REPO/deploy/saasahko.plist.in"
}

case "${1:-}" in
    --print) plist; exit 0 ;;
    "") ;;
    *) echo "käyttö / usage: $(basename "$0") [--print]" >&2; exit 2 ;;
esac

if [ ! -f "$REPO/config.toml" ]; then
    echo "virhe / error: $REPO/config.toml puuttuu / missing (cp config.example.toml config.toml)" >&2
    exit 1
fi

mkdir -p "$HOME/Library/LaunchAgents" "$HOME/Library/Logs"
plist > "$DEST"
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$DEST"
echo "asennettu / installed: $DEST"
echo "loki / log: $LOG"

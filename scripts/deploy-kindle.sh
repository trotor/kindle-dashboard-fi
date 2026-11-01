#!/usr/bin/env bash
# Kopioi Kindle-puolen tiedostot USB-liitettyyn Kindleen.
# --dev: kopioi myös kehitysyhteys.sh (telnet). Ilman sitä se poistetaan Kindleltä.
set -euo pipefail

DEV=0
for arg in "$@"; do
    case "$arg" in
        --dev) DEV=1 ;;
        *) echo "käyttö: $(basename "$0") [--dev]" >&2; exit 2 ;;
    esac
done

VOL="${KINDLE_VOLUME:-/Volumes/Kindle}"
SRC="$(cd "$(dirname "$0")/.." && pwd)/kindle"
DEV_SCRIPT=kehitysyhteys.sh

if [ ! -d "$VOL" ]; then
    echo "virhe: Kindlea ei ole liitetty ($VOL puuttuu)" >&2
    exit 1
fi

mkdir -p "$VOL/documents"
shopt -s nullglob
scripts=()
for f in "$SRC"/documents/*.sh; do
    if [ "$DEV" -eq 1 ] || [ "$(basename "$f")" != "$DEV_SCRIPT" ]; then
        scripts+=("$f")
    fi
done
if [ ${#scripts[@]} -gt 0 ]; then
    cp "${scripts[@]}" "$VOL/documents/"
else
    echo "ohitetaan: ei scriptlettejä"
fi
if [ "$DEV" -eq 0 ] && [ -e "$VOL/documents/$DEV_SCRIPT" ]; then
    rm -f "$VOL/documents/$DEV_SCRIPT"
    echo "poistettu Kindleltä: documents/$DEV_SCRIPT (kehitysyhteys)"
fi

if [ -d "$SRC/saa-ja-sahko" ]; then
    mkdir -p "$VOL/saa-ja-sahko"
    cp -R "$SRC/saa-ja-sahko/." "$VOL/saa-ja-sahko/"
else
    echo "ohitetaan: kindle/saa-ja-sahko/ puuttuu"
fi

if [ -f "$SRC/saa-ja-sahko.conf" ]; then
    if [ -e "$VOL/saa-ja-sahko.conf" ]; then
        echo "saa-ja-sahko.conf on jo Kindlellä, ei ylikirjoiteta"
    else
        # MAC_IP: Macin osoite kotiverkossa (oletus: en0/en1:n osoite)
        ip="${MAC_IP:-$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || true)}"
        if [ -z "$ip" ]; then
            echo "varoitus: Macin IP:tä ei löytynyt, muokkaa URL tiedostoon $VOL/saa-ja-sahko.conf" >&2
            ip=MAC_IP
        fi
        sed "s|MAC_IP|$ip|" "$SRC/saa-ja-sahko.conf" > "$VOL/saa-ja-sahko.conf"
        echo "kirjoitettu saa-ja-sahko.conf (Mac: $ip)"
    fi
else
    echo "ohitetaan: kindle/saa-ja-sahko.conf puuttuu"
fi

dot_clean -m "$VOL"
echo "valmis"

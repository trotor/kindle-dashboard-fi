#!/usr/bin/env bash
# Kopioi Kindle-puolen tiedostot USB-liitettyyn Kindleen.
set -euo pipefail

VOL="${KINDLE_VOLUME:-/Volumes/Kindle}"
SRC="$(cd "$(dirname "$0")/.." && pwd)/kindle"

if [ ! -d "$VOL" ]; then
    echo "virhe: Kindlea ei ole liitetty ($VOL puuttuu)" >&2
    exit 1
fi

mkdir -p "$VOL/documents"
shopt -s nullglob
scripts=("$SRC"/documents/*.sh)
if [ ${#scripts[@]} -gt 0 ]; then
    cp "${scripts[@]}" "$VOL/documents/"
else
    echo "ohitetaan: ei scriptlettejä"
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
        cp "$SRC/saa-ja-sahko.conf" "$VOL/saa-ja-sahko.conf"
    fi
else
    echo "ohitetaan: kindle/saa-ja-sahko.conf puuttuu"
fi

dot_clean -m "$VOL"
echo "valmis"

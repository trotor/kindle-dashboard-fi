#!/bin/sh
# Sää ja sähkö: hakee kuvan Macilta ja näyttää sen. Käynnistetään scriptletistä.

. /mnt/us/saa-ja-sahko.conf
. "$(dirname "$0")/lib.sh"

HOST=192.168.0.157
echo $$ > /tmp/saa-ja-sahko.pid

stop framework
lipc-set-prop com.lab126.powerd preventScreenSaver 1
lipc-set-prop com.lab126.powerd flIntensity "$FRONTLIGHT"

while true; do
    stop otaupd 2>/dev/null
    stop otav3 2>/dev/null
    stop ota-update 2>/dev/null
    rm -f /mnt/us/update*.bin /mnt/us/*.bin.tmp /mnt/us/*.tmp.partial

    i=0
    while [ "$i" -lt 20 ] && ! ping -c1 -W2 "$HOST" >/dev/null 2>&1; do
        i=$((i + 1))
        sleep 1
    done

    batt=$(lipc-get-prop com.lab126.powerd battLevel)
    curl -fsS -m 60 -o /tmp/dash.new.png "$(build_url "$URL" "$batt")"
    rc=$?
    if [ "$rc" -eq 0 ]; then
        mv -f /tmp/dash.new.png /tmp/dash.png
        eips -f -g /tmp/dash.png
        log "fetch ok batt=$batt"
    else
        eips 1 1 "$(fail_text "$(date +%H%M)")"
        log "fetch failed rc=$rc"
    fi

    sleep "$(interval_for_hour "$(date +%H | sed 's/^0//')")"
done

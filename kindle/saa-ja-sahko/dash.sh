#!/bin/sh
# Sää ja sähkö: hakee kuvan Macilta ja näyttää sen. Käynnistetään scriptletistä.

. /mnt/us/saa-ja-sahko.conf
. "$(dirname "$0")/lib.sh"

HOST=$(host_from_url "$URL")
PIDFILE=/tmp/saa-ja-sahko.pid

# Kaksoiskäynnistyksen esto: mkdir on atominen. Jos lukko on jo, ja sen
# pitäjä elää, poistutaan. Muuten (vanhentunut lukko) jatketaan.
if ! mkdir /tmp/saa-ja-sahko.lock 2>/dev/null; then
    if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
        exit 0
    fi
fi
echo $$ > "$PIDFILE"

stop framework
# Ilman tätä pillow piirtää kaatumisikkunoita. ÄLÄ KOSKAAN: stop lab126_gui (kaataa koko session).
stop pillow 2>/dev/null
lipc-set-prop com.lab126.powerd preventScreenSaver 1
lipc-set-prop com.lab126.powerd flIntensity "$FRONTLIGHT"

while true; do
    stop otaupd 2>/dev/null
    stop otav3 2>/dev/null
    stop ota-update 2>/dev/null
    rm -f /mnt/us/update*.bin /mnt/us/*.bin.tmp /mnt/us/*.tmp.partial

    # Wi-Fi päälle ja odotus yhteyteen (max 60 s), sitten Macin tavoitettavuus (max 20 s)
    lipc-set-prop com.lab126.cmd wirelessEnable 1 2>/dev/null
    i=0
    while [ "$i" -lt 60 ] && [ "$(lipc-get-prop com.lab126.wifid cmState 2>/dev/null)" != CONNECTED ]; do
        i=$((i + 1))
        sleep 1
    done
    if [ -n "$HOST" ]; then
        i=0
        while [ "$i" -lt 20 ] && ! ping -c1 -W2 "$HOST" >/dev/null 2>&1; do
            i=$((i + 1))
            sleep 1
        done
    fi

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

    sleep "$(sleep_seconds "$(date +%H)" "$(date +%M)")"
done

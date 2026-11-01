#!/bin/sh
# Sää ja sähkö: hakee kuvan Macilta ja näyttää sen. Käynnistetään scriptletistä.

. /mnt/us/saa-ja-sahko.conf
. "$(dirname "$0")/lib.sh"

HOST=$(host_from_url "$URL")
PIDFILE=/tmp/saa-ja-sahko.pid
FBINK=/mnt/us/libkh/bin/fbink

wifi_state() { lipc-get-prop com.lab126.wifid cmState 2>/dev/null; }
wifi_connected() { [ "$(wifi_state)" = CONNECTED ]; }

# Virheteksti isolla, valkoinen mustalla, näytön alareunaan (vanha kuva jää)
show_fail() {
    if [ -x "$FBINK" ]; then
        "$FBINK" -q -S 4 -y -2 -m -h -p "$1" >/dev/null 2>&1 && return 0
    fi
    eips 1 1 "$1"
}

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

    # Wi-Fi päälle ja odotus yhteyteen. Jos yhteys ei palaa, porras kerrallaan:
    # radio pois/päälle, sitten wifid uudelleen (wifid voi jumittua "Searching"-
    # tilaan, kun tukiasema hylkää yhteyden toistuvasti: 1.11.2026 klo 02.27).
    lipc-set-prop com.lab126.cmd wirelessEnable 1 2>/dev/null
    if ! wait_for 30 wifi_connected; then
        log "wifi $(wifi_state) -> radio pois/päälle"
        lipc-set-prop com.lab126.cmd wirelessEnable 0 2>/dev/null
        sleep 5
        lipc-set-prop com.lab126.cmd wirelessEnable 1 2>/dev/null
        if ! wait_for 60 wifi_connected; then
            log "wifi $(wifi_state) -> restart wifid"
            restart wifid >/dev/null 2>&1
            sleep 2
            lipc-set-prop com.lab126.cmd wirelessEnable 1 2>/dev/null
            wait_for 60 wifi_connected || log "wifi $(wifi_state) -> ei yhteyttä"
        fi
    fi
    if [ -n "$HOST" ]; then
        wait_for 20 ping -c1 -W2 "$HOST" >/dev/null 2>&1
    fi

    batt=$(lipc-get-prop com.lab126.powerd battLevel)
    curl -fsS -m 60 -o /tmp/dash.new.png "$(build_url "$URL" "$batt")"
    rc=$?
    if [ "$rc" -eq 0 ]; then
        mv -f /tmp/dash.new.png /tmp/dash.png
        eips -f -g /tmp/dash.png
        log "fetch ok batt=$batt"
    else
        show_fail "$(fail_text "$(date +%H%M)")"
        log "fetch failed rc=$rc batt=$batt wifi=$(wifi_state)"
    fi

    # Radio pois hakujen väliltä: säästää akkua, eikä tukiasema ehdi pudottaa
    # yhteyttä. Kehitysyhteys (telnet) toimii vain, kun tämä on 0.
    if [ "${WIFI_OFF_BETWEEN:-0}" = 1 ]; then
        lipc-set-prop com.lab126.cmd wirelessEnable 0 2>/dev/null
    fi

    sleep "$(sleep_seconds "$(date +%H)" "$(date +%M)")"
done

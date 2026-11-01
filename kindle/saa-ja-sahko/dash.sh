#!/bin/sh
# Sää ja sähkö: hakee kuvan Macilta ja näyttää sen. Käynnistetään scriptletistä.

. /mnt/us/saa-ja-sahko.conf
. "$(dirname "$0")/lib.sh"

HOST=$(host_from_url "$URL")
PIDFILE=/tmp/saa-ja-sahko.pid
FBINK=/mnt/us/libkh/bin/fbink
FONT=/usr/java/lib/fonts/Amazon-Ember-Bold.ttf

wifi_state() { lipc-get-prop com.lab126.wifid cmState 2>/dev/null; }
wifi_connected() { [ "$(wifi_state)" = CONNECTED ]; }
# Yhteys on kunnossa vasta, kun Mac vastaa: wifid voi näyttää CONNECTED,
# vaikka tukiasema on jo pudottanut Kindlen (syy 4 = käyttämättömyys).
online() {
    wifi_connected || return 1
    [ -z "$HOST" ] && return 0
    ping -c1 -W2 "$HOST" >/dev/null 2>&1
}

# Virheteksti isolla, valkoinen mustalla (vanha kuva jää näkyviin)
show_fail() {
    if [ -x "$FBINK" ]; then
        # sähkökuvaajan yläpuolelle keskelle (tyhjä kohta "SÄHKÖ"- ja "nyt"-tekstien välissä)
        "$FBINK" -q -h -m -t "regular=$FONT,px=52,top=780,bottom=568,left=200,right=372,padding=BOTH" "$1" \
            >/dev/null 2>&1 && return 0
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

    # Wi-Fi päälle ja odotus, kunnes Mac vastaa. Jos yhteys ei palaa, porras kerrallaan:
    # radio pois/päälle, sitten wifid uudelleen (wifid voi jumittua "Searching"-
    # tilaan, kun tukiasema hylkää yhteyden toistuvasti: 1.11.2026 klo 02.27).
    lipc-set-prop com.lab126.cmd wirelessEnable 1 2>/dev/null
    if ! wait_for 30 online; then
        log "wifi $(wifi_state) -> radio pois/päälle"
        lipc-set-prop com.lab126.cmd wirelessEnable 0 2>/dev/null
        sleep 5
        lipc-set-prop com.lab126.cmd wirelessEnable 1 2>/dev/null
        if ! wait_for 60 online; then
            log "wifi $(wifi_state) -> restart wifid"
            restart wifid >/dev/null 2>&1
            sleep 2
            lipc-set-prop com.lab126.cmd wirelessEnable 1 2>/dev/null
            wait_for 60 online || log "wifi $(wifi_state) -> ei yhteyttä"
        fi
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

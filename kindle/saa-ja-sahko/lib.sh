# Apufunktiot (POSIX sh). Luetaan dash.sh:ssa ja testeissä.

LOG_FILE="${LOG_FILE:-/mnt/us/saa-ja-sahko.log}"
LOG_MAX="${LOG_MAX:-100000}"

# _dec N -> N ilman etunollia ("08" -> 8, "00" -> 0); $((08)) olisi oktaalivirhe
_dec() {
    _n=$(printf '%s' "$1" | sed 's/^0*//')
    echo "${_n:-0}"
}

# sleep_seconds H M -> odotus sekunteina: päivällä (06-23) 1800,
# yöllä 7200 mutta herätys viimeistään klo 06.00
sleep_seconds() {
    _h=$(_dec "$1")
    _m=$(_dec "$2")
    if [ "$_h" -ge 6 ] && [ "$_h" -lt 23 ]; then
        echo 1800
        return 0
    fi
    if [ "$_h" -lt 6 ]; then
        _s=$(( ((6 - _h) * 60 - _m) * 60 ))
    else
        _s=$(( ((30 - _h) * 60 - _m) * 60 ))
    fi
    if [ "$_s" -gt 7200 ]; then
        _s=7200
    fi
    echo "$_s"
}

# host_from_url URL -> palvelimen nimi tai IP (tyhjä, jos URL ei kelpaa)
host_from_url() {
    case "$1" in
        *://*) ;;
        *) echo ""; return 0 ;;
    esac
    _u=${1#*://}
    _u=${_u%%/*}
    _u=${_u##*@}
    _u=${_u%%:*}
    case "$_u" in
        *[!A-Za-z0-9.-]*) _u= ;;
    esac
    echo "$_u"
}

# build_url BASE BATT -> BASE?batt=BATT (pelkkä BASE, jos BATT ei ole numero)
build_url() {
    case "$2" in
        ''|*[!0-9]*) echo "$1" ;;
        *) echo "$1?batt=$2" ;;
    esac
}

# log MSG -> rivi lokiin, kierrätys $LOG_MAX tavun jälkeen
log() {
    if [ -f "$LOG_FILE" ] && [ "$(wc -c < "$LOG_FILE")" -gt "$LOG_MAX" ]; then
        mv -f "$LOG_FILE" "$LOG_FILE.1"
    fi
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1" >> "$LOG_FILE"
}

# fail_text HHMM -> yhteysvirhe HH.MM
fail_text() {
    echo "yhteysvirhe $(printf '%s' "$1" | cut -c1-2).$(printf '%s' "$1" | cut -c3-4)"
}

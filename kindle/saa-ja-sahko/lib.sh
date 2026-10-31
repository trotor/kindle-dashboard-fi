# Apufunktiot (POSIX sh). Luetaan dash.sh:ssa ja testeissä.

LOG_FILE="${LOG_FILE:-/mnt/us/saa-ja-sahko.log}"
LOG_MAX="${LOG_MAX:-100000}"

# interval_for_hour H -> päivitysväli sekunteina (H voi olla "08")
interval_for_hour() {
    h=$(printf '%s' "$1" | sed 's/^0*//')
    h=${h:-0}
    if [ "$h" -ge 6 ] && [ "$h" -lt 23 ]; then
        echo 1800
    else
        echo 7200
    fi
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

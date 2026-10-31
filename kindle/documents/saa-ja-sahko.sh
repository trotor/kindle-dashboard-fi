#!/bin/sh
# Name: Sää ja sähkö
# Author: Tero
# DontUseFBInk

PIDFILE=/tmp/saa-ja-sahko.pid

if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
    exit 0
fi

setsid nohup sh /mnt/us/saa-ja-sahko/dash.sh >/dev/null 2>&1 &

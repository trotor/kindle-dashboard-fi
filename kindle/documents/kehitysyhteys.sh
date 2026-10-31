#!/bin/sh
# Name: Kehitysyhteys (väliaikainen)
# Author: saasahko
# DontUseFBInk

# Macin osoite samasta asetuksesta kuin näyttöohjelmalla (URL), varalla oletus
MAC=
if [ -r /mnt/us/saa-ja-sahko.conf ] && [ -r /mnt/us/saa-ja-sahko/lib.sh ]; then
    . /mnt/us/saa-ja-sahko.conf
    . /mnt/us/saa-ja-sahko/lib.sh
    MAC=$(host_from_url "$URL")
fi
MAC=${MAC:-192.168.0.157}

# Salli telnet vain Mac minilta (ei tuplasääntöä, jos skripti ajetaan uudelleen)
iptables -C INPUT -p tcp --dport 23 -s "$MAC" -j ACCEPT 2>/dev/null ||
    iptables -I INPUT -p tcp --dport 23 -s "$MAC" -j ACCEPT

# Ala käynnistä toista telnetd:tä, jos sellainen jo pyörii
if ! ps | grep '[t]elnetd' >/dev/null 2>&1; then
    telnetd -l /bin/sh -p 23
fi

IP=$(ifconfig wlan0 2>/dev/null | sed -n 's/.*inet addr:\([0-9.]*\).*/\1/p')
echo "Telnet auki: $IP"
eips 1 5 "Telnet auki: ${IP:-tuntematon IP}"

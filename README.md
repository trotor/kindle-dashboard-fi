# Sää ja sähkö

Mac mini piirtää Toivalan sään (Ilmatieteen laitos) ja pörssisähkön hinnat yhdeksi harmaasävykuvaksi (1072×1448), ja jailbreakattu Kindle Paperwhite 3 hakee kuvan ja näyttää sen e-ink-näytöllä.

```
FMI + sähkön pörssihinnat -> Mac mini (saasahko, portti 8088) -> Kindle (curl + eips) -> näyttö
```

## Käyttö Kindlellä

- Käynnistys: napauta kirjastossa "Sää ja sähkö". Kindle sulkee tavallisen käyttöliittymän ja näyttää kuvan.
- Paluu lukemiseen: käynnistä Kindle uudelleen pitämällä virtanappia pohjassa noin 20-40 sekuntia. Sen jälkeen Kindle on taas tavallinen Kindle.
- Näyttötila ei käynnisty itsestään uudelleenkäynnistyksen jälkeen. Napauta "Sää ja sähkö" uudelleen, kun haluat sen takaisin.

## Asetukset Macilla

Asetukset ovat tiedostossa `config.toml` (pohja: `config.example.toml`):

| Asetus | Merkitys |
| --- | --- |
| `margin_c` | Sähkönmyyjän marginaali c/kWh. Herrfors: `0.23` |
| `transfer_c` | Siirtomaksu c/kWh |
| `low_battery_percent` | Akun varoitusraja (oletus 20) |
| `place_name`, `lat`, `lon` | Paikka ja koordinaatit sääennusteelle |
| `port` | Palvelimen portti (oletus 8088) |
| `cache_dir`, `timezone` | Välimuistin kansio ja aikavyöhyke |

Näytetyt hinnat sisältävät ALV:n. Muutoksen jälkeen käynnistä palvelu uudelleen:

```
launchctl kickstart -k gui/$(id -u)/fi.ronkko.saasahko
```

Palvelu on launchd-agentti (`deploy/fi.ronkko.saasahko.plist`), joka käynnistyy Macin mukana ja nousee itse takaisin pystyyn.

Mac minin uudelleenkäynnistyksen jälkeen palvelu käynnistyy vasta kun kirjaudut sisään (FileVault on päällä). Kindle näyttää siihen asti 'yhteysvirhe'.

## Kindlen asetukset

Tiedosto `/mnt/us/saa-ja-sahko.conf` Kindlellä:

```
URL=http://192.168.0.157:8088/kindle.png
FRONTLIGHT=0
```

- `URL`: Mac minin osoite ja portti.
- `FRONTLIGHT`: näytön valon kirkkaus (0 = pois).

Muokkaa tiedostoa USB:n kautta: liitä Kindle Maciin, ja tiedosto `saa-ja-sahko.conf` on USB-levyn juuressa.

Mac minin osoite on nyt 192.168.0.157. Suositus: tee Mac minille DHCP-varaus reitittimestä, niin osoite ei vaihdu. Jos osoite silti vaihtuu, päivitä se vain `URL`-riville tiedostossa `saa-ja-sahko.conf`. Näyttöohjelma ja kehitysyhteys lukevat Macin osoitteen sieltä.

## Päivitykset

- Päivällä (06-23) kuva päivittyy 30 minuutin välein, yöllä 2 tunnin välein. Aamulla kuva päivittyy klo 6, vaikka edellisestä hausta ei olisi kulunut 2 tuntia.
- Huomisen hinnat julkaistaan noin klo 14. Sitä ennen näytöllä lukee "huomisen hinnat n. klo 14".

## Vianetsintä

Mac:

```
curl http://192.168.0.157:8088/health
tail -f ~/Library/Logs/saasahko.log
uv run python -m saasahko preview out.png --config config.toml
```

Viimeinen komento hakee tiedot kerran ja piirtää kuvan tiedostoon `out.png`.

Kindle:

- Loki on `/mnt/us/saa-ja-sahko.log`, ja se näkyy USB:llä (onnistuneet haut: `fetch ok`, epäonnistuneet: `fetch failed`).
- Näytöllä "yhteysvirhe HH.MM" tarkoittaa, ettei Mac vastannut kello HH.MM. Tarkista Macin palvelu (`/health`) ja osoite.
- Kehitysyhteys (väliaikaiseen vianetsintään): aja `scripts/deploy-kindle.sh --dev`, joka kopioi myös `kehitysyhteys.sh`:n Kindlen `documents`-kansioon, ja napauta kirjastossa "Kehitysyhteys". Se avaa salaamattoman root-yhteyden (telnet) vain Mac minille, ja yhteys katoaa Kindlen uudelleenkäynnistyksessä. Näytölle tulee Kindlen IP-osoite. Komennot Kindlellä:

  ```
  KINDLE_IP=<Kindlen IP> scripts/kindle-sh "tail -20 /mnt/us/saa-ja-sahko.log"
  ```

  (`KINDLE_IP`:n oletus on 192.168.0.186.) Kun et enää tarvitse yhteyttä, aja `scripts/deploy-kindle.sh` ilman `--dev`-valitsinta: se poistaa `kehitysyhteys.sh`:n Kindleltä.
- Kopiointi Kindlelle: liitä Kindle USB:llä ja aja `scripts/deploy-kindle.sh`. Se kopioi scriptletit (ei kehitysyhteyttä) ja näyttöohjelman, mutta ei ylikirjoita olemassa olevaa `saa-ja-sahko.conf`-tiedostoa.

## Amazonin päivitykset

Jailbreak on estänyt Amazonin ohjelmistopäivitykset (`otaupd` ja `otav3` on nimetty `.bck`). Näyttöohjelma pysäyttää ne lisäksi joka kierroksella ja poistaa ladatut päivitystiedostot.

## Kehitys

```
uv run pytest
```

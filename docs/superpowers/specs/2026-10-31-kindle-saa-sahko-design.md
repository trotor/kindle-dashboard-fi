# Kindle sää- ja sähkönäyttö – suunnittelu

Päivitetty 2026-10-31

## Tarkoitus

Vanha jailbreakattu Kindle Paperwhite seinällä tai pöydällä näyttää yhdellä silmäyksellä Toivalan (Siilinjärvi) sään ja pörssisähkön hinnat tälle ja seuraavalle päivälle. Käyttäjä suunnittelee niiden avulla ruoanlaittoa ja sähköauton latausta halvoille tunneille. Laitetta vilkaistaan ohimennen, eikä sillä tehdä mitään muuta.

## Tavoitteet

- Näytöllä näkyy aina ajantasainen tilanne: sää nyt, lähituntien ja lähipäivien ennuste, sähkön hinta nyt sekä 48 tunnin hintakäyrä, jossa halvimmat tunnit erottuvat.
- Toimii itsekseen. Käyttäjän ei tarvitse tehdä mitään sen jälkeen, kun hän on napauttanut "Sää ja sähkö" -kirjaa.
- Pärjää akulla mahdollisimman pitkään. Laturissa käyttö on myös ok.
- Marginaalin ja siirtomaksun voi lisätä myöhemmin muuttamalla asetustiedostoa, ilman koodimuutoksia.

## Ei tavoitteita

- Interaktiivisuutta (kosketusnäytön käyttöä näytöllä) ei ole.
- Ei automaattista käynnistystä uudelleenkäynnistyksen jälkeen (voidaan lisätä myöhemmin).
- Ei muita tietoja (kalenteri, uutiset ym.).
- Ei etäpääsyä (SSH) Kindleen. Sitä ei tarvita tähän.

## Anti-tavoitteet (epäonnistuminen vaikka "toimisi")

- Kindle päivittyy Amazonin OTA-päivityksellä ja jailbreak katoaa.
- Kindlen käyttöliittymä (näytönsäästäjä, mainos, valikko) peittää näytön.
- Näytöllä on vanhentunutta tietoa ilman, että siitä näkee sen olevan vanhaa.
- Kindle muuttuu käyttökelvottomaksi lukemiseen (uudelleenkäynnistyksen jälkeen sen pitää olla taas tavallinen Kindle).

## Ympäristö (tarkistettu laitteelta 2026-10-31)

**Kindle**
- Paperwhite 3 (7. sukupolvi), firmware 5.16.2.1.1, alusta `kindlepw2` (armel, ei armhf).
- Jailbreak: WinterBreak2 / jb.sh v2.3.0 (`hdnext`-pino). Hotfix on asennettu jailbreakin mukana. KUAL/MRPI ovat vanhentuneita, eikä niitä käytetä.
- **Scriptlets:** `.sh`-tiedosto kansiossa `/mnt/us/documents` (USB-levyllä `documents/`) näkyy kirjastossa kirjana, ja napautus ajaa sen roottina. Metatiedot otsikkoriveillä: `# Name:`, `# Author:`, `# Icon:`, `# DontUseFBInk`, `# UseHooks`. Dokumentaatio: https://github.com/KindleModding/kindlemodding.github.io/blob/main/content/kindle-dev/scriptlets.md
- Näyttö: 1072 × 1448, 8-bittinen harmaasävy, 300 dpi, framebuffer `mxc_epdc_fb`, `rotate: 3`.
- Saatavilla: `curl` 7.86 (OpenSSL 1.0.2, HTTPS toimii), `wget`, `eips`, `lipc-get-prop`/`lipc-set-prop`, `rtcwake`, `sqlite3`, `telnetd`. FBInk: `/mnt/us/libkh/bin/fbink`. Ei Pythonia.
- RTC: `/sys/class/rtc/rtc{0,1,2}/wakealarm` ovat olemassa.
- OTA: `otaupd`- ja `otav3`-jobit ovat tilassa `stop/waiting`. Binäärejä ei löydy polusta `/usr/bin`.
- Verkko: Kindle 192.168.0.185 (Wi-Fi, DHCP).
- macOS luo USB-levylle `._*`-tiedostoja. `documents/`-kansiossa ne näkyisivät rikkinäisinä scriptleteinä, joten aja aina `dot_clean -m /Volumes/Kindle/documents` kopioinnin jälkeen.

**Mac mini**
- Aina päällä, kotiverkossa 192.168.0.157. Toimii palvelimena.

## Arkkitehtuuri (päätetty)

Mac mini hakee datan, piirtää valmiin kuvan ja jakaa sen HTTP:llä kotiverkkoon. Kindle vain hakee kuvan ja näyttää sen. Kaikki logiikka ja ulkoasu ovat Macilla, joten Kindleen ei tarvitse koskea, kun ulkoasua muutetaan.

```
[Ilmatieteen laitos] ─┐
                      ├─> Mac mini: hae → piirrä PNG 1072×1448 → HTTP :portti/kindle.png
[pörssisähkö-API] ────┘                                  ▲
                                                         │ curl
                                   Kindle (scriptlet): hae → näytä (eips/fbink) → nuku (RTC) → toista
```

## Näytön sisältö (käyttäjä valitsi luonnoksen B "Sää pääosassa")

Pystysuunta, ylhäältä alas:

1. **Yläpalkki:** "TOIVALA" vasemmalla, oikealla päivä ja kellonaika (kuvan muodostusaika, esim. "la 31.10. · 14.30"). Akkumerkki, kun akkua on vähän. Huomautus, jos päivitys on epäonnistunut (ks. virhetilanteet).
2. **Sää nyt:** iso lämpötila ja sääsymboli. Pienellä pilvisyys tekstinä, tuntuu kuin -lämpötila ja tuuli (m/s).
3. **Tuntiennuste:** seuraavat 6 tuntia (kellonaika, symboli, lämpötila).
4. **Päiväennuste:** seuraavat 3 päivää (viikonpäivä, symboli, ylin/alin).
5. **Sähkö:** otsikko "SÄHKÖ" ja hinta nyt isolla (c/kWh). Sen alla pylväskäyrä tälle päivälle ja huomiselle (48 tuntia, klo 00–24 + 00–24):
   - Pylväs = tunnin keskihinta (lähdedata on 15 minuutin jaksoina).
   - Mennyt aika vaalean harmaana, nykyhetki katkoviivana ja "nyt"-merkintä, päivänvaihto pystyviivana.
   - Kunkin päivän 3 halvinta tuntia mustalla, muut keskiharmaalla.
   - X-akselin merkinnät: 00, 06, 12, 18, su 00, 06, 12, 18, 24 (viikonpäivän lyhenne seuraavan päivän kohdalla).
   - Jos huomisen hintoja ei vielä ole (julkaistaan noin klo 14), käyrän oikea puoli on tyhjä ja siinä lukee "huomisen hinnat n. klo 14".

Luonnos: `.superpowers/brainstorm/90355-1793481098/content/layout.html` (vaihtoehto B). Mittasuhteet ja tiedon järjestys ovat sitovia. Tarkka typografia ja symbolien piirtotapa jätetään tekijälle, mutta tekstin pitää olla luettavaa 1–2 metrin päästä (iso lämpötila ja hinta).

Kieli on suomi. Hinnat pilkulla (6,4 c), lämpötilat merkillä (+4°, −6°).

## Data

**Sää: Ilmatieteen laitoksen avoin data** (WFS, ei avainta).
- Ennuste: stored query `fmi::forecast::edited::weather::scandinavia::point::simple`, esim. parametrit `Temperature, WeatherSymbol3, WindSpeedMS, FeelsLike` (tarkista nimet), `timestep=60`.
- **Käytä koordinaatteja, ei paikannimeä:** `latlon=62.9876,27.7216`. `place=toivala` palauttaa väärän Toivalan (60.40, 24.83).
- "Sää nyt" voidaan ottaa ennusteen lähimmästä tunnista tai lähimmältä havaintoasemalta (Kuopion lentoasema / Siilinjärvi). Tekijä valitsee.

**Sähkö: `https://api.porssisahko.net/v2/latest-prices.json`** (avoin, ei avainta).
- Palauttaa 15 minuutin jaksot (`price`, `startDate`, `endDate`, UTC), vähintään kuluvan ja julkaisun jälkeen seuraavan päivän.
- **`price` sisältää jo ALV:n 25,5 % (c/kWh)** – tarkistettu 2026-10-31 vertaamalla spot-hinta.fi:n `PriceNoTax`/`PriceWithTax`-arvoihin (esim. 12,828 × 1,255 = 16,099). ALV:tä ei siis lisätä. Varalähde: `https://api.spot-hinta.fi/TodayAndDayForward` (`PriceWithTax`, €/kWh).
- Muunna ajat Suomen aikaan (Europe/Helsinki, huomioi kesäaika).

**Asetustiedosto** (Macilla, esim. `config.toml` tai `.json`):
- `margin_c_per_kwh = 0` (kommentti: Herrfors 0,23)
- `transfer_c_per_kwh = 0` (siirtomaksu, lisätään myöhemmin)
- `lat`, `lon`, paikan nimi näytölle, HTTP-portti.
- Näytetty hinta = rajapinnan hinta (sis. ALV) + marginaali + siirto. Marginaali ja siirto syötetään sellaisinaan (c/kWh, sis. ALV). Kun ne ovat nollia, näytöllä on pörssihinta + ALV.

## Mac minin palvelu

- Pieni ohjelma käynnistyy automaattisesti (launchd) ja pysyy käynnissä uudelleenkäynnistysten yli.
- Hakee säädatan noin 30 minuutin välein ja hintadatan useammin klo 13–16 välillä, kunnes huomisen hinnat löytyvät, muuten harvoin. Välimuistiin tallennetaan viimeisin onnistunut data, ettei katkos tyhjennä näyttöä.
- Kuva piirretään **pyydettäessä** (tai heti ennen pyyntöä), jotta kellonaika ja "nyt"-merkki ovat tuoreita.
- Kuva: PNG, 1072 × 1448, 8-bittinen harmaasävy, pystysuunta. Selkeät mustat ja valkoiset pinnat. Harmaasävyjä vain muutama (e-ink).
- Jaetaan vain kotiverkkoon (HTTP, esim. `http://192.168.0.157:<portti>/kindle.png`).
- Kindle voi lähettää akun varauksen pyynnön parametrina (esim. `?batt=70`), jolloin Mac piirtää akkumerkin, kun akku on vähissä (esim. < 20 %).
- Kieli/työkalut: tekijän valinta (ks. alla).

## Kindlen scriptlet "Sää ja sähkö"

Tiedosto `documents/saa-ja-sahko.sh` (`# Name: Sää ja sähkö`, `# DontUseFBInk`).

Napautettaessa:
1. Ajetaan pääsilmukka taustalla (irrotettuna scriptletin ajosta), jotta Kindlen kirjasto ei jää odottamaan.
2. Kindlen oma käyttöliittymä pysäytetään (esim. `stop framework` tai vastaava PW3/5.16:lle sopiva), jottei näytönsäästäjä tai valikot tule näkyviin. Näytönsäästäjä/automaattinen lepo estetään (`lipc-set-prop com.lab126.powerd preventScreenSaver 1` tai vastaava).
3. OTA-palvelut pysäytetään varmuuden vuoksi jokaisella kierroksella (`stop otaupd`, `stop otav3`, `stop ota-update`), ja `/mnt/us/*.bin`- ja `*.tmp.partial`-päivitystiedostot poistetaan, jos niitä ilmestyy.
4. Silmukka: Wi-Fi päälle ja odotus, että yhteys on ylhäällä → `curl` kuva Macilta (aikakatkaisu) → jos onnistui, näytä (täysi päivitys, ei haamukuvia) → nuku seuraavaan päivitykseen RTC-herätyksellä (`rtcwake` tai `wakealarm`) → toista.
5. Väli: päivällä (06–23) 30 min, yöllä (23–06) esim. 2 h. Kun huomisen hinnat ilmestyvät, ne näkyvät viimeistään seuraavalla kierroksella.

**Lukemiseen palaaminen:** Kindlen uudelleenkäynnistys (virtanappi pohjassa). Mikään ei käynnisty automaattisesti, joten Kindle palaa tavalliseksi.

**Virhetilanteet:**
- Mac tai verkko ei vastaa: näytölle jää edellinen kuva. Tekijä valitsee tavan näyttää, että kuva on vanha. Esimerkiksi Kindle piirtää FBInkillä pienen tekstin "päivitys epäonnistui HH.MM" kulmaan, tai Mac piirtää aikaleiman, josta vanhuuden näkee. Vähintään aikaleima yläpalkissa riittää.
- Lokit tiedostoon `/mnt/us/saa-ja-sahko.log` (näkyy USB-levyllä). Pidetään lyhyenä (kierrätys).

## Pysyvä OTA-esto (käyttäjän päätös 2026-10-31)

Käyttäjä hyväksyi pysyvän päivitysten eston, joka on voimassa myös silloin, kun näyttötila ei ole käynnissä. Toteutetaan erillisenä, kertaluontoisena scriptletinä (esim. "Estä päivitykset"), jota ei sotketa näyttöohjelmaan:
- Etsitään OTA-ohjelmat (`otaupd`, `otav3` ja niiden upstart-jobit; ne eivät ole polussa `/usr/bin`, joten sijainti selvitetään ensin diagnostiikalla) ja neutraloidaan ne yhteisön vakiintuneella tavalla (esim. nimetään uudelleen `.bak`-päätteelle, `mntroot rw` → muutos → `mntroot ro`).
- Juuritiedostojärjestelmässä on vain 32 Mt vapaata, joten tiedostoja ei kopioida vaan ainoastaan nimetään uudelleen.
- Tehdään myös peruutus-scriptlet ("Salli päivitykset"), joka palauttaa alkuperäiset nimet.
- Tulos lokitetaan tiedostoon `/mnt/us/ota-esto.log` tarkistusta varten.
- Näyttöohjelman omat OTA-pysäytykset jäävät varmistukseksi.

Tämä korvaa ei-tavoitteen "Kindle palaa tavalliseksi" siltä osin, että Kindle ei enää saa Amazonin päivityksiä.

## Suunnittelijan ratkaisut tarkistuksen jälkeen (Clauden päätöksiä, käyttäjä voi muuttaa)

- **Macin osoite:** Kindle lukee kuvan osoitteen tiedostosta `/mnt/us/saa-ja-sahko.conf` (USB-levyn juuressa), joten sen voi korjata USB:n kautta ilman koodimuutosta. Käyttäjää suositellaan varaamaan reitittimestä Mac minille kiinteä osoite (DHCP-varaus 192.168.0.157).
- **Hinta nyt -luvun koko:** suurempi kuin luonnoksessa B, noin puolet lämpötilan koosta, jotta se on luettavissa 1–2 metristä. Tilaa otetaan pienentämällä hintakäyrää ja tuntiennustetta hieman. Sisällön järjestys pysyy B:n mukaisena; "mittasuhteet sitovia" tarkoittaa järjestystä ja painotusta (sää ylempänä ja isompana), ei pikselikokoja.
- **Akku ja lepotila:** laturi on käyttäjälle ok. Ensin tehdään yksinkertainen ja luotettava versio, joka pysyy hereillä ja nukkuu `sleep`-komennolla. RTC-syväuni lisätään toisena vaiheena, jos se toimii luotettavasti PW3/5.16:lla; muuten jäädään hereillä pysyvään versioon ja laite on laturissa. Kulutus mitataan 24 tunnin aikana.
- **Etuvalo:** pois päältä oletuksena (e-ink näkyy huonevalossa). Valon taso asetustiedostoon Kindlelle, jos käyttäjä haluaa sen myöhemmin.

## Tekijän päätettävissä

- Mac-palvelun kieli ja kirjastot (esim. Python + Pillow tai HTML → kuva). Kirjataan suunnitelmaan.
- Kuvan näyttäminen `eips -g` vai `fbink -g`, ja kiertosuunnan käsittely (framebufferin `rotate: 3`).
- Tarkka tapa pysäyttää Kindlen käyttöliittymä ja estää lepotila tällä firmwarella. Ennakkotapaus: pascalw/kindle-dash (https://github.com/pascalw/kindle-dash), joka tekee lähes saman asian.
- Sääsymbolien piirtotapa (ikonifontti tai omat yksinkertaiset kuvat). FMI:n `WeatherSymbol3`-koodit pitää kuvata symboleiksi ja suomenkielisiksi kuvauksiksi.
- Portti, tiedostorakenne.

## Ennen valmista: tarkistettavat

- Kindle näyttää kuvan oikein päin ja koko näytön kokoisena.
- Kindle herää ajallaan ja päivittää kuvan; akunkulutus 24 tunnin aikana mitataan.
- Uudelleenkäynnistyksen jälkeen Kindle on tavallinen Kindle.
- Ennen klo 14 näkyy "huomisen hinnat n. klo 14", ja sen jälkeen huomisen käyrä.
- Mac-palvelu käynnistyy itsestään Macin uudelleenkäynnistyksen jälkeen.

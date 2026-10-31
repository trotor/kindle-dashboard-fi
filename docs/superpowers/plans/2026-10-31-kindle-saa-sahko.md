# Kindle sää- ja sähkönäyttö – toteutussuunnitelma

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mac mini piirtää Toivalan sään ja pörssisähkön hinnat Kindlen kokoiseksi PNG:ksi, ja jailbreakattu Kindle Paperwhite 3 hakee ja näyttää sen itsenäisesti.

**Architecture:** Python-palvelu Mac minillä (launchd) hakee taustalla FMI:n ennusteen ja porssisahko.netin hinnat välimuistiin ja palvelee `GET /kindle.png` -pyynnöt kotiverkkoon. Kindlellä on shell-scriptlet, joka pysäyttää Kindlen käyttöliittymän ja hakee kuvan silmukassa `curl`illa ja näyttää sen `eips`illä. Erilliset scriptletit estävät OTA-päivitykset pysyvästi.

**Tech Stack:** Python 3.13 + uv, Pillow, pytest, stdlib (`http.server`, `urllib`, `zoneinfo`, `tomllib`, `xml.etree`); Kindle: busybox sh, `curl`, `eips`, `lipc-*`.

**Spec:** `docs/superpowers/specs/2026-10-31-kindle-saa-sahko-design.md`

## Global Constraints

- Kuva: PNG, 1072 × 1448, Pillow-tila `"L"` (8-bit harmaa), pystysuunta.
- Paikka: "TOIVALA", `lat=62.9876`, `lon=27.7216`. FMI:lle aina `latlon=`, ei `place=`.
- Aikavyöhyke `Europe/Helsinki`. Kaikki sisäiset ajat ovat UTC-aikaleimoja (aware), ja muunnos paikalliseen aikaan tehdään vasta näyttövaiheessa.
- Hinnat: `https://api.porssisahko.net/v2/latest-prices.json`, `price` = c/kWh **sis. ALV 25,5 %**. Näytetty hinta = `price + margin_c + transfer_c`. Oletukset 0, ja kommentti `# Herrfors: 0.23`.
- Suomenkielinen muotoilu: desimaalipilkku (`6,4`), lämpötila `+4°` / `−6°` (U+2212) / `0°`, kellonaika `14.30`, viikonpäivät `ma ti ke to pe la su`.
- Kindlen päivitysväli on 1800 s klo 06–23 ja 7200 s klo 23–06.
- Kindle: firmware 5.16.2.1.1, `kindlepw2` (armel), ei Pythonia. Scriptletit kansioon `/mnt/us/documents`. Kopioinnin jälkeen aina `dot_clean -m /Volumes/Kindle/documents`.
- Mac mini 192.168.0.157, Kindle 192.168.0.185, palvelun portti 8088.
- Fontit: `/System/Library/Fonts/Supplemental/Arial.ttf` ja `Arial Bold.ttf`.

## Review Focus

1. **Negatiiviset ja nollahinnat** (Suomessa yleisiä tuulisina öinä): pylväs piirretään nollaviivasta alaspäin, ja "halvimmat" valitsee negatiiviset. Testit ovat Taskeissa 2 ja 5.
2. **Kesäajan vaihtopäivät** (23 tai 25 tuntia): `hourly_prices` palauttaa aina 24 paikallista tuntia. Tuplatunti keskiarvoistetaan, puuttuva tunti on `None`. Testi on Taskissa 2.
3. **Huomisen hinnat puuttuvat** (ennen klo 14) **ja päivänvaihde** (klo 00.05 eilinen "huominen" on tänään): näytölle tulee teksti "huomisen hinnat n. klo 14" eikä tyhjää käyrää ilman selitystä. Testit ovat Taskeissa 4 ja 5.
4. **Rajapinta tai verkko ei vastaa:** palvelu näyttää viimeisimmän onnistuneen datan ja yläpalkkiin tulee huomautus. Jos Mac ei vastaa, Kindle jättää vanhan kuvan ja kirjoittaa "yhteysvirhe HH.MM". Testit ovat Taskeissa 4, 6 ja 8.
5. **FMI palauttaa `NaN`-arvoja tai lyhyemmän ennusteen:** rivit ohitetaan, ja puuttuvat sarakkeet jätetään piirtämättä ilman kaatumista. Testit ovat Taskeissa 3 ja 5.

---

## Tiedostorakenne

```
pyproject.toml                 uv-projekti (pillow, pytest)
config.example.toml            esimerkkiasetukset (versionhallinnassa)
config.toml                    oikeat asetukset (gitignore)
saasahko/__init__.py
saasahko/config.py             Config + load_config
saasahko/fmt.py                suomenkieliset muotoilut
saasahko/prices.py             hintojen jäsennys, tuntikeskiarvot, halvimmat
saasahko/weather.py            FMI-jäsennys, nykyhetki, tunnit, päivät
saasahko/symbols.py            WeatherSymbol3 → kuvaus + ikonityyppi
saasahko/store.py              DataStore: haku, välimuisti, ajastus
saasahko/state.py              DashboardState + build_state
saasahko/icons.py              sääikonit Pillow-primitiiveillä
saasahko/render.py             render(state) -> Image
saasahko/app.py                HTTP-palvelin + taustapäivitys
saasahko/__main__.py           CLI: serve | preview
tests/...                      pytest
deploy/fi.ronkko.saasahko.plist  launchd
kindle/documents/saa-ja-sahko.sh      scriptlet (käynnistin)
kindle/documents/kehitysyhteys.sh     väliaikainen telnet (poistetaan lopuksi)
kindle/documents/esta-paivitykset.sh  OTA-esto
kindle/documents/salli-paivitykset.sh OTA-eston peruutus
kindle/saa-ja-sahko/lib.sh            testattavat apufunktiot
kindle/saa-ja-sahko/dash.sh           pääsilmukka
kindle/saa-ja-sahko.conf              Kindlen asetukset (URL, FRONTLIGHT)
scripts/deploy-kindle.sh       kopioi kindle/ → /Volumes/Kindle
scripts/kindle-sh              aja komento Kindlellä telnetin yli (nc)
```

---

### Task 1: Projektipohja ja asetukset

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `config.example.toml`, `saasahko/__init__.py`, `saasahko/config.py`, `saasahko/fmt.py`
- Test: `tests/test_config.py`, `tests/test_fmt.py`

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) class Config: place_name: str = "TOIVALA"; lat: float = 62.9876; lon: float = 27.7216; port: int = 8088; margin_c: float = 0.0; transfer_c: float = 0.0; low_battery_percent: int = 20; cache_dir: Path = Path("cache"); timezone: str = "Europe/Helsinki"`
  - `load_config(path: Path) -> Config` (TOML. Puuttuvat avaimet saavat oletusarvon, ja tuntematon avain aiheuttaa `ValueError`. `cache_dir` on suhteellinen asetustiedoston kansioon nähden.)
  - `fmt_temp(t: float) -> str`, `fmt_price(c: float) -> str`, `fmt_clock(dt: datetime) -> str`, `fmt_weekday(d: date) -> str`, `fmt_header(dt: datetime) -> str`

- [ ] **Step 1:** Aja `git init` kansiossa `/Users/teroronkko/code/kindle`. Tee `.gitignore`, jossa ovat `.superpowers/`, `cache/`, `config.toml`, `.venv/`, `__pycache__/` ja `*.png` paitsi `!tests/golden/*.png`. Aja `uv init --bare` ja `uv add pillow` sekä `uv add --dev pytest`.
- [ ] **Step 2: Kirjoita testit**

```python
def test_defaults_when_keys_missing(tmp_path):
    p = tmp_path / "c.toml"; p.write_text('margin_c = 0.23\n')
    c = load_config(p)
    assert c.margin_c == 0.23 and c.lat == 62.9876 and c.port == 8088
    assert c.cache_dir == tmp_path / "cache"

def test_unknown_key_rejected(tmp_path):
    p = tmp_path / "c.toml"; p.write_text('marginaali = 1\n')
    with pytest.raises(ValueError): load_config(p)

@pytest.mark.parametrize("t,s", [(4.2,"+4°"), (-6.4,"−6°"), (-0.3,"0°"), (0.4,"0°"), (12.5,"+13°"), (-2.5,"−3°")])
def test_fmt_temp(t, s): assert fmt_temp(t) == s

@pytest.mark.parametrize("c,s", [(6.43,"6,4"), (12.06,"12,1"), (-0.44,"−0,4"), (0.0,"0,0")])
def test_fmt_price(c, s): assert fmt_price(c) == s

def test_fmt_header():
    dt = datetime(2026,10,31,14,30, tzinfo=ZoneInfo("Europe/Helsinki"))
    assert fmt_header(dt) == "la 31.10. · 14.30"
    assert fmt_clock(dt) == "14.30" and fmt_weekday(dt.date()) == "la"
```

(Pyöristys: tavallinen pyöristys, jossa .5 pyöristyy itseisarvoltaan ylöspäin (`math.floor(abs(x)+0.5)` ja etumerkki takaisin). Pythonin `round()`-pankkiiripyöristystä ei käytetä.)

- [ ] **Step 3:** Aja `uv run pytest tests/test_config.py tests/test_fmt.py -v`. Odotettu tulos: FAIL (import).
- [ ] **Step 4:** Toteuta `config.py` ja `fmt.py`. Tee `config.example.toml`, jossa on kaikki avaimet oletusarvoineen sekä kommentit `# Herrfors: 0.23` ja `# siirtomaksu c/kWh sis. alv`. Kopioi se tiedostoksi `config.toml`.
- [ ] **Step 5:** Aja `uv run pytest -v`. Odotettu tulos: PASS.
- [ ] **Step 6:** Commit `feat: project skeleton, config and Finnish formatting`.

### Task 2: Pörssihinnat

**Files:**
- Create: `saasahko/prices.py`
- Test: `tests/test_prices.py`

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) class PriceSlot: start: datetime; price_c: float` (start UTC)
  - `parse_porssisahko(data: dict) -> list[PriceSlot]` (lajiteltu alkuajan mukaan)
  - `hourly_prices(slots: list[PriceSlot], day: date, tz: ZoneInfo, extra_c: float = 0.0) -> list[float | None]` (aina 24 alkiota, indeksi = paikallinen tunti 0–23. Arvo on tunnin varttien keskiarvo + `extra_c`, tai `None`, jos varttia ei ole.)
  - `price_at(slots, at: datetime, extra_c: float = 0.0) -> float | None` (se vartti, jonka `start <= at < start+15min`)
  - `cheapest_hours(hourly: list[float | None], n: int = 3) -> set[int]` (n pienintä tuntia, `None` ohitetaan, tasapelissä aiempi tunti)
  - `fetch_porssisahko(timeout: float = 15) -> dict`

- [ ] **Step 1: Kirjoita testit** (data rakennetaan testissä apufunktiolla `make_slots(start_utc, prices)`, joka tuottaa rajapinnan muotoisen dictin, jossa on `startDate` ja `endDate` `Z`-päätteellä):

```python
def test_parse_sorted_and_utc(): ...  # käänteinen syöte → nouseva, tzinfo == UTC
def test_hourly_average_of_quarters():
    # 2026-10-31 00:00 Helsinki = 2026-10-30T22:00Z; vartit 1,2,3,4 → tunti 0 = 2.5
    assert hourly_prices(slots, date(2026,10,31), HEL)[0] == 2.5
def test_hourly_extra_added(): ... == 2.5 + 0.23
def test_missing_hours_are_none(): # vain klo 0–13 dataa → [14:] kaikki None
def test_dst_25h_day():  # 2026-10-25: paikallinen klo 03 esiintyy kahdesti → keskiarvo kahdeksasta vartista, len == 24
def test_dst_23h_day():  # 2027-03-28: paikallinen klo 03 puuttuu → [3] is None, len == 24
def test_price_at_quarter_boundary(): price_at(slots, 22:15Z) == toisen vartin hinta
def test_cheapest_includes_negative():
    assert cheapest_hours([5, -0.4, 3, None, 0.0, 7]) == {1, 2, 4}
def test_cheapest_tie_prefers_earlier():
    assert cheapest_hours([1, 1, 1, 1], n=3) == {0, 1, 2}
```

- [ ] **Step 2:** Aja `uv run pytest tests/test_prices.py -v`. Odotettu tulos: FAIL.
- [ ] **Step 3:** Toteuta `prices.py`. `hourly_prices` ryhmittelee vartit `slot.start.astimezone(tz)`:n (päivä, tunti) mukaan. `fetch_porssisahko` käyttää `urllib.request`, ja otsakkeena on `User-Agent: saasahko-kindle`.
- [ ] **Step 4:** Aja `uv run pytest tests/test_prices.py -v`. Odotettu tulos: PASS.
- [ ] **Step 5:** Commit `feat: spot price parsing, hourly averages, cheapest hours`.

### Task 3: Sää (FMI) ja symbolit

**Files:**
- Create: `saasahko/weather.py`, `saasahko/symbols.py`, `tests/fixtures/fmi_toivala.xml`
- Test: `tests/test_weather.py`, `tests/test_symbols.py`

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) class HourForecast: time: datetime; temp: float; symbol: int; wind: float; feels_like: float`
  - `@dataclass(frozen=True) class DaySummary: day: date; tmin: float; tmax: float; symbol: int`
  - `build_fmi_url(lat: float, lon: float, start: datetime, hours: int = 100) -> str` (stored query `fmi::forecast::edited::weather::scandinavia::point::simple`, `parameters=Temperature,WeatherSymbol3,WindSpeedMS,FeelsLike`, `timestep=60`, `starttime`/`endtime` ISO Z, `latlon=lat,lon`)
  - `parse_fmi(xml: str) -> list[HourForecast]` (aikajärjestys. Jos jokin neljästä arvosta puuttuu tai on `NaN`, tunti ohitetaan.)
  - `fetch_fmi(url: str, timeout: float = 20) -> str`
  - `current(hours, now: datetime) -> HourForecast | None` (tunti, joka on lähimpänä hetkeä `now`. Jos lähin on yli 90 minuutin päässä, palautetaan `None`.)
  - `next_hours(hours, now: datetime, n: int = 6) -> list[HourForecast]` (ensimmäiset n tuntia, joille `time > now`)
  - `daily_summaries(hours, tz: ZoneInfo, today: date, n: int = 3) -> list[DaySummary]` (päivät today+1…today+n. min/max lasketaan paikallisen päivän tunneista, ja symboli otetaan paikallisen klo 12 tunnista tai lähimmästä. Jos päivälle ei ole yhtään tuntia, päivä jätetään pois.)
  - `describe(code: int) -> str` ja `icon_kind(code: int, night: bool) -> str`, jonka arvo on joukosta `{"sun","moon","partly","partly_night","cloud","rain","sleet","snow","thunder","fog"}`
  - `is_night(local: datetime) -> bool` (paikallinen tunti `< 7` tai `>= 19`)

- [ ] **Step 1:** Tallenna fixtureksi oikea vastaus: `curl -s "https://opendata.fmi.fi/wfs?service=WFS&version=2.0.0&request=getFeature&storedquery_id=fmi::forecast::edited::weather::scandinavia::point::simple&latlon=62.9876,27.7216&parameters=Temperature,WeatherSymbol3,WindSpeedMS,FeelsLike&timestep=60" > tests/fixtures/fmi_toivala.xml`. Vaihda käsin yhden `Temperature`-rivin arvoksi `NaN` NaN-testiä varten, ja kirjaa testiin sen aikaleima.
- [ ] **Step 2: Kirjoita testit**

```python
def test_parse_fixture(): hours = parse_fmi(FIX); assert len(hours) > 60 and all(h.time.tzinfo for h in hours)
def test_nan_hour_skipped(): # se aikaleima, johon NaN lisättiin, puuttuu tuloksesta
def test_url_uses_latlon(): u = build_fmi_url(62.9876, 27.7216, T0); assert "latlon=62.9876,27.7216" in u and "place=" not in u
def test_current_nearest_and_none_when_far(): ...
def test_next_hours_strictly_after_now(): assert [h.time for h in next_hours(H, T0+30min)][0] == T0+1h
def test_daily_summary_minmax_local_day(): # synteettiset tunnit: paikallinen päivä 1.11. klo 0–23, temp = tunti-10 → tmin -10, tmax 13, symboli klo 12:n tunnista
def test_daily_summary_skips_empty_days(): # dataa vain 1 päivälle → len == 1
@pytest.mark.parametrize("code,kind", [(1,"sun"),(2,"partly"),(3,"cloud"),(22,"rain"),(32,"rain"),(42,"snow"),(52,"snow"),(63,"thunder"),(72,"sleet"),(82,"sleet"),(92,"fog")])
def test_icon_kind_day(code, kind): assert icon_kind(code, night=False) == kind
def test_icon_kind_night(): assert icon_kind(1, True) == "moon" and icon_kind(2, True) == "partly_night"
def test_describe(): assert describe(3) == "pilvistä" and describe(999) == ""
```

- [ ] **Step 3:** Aja `uv run pytest tests/test_weather.py tests/test_symbols.py -v`. Odotettu tulos: FAIL.
- [ ] **Step 4:** Toteuta. Kuvaukset `describe`-funktiolle (WeatherSymbol3):
  1 selkeää · 2 puolipilvistä · 3 pilvistä · 21 heikkoja sadekuuroja · 22 sadekuuroja · 23 voimakkaita sadekuuroja · 31 heikkoa vesisadetta · 32 vesisadetta · 33 voimakasta vesisadetta · 41 heikkoja lumikuuroja · 42 lumikuuroja · 43 voimakkaita lumikuuroja · 51 heikkoa lumisadetta · 52 lumisadetta · 53 voimakasta lumisadetta · 61 ukkoskuuroja · 62 voimakkaita ukkoskuuroja · 63 ukkosta · 64 voimakasta ukkosta · 71 heikkoja räntäkuuroja · 72 räntäkuuroja · 73 voimakkaita räntäkuuroja · 81 heikkoa räntäsadetta · 82 räntäsadetta · 83 voimakasta räntäsadetta · 91 utua · 92 sumua.
  `icon_kind` toimii koodiväleittäin: 1→sun/moon, 2→partly/partly_night, 3→cloud, 21–33→rain, 41–53→snow, 61–64→thunder, 71–83→sleet, 91–92→fog, muut→cloud. XML jäsennetään `xml.etree.ElementTree`:llä nimiavaruuksien kanssa.
- [ ] **Step 5:** Aja `uv run pytest -v`. Odotettu tulos: PASS.
- [ ] **Step 6:** Commit `feat: FMI forecast parsing and weather symbols`.

### Task 4: Datavarasto ja näyttötila

**Files:**
- Create: `saasahko/store.py`, `saasahko/state.py`
- Test: `tests/test_store.py`, `tests/test_state.py`

**Interfaces:**
- Consumes: Task 1–3.
- Produces:
  - `@dataclass class Snapshot: slots: list[PriceSlot]; hours: list[HourForecast]; prices_fetched_at: datetime | None; weather_fetched_at: datetime | None; last_error: str | None`
  - `class DataStore: __init__(self, cfg: Config, fetch_prices=fetch_porssisahko, fetch_weather=fetch_fmi, clock=lambda: datetime.now(UTC))`, `refresh(self) -> None`, `snapshot(self) -> Snapshot`
  - `@dataclass class DashboardState: now_local: datetime; place: str; current: HourForecast | None; current_desc: str; next_hours: list[HourForecast]; days: list[DaySummary]; prices_today: list[float | None]; prices_tomorrow: list[float | None]; cheapest_today: set[int]; cheapest_tomorrow: set[int]; price_now: float | None; battery: int | None; low_battery: bool; note: str | None`
  - `build_state(snap: Snapshot, cfg: Config, now: datetime, battery: int | None) -> DashboardState`

Ajastussäännöt (`refresh`):
- Sää haetaan, jos `weather_fetched_at` puuttuu tai on yli 30 minuuttia vanha.
- Hinnat haetaan, jos `prices_fetched_at` puuttuu, jos se on yli 6 tuntia vanha, tai jos paikallinen kello on 13.00–17.59, huomisen hintoja ei vielä ole ja edellisestä hausta on yli 15 minuuttia.
- Jos haku epäonnistuu, vanha data säilyy. Silloin `last_error` = `"<lähde>: <virhe>"`, ja samaa lähdettä yritetään uudelleen aikaisintaan 5 minuutin päästä.
- Kun haku onnistuu, raakadata tallennetaan kansioon `cache_dir`, tiedostoiksi `prices.json` ja `weather.xml`, ja niiden hakuajat tiedostoon `meta.json`. `__init__` lataa nämä, jos ne ovat olemassa.

`build_state`:
- `prices_today` ja `prices_tomorrow` lasketaan funktiolla `hourly_prices(..., extra_c=margin_c+transfer_c)` paikalliselle päivälle.
- `cheapest_*` lasketaan vain silloin, kun päivälle on vähintään 20 tuntia dataa; muuten tulos on tyhjä joukko.
- `low_battery` on tosi, kun `battery is not None and battery < cfg.low_battery_percent`.
- `note` saa ensimmäisen sopivan arvon tässä järjestyksessä:
  1. Jos `prices_today` on kokonaan `None`, `"ei hintatietoja"`.
  2. Jos säädata on yli 2 tuntia vanha tai puuttuu, `"sää päivitetty HH.MM"` (tai `"ei säätietoja"`).
  3. Muuten `None`.

- [ ] **Step 1: Kirjoita testit** (väärennetyt fetch-funktiot laskevat kutsuja, ja kellon voi asettaa):

```python
def test_first_refresh_fetches_both_and_persists(tmp_path): ...  # tiedostot cache_dir:ssä
def test_weather_not_refetched_within_30min(): ...
def test_prices_polled_every_15min_in_afternoon_until_tomorrow_present(): # klo 13.10 ilman huomista → haku; 13.20 → ei; 13.26 → haku; kun huominen on → ei ennen kuin 6 h
def test_failure_keeps_old_data_and_sets_error(): ...
def test_failure_backoff_5min(): ...
def test_loads_cache_on_init(tmp_path): ...
def test_state_midnight_rollover(): # data la+su, now = su 00.05 → prices_today = sunnuntain tunnit, prices_tomorrow kaikki None
def test_state_tomorrow_missing_before_14(): # prices_tomorrow kaikki None, cheapest_tomorrow == set()
def test_state_extra_cost_applied(): # margin 0.23 + transfer 5 → price_now == raw + 5.23
def test_state_note_priorities(): ...
def test_low_battery_flag(): build_state(..., battery=15).low_battery is True; battery=None → False
```

- [ ] **Step 2:** Aja `uv run pytest tests/test_store.py tests/test_state.py -v`. Odotettu tulos: FAIL.
- [ ] **Step 3:** Toteuta `store.py` (`threading.Lock` suojaa tilan, koska HTTP ja taustasäie käyttävät sitä yhtä aikaa) ja `state.py`.
- [ ] **Step 4:** Aja `uv run pytest -v`. Odotettu tulos: PASS.
- [ ] **Step 5:** Commit `feat: data store with caching and dashboard state`.

### Task 5: Piirto

**Files:**
- Create: `saasahko/icons.py`, `saasahko/render.py`, `tests/sample_state.py`
- Test: `tests/test_render.py`

**Interfaces:**
- Consumes: `DashboardState` (Task 4), `icon_kind`, `describe`, `is_night` (Task 3), `fmt_*` (Task 1).
- Produces: `render(state: DashboardState) -> PIL.Image.Image` (`"L"`, 1072×1448); `draw_icon(draw: ImageDraw, kind: str, box: tuple[int,int,int,int]) -> None`; `tests/sample_state.py: sample_state(**overrides) -> DashboardState` (luonnoksen B data: la 31.10. klo 14.30, +4°, pilvistä, keksityt 48 tunnin hinnat sisältäen yhden negatiivisen tunnin huomenna)

Asettelu (y-koordinaatit pikseleinä, sivumarginaali 40). Tekijä saa hienosäätää ±20 px, kunhan järjestys ja koot säilyvät:

| Alue | y | Sisältö |
|---|---|---|
| Yläpalkki | 0–90 | `place` Arial Bold 40 vasemmalla. Oikealla `fmt_header(now)` Arial 36. Jos `low_battery`, akkumerkki ja `%` ennen päiväystä. Jos `note` on asetettu, se näkyy keskellä Arial 30 käänteisenä (valkoinen teksti mustalla pohjalla). Viiva y=90 (3 px). |
| Sää nyt | 100–400 | Ikoni 240×240 vasemmalla. Lämpötila Arial Bold 200 ikonin oikealla puolella. Alla Arial 38: `"Pilvistä · tuntuu kuin +1° · tuuli 4 m/s"` (kuvauksen ensimmäinen kirjain isolla, tuuli pyöristetään kokonaisluvuksi). |
| Tunnit | 420–610 | 6 saraketta: tunti Arial 34, ikoni 80×80, lämpötila Arial Bold 46 |
| Päivät | 620–740 | Ohut viiva yläpuolella. 3 saraketta: viikonpäivä Arial Bold 38, ikoni 60×60, `"+5° / 0°"` Arial 38 |
| Erotin | 760 | Viiva 5 px |
| Sähkö-otsikko | 775–905 | `"SÄHKÖ"` Arial Bold 40 vasemmalla ylhäällä. Oikealla `"nyt"` Arial 34 + `fmt_price(price_now)` Arial Bold 100 + `" c/kWh"` Arial 34. Jos `price_now is None`: `"–"`. |
| Käyrä | 930–1370 | 48 pylvästä (tänään 0–23, huominen 24–47). Väli 2 px. Pystyakselin apuviivat ja arvot (Arial 26) vasemmalla, 5 c:n välein. Asteikko: `top = max(10, ceil(max/5)*5)`, `bottom = min(0, floor(min/5)*5)`. Nollaviiva 2 px. Värit: mennyt tunti 0xCC, halvin 0x00, muu 0x88. Päivänvaihtoviiva musta 2 px. "nyt"-katkoviiva 3 px kohdassa `tunti + minuutit/60`, ja sen yläpuolella `"nyt"` Arial Bold 28. |
| Akseli | 1375–1420 | Arial 28: `00 06 12 18 <huomisen viikonpäivä> 00 06 12 18 24` (00 ja viikonpäivä samassa kohdassa: viikonpäivä + " 00") |
| Ei huomista | – | Jos `prices_tomorrow` on kokonaan `None`, käyrän oikealle puoliskolle keskelle teksti `"huomisen hinnat"` / `"n. klo 14"` Arial 34 kahdella rivillä. |

Negatiivinen pylväs piirretään nollaviivasta alaspäin. `draw_icon` piirtää ikonit primitiiveillä:
- **sun:** täytetty ympyrä ja 8 sädettä
- **moon:** sirppi, eli kaksi ympyrää, joista toinen on taustan värinen
- **cloud:** 3 päällekkäistä ellipsiä ja suorakulmio, ääriviiva 0x00 ja täyttö 0x88
- **partly:** aurinko oikeassa yläkulmassa ja pilvi sen edessä
- **partly_night:** sama kuin partly, mutta auringon tilalla kuu
- **rain:** pilvi ja 3 vinoa viivaa
- **snow:** pilvi ja 3 tähteä
- **sleet:** pilvi, 1 viiva ja 1 tähti
- **thunder:** pilvi ja salama (monikulmio)
- **fog:** 4 vaakaviivaa

Viivanpaksuus on `box`-leveys/20.

- [ ] **Step 1: Kirjoita testit**

```python
def test_size_and_mode(): img = render(sample_state()); assert img.size == (1072, 1448) and img.mode == "L"
def test_cheapest_bar_is_black(): # sample-datan huomisen halvimman tunnin pylvään keskikohdan pikseli == 0
def test_past_bar_is_light(): # klo 03 pylväs == 0xCC
def test_negative_bar_below_zero_line(): # negatiivisen tunnin pylväs ulottuu nollaviivan alapuolelle
def test_no_tomorrow_shows_text_and_no_bars(): img = render(sample_state(prices_tomorrow=[None]*24, cheapest_tomorrow=set())) # oikean puoliskon käyräalueella ei ole yhtään 0x88-pikseliä
def test_missing_weather_does_not_crash(): render(sample_state(current=None, next_hours=[], days=[]))
def test_note_drawn_inverted(): # note="ei hintatietoja" → yläpalkin keskellä on mustia pikseleitä, joita ilman notea ei ole
@pytest.mark.parametrize("kind", ["sun","moon","partly","partly_night","cloud","rain","sleet","snow","thunder","fog"])
def test_icon_draws_something(kind): # 100×100 valkoiselle: vähintään 200 ei-valkoista pikseliä
```

(Testit laskevat pylväiden x-koordinaatit samoista vakioista kuin `render.py`. Vie siksi `CHART_X0, CHART_X1, CHART_Y0, CHART_Y1` moduulitason vakioiksi, ja tee lisäksi `bar_x(i: int) -> tuple[int,int]` ja `value_y(v: float, top: float, bottom: float) -> int`.)

- [ ] **Step 2:** Aja `uv run pytest tests/test_render.py -v`. Odotettu tulos: FAIL.
- [ ] **Step 3:** Toteuta `icons.py` ja `render.py`.
- [ ] **Step 4:** Aja `uv run pytest -v`. Odotettu tulos: PASS.
- [ ] **Step 5: Silmämääräinen tarkistus.** Aja `uv run python -c "from tests.sample_state import sample_state; from saasahko.render import render; render(sample_state()).save('/tmp/preview.png')"` (käytä scratchpad-polkua). Avaa kuva Read-työkalulla ja tarkista, että tekstit eivät mene päällekkäin, että lämpötila on selvästi isoin ja hinta toiseksi isoin, ja että ä/ö-kirjaimet ja `−`-merkki näkyvät. Näytä kuva käyttäjälle ja korjaa, mitä hän haluaa.
- [ ] **Step 6:** Commit `feat: render dashboard image`.

### Task 6: HTTP-palvelin, CLI ja launchd

**Files:**
- Create: `saasahko/app.py`, `saasahko/__main__.py`, `deploy/fi.ronkko.saasahko.plist`
- Test: `tests/test_app.py`

**Interfaces:**
- Consumes: `DataStore`, `build_state`, `render`, `load_config`.
- Produces:
  - `make_server(cfg: Config, store: DataStore, host: str = "0.0.0.0", port: int | None = None) -> ThreadingHTTPServer`
  - `start_refresher(store: DataStore, interval_s: float = 300) -> threading.Thread` (daemon. Kutsuu `store.refresh()` heti ja sen jälkeen `interval_s` välein. Poikkeukset kirjataan lokiin, eikä säie kaadu.)
  - HTTP: `GET /kindle.png[?batt=NN]` palauttaa 200 `image/png` ja `Cache-Control: no-store`. Kuva piirretään pyynnön hetkellä, ja virheellinen `batt` jätetään huomiotta. `GET /health` palauttaa 200 JSON `{"weather_fetched_at":…, "prices_fetched_at":…, "last_error":…}`. Muut polut palauttavat 404.
  - CLI: `python -m saasahko serve --config PATH` ja `python -m saasahko preview OUT.png --config PATH` (preview tekee yhden `refresh()`-kutsun ja piirtää tuloksen).

- [ ] **Step 1: Kirjoita testit** (palvelin portissa 0 omassa säikeessään, store väärennetyillä hauilla):

```python
def test_png_endpoint(): r = get("/kindle.png?batt=55"); assert r.status == 200 and r.headers["Content-Type"] == "image/png"; Image.open(io.BytesIO(r.read())).size == (1072,1448)
def test_bad_batt_ignored(): get("/kindle.png?batt=abc").status == 200
def test_health_reports_error(): # fetch_prices nostaa poikkeuksen → last_error alkaa "prices:"
def test_404(): get("/x").status == 404
def test_refresher_survives_exception(): # refresh nostaa poikkeuksen 1. kerralla → säie elää ja kutsuu uudelleen (interval_s=0.01)
```

- [ ] **Step 2:** Aja `uv run pytest tests/test_app.py -v`. Odotettu tulos: FAIL.
- [ ] **Step 3:** Toteuta `app.py` ja `__main__.py` (argparse, loggaus stdout:iin).
- [ ] **Step 4:** Aja `uv run pytest -v`. Odotettu tulos: PASS.
- [ ] **Step 5: Oikea data.** Aja `uv run python -m saasahko preview <scratchpad>/live.png --config config.toml`. Avaa kuva Read-työkalulla ja tarkista, että lämpötila ja hinta ovat uskottavia (vertaa porssisahko.net ja ilmatieteenlaitos.fi). Näytä kuva käyttäjälle.
- [ ] **Step 6: launchd.** Tee plist: `Label=fi.ronkko.saasahko`, `ProgramArguments=[/opt/homebrew/bin/uv, run, --project, /Users/teroronkko/code/kindle, python, -m, saasahko, serve, --config, /Users/teroronkko/code/kindle/config.toml]`, `WorkingDirectory=/Users/teroronkko/code/kindle`, `RunAtLoad=true`, `KeepAlive=true`, `StandardOutPath` ja `StandardErrorPath=/Users/teroronkko/Library/Logs/saasahko.log`. Asenna: `cp deploy/fi.ronkko.saasahko.plist ~/Library/LaunchAgents/ && launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/fi.ronkko.saasahko.plist`.
- [ ] **Step 7:** Aja `curl -s http://192.168.0.157:8088/health`. Odotettu tulos: JSON, jossa molemmilla hakuajoilla on arvo ja `last_error` on null. Jos macOS:n palomuuri kysyy, salliiko Pythonin vastaanottaa yhteyksiä, käyttäjä hyväksyy sen.
- [ ] **Step 8:** Commit `feat: HTTP server, CLI and launchd agent`.

### Task 7: Kindlen kehitysyhteys ja laiteselvitys

Tämä tehtävä vaatii käyttäjää: USB-kytkentä, ja scriptletin napautus Kindlellä. Väliaikainen telnet on rajattu vain Mac minin osoitteeseen ja poistetaan Taskissa 10.

**Files:**
- Create: `kindle/documents/kehitysyhteys.sh`, `scripts/deploy-kindle.sh`, `scripts/kindle-sh`

**Interfaces:**
- Produces:
  - `scripts/deploy-kindle.sh` kopioi `kindle/documents/*.sh` → `/Volumes/Kindle/documents/` ja `kindle/saa-ja-sahko/` → `/Volumes/Kindle/saa-ja-sahko/`. `kindle/saa-ja-sahko.conf` kopioidaan vain, jos sitä ei vielä ole. Lopuksi `dot_clean -m /Volumes/Kindle`. Jos `/Volumes/Kindle` puuttuu, skripti päättyy virheeseen.
  - `scripts/kindle-sh "<komento>"` lähettää komennon `printf '%s; exit\n' "$1" | nc -w 15 192.168.0.185 23` ja tulostaa vastauksen ilman telnetin ohjaustavuja (`LC_ALL=C tr -cd '\11\12\15\40-\176'`).
  - Selvitystulokset, jotka kirjataan tämän suunnitelman loppuun kohtaan "Laiteselvitys": KÄYTTÖLIITTYMÄN_PYSÄYTYS, NÄYTTÖKOMENTO, OTA_POLUT.

- [ ] **Step 1:** Kirjoita `kehitysyhteys.sh` (`# Name: Kehitysyhteys (väliaikainen)`, `# DontUseFBInk`): `iptables -I INPUT -p tcp --dport 23 -s 192.168.0.157 -j ACCEPT; telnetd -l /bin/sh -p 23`, ja lopuksi echo, jossa on IP-osoite. Kirjoita deploy- ja kindle-sh-skriptit.
- [ ] **Step 2:** Pyydä käyttäjää kytkemään Kindle USB:llä. Aja `scripts/deploy-kindle.sh`. Pyydä käyttäjää irrottamaan Kindle ja napauttamaan "Kehitysyhteys (väliaikainen)".
- [ ] **Step 3:** Aja `scripts/kindle-sh "id; uname -m"`. Odotettu tulos: `uid=0(root)` ja `armv7l`.
- [ ] **Step 4: Laiteselvitys.** Aja ja kirjaa tulokset:
  - `ls /etc/init.d/framework; initctl list | grep -iE "framework|lab126_gui|webreader|ota"` kertoo, millä käyttöliittymä pysäytetään (ehdokkaat `stop lab126_gui`, `/etc/init.d/framework stop`, `stop framework`).
  - `find / -xdev \( -name 'otaupd*' -o -name 'otav3*' -o -name 'ota-update*' \) 2>/dev/null; ls /etc/upstart | grep -i ota` kertoo OTA-ohjelmien ja -jobien polut.
  - `lipc-get-prop com.lab126.powerd flIntensity` kertoo, toimiiko etuvalon säätö.
  - Kuvan näyttäminen: aja `curl -s -o /tmp/t.png http://192.168.0.157:8088/kindle.png && eips -f -g /tmp/t.png` ja pyydä käyttäjää kertomaan, onko kuva oikein päin ja koko näytön kokoinen. Jos ei, kokeile `/mnt/us/libkh/bin/fbink -c -f -g file=/tmp/t.png`. Kirjaa, mikä toimi.
  - Kokeile ensin käyttöliittymän pysäytystä ja sen jälkeen `eips`-näyttöä uudelleen. Palauta lopuksi käyttöliittymä vastaavalla `start`-komennolla ja varmista käyttäjältä, että Kindle näyttää taas kirjaston.
- [ ] **Step 5:** Kirjaa tulokset tämän suunnitelman loppuun ja commitoi `chore: kindle dev access and device probe` (mukana suunnitelman päivitys).

### Task 8: Kindlen näyttöohjelma

**Files:**
- Create: `kindle/saa-ja-sahko/lib.sh`, `kindle/saa-ja-sahko/dash.sh`, `kindle/documents/saa-ja-sahko.sh`, `kindle/saa-ja-sahko.conf`
- Test: `tests/test_kindle_lib.py`

**Interfaces:**
- Consumes: Taskin 7 laiteselvitys (KÄYTTÖLIITTYMÄN_PYSÄYTYS, NÄYTTÖKOMENTO, OTA_POLUT), `GET /kindle.png?batt=NN` (Task 6).
- Produces (`lib.sh`, POSIX sh, ei bashismeja):
  - `interval_for_hour H` → tulostaa `1800`, kun 6 ≤ H < 23, muuten `7200`
  - `build_url BASE BATT` → `BASE?batt=BATT`. Jos BATT on tyhjä tai ei-numeerinen, tulos on pelkkä `BASE`.
  - `log MSG` → `$LOG_FILE`-tiedostoon rivi `YYYY-MM-DD HH:MM:SS MSG`. Jos tiedosto ylittää `$LOG_MAX` tavua (oletus 100000), se siirretään nimelle `$LOG_FILE.1`.
  - `fail_text HHMM` → `yhteysvirhe HH.MM` (ASCII. `HHMM` muodossa `1530`.)
- `kindle/saa-ja-sahko.conf`: `URL=http://192.168.0.157:8088/kindle.png` ja `FRONTLIGHT=0`
- `saa-ja-sahko.sh` (`# Name: Sää ja sähkö`, `# Author: Tero`, `# DontUseFBInk`): jos `/tmp/saa-ja-sahko.pid` osoittaa elävään prosessiin, ei tehdä mitään. Muuten `nohup sh /mnt/us/saa-ja-sahko/dash.sh >/dev/null 2>&1 &`.
- `dash.sh`: lukee konffin `. /mnt/us/saa-ja-sahko.conf` ja kirjoittaa PID:n. Alussa: KÄYTTÖLIITTYMÄN_PYSÄYTYS, `lipc-set-prop com.lab126.powerd preventScreenSaver 1`, etuvalo `lipc-set-prop com.lab126.powerd flIntensity $FRONTLIGHT`. Silmukka:
  1. `stop otaupd; stop otav3; stop ota-update` (virheet ohitetaan) ja `rm -f /mnt/us/update*.bin /mnt/us/*.bin.tmp /mnt/us/*.tmp.partial`.
  2. Odotetaan, että `ping -c1 -W2 192.168.0.157` onnistuu, enintään 60 s.
  3. `curl -fsS -m 60 -o /tmp/dash.new.png "$(build_url "$URL" "$(lipc-get-prop com.lab126.powerd battLevel)")"`.
  4. Jos haku onnistuu: `mv` → `/tmp/dash.png`, NÄYTTÖKOMENTO (täysi päivitys) ja `log "fetch ok batt=<N>"`. Jos ei: `eips 1 1 "$(fail_text "$(date +%H%M)")"` vanhan kuvan päälle ja `log "fetch failed rc=<curl-paluuarvo>"`.
  5. `sleep $(interval_for_hour $(date +%H | sed 's/^0//'))`.

  Loki: `LOG_FILE=/mnt/us/saa-ja-sahko.log`.

- [ ] **Step 1: Kirjoita testit** (`subprocess.run(["sh","-c",". kindle/saa-ja-sahko/lib.sh; <kutsu>"])`):

```python
@pytest.mark.parametrize("h,s", [(0,"7200"),(5,"7200"),(6,"1800"),(14,"1800"),(22,"1800"),(23,"7200")])
def test_interval(h, s): assert run(f"interval_for_hour {h}") == s
def test_build_url(): assert run('build_url http://x/k.png 70') == "http://x/k.png?batt=70"
def test_build_url_bad_batt(): assert run('build_url http://x/k.png ""') == "http://x/k.png" and run('build_url http://x/k.png abc') == "http://x/k.png"
def test_fail_text(): assert run("fail_text 1530") == "yhteysvirhe 15.30"
def test_log_rotates(tmp_path): # LOG_MAX=50, kolme kirjoitusta → .1 olemassa ja päätiedosto < 50 tavua
```

- [ ] **Step 2:** Aja `uv run pytest tests/test_kindle_lib.py -v`. Odotettu tulos: FAIL.
- [ ] **Step 3:** Toteuta `lib.sh`, `dash.sh`, scriptlet ja konffi.
- [ ] **Step 4:** Aja `uv run pytest -v`. Odotettu tulos: PASS. Aja lisäksi `sh -n kindle/saa-ja-sahko/dash.sh kindle/documents/*.sh`, jonka pitää onnistua ilman tulostetta.
- [ ] **Step 5: Laitetesti.** Kytke USB ja aja `scripts/deploy-kindle.sh`. Pyydä käyttäjää irrottamaan Kindle ja napauttamaan "Sää ja sähkö". Tarkista telnetillä: `scripts/kindle-sh "tail -5 /mnt/us/saa-ja-sahko.log; cat /tmp/saa-ja-sahko.pid"`. Lokissa pitää näkyä onnistunut haku. Kysy käyttäjältä, näkyykö näyttö oikein.
- [ ] **Step 6: Virhetilanne.** Pysäytä Mac-palvelu: `launchctl bootout gui/$(id -u)/fi.ronkko.saasahko`. Käynnistä silmukka uudelleen, jotta haku tehdään heti: `scripts/kindle-sh "kill \$(cat /tmp/saa-ja-sahko.pid); sleep 1; nohup sh /mnt/us/saa-ja-sahko/dash.sh >/dev/null 2>&1 &"`. Noin 70 sekunnin kuluttua lokissa pitää olla `fetch failed`, ja käyttäjä vahvistaa, että näytöllä lukee "yhteysvirhe HH.MM" vanhan kuvan päällä. Käynnistä palvelu taas: `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/fi.ronkko.saasahko.plist`.
- [ ] **Step 7:** Commit `feat: kindle dashboard loop and scriptlet`.

### Task 9: Pysyvä OTA-esto

**Files:**
- Create: `kindle/documents/esta-paivitykset.sh`, `kindle/documents/salli-paivitykset.sh`

**Interfaces:**
- Consumes: Taskin 7 OTA_POLUT.
- Produces: scriptletit `# Name: Estä päivitykset` ja `# Name: Salli päivitykset`, molemmissa `# DontUseFBInk`. Loki menee tiedostoon `/mnt/us/ota-esto.log`, ja lopuksi `eips` näyttää yhden rivin tuloksen (ASCII).

Esto toimii näin:
1. `mntroot rw`.
2. Jokainen OTA_POLUT-ohjelma nimetään uudelleen `<polku>.bak`-nimelle, jos `.bak`-tiedostoa ei vielä ole. Tämä on idempotentti.
3. Jokainen OTA_POLUT-upstart-conf nimetään uudelleen `<conf>.disabled`-nimelle.
4. `mntroot ro`.
5. Jobit pysäytetään.

Salli tekee käänteiset nimenvaihdot. Tiedostoja ei kopioida, koska juuressa on vain 32 Mt vapaata.

- [ ] **Step 1:** Kirjoita molemmat scriptletit.
- [ ] **Step 2:** Aja `sh -n` kummallekin. Odotettu tulos: ei tulostetta.
- [ ] **Step 3:** Asenna deploy-skriptillä. Pyydä käyttäjää napauttamaan "Estä päivitykset". Aja `scripts/kindle-sh "cat /mnt/us/ota-esto.log; ls -la <OTA_POLUT>*; mount | grep ' / '"`. Odotettu tulos: `.bak`- ja `.disabled`-nimet löytyvät, ja `/` on `ro`.
- [ ] **Step 4:** Pyydä käyttäjää käynnistämään Kindle uudelleen ja varmistamaan, että kirjasto toimii normaalisti. Napautetaan "Kehitysyhteys" uudelleen, ja `scripts/kindle-sh "initctl list | grep -i ota; ls <OTA_POLUT>*"` näyttää, että esto on yhä voimassa ja OTA-jobit eivät ole käynnissä.
- [ ] **Step 5:** Commit `feat: permanent OTA block scriptlets`.

### Task 10: Lopputarkistus ja siivous

- [ ] **Step 1:** Varmista käyttäjän kanssa, että "Sää ja sähkö" on käynnissä. 24 tunnin kuluttua aja `scripts/kindle-sh "grep -c 'fetch ok' /mnt/us/saa-ja-sahko.log; lipc-get-prop com.lab126.powerd battLevel"`. Kirjaa akun kulutus vuorokaudessa ja kierrosten määrä (odotus noin 38–40).
- [ ] **Step 2:** Tarkista spekin "Ennen valmista" -lista:
  - Kuva näkyy oikein päin.
  - Herätykset tapahtuvat ajallaan.
  - Uudelleenkäynnistyksen jälkeen Kindle on tavallinen Kindle.
  - Ennen klo 14 näkyy teksti "huomisen hinnat n. klo 14".
  - Mac-palvelu käynnistyy uudelleenkäynnistyksen jälkeen. Testaa `launchctl kickstart -k gui/$(id -u)/fi.ronkko.saasahko` ja sen jälkeen `curl …/health`.
- [ ] **Step 3: Siivous.** Poista `documents/kehitysyhteys.sh` ja `documents/diagnostiikka.sh` Kindleltä, ja `diag.txt` USB-juuresta. Telnet sammuu Kindlen uudelleenkäynnistyksessä. Jätä `kehitysyhteys.sh` repoon tulevaa vianetsintää varten, ja lisää README.md-tiedostoon lyhyt käyttöohje: käynnistys, lukemiseen paluu, marginaalin/siirron asetus, Mac-osoitteen vaihto ja vianetsintä.
- [ ] **Step 4:** Commit `docs: usage README, remove dev access from device`.
- [ ] **Step 5 (vaihe 2, vain jos akkukesto on käyttäjälle tärkeä):** RTC-syväuni kindle-dashin mallin mukaan (`/sys/class/rtc/rtcN/wakealarm` + `echo mem > /sys/power/state`). Tämä tehdään erillisenä suunnitelmana, eikä se kuulu tähän.

---

## Laiteselvitys

(Täytetty 2026-10-31, laite PW3 5.16.2.1.1.)

- KÄYTTÖLIITTYMÄN_PYSÄYTYS: `stop framework` (upstart; `/etc/init.d/framework` ei ole olemassa). Testattu: käyttöliittymä ei piirrä näytön päälle eikä reagoi kosketukseen. `lab126_gui` ja `webreader` jäävät käyntiin – ei haittaa.
- KÄYTTÖLIITTYMÄN_PALAUTUS: `start framework` (toimii, mutta näyttö jää sotkuiseksi kunnes sivu vaihtuu – virallinen paluutapa on uudelleenkäynnistys).
- NÄYTTÖKOMENTO: `eips -f -g <png>` – testattu: oikein päin, koko näyttö, täysi päivitys.
- OTA_POLUT: jailbreak on JO nimennyt ohjelmat: `/usr/bin/otaupd.bck`, `/usr/bin/otav3.bck` (alkuperäiset puuttuvat). Upstart-confit `/etc/upstart/{ota-update,otaupd,otav3}.conf`, jobit `stop/waiting`. → Task 9 supistuu tarkistukseksi.
- Etuvalo: `lipc-get-prop com.lab126.powerd flIntensity` → 18 (luku toimii; asetus `lipc-set-prop com.lab126.powerd flIntensity N`).
- Palomuuri: INPUT policy DROP; `iptables` v1.4.15. Kindlestä lähtevä `ping -c1 -W2 192.168.0.157` toimii (rc=0), joten `dash.sh`:n verkon odotus pingillä on ok. Akku: `lipc-get-prop com.lab126.powerd battLevel` → 93.
- Kehitysyhteys: `scripts/kindle-sh` toimii (KINDLE_SH_WAIT pidempiin komentoihin).

# Sklad Foto Katalog

Mala Flask aplikace pro prezentaci skladoveho zbozi podle fotografii a pro odeslani nezavazne rezervace do Microsoft Teams. Projekt je navrzeny pro jednoduche nasazeni na Apache2 pod ISPConfig pres WSGI.

## Co aplikace umi

- verejny katalog s galerii skladovych polozek
- detail polozky s vice fotografiemi
- session-based rezervacni kosik
- formular s validaci, honeypotem a jednoduchym rate limitingem
- ulozeni rezervace do SQLite
- odeslani webhooku do Microsoft Teams Workflow nebo klasickeho Incoming Webhooku
- Python import obrazku a metadat z YAML
- vytvareni optimalizovanych variant `thumb`, `web`, `detail`
- jednoduche spravni CLI skripty bez robustniho CMS

## Struktura projektu

```text
app/                 Flask aplikace a sluzby
apache/              ukazka Apache VirtualHost konfigurace
data/                YAML metadata a SQLite databaze
logs/                aplikační logy
media/originals/     puvodni obrazky
media/derived/       vygenerovane varianty pro web
scripts/             import a jednoduche spravni skripty
static/              CSS a drobny JavaScript
templates/           Jinja2 sablony
wsgi.py              vstup pro Apache mod_wsgi
```

## Poznamka k nasazeni

Python backend **nejde** realisticky provozovat stylem "jen nakopirovat HTML do www rootu", protoze formular rezervace, session kosik, SQLite a Teams webhook potrebuji backendovy proces. Nejjednodussi realisticke nasazeni je:

1. nahrat projekt do web rootu
2. vytvorit Python virtual environment
3. nainstalovat zavislosti
4. spoustet aplikaci pres `mod_wsgi` pod Apache2

To je presne varianta, na kterou je projekt pripraveny.

## Lokální spuštění

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python scripts/import_catalog.py
python run_local.py
```

Alternativne lze pouzit i Flask CLI:

```bash
flask --app app:create_app run --debug
```

Otevri [http://127.0.0.1:5000](http://127.0.0.1:5000).

Poznamka:
- Pri beznem provozu nahravej nove soubory primo do `media/originals/` a potom spust `python scripts/import_catalog.py`.
- Parametr `--source-dir` je volitelny a hodi se hlavne pri jednorazovem importu z jine slozky.

## Import fotek a katalogu

Hlavni metadata jsou v souboru [data/catalog.yaml](/Users/radek/Downloads/Sklad/data/catalog.yaml).

Import udela:

1. volitelne zkopiruje obrazky ze zdrojove slozky do `media/originals/`
2. nacte YAML metadata
3. pro vsechny originaly vytvori `thumb`, `web` a `detail`
4. pro obrazky bez metadat automaticky vytvori polozku typu `auto-...`
5. synchronizuje katalog do SQLite databaze `data/app.db`

Priklady:

```bash
python scripts/import_catalog.py
python scripts/import_catalog.py --source-dir /cesta/k/fotkam
python scripts/import_catalog.py --catalog data/catalog.yaml --database data/app.db
```

### Jak funguje vice polozek nad jednou fotkou

Neprovadi se zadne AI rozpoznavani. Jednoduche reseni je rucne nadefinovat vice katalogovych zaznamu, ktere odkazuji na stejny soubor v poli `images`. Ukazku najdes v [data/catalog.yaml](/Users/radek/Downloads/Sklad/data/catalog.yaml) u polozek `kus-2275-a` a `kus-2275-b`.

## Sprava katalogu

Zmena stavu polozky:

```bash
python scripts/set_item_status.py stul-2271 reserved
python scripts/set_item_status.py stul-2271 hidden
python scripts/set_item_status.py stul-2271 available
```

Vygenerovani YAML sablony pro novou polozku:

```bash
python scripts/edit_metadata_template.py nova-polozka IMG_3001.png --title "Nova polozka"
```

Opakovane odeslani selhanych webhooku:

```bash
python scripts/retry_webhooks.py
```

## Microsoft Teams webhook

Konfigurace je v `.env`:

```env
TEAMS_WEBHOOK_URL=https://...
TEAMS_WEBHOOK_MODE=workflow
APP_BASE_URL=https://sklad.radekvymazal.cz
```

Podporovane rezimy:

- `workflow`: doporuceny rezim pro Power Automate / Teams Workflow
- `incoming`: fallback pro klasicky Incoming Webhook MessageCard

### Doporuceny Workflow postup

V Power Automate vytvor flow s triggerem **When an HTTP request is received** a nasledne odesli zpravu do Teams kanalu nebo chatu. Aplikace posila strukturovany JSON a zaroven text `summary_markdown`, ktery lze v toku rovnou pouzit do zpravy.

Ukazka payloadu pro `workflow`:

```json
{
  "title": "Nova rezervace zbozi",
  "submitted_at": "2026-03-29T15:20:00+00:00",
  "reservation_code": "RZV-1A2B3C4D",
  "customer": {
    "first_name": "Jan",
    "last_name": "Novak",
    "city": "Brno",
    "email": "jan@example.com",
    "phone": "+420 777 123 456"
  },
  "items": [
    {
      "item_id": "stul-2271",
      "title": "Kovovy stul se skladovou deskou",
      "dimensions": "120 x 80 x 60 cm",
      "quantity": 1,
      "detail_url": "https://example.com/item/kovovy-stul-se-skladovou-deskou"
    }
  ],
  "note": "Prosim o potvrzeni dostupnosti.",
  "summary_markdown": "## Nova rezervace zbozi\n...",
  "catalog_url": "https://example.com"
}
```

### Chovani pri chybe webhooku

Kdyz webhook selze:

- rezervace se **neztrati**
- zustane ulozena v SQLite
- chyba se zaloguje do `reservation_logs` a do aplikačního logu
- pozdeji lze spustit `python scripts/retry_webhooks.py`

## Apache2 / ISPConfig nasazeni

### 1. Nahraj projekt

Nahraj cely projekt do web rootu, napriklad:

```text
/var/www/clients/client1/web1/web
```

### 2. Vytvor virtual environment

```bash
cd /var/www/clients/client1/web1/web
python3.11 -m venv /var/www/clients/client1/web1/venv
source /var/www/clients/client1/web1/venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python scripts/import_catalog.py
```

### 3. Uprav `.env`

Minimalne nastav:

```env
SECRET_KEY=...
APP_BASE_URL=https://sklad.radekvymazal.cz
TEAMS_WEBHOOK_URL=https://...
TEAMS_WEBHOOK_MODE=workflow
```

### 4. Zapni Apache konfiguraci

Pouzij ukazku z [apache/sklad-fotokatalog.conf](/Users/radek/Downloads/Sklad/apache/sklad-fotokatalog.conf) a uprav cesty podle konkretniho ISPConfig webu.

Dulezite body:

- `WSGIDaemonProcess` musi ukazovat na spravny virtualenv
- `WSGIScriptAlias` musi smerovat na `wsgi.py`
- `Alias /media/` a `Alias /static/` musi mit pravo `Require all granted`
- uzivatel Apache musi mit zapis do `data/` a `logs/`

### 5. Doporucene prava

- `media/originals/`, `media/derived/`, `data/`, `logs/` musi byt zapisovatelne uzivatelem webu
- web root muze byt jinak read-only

## Data a media

- vsechny puvodni fotky patri do `media/originals/`
- optimalizovane varianty se generuji do `media/derived/`
- katalogova metadata jsou v `data/catalog.yaml`
- SQLite provozni data jsou v `data/app.db`

V tomto workspace uz je nactena cela sada skladovych fotek v `media/originals/`. Prvnich nekolik polozek je rucne popsanych v YAML a zbytek se umi doplnit automaticky jako jednoduche skladove kusy podle nazvu souboru.

## Doporuceny provozni postup

1. Nahraj nove fotky do `media/originals/` nebo je nasynchronizuj pres `--source-dir`.
2. Doplň nebo uprav metadata v `data/catalog.yaml`.
3. Spust `python scripts/import_catalog.py`.
4. Pokud je potreba, zmen stav polozek skriptem `set_item_status.py`.
5. Pravidelne kontroluj `logs/app.log` a pripadne spoustěj `retry_webhooks.py`.

## Poznamky k dalsimu rozsireni

Pokud budes chtit druhou iteraci, rozumne dalsi kroky jsou:

- lehke interni admin rozhrani pouze za basic auth
- tagy nebo jednoduche kategorie
- export rezervaci do CSV
- lepsi galerie s fullscreen lightboxem

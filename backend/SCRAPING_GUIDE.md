# CTPB Scraping Guide

## Overview

This guide documents the key elements of scraping CTPB (Comité Territorial Pays Basque) resultats.php for Basque Pelota game data.

**Target URL:** `https://ctpb.euskalpilota.fr/resultats.php`

---

## Authentication Flow

### Session Cookie (PHPSESSID)

The CTPB website requires a session cookie for accessing results data.

**Flow:**
1. **GET** `resultats.php` → Receive `PHPSESSID` cookie in response
2. **Wait 5-10 seconds** (rate limiting)
3. **POST** `resultats.php` with form data + cookie → Get results HTML

**Headers required:**
```python
headers = {
    'User-Agent': 'Mozilla/5.0',
    'Content-Type': 'application/x-www-form-urlencoded',
    'Origin': 'https://ctpb.euskalpilota.fr',
    'Referer': 'https://ctpb.euskalpilota.fr/resultats.php',
}
```

---

## Form Parameters

### POST Body

```
InSel=&InCompet=20250102&InSpec=11&InVille=&InClub=&InDate=&InDatef=&InCat=0&InPhase=0&InVoir=Voir+les+r%C3%A9sultats
```

**Key parameters:**
- `InCompet` - Competition ID (e.g., `20250102` = Championnat été 2025)
- `InSpec` - Specialty ID (e.g., `11` = Main Nue - Groupe A)
- `InCat` - Category (0 = all)
- `InPhase` - Phase (0 = all)

**Available competitions (2025-2026):**
- `20260102` - Championnat été 2026
- `20260104` - Championnat d'Hiver 2025/2026
- `20260108` - Tournoi PILOTARIAK 2025/2026
- `20250102` - Championnat été 2025
- `20250104` - Championnat d'Hiver 2024/2025

**Available specialties:**
- `11` - Main Nue - Groupe A
- `12` - Place Libre / Chistera Joko Garbi
- `13` - Place Libre / Grand Chistera
- `15` - Place Libre / Rebot
- `16` - Place Libre / P.G Pleine Masculin
- `59` - Place Libre / Main Nue - Groupe B

---

## HTML Structure

### Results Table

```html
<table class="mBloc">
    <tr>
        <td colspan="7">Place Libre/Main Nue - Groupe A</td>
    </tr>
    <tr>
        <td><a href="resultats2.php?no_renc=146998">10/05/2025</a></td>
        <td class="L0">U.S.S.P. AMIKUZE 
            <span class="small">(01)<br/>
                <li> (061721) MENDIBURU Florian </li>
                <li> (063150) THICOIPE Bittor </li>
            </span>
        </td>
        <td class="L0">AIRETIK 
            <span class="small">(01)<br/>
                <li> (057867) OLHAGARAY Mathieu </li>
                <li> (052536) OXARANGO Simon </li>
            </span>
        </td>
        <td>30/21</td>
        <td></td>
    </tr>
</table>
```

### Key Elements

1. **Game ID**: Extracted from `resultats2.php?no_renc=146998` link
2. **Date**: First cell, text content
3. **Club names**: In cells with class `L0`, before `<span>` tag
4. **Players**: Inside `<li>` elements within `<span class="small">`
5. **Score**: Cell after club cells

---

## Player Extraction

### HTML Format

```html
<li> (061721) MENDIBURU Florian </li>
```

### Player Name Formats

1. **`(license) Name`** - Most common
   - Example: `(061721) MENDIBURU Florian`
   - Extracted: `license='061721'`, `name='MENDIBURU Florian'`

2. **`Name (license)`** - Less common
   - Example: `OLHAGARAY Mathieu (057867)`
   - Extracted: `license='057867'`, `name='OLHAGARAY Mathieu'`

3. **`Name (marker) (license)`** - With status marker
   - Example: `BERROGAIN Andde (S) (088069)`
   - Extracted: `license='088069'`, `name='BERROGAIN Andde (S)'`
   - Markers: `(S)` = Substitute, `(E)` = Equipment

4. **`license` only** - Rare
   - Example: `040341`
   - Extracted: `license='040341'`, `name=''`

### Parser Code

```python
def _parse_players_from_cell(cell) -> List[Dict[str, str]]:
    players = []
    for li in cell.find_all("li"):
        text = li.get_text(strip=True)
        
        # "(12345) Name" format
        match = re.match(r"\((\d+)\)\s*(.+)", text)
        if match:
            license_id = match.group(1)
            name_part = match.group(2).strip()
            players.append({"license": license_id, "name": name_part})
            continue
        
        # "Name (12345)" format
        match_trailing = re.match(r"(.+?)\s*\((\d+)\)\s*$", text)
        if match_trailing:
            players.append({"license": match_trailing.group(2), "name": match_trailing.group(1).strip()})
            continue
        
        # Plain license
        if re.match(r"^\d+$", text):
            players.append({"license": text, "name": ""})
    
    return players
```

---

## Rate Limiting

### Configuration

```python
# Rate limiting for CTPB scraping (DEV/TEST ONLY)
CTPB_REQUEST_DELAY_MIN_SECONDS = 5.0
CTPB_REQUEST_DELAY_MAX_SECONDS = 10.0
CTPB_MAX_COMBINATIONS_PER_RUN = 5
CTPB_RATE_LIMIT_PER_MINUTE = 10
```

### Why Rate Limiting?

1. **Respect robots.txt** - CTPB disallows all scraping (`Disallow: /`)
2. **Avoid server overload** - Prevent 429 errors
3. **Session stability** - Delays help maintain PHPSESSID session

### Usage

```python
# Between GET and POST
await asyncio.sleep(random.uniform(5.0, 10.0))

# Between multiple competition scrapes
await asyncio.sleep(random.uniform(5.0, 10.0))
```

---

## Common Issues & Troubleshooting

### Issue 1: No Players Extracted (Empty Arrays)

**Symptom:** `club1_players: []`, `club2_players: []`

**Cause:** Scraping without specialty filter (`InSpec=0`)

**Solution:** Use specific specialty filter:
```
InSpec=11  # Main Nue - Groupe A
InSpec=12  # Place Libre / Chistera Joko Garbi
```

### Issue 2: "Pas de résultat pour cette sélection"

**Symptom:** Error message in HTML

**Cause:** No games match the filter criteria

**Solution:** 
- Use valid competition ID
- Use valid specialty ID
- Check date range

### Issue 3: Session Cookie Expired

**Symptom:** Redirects to home page instead of results

**Solution:** 
- Always do GET before POST
- Maintain 5-10s delay between requests
- Reuse session object in httpx

### Issue 4: HTML Structure Changed

**Symptom:** Parser finds 0 games, or mBloc table not found

**Solution:**
1. Fetch fresh HTML
2. Inspect table structure
3. Update parser selectors

---

## Testing

### Run Tests

```bash
cd backend
pytest tests/test_ctpb_player_extraction.py -v
```

### Test Coverage

- Player extraction formats
- Club name extraction
- Full HTML parsing
- Edge cases (hyphenated names, markers, etc.)

---

## Data Ingestion

### Where ingestion happens

The Python service never touches the database — it is stateless and returns
payloads. Persistence belongs to the Node API, which owns PostgreSQL through
Prisma.

Ingestion is what `POST /scrape/ctpb/pipeline` does on the Node API: it calls the
scraper, then hands the payload to `ingestFromPipelineResult`
(`api/src/services/ingest-scraped-games.ts`), which upserts the games, their
players, clubs and scores.

```bash
curl -X POST http://localhost:3000/scrape/ctpb/pipeline \
  -H 'Content-Type: application/json' \
  -d '{"already_scraped_urls": []}'
```

**Input:** the scraper's payload — `raw_content.games[]`, one entry per match
**Output:** rows in PostgreSQL, with `scoreComplete` and `scrapedFromUrl` set so a
rescan can tell finished games from unfinished ones

### Database Tables

- `Game` - Match data
- `GameScore` - Score data
- `Player` - Player info (license, name)
- `GameSidePlayer` - Game-player relationship
- `Club` - Club info
- `Competition` - Competition metadata

---

## Production Deployment

### CapRover Setup

1. Deploy FastAPI scraper service
2. Set environment variables:
   ```
   PELOTA_SCRAPER_HTTP_TIMEOUT_SECONDS=30.0
   CTPB_REQUEST_DELAY_MIN_SECONDS=5.0
   CTPB_REQUEST_DELAY_MAX_SECONDS=10.0
   CTPB_MAX_COMBINATIONS_PER_RUN=5
   ```

3. Deploy Node.js API
4. Set DATABASE_URL:
   ```
   postgresql://postgres:PASSWORD@srv-captain--bot-db:5432/2k26_pilota_bot
   ```

5. Run migrations:
   ```bash
   npx prisma migrate deploy
   ```

---

## Maintenance

### When Site Structure Changes

1. **Fetch fresh HTML** - Save sample page
2. **Update selectors** - Modify `ctpb_parser.py`
3. **Update tests** - Add new test cases
4. **Re-scrape** - Test with live data
5. **Create PR** - Document changes

### Monitoring

- Check scrape success rate
- Monitor 429 errors
- Track player extraction rate
- Log parse failures

---

## Legal Notice

**⚠️  DEV/TEST ONLY**

CTPB robots.txt states: `Disallow: /`

This scraper is for **development and testing purposes only**. Production scraping requires:
- Authorization from CTPB
- Official API access if available
- Respect for rate limits and server resources

---

## References

- **Scraper code:** `app/services/scraper.py`
- **Parser code:** `app/services/ctpb_parser.py`
- **Tests:** `tests/test_ctpb_player_extraction.py`
- **Ingestion:** `api/src/services/ingest-scraped-games.ts` (Node API)

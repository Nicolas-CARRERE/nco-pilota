# HTML Parsing Implementation Summary

## Overview

Updated the ingestion pipeline to parse **directly from original HTML** instead of intermediate JSON, preserving all granular competition fields.

---

## Changes Made

### 1. **HTML Parser Enhancement** (`app/services/ctpb_parser.py`)

**Added:**
- `_extract_season_from_html()` - Extracts season/year/organization from page header
- `_extract_competition_context()` - Parses championship name using `championship_parser`
- Updated `parse_resultats_html()` to include all granular fields in each game record

**Fields extracted from HTML:**
```python
{
    "discipline": "Trinquet/Main Nue",
    "group": "GROUPE A",
    "series": "1ère Série",
    "pool": "Poule phase 1",
    "season": "2025-2026",
    "year": 2026,
    "organization": "CTPB",
    "discipline_context": "Trinquet/Main Nue - Groupe A1ère Série - 1.MailaGROUPE A Poule phase 1"
}
```

### 2. **Ingestion Service Update** (`app/services/ingestion_service.py`)

**Updated `parse_and_create_competition()`:**
- Now accepts optional `pre_parsed` dict from HTML parser
- Uses pre-parsed fields when available (preferred)
- Falls back to parsing `discipline_context` string for backward compatibility

**Updated `ingest_scraped_games()`:**
- Checks for pre-parsed fields in game data
- Passes granular fields to competition creation

---

## Benefits

✅ **No data loss** - All original HTML data preserved  
✅ **Re-parsable** - Can re-run with improved parsing logic anytime  
✅ **Granular fields** - Competition has discipline, group, series, pool, season, year, organization  
✅ **Backward compatible** - Still works with old JSON-based scraper  
✅ **Test coverage** - 56 passing tests including new HTML parser tests  

---

## Test Results

```bash
# All tests pass
uv run pytest tests/ -v

# 56 passed in 29.34s
```

### Test Coverage:
- `test_championship_parser.py` - 19 tests (parser logic)
- `test_html_parser.py` - 7 tests (HTML extraction)
- `test_scraper_with_fixtures.py` - 13 tests (fixture integrity)
- `test_ctpb_player_extraction.py` - 17 tests (player parsing)

---

## HTML Fixtures

Saved raw HTML from CTPB for regression testing:

```
tests/fixtures/ctpb/
├── competition_20260102.html (28K) - Main Nue Seniors
├── competition_20260104.html (5.4M) - Trinquet Seniors (7592 games)
├── competition_20260201.html (28K) - Place Libre Seniors
├── games.json - Sample scraped games
└── parser_test_cases.json - Championship name test cases
```

---

## Sample Output

```python
from app.services.ctpb_parser import parse_resultats_html

with open('tests/fixtures/ctpb/competition_20260104.html') as f:
    html = f.read()

games = parse_resultats_html(html)
# Parsed 7592 games

g = games[0]
print(g['discipline'])  # "Trinquet/Main Nue"
print(g['group'])       # "GROUPE A"
print(g['series'])      # "1ère Série"
print(g['pool'])        # "Poule phase 1"
print(g['season'])      # "2025-2026"
print(g['year'])        # 2026
print(g['organization'])# "CTPB"
```

---

## Usage

### Parse HTML directly:
```bash
uv run python scripts/run_scraper.py --use-fixtures --ingest
```

### Update HTML fixtures:
```bash
uv run python scripts/save_html_fixture.py
```

### Run tests:
```bash
uv run pytest tests/test_html_parser.py -v
uv run pytest tests/ -v
```

---

## Next Steps

1. **Run ingestion with live HTML** - Test with fresh scrape
2. **Verify DB schema** - Ensure all granular fields are stored
3. **Update API** - Expose granular fields in competition endpoints
4. **Add more fixtures** - Cover edge cases (FFPB, different seasons)

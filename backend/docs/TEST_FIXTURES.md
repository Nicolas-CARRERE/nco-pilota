# Test Fixtures for Scraper

This document describes the test fixture system for the pelota scraper, ensuring consistent testing regardless of live scraping changes.

## 🎯 Purpose

Test fixtures provide:
- **Consistent test data** for parser development
- **Regression testing** to catch parser bugs
- **Offline testing** without hitting the CTPB website
- **CI/CD reliability** - tests don't fail due to website changes

## 📁 Fixture Directory Structure

```
backend/
  tests/
    fixtures/
      ctpb/
        games.json                 # Full scraped games data
        parser_test_cases.json     # Championship name test cases
        sample_games.json          # First 10 games (quick testing)
      ffpb/
        (future FFPB fixtures)
```

## 🛠️ Usage

### Save Fixtures from Live Scrape

```bash
cd backend

# Save all fixtures
uv run python scripts/save_fixtures.py

# Update CTPB fixtures only
uv run python scripts/save_fixtures.py --update ctpb

# Update with custom URL
uv run python scripts/save_fixtures.py --update ctpb --url "https://ctpb.euskalpilota.fr/resultats.php?..."
```

### Use Fixtures for Testing

```bash
# Run scraper with fixtures (no live scraping)
uv run python scripts/run_scraper.py --use-fixtures --ingest

# Run pytest against fixtures
uv run pytest tests/test_scraper_with_fixtures.py -v

# Run all scraper tests
uv run pytest tests/ -k scraper -v
```

### Validate Fixtures

```bash
# Check fixtures against parsers
uv run python scripts/save_fixtures.py --validate
```

### Update Scraper Flags

The scraper now supports three modes:

```bash
# Live scraping (default)
uv run python scripts/run_scraper.py --ingest

# Use saved fixtures for testing
uv run python scripts/run_scraper.py --use-fixtures --ingest

# Update fixtures from live scrape
uv run python scripts/run_scraper.py --update-fixtures
```

## 📝 Fixture Format

### games.json

```json
{
  "games": [
    {
      "no_renc": "151699",
      "date": "04/10/2025",
      "club1_name": "AIRETIK",
      "club2_name": "URRUNARRAK",
      "score": "31/40",
      "discipline_context": "Trinquet/Main Nue - Groupe A...",
      ...
    }
  ],
  "scraped_at": "2026-03-30T08:00:00+00:00"
}
```

### parser_test_cases.json

```json
{
  "championship_names": [
    {
      "input": "Trinquet/Main Nue - Groupe A1ère Série - 1.MailaGROUPE A Poule phase 1",
      "expected": {
        "discipline": "Trinquet/Main Nue",
        "group": "GROUPE A",
        "series": "1ère Série",
        "pool": "Poule phase 1"
      },
      "source": "ctpb_live_scrape"
    }
  ],
  "generated_at": "2026-03-30T08:00:00+00:00",
  "source_games_count": 7592
}
```

## 🔄 When to Update Fixtures

### Update When:
- ✅ CTPB website structure changes
- ✅ Parser is updated and needs new test cases
- ✅ Monthly refresh to keep fixtures current
- ✅ New championship formats discovered

### Do NOT Update When:
- ❌ During active parser development (use fixtures for consistency)
- ❌ When tests fail due to parser bugs (fix parser, not fixtures)
- ❌ Mid-sprint (wait for stable parser state)

## 🧪 Adding New Test Cases

### Manual Addition

Edit `tests/fixtures/ctpb/parser_test_cases.json`:

```json
{
  "championship_names": [
    {
      "input": "Your Championship Name Here",
      "expected": {
        "discipline": "...",
        "group": "...",
        "series": "...",
        "pool": "..."
      },
      "source": "manual"
    }
  ]
}
```

### From Live Data

Run the save script to auto-extract test cases from current scrape:

```bash
uv run python scripts/save_fixtures.py --update ctpb
```

This extracts up to 20 unique championship names and adds known complex cases.

## 🚨 CI/CD Integration

Add to your CI pipeline:

```yaml
# .github/workflows/test.yml
- name: Run scraper tests with fixtures
  run: |
    cd backend
    uv run pytest tests/test_scraper_with_fixtures.py -v
    uv run pytest tests/test_championship_parser.py -v
```

## 📊 Fixture Statistics

Track fixture health:

```bash
# Quick validation
uv run python scripts/save_fixtures.py --validate

# Expected output:
# 📊 Validation Results:
#   CTPB Parser Test Cases: 25/25 passed
#   CTPB Games: 7592/7592 valid
```

## 🐛 Troubleshooting

### "Fixture file not found"
Run `--update-fixtures` to create initial fixtures.

### "Parser test cases failed"
1. Check if parser regression (fix parser)
2. Check if website format changed (update fixtures)
3. Run validation: `--validate`

### "Games fixture has invalid structure"
Re-save fixtures from known-good scrape:
```bash
uv run python scripts/run_scraper.py --update-fixtures
```

## 📚 Related Files

- `scripts/save_fixtures.py` - Fixture management script
- `scripts/run_scraper.py` - Scraper with fixture support
- `tests/test_scraper_with_fixtures.py` - Fixture-based tests
- `tests/test_championship_parser.py` - Parser unit tests

---

**Goal:** Never lose test reliability due to live scraping changes!

## Known Issues (Being Fixed)

### 1. Competition Deduplication
- **Current:** Creates 7,592 competitions (one per game)
- **Expected:** ~39 competitions (grouped by discipline/series/group/pool)
- **Fix in progress:** Update matching query in ingestion_service.py

### 2. Engagements.php Redirects
- **Current:** Club names with spaces cause 302 redirects
- **Expected:** Successfully scrape player rosters
- **Fix in progress:** URL encoding or session handling

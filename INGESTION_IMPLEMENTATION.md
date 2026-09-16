# Database Ingestion Implementation for CTPB Data

## Overview

This implementation adds database ingestion capabilities for scraped CTPB data, parsing the `discipline_context` field and saving structured data to the PostgreSQL database via Prisma.

## Example Input

```
discipline_context: "Trinquet/Main Nue - Groupe A1ère Série - 1.MailaGROUPE A Poule phase 1"
```

Parsed into:
- `discipline`: "Trinquet" or "Main Nue"
- `season`: "2026"
- `year`: 2026
- `series`: "1ère Série" or "1.Maila"
- `group`: "GROUPE A"
- `pool`: "Poule phase 1"
- `organization`: "CTPB"

## Files Created/Modified

### 1. Python Ingestion Service (NEW)
**File:** `backend/app/services/ingestion_service.py`

**Key Functions:**
- `ingest_scraped_games(games: List[dict])` - Main ingestion function
- `parse_and_create_competition(discipline_context: str)` - Parse context, find/create Competition
- `create_game(game_data: dict, competition_id: str)` - Create/update Game record

**Features:**
- Uses `asyncpg` for async PostgreSQL access
- Parses `discipline_context` using existing `championship_parser.parse_championship_name()`
- Finds or creates Competition with granular fields
- Handles duplicates via `no_renc` (external_id) field
- Creates/updates players, clubs, teams, game scores
- Determines winner from score patterns (X/P, P/X, numeric)

### 2. API Endpoint (NEW)
**File:** `api/src/routes/scrape.ts` (updated)
**File:** `api/src/controllers/scrape.controller.ts` (NEW)

**Endpoints:**
- `POST /api/scrape/ingest` - Scrape URL and ingest immediately
  - Body: `{ url: string, sourceId?: string }`
  - Returns: `{ status, competitions, games, details }`
  
- `POST /api/scrape/ingest/batch` - Batch ingest multiple results
  - Body: `{ results: [...], sourceId?: string }`
  - Returns: `{ status, summary, details }`

### 3. CLI Scraper (UPDATED)
**File:** `backend/scripts/run_scraper.py`

**New Flags:**
- `--ingest` - Save scraped games to database
- `--url URL` - Specify custom URLs (can be used multiple times)

**Example Usage:**
```bash
# Default URLs with ingestion
python3 scripts/run_scraper.py --ingest

# Custom URL with ingestion
python3 scripts/run_scraper.py --ingest --url "https://ctpb.euskalpilota.fr/resultats.php?..."

# Multiple URLs
python3 scripts/run_scraper.py --ingest \
  --url "https://..." \
  --url "https://..."
```

### 4. Configuration (UPDATED)
**Files:**
- `backend/app/config.py` - Added `database_url` to settings
- `backend/requirements.txt` - Added `asyncpg>=0.29.0`
- `backend/.env.example` - Added `PELOTA_POSTGRES_DATABASE_URL`

### 5. Test Script (NEW)
**File:** `backend/scripts/test_ingestion.py`

Test ingestion with sample data:
```bash
python3 scripts/test_ingestion.py
```

## Prisma Schema Verification

The following models already exist with required fields:

### Competition Model
```prisma
model Competition {
  discipline      String?  // Place Libre, Trinquet, Main Nue, etc.
  season          String?  // 2026
  year            Int?     // 2026
  series          String?  // 1ère Série - 1.Maila
  group           String?  // GROUPE A, M19, Cadets, Gazteak
  pool            String?  // Poule phase 1, Finale
  organization    String?  // CTPB, FFPB
  // ... plus relations to Discipline, Organizer, CompetitionYear, etc.
}
```

### Game Model
```prisma
model Game {
  competitionId   String   @map("competition_id")
  player1Id       String   @map("player1_id")
  player2Id       String   @map("player2_id")
  startDate       DateTime @map("start_date")
  status          String
  externalId      String?  @map("external_id")   // CTPB no_renc
  scrapedFromUrl  String?  @map("scraped_from_url")
  scoreComplete   Boolean? @map("score_complete")
  phase           String?
  competition     Competition @relation(...)
  // ... plus relations to players, scores, etc.
}
```

## Architecture

```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────┐
│   Node.js API   │─────▶│  Python Scraper  │─────▶│   PostgreSQL    │
│  (Express.js)   │      │   (FastAPI)      │      │   (Prisma)      │
└─────────────────┘      └──────────────────┘      └─────────────────┘
        │                        │
        │ POST /scrape/ingest    │ ingestion_service.py
        │                        │
        ▼                        ▼
┌─────────────────┐      ┌──────────────────┐
│  scrape.        │      │  championship_   │
│  controller.ts  │      │  parser.py       │
└─────────────────┘      └──────────────────┘
```

## Workflow

1. **Scrape**: Node.js calls Python scraper via FastAPI
2. **Parse**: Scraper returns games with `discipline_context`
3. **Ingest**: 
   - Parse `discipline_context` → granular fields
   - Find/create Competition with these fields
   - Find/create Game (check `no_renc` for duplicates)
   - Create/update related records (players, clubs, scores)
4. **Report**: Return counts of competitions/games created/updated

## Testing

### Manual Test with CLI
```bash
cd backend
python3 scripts/run_scraper.py --ingest --url "YOUR_CTPB_URL"
```

### API Test
```bash
curl -X POST http://localhost:3000/api/scrape/ingest \
  -H "Content-Type: application/json" \
  -d '{"url": "https://ctpb.euskalpilota.fr/resultats.php?..."}'
```

### Unit Test
```bash
cd backend
python3 scripts/test_ingestion.py
```

## Environment Variables

Add to `.env`:
```bash
# Database connection for ingestion
PELOTA_POSTGRES_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/pilota
```

## Dependencies

**Python:**
- `asyncpg>=0.29.0` - Async PostgreSQL driver

**Node.js:**
- Existing Prisma client (no new dependencies)

## Notes

- The Python ingestion service uses direct SQL via `asyncpg` (not Prisma Python client)
- Duplicate detection uses `no_renc` field (stored as `external_id`)
- Score patterns like "40/P" or "P/30" are marked as complete (no rescan needed)
- Player names are parsed from "NOM Prénom" format (Basque/French convention)
- All database operations are wrapped in transactions where appropriate

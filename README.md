# Pilota

Basque Pelota results and statistics: the official federation results are scraped,
stored in PostgreSQL, and served by a public Angular front end — games, players,
teams, championships and a dashboard with analytics.

## The three services

| Path | What it is | Port in the container | Port on your machine |
|---|---|---|---|
| `frontend/` | Angular 18 front end, served by nginx | 80 | 8081 |
| `api/` | Node.js + Express API, Prisma. **Owns the database** | 3000 | 3001 |
| `backend/` | FastAPI scraper. No database connection | 8001 | 8003 |
| — | PostgreSQL 15 (`db`) | 5432 | 5436 |

```
Angular (nginx)  ──HTTP──▶  Node API  ──▶  PostgreSQL
                                │
                                └──HTTP──▶  FastAPI scraper ──▶ CTPB / FFPB
```

The Node API is the only writer: `api/prisma/schema.prisma` is the schema's single
source, and its migrations are in `api/prisma/migrations`. The Python service fetches
and parses HTML and XML and returns payloads; it opens no database connection. The
front end never calls the scraper directly.

Each service has its own README, its own Dockerfile and its own `.env.example`:
[`api/README.md`](api/README.md), [`backend/README.md`](backend/README.md),
[`frontend/README.md`](frontend/README.md).

## Running it locally

```bash
docker compose up --build
```

Once up:

| | |
|---|---|
| Front end | http://localhost:8081 |
| API | http://localhost:3001/health |
| Scraper | http://localhost:8003/scrape/health |
| PostgreSQL | `localhost:5436`, user `pilota`, database `pilota` |

The API applies the Prisma migrations before it serves, so a fresh volume comes up
with its tables. `db`, `backend`, `api` and `frontend` are the four services; a fifth,
`backend-test`, runs the Python test suite inside the stack.

The credentials in `docker-compose.yml` are development values, not deployable.
`POSTGRES_PASSWORD` overrides the database password, and both connection URLs are
built from it.

Without Docker, run one service at a time as its own README describes; the front end
then talks to `http://localhost:3000` (`frontend/src/environments/environment.ts`),
not to the nginx proxy.

## What it scrapes

| Source | Format |
|---|---|
| CTPB, `ctpb.euskalpilota.fr/resultats.php` | HTML tables, behind a `PHPSESSID` cookie obtained by a GET before the form POST |
| FFPB, `competition.ffpb.net` | XML |

`backend/SCRAPING_GUIDE.md` documents the CTPB page structure, the cookie flow and the
player-name formats in detail — it is the most useful document in this repository if
you are going to touch the parsing. The CTPB `robots.txt` disallows scraping, so the
scraper is for development and testing only (`CTPB_DEV_MODE` guards the rate limits).

## Tests

| Service | Command | What it covers |
|---|---|---|
| `backend/` | `uv run pytest tests/ -v` | The parser and ingestion suite, from the fixtures under `backend/tests/fixtures/`. No network, no database — a run touches neither |
| `api/` | `npm run build` | No test file: type-checking is all this repository can say about the API today |
| `frontend/` | `npm test` | The accessibility spec |

Three workflows run these on pull requests, one per service, each only when its own
paths change: `.github/workflows/backend.yml`, `api.yml`, `frontend.yml`. They report;
branch protection does not yet *require* them, so a red pull request can still be
merged by hand.

## Test-mode endpoints (development only)

⚠️ Destructive. Never enable these in production.

They are disabled unless `TEST_MODE=true` or `DEV_MODE=true` is set in the API's
environment — the compose file deliberately leaves both unset.

| Endpoint | Effect |
|---|---|
| `POST /api/test/purge-database` | Drops every table and re-runs the migrations. Rate limited to one request per minute per IP |
| `GET /api/test/status` | Reports whether test mode is on |

## Accessibility guidelines

### Images and alt text

All images must include descriptive alt text:

```html
<img [src]="imageUrl" [alt]="imageDescription" />
```

**Rules:**
- Decorative images: use `alt=""` (empty string)
- Informative images: describe the content and purpose
- Avoid "image of" or "picture of" prefixes
- Keep alt text concise but meaningful

### ARIA labels

- All interactive elements must have accessible names
- Use `aria-label` for icon-only buttons
- Use `aria-describedby` for additional context
- Use `role` attributes where semantic HTML is insufficient

### Focus states

- All interactive elements have visible focus indicators
- Skip link provided for keyboard navigation
- Focus order follows visual layout

### Colour contrast

- Text meets WCAG AA contrast requirements (4.5:1 for normal text)
- Interactive elements have distinct hover/focus states

## Contributing

- **Never commit to `main`.** Work happens on a branch cut from an up-to-date `main`,
  and lands through a pull request.
- A branch is named `<type>/nc/<ID>-<slug>`, where `ID` is the task it serves in the
  project's backlog (`PIL-02`) and the slug says what the change is.
- One task per branch, one commit per logical change. No agent reports or audit files
  in the repository: if something must be remembered, it belongs in an issue, the
  guide, or this README.

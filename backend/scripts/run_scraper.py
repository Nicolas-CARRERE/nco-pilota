#!/usr/bin/env python3
"""CLI script to run the scraper directly with debug output."""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load .env file from backend directory
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)
print(f"📄 Loaded .env from: {env_path}")

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.scraper import scrape_url
from app.services.html_game_parser import parse_competition_html
from app.config import get_settings

# Fixture directory for testing
FIXTURES_DIR = Path(__file__).parent.parent / "tests" / "fixtures" / "ctpb"

def load_fixtures() -> dict:
    """Load saved fixtures for testing."""
    games_path = FIXTURES_DIR / "games.json"
    if not games_path.exists():
        raise FileNotFoundError(f"Fixtures not found: {games_path}")
    
    with open(games_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_html_fixture(fixture_path: str) -> dict:
    """Load and parse HTML fixture for testing."""
    html_path = Path(fixture_path)
    if not html_path.exists():
        raise FileNotFoundError(f"HTML fixture not found: {html_path}")
    
    print(f"📊 Parsing HTML fixture: {html_path.name}")
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()
    
    return parse_competition_html(html)

async def main():
    parser = argparse.ArgumentParser(description="Run CTPB scraper")
    parser.add_argument(
        "--ingest",
        action="store_true",
        help="Ingest scraped games into database after scraping",
    )
    parser.add_argument(
        "--url",
        type=str,
        action="append",
        help="URL(s) to scrape (can be specified multiple times)",
    )
    parser.add_argument(
        "--use-fixtures",
        action="store_true",
        help="Use saved fixtures instead of live scraping (for testing)",
    )
    parser.add_argument(
        "--update-fixtures",
        action="store_true",
        help="Update fixtures from live scrape, then exit",
    )
    # Deprecated flags (kept for backward compatibility, now automatic)
    parser.add_argument(
        "--use-html-fixture",
        action="store_true",
        help="Deprecated: HTML parsing is now automatic",
    )
    parser.add_argument(
        "--html-fixture",
        type=str,
        default="tests/fixtures/ctpb/competition_20260104.html",
        help="Deprecated: HTML fixture path (no longer used)",
    )
    args = parser.parse_args()

    settings = get_settings()
    print(f"🔧 Database URL: {settings.database_url[:50]}...")
    
    # Handle fixture update mode
    if args.update_fixtures:
        print("🔄 Updating fixtures from live scrape...")
        from scripts.save_fixtures import save_ctpb_fixtures
        competitions = args.url or [
            "https://ctpb.euskalpilota.fr/resultats.php?InSel=&InCompet=20260102&InSpec=0&InVille=&InClub=&InDate=&InDatef=&InCat=0&InPhase=0&InVoir=Voir+les+r%C3%A9sultats",
        ]
        result = await save_ctpb_fixtures(competitions[0])
        if result.get("status") == "success":
            print(f"✅ Fixtures updated: {result.get('games_count')} games, {result.get('test_cases_count')} test cases")
            return
        else:
            print(f"❌ Fixture update failed: {result}")
            return
    
    # Handle fixture-only mode (no live scraping)
    if args.use_fixtures:
        print("📁 Using saved fixtures (no live scraping)...")
        try:
            fixture_data = load_fixtures()
            games = fixture_data.get("games", [])
            print(f"   📊 Loaded {len(games)} games from fixtures")
            
            total_games = len(games)
            total_competitions = set()
            
            # Extract competition info
            for game in games:
                if "discipline_context" in game:
                    total_competitions.add(game["discipline_context"])
            
            if args.ingest and games:
                print(f"   📦 Ingesting {len(games)} games from fixtures...")
                from app.services.ingestion_service import ingest_scraped_games
                ingest_result = await ingest_scraped_games(games)
                print(f"      - Competitions created: {ingest_result.get('competitions_created', 0)}")
                print(f"      - Games created: {ingest_result.get('games_created', 0)}")
                print(f"      - Games updated: {ingest_result.get('games_updated', 0)}")
            
            print(f"\n✅ Fixture test complete!")
            print(f"   Total games: {total_games}")
            print(f"   Total competitions: {len(total_competitions)}")
            return
        except FileNotFoundError as e:
            print(f"   ❌ {e}")
            print(f"   💡 Run with --update-fixtures first to create fixtures")
            return
    
    # Default: live scraping mode with automatic player scraping
    competitions = args.url or [
        "https://ctpb.euskalpilota.fr/resultats.php?InSel=&InCompet=20260102&InSpec=0&InVille=&InClub=&InDate=&InDatef=&InCat=0&InPhase=0&InVoir=Voir+les+r%C3%A9sultats",
        "https://ctpb.euskalpilota.fr/resultats.php?InSel=&InCompet=20260104&InSpec=0&InVille=&InClub=&InDate=&InDatef=&InCat=0&InPhase=0&InVoir=Voir+les+r%C3%A9sultats",
    ]
    
    print(f"🚀 Starting scraper for {len(competitions)} competitions...")
    if args.ingest:
        print("📦 Will ingest results into database after scraping")
        print("👤 Will automatically scrape player rosters from engagements.php")
    
    total_games = 0
    total_competitions = set()
    all_games = []
    
    # Step 1: Scrape competitions
    for url in competitions:
        print(f"\n📊 Scraping: {url[:100]}...")
        result = await scrape_url(url)
        print(f"   Status: {result.status}")
        if result.status == "success":
            print(f"   ✅ Success!")
            if hasattr(result, 'raw_content') and result.raw_content:
                content = result.raw_content
                games = content.get("games", []) if isinstance(content, dict) else []
                games_count = len(games) if isinstance(games, list) else 0
                print(f"   Games found: {games_count}")
                total_games += games_count
                all_games.extend(games)
                
                # Extract competition info from discipline_context
                if isinstance(games, list) and games:
                    for game in games:
                        if "discipline_context" in game:
                            total_competitions.add(game["discipline_context"])
        elif result.errors:
            print(f"   ❌ Errors: {result.errors}")
    
    # Step 2: Ingest games first (creates clubs)
    if args.ingest and all_games:
        print(f"\n📦 Ingesting {len(all_games)} games...")
        from app.services.ingestion_service import ingest_scraped_games
        ingest_result = await ingest_scraped_games(all_games)
        print(f"   - Competitions created: {ingest_result.get('competitions_created', 0)}")
        print(f"   - Games created: {ingest_result.get('games_created', 0)}")
        print(f"   - Games updated: {ingest_result.get('games_updated', 0)}")
    
    # Step 3: Extract unique clubs and scrape player rosters (only if ingesting)
    players_created = 0
    if args.ingest and all_games:
        # Extract unique club names from games
        unique_clubs = set()
        for game in all_games:
            club1 = game.get("club1_name", "") or game.get("club1", "")
            club2 = game.get("club2_name", "") or game.get("club2", "")
            if club1:
                unique_clubs.add(club1)
            if club2:
                unique_clubs.add(club2)
        
        print(f"\n👤 Found {len(unique_clubs)} unique clubs")
        print(f"   Scraping player rosters from engagements.php...")
        
        # Import engagements scraper
        from app.services.engagements_scraper import scrape_club_engagements
        from app.services.ingestion_service import IngestionService
        
        # Create ingestion service to access player creation
        service = IngestionService()
        await service.connect()
        
        async with service._pool.acquire() as conn:
            for club_name in unique_clubs:
                # Get club ID from database (should exist after game ingestion)
                club_record = await conn.fetchrow(
                    "SELECT id FROM club WHERE name = $1", club_name
                )
                
                if not club_record:
                    logger.warning("Club not found after ingestion: %s", club_name)
                    continue
                
                club_id = club_record["id"]
                
                # Scrape engagements for this club (use club name as parameter)
                players = await scrape_club_engagements(club_name)
                
                if players:
                    print(f"   - {club_name}: {len(players)} players")
                    for player_data in players:
                        await service._get_or_create_player(
                            conn,
                            player_data['first_name'],
                            player_data['last_name'],
                            None,  # external_id
                            player_data['license']
                        )
                        players_created += 1
        
        await service.disconnect()
        print(f"   ✅ Players created: {players_created}")
    
    print(f"\n✅ Scraper finished!")
    print(f"   Total games: {total_games}")
    print(f"   Total competitions: {len(total_competitions)}")
    if args.ingest:
        print(f"   Players created: {players_created}")
        print(f"   All data ingested into database")

if __name__ == "__main__":
    asyncio.run(main())

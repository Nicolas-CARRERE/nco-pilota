#!/usr/bin/env python3
"""CLI script to run the scraper directly, with debug output.

Scraping and parsing only: it prints what it finds and writes nothing. The database
belongs to the Node API, which ingests what this service returns
(`api/src/services/ingest-scraped-games.ts`) — see the root README.
"""

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
            
            print(f"\n✅ Fixture test complete!")
            print(f"   Total games: {total_games}")
            print(f"   Total competitions: {len(total_competitions)}")
            return
        except FileNotFoundError as e:
            print(f"   ❌ {e}")
            print(f"   💡 Run with --update-fixtures first to create fixtures")
            return
    
    # Default: live scraping mode
    competitions = args.url or [
        "https://ctpb.euskalpilota.fr/resultats.php?InSel=&InCompet=20260102&InSpec=0&InVille=&InClub=&InDate=&InDatef=&InCat=0&InPhase=0&InVoir=Voir+les+r%C3%A9sultats",
        "https://ctpb.euskalpilota.fr/resultats.php?InSel=&InCompet=20260104&InSpec=0&InVille=&InClub=&InDate=&InDatef=&InCat=0&InPhase=0&InVoir=Voir+les+r%C3%A9sultats",
    ]
    
    print(f"🚀 Starting scraper for {len(competitions)} competitions...")
    
    total_games = 0
    total_competitions = set()
    
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
                
                # Extract competition info from discipline_context
                if isinstance(games, list) and games:
                    for game in games:
                        if "discipline_context" in game:
                            total_competitions.add(game["discipline_context"])
        elif result.errors:
            print(f"   ❌ Errors: {result.errors}")
    
    print(f"\n✅ Scraper finished!")
    print(f"   Total games: {total_games}")
    print(f"   Total competitions: {len(total_competitions)}")

if __name__ == "__main__":
    asyncio.run(main())

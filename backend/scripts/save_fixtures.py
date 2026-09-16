#!/usr/bin/env python3
"""
Fixture Management Script for Scraper Testing

Saves HTML fixtures and parsed JSON output for consistent testing,
parser development, and regression testing.

Usage:
    # Save fixtures from live scrape
    uv run python scripts/save_fixtures.py

    # Validate fixtures against parser
    uv run python scripts/save_fixtures.py --validate

    # Update specific fixture
    uv run python scripts/save_fixtures.py --update ctpb
"""

import argparse
import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# Add parent directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from app.services.scraper import scrape_url
from app.services.ctpb_parser import parse_resultats_html
from app.services.championship_parser import parse_championship_name

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("fixture_manager")

# Fixture directory
FIXTURES_DIR = Path(__file__).parent.parent / "tests" / "fixtures"
CTPB_FIXTURES_DIR = FIXTURES_DIR / "ctpb"
FFPB_FIXTURES_DIR = FIXTURES_DIR / "ffpb"


def ensure_fixture_dirs():
    """Ensure fixture directories exist."""
    CTPB_FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    FFPB_FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Fixture directories ready: {CTPB_FIXTURES_DIR}, {FFPB_FIXTURES_DIR}")


async def save_ctpb_fixtures(
    url: str = "https://ctpb.euskalpilota.fr/resultats.php?InSel=&InCompet=20260102&InSpec=0&InVille=&InClub=&InDate=&InDatef=&InCat=0&InPhase=0&InVoir=Voir+les+r%C3%A9sultats"
) -> dict[str, Any]:
    """
    Scrape CTPB results page and save fixtures.
    
    Returns:
        Dict with counts and paths of saved fixtures.
    """
    logger.info(f"📥 Fetching CTPB results from: {url[:80]}...")
    
    # Scrape live data
    result = await scrape_url(url)
    
    if result.status != "success":
        logger.error(f"❌ Scrape failed: {result.errors}")
        return {"status": "failed", "errors": result.errors}
    
    # Extract games
    raw_content = result.raw_content or {}
    games = raw_content.get("games", [])
    
    if not games:
        logger.warning("⚠️ No games found in scrape result")
        return {"status": "no_data", "games_count": 0}
    
    logger.info(f"✅ Scraped {len(games)} games")
    
    # Save HTML fixture (reconstruct from parsed data for consistency)
    # Note: For true HTML fixture, we'd need to save response.text from scraper
    # For now, we save the parsed JSON which is more useful for testing
    games_fixture_path = CTPB_FIXTURES_DIR / "games.json"
    with open(games_fixture_path, "w", encoding="utf-8") as f:
        json.dump({"games": games, "scraped_at": datetime.now(timezone.utc).isoformat()}, f, indent=2, ensure_ascii=False)
    logger.info(f"💾 Saved games JSON: {games_fixture_path}")
    
    # Extract unique championship names for test cases
    championship_names = set()
    for game in games:
        if "discipline_context" in game and game["discipline_context"]:
            championship_names.add(game["discipline_context"])
    
    logger.info(f"📊 Found {len(championship_names)} unique championship names")
    
    # Create parser test cases from championship names
    test_cases = []
    for name in list(championship_names)[:20]:  # Limit to 20 for manageability
        expected = parse_championship_name(name)
        if expected:  # Only include if parser extracted something
            test_cases.append({
                "input": name,
                "expected": expected,
                "source": "ctpb_live_scrape"
            })
    
    # Add known complex cases manually
    known_cases = [
        {
            "input": "Trinquet/Main Nue - Groupe A1ère Série - 1.MailaGROUPE A Poule phase 1",
            "expected": {
                "discipline": "Trinquet/Main Nue",
                "group": "GROUPE A",
                "series": "1ère Série",
                "pool": "Poule phase 1"
            },
            "source": "manual"
        },
        {
            "input": "CTPB 2026 - Trinquet - Cadets - Finale",
            "expected": {
                "discipline": "Trinquet",
                "group": "Cadets",
                "pool": "Finale",
                "year": 2026,
                "organization": "CTPB"
            },
            "source": "manual"
        }
    ]
    test_cases.extend(known_cases)
    
    # Save parser test cases
    test_cases_path = CTPB_FIXTURES_DIR / "parser_test_cases.json"
    with open(test_cases_path, "w", encoding="utf-8") as f:
        json.dump({
            "championship_names": test_cases,
            "games": [],  # Can be populated with specific game samples
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source_games_count": len(games)
        }, f, indent=2, ensure_ascii=False)
    logger.info(f"💾 Saved parser test cases: {test_cases_path} ({len(test_cases)} cases)")
    
    # Save sample game for HTML fixture testing
    if games:
        sample_game = games[0]
        sample_games_path = CTPB_FIXTURES_DIR / "sample_games.json"
        with open(sample_games_path, "w", encoding="utf-8") as f:
            json.dump({"games": games[:10], "total": len(games)}, f, indent=2, ensure_ascii=False)
        logger.info(f"💾 Saved sample games: {sample_games_path} (10 of {len(games)})")
    
    return {
        "status": "success",
        "games_count": len(games),
        "championship_names_count": len(championship_names),
        "test_cases_count": len(test_cases),
        "fixtures_saved": [
            str(games_fixture_path),
            str(test_cases_path),
            str(sample_games_path)
        ]
    }


def validate_fixtures() -> dict[str, Any]:
    """
    Validate existing fixtures against parsers.
    
    Returns:
        Dict with validation results.
    """
    results = {
        "ctpb_parser_test_cases": {"total": 0, "passed": 0, "failed": 0, "failures": []},
        "ctpb_games": {"total": 0, "valid": 0, "invalid": 0}
    }
    
    # Validate parser test cases
    test_cases_path = CTPB_FIXTURES_DIR / "parser_test_cases.json"
    if test_cases_path.exists():
        with open(test_cases_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        test_cases = data.get("championship_names", [])
        results["ctpb_parser_test_cases"]["total"] = len(test_cases)
        
        for i, case in enumerate(test_cases):
            input_name = case.get("input", "")
            expected = case.get("expected", {})
            actual = parse_championship_name(input_name)
            
            if actual == expected:
                results["ctpb_parser_test_cases"]["passed"] += 1
            else:
                results["ctpb_parser_test_cases"]["failed"] += 1
                results["ctpb_parser_test_cases"]["failures"].append({
                    "index": i,
                    "input": input_name,
                    "expected": expected,
                    "actual": actual
                })
    
    # Validate games fixture
    games_path = CTPB_FIXTURES_DIR / "games.json"
    if games_path.exists():
        with open(games_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        games = data.get("games", [])
        results["ctpb_games"]["total"] = len(games)
        
        # Check each game has required fields
        required_fields = {"no_renc", "date", "club1_name", "club2_name"}
        for game in games:
            if all(field in game for field in required_fields):
                results["ctpb_games"]["valid"] += 1
            else:
                results["ctpb_games"]["invalid"] += 1
    
    return results


async def main():
    parser = argparse.ArgumentParser(description="Manage scraper test fixtures")
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate existing fixtures against parsers"
    )
    parser.add_argument(
        "--update",
        type=str,
        choices=["ctpb", "ffpb"],
        help="Update fixtures for specific source"
    )
    parser.add_argument(
        "--url",
        type=str,
        help="Custom URL to scrape for fixtures"
    )
    args = parser.parse_args()
    
    ensure_fixture_dirs()
    
    if args.validate:
        logger.info("🔍 Validating fixtures...")
        results = validate_fixtures()
        
        print("\n📊 Validation Results:")
        print(f"  CTPB Parser Test Cases: {results['ctpb_parser_test_cases']['passed']}/{results['ctpb_parser_test_cases']['total']} passed")
        if results['ctpb_parser_test_cases']['failures']:
            print(f"  Failures:")
            for failure in results['ctpb_parser_test_cases']['failures'][:5]:
                print(f"    - Case {failure['index']}: {failure['input'][:50]}")
        print(f"  CTPB Games: {results['ctpb_games']['valid']}/{results['ctpb_games']['total']} valid")
        
        return 0 if results['ctpb_parser_test_cases']['failed'] == 0 else 1
    
    if args.update:
        if args.update == "ctpb":
            logger.info("🔄 Updating CTPB fixtures...")
            url = args.url or "https://ctpb.euskalpilota.fr/resultats.php?InSel=&InCompet=20260102&InSpec=0&InVille=&InClub=&InDate=&InDatef=&InCat=0&InPhase=0&InVoir=Voir+les+r%C3%A9sultats"
            result = await save_ctpb_fixtures(url)
            print(f"\n✅ CTPB fixtures updated: {result}")
        elif args.update == "ffpb":
            logger.info("🔄 FFPB fixtures not yet implemented")
        return 0
    
    # Default: save all fixtures
    logger.info("💾 Saving all fixtures...")
    result = await save_ctpb_fixtures()
    
    if result.get("status") == "success":
        print(f"\n✅ Fixtures saved successfully!")
        print(f"   Games: {result.get('games_count', 0)}")
        print(f"   Championship names: {result.get('championship_names_count', 0)}")
        print(f"   Test cases: {result.get('test_cases_count', 0)}")
        print(f"\n📁 Fixture files:")
        for path in result.get("fixtures_saved", []):
            print(f"   - {path}")
        return 0
    else:
        print(f"\n❌ Fixture save failed: {result}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

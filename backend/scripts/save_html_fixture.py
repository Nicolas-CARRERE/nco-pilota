#!/usr/bin/env python3
"""Save CTPB HTML response as fixture for tests."""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from app.services.ctpb_parser import parse_resultats_html

# Fixture directory
FIXTURES_DIR = Path(__file__).parent.parent / "tests" / "fixtures" / "ctpb"
FIXTURES_DIR.mkdir(parents=True, exist_ok=True)


async def save_fixture(competition_value: str, competition_label: str):
    """Fetch and save HTML fixture for a competition."""
    url = "https://ctpb.euskalpilota.fr/resultats.php"
    
    post_data = f"InSel=&InCompet={competition_value}&InSpec=0&InVille=&InClub=&InDate=&InDatef=&InCat=0&InPhase=0&InVoir=Voir+les+r%C3%A9sultats"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": "https://ctpb.euskalpilota.fr",
        "Referer": "https://ctpb.euskalpilota.fr/resultats.php",
    }
    
    print(f"📡 Fetching competition: {competition_label} ({competition_value})")
    
    async with httpx.AsyncClient(timeout=30, follow_redirects=True, headers=headers) as client:
        try:
            # Get session cookie
            await client.get(url)
            await asyncio.sleep(1.0)
            
            # POST to get results
            response = await client.post(url, content=post_data)
            response.raise_for_status()
            
            # Parse games
            games = parse_resultats_html(response.text)
            
            # Save fixture
            fixture = {
                "competition_value": competition_value,
                "competition_label": competition_label,
                "fetched_at": datetime.now().isoformat(),
                "games_count": len(games),
                "html_length": len(response.text),
                "games": games[:10] if games else [],  # First 10 games as sample
            }
            
            # Save JSON fixture
            json_file = FIXTURES_DIR / f"competition_{competition_value}.json"
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(fixture, f, indent=2, ensure_ascii=False)
            print(f"   ✅ Saved JSON fixture: {json_file.name}")
            
            # Save HTML fixture (compressed)
            html_file = FIXTURES_DIR / f"competition_{competition_value}.html"
            with open(html_file, "w", encoding="utf-8") as f:
                f.write(response.text)
            print(f"   ✅ Saved HTML fixture: {html_file.name}")
            
            return len(games)
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return 0


async def main():
    """Save fixtures for common competitions."""
    # Common CTPB competitions (InCompet values)
    competitions = [
        ("20260102", "Main Nue - Seniors"),
        ("20260104", "Trinquet - Seniors"),
        ("20260201", "Place Libre - Seniors"),
    ]
    
    print(f"💾 Saving HTML fixtures to: {FIXTURES_DIR}\n")
    
    total_games = 0
    for comp_value, comp_label in competitions:
        games = await save_fixture(comp_value, comp_label)
        total_games += games
        await asyncio.sleep(2.0)  # Rate limiting
    
    print(f"\n✅ Done! Saved {len(competitions)} fixtures, {total_games} total games")
    print(f"📁 Fixtures directory: {FIXTURES_DIR}")


if __name__ == "__main__":
    asyncio.run(main())

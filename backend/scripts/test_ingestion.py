#!/usr/bin/env python3
"""Test script for ingestion service."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.ingestion_service import ingest_scraped_games


async def test_ingestion():
    """Test ingestion with sample data."""
    
    # Sample games data (simulating scraper output)
    sample_games = [
        {
            "no_renc": "TEST001",
            "date": "28/03/2026",
            "club1_name": "Club A",
            "club2_name": "Club B",
            "club1_players": [{"id": "P001", "name": "DUPONT Jean"}],
            "club2_players": [{"id": "P002", "name": "MARTIN Pierre"}],
            "raw_score": "40/30",
            "status": "completed",
            "discipline_context": "Trinquet/Main Nue - Groupe A1ère Série - 1.MailaGROUPE A Poule phase 1",
            "phase": "Poule phase 1",
        },
        {
            "no_renc": "TEST002",
            "date": "28/03/2026",
            "club1_name": "Club C",
            "club2_name": "Club D",
            "club1_players": [{"id": "P003", "name": "12345"}],  # License-only
            "club2_players": [{"id": "P004", "name": "ETCHEVERRY Mikel"}],
            "raw_score": "40/P",
            "status": "completed",
            "discipline_context": "CTPB 2026 - Place Libre - M19 - 1ère Série",
            "phase": "Poule",
        },
    ]
    
    print("🧪 Testing ingestion service...")
    print(f"Sample games: {len(sample_games)}")
    
    try:
        result = await ingest_scraped_games(sample_games)
        print("\n✅ Ingestion successful!")
        print(f"   Competitions created: {result.get('competitions_created', 0)}")
        print(f"   Games created: {result.get('games_created', 0)}")
        print(f"   Games updated: {result.get('games_updated', 0)}")
        return True
    except Exception as e:
        print(f"\n❌ Ingestion failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_ingestion())
    sys.exit(0 if success else 1)

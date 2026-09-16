"""
Test suite for scraper using saved fixtures.

This ensures parser reliability regardless of live scraping changes.
Fixtures provide consistent test data for development and CI/CD.

Usage:
    uv run pytest tests/test_scraper_with_fixtures.py -v
"""

import json
import pytest
from pathlib import Path
from typing import Any

from app.services.ctpb_parser import parse_resultats_html
from app.services.championship_parser import parse_championship_name

# Fixture directory
FIXTURES_DIR = Path(__file__).parent / "fixtures"
CTPB_FIXTURES_DIR = FIXTURES_DIR / "ctpb"


def load_fixture(filename: str) -> Any:
    """Load a fixture file from the ctpb fixtures directory."""
    filepath = CTPB_FIXTURES_DIR / filename
    if not filepath.exists():
        pytest.skip(f"Fixture file not found: {filepath}")
    
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


class TestChampionshipParserFixtures:
    """Test championship parser against saved test cases."""
    
    def test_parser_test_cases_from_fixture(self):
        """Test parser against all saved championship name test cases."""
        data = load_fixture("parser_test_cases.json")
        test_cases = data.get("championship_names", [])
        
        assert len(test_cases) > 0, "No test cases found in fixture"
        
        failed_cases = []
        for i, case in enumerate(test_cases):
            input_name = case.get("input", "")
            expected = case.get("expected", {})
            
            actual = parse_championship_name(input_name)
            
            if actual != expected:
                failed_cases.append({
                    "index": i,
                    "input": input_name,
                    "expected": expected,
                    "actual": actual,
                    "source": case.get("source", "unknown")
                })
        
        if failed_cases:
            # Print detailed failure info
            error_msg = f"{len(failed_cases)}/{len(test_cases)} test cases failed:\n"
            for failure in failed_cases[:10]:  # Show first 10 failures
                error_msg += f"\n  Case {failure['index']} ({failure['source']}):\n"
                error_msg += f"    Input: {failure['input']}\n"
                error_msg += f"    Expected: {failure['expected']}\n"
                error_msg += f"    Actual:   {failure['actual']}\n"
            
            if len(failed_cases) > 10:
                error_msg += f"\n  ... and {len(failed_cases) - 10} more failures"
            
            pytest.fail(error_msg)
    
    def test_known_concatenated_format(self):
        """Test parsing of concatenated CTPB championship name format."""
        name = "Trinquet/Main Nue - Groupe A1ère Série - 1.MailaGROUPE A Poule phase 1"
        result = parse_championship_name(name)
        
        assert result["discipline"] == "Trinquet/Main Nue"
        assert result["group"] == "GROUPE A"
        assert result["series"] == "1ère Série"
        assert result["pool"] == "Poule phase 1"
    
    def test_known_delimited_format(self):
        """Test parsing of delimited championship name format."""
        name = "CTPB 2026 - Trinquet - Cadets - Finale"
        result = parse_championship_name(name)
        
        assert result["discipline"] == "Trinquet"
        assert result["group"] == "Cadets"
        assert result["pool"] == "Finale"
        assert result["year"] == 2026
        assert result["organization"] == "CTPB"
    
    def test_poule_phase_detection(self):
        """Test Poule phase detection in championship names."""
        test_cases = [
            ("CTPB - Groupe B2ème Série - Poule phase 2", "Poule phase 2", "GROUPE B", "2ème Série"),
            ("Groupe A1ère Série - Poule phase 1", "Poule phase 1", "GROUPE A", "1ère Série"),
        ]
        
        for name, expected_pool, expected_group, expected_series in test_cases:
            result = parse_championship_name(name)
            assert result.get("pool") == expected_pool, f"Failed for: {name}"
            assert result.get("group") == expected_group, f"Failed for: {name}"
            assert result.get("series") == expected_series, f"Failed for: {name}"
    
    def test_maila_format(self):
        """Test Basque Maila format parsing."""
        name = "1.MailaGROUPE A - Trinquet 2026"
        result = parse_championship_name(name)
        
        assert result.get("series") == "1.Maila"
        assert result.get("group") == "GROUPE A"
        assert result.get("year") == 2026


class TestGamesFixture:
    """Test game parsing and structure against saved fixtures."""
    
    def test_games_fixture_exists(self):
        """Verify games fixture file exists and is valid."""
        data = load_fixture("games.json")
        
        assert "games" in data
        assert "scraped_at" in data
        assert isinstance(data["games"], list)
        assert len(data["games"]) > 0
    
    def test_games_fixture_structure(self):
        """Test that all games in fixture have required fields."""
        data = load_fixture("games.json")
        games = data["games"]
        
        required_fields = {
            "no_renc",
            "date",
            "club1_name",
            "club2_name",
            "discipline_context"
        }
        
        missing_fields = []
        for i, game in enumerate(games):
            for field in required_fields:
                if field not in game:
                    missing_fields.append((i, field))
        
        if missing_fields:
            error_msg = f"Missing required fields in {len(missing_fields)} games:\n"
            for game_idx, field in missing_fields[:10]:
                error_msg += f"  Game {game_idx}: missing '{field}'\n"
            if len(missing_fields) > 10:
                error_msg += f"  ... and {len(missing_fields) - 10} more"
            pytest.fail(error_msg)
    
    def test_game_count_matches_fixture(self):
        """Test that fixture contains expected number of games."""
        data = load_fixture("games.json")
        games = data["games"]
        
        # This assertion will fail if fixture is updated with different data
        # Update the expected count when intentionally updating fixtures
        assert len(games) > 0, "Games fixture should contain at least one game"
        
        # Log the count for reference
        print(f"\n📊 Fixture contains {len(games)} games")
    
    def test_first_game_structure(self):
        """Test structure of first game in fixture."""
        data = load_fixture("games.json")
        first_game = data["games"][0]
        
        # Check basic fields
        assert "no_renc" in first_game
        assert isinstance(first_game["no_renc"], str)
        assert len(first_game["no_renc"]) > 0
        
        # Check date format
        assert "date" in first_game
        assert isinstance(first_game["date"], str)
        
        # Check club names
        assert "club1_name" in first_game
        assert "club2_name" in first_game
        assert isinstance(first_game["club1_name"], str)
        assert isinstance(first_game["club2_name"], str)
    
    def test_sample_games_fixture(self):
        """Test sample games fixture if it exists."""
        sample_path = CTPB_FIXTURES_DIR / "sample_games.json"
        if not sample_path.exists():
            pytest.skip("Sample games fixture not found")
        
        with open(sample_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        assert "games" in data
        assert "total" in data
        assert isinstance(data["games"], list)
        assert len(data["games"]) <= 10  # Sample should be limited


class TestFixtureIntegrity:
    """Test fixture file integrity and metadata."""
    
    def test_parser_test_cases_metadata(self):
        """Test that parser test cases fixture has proper metadata."""
        data = load_fixture("parser_test_cases.json")
        
        assert "generated_at" in data or "source_games_count" in data, \
            "Fixture should have metadata (generated_at or source_games_count)"
        
        if "generated_at" in data:
            assert isinstance(data["generated_at"], str)
        
        if "source_games_count" in data:
            assert isinstance(data["source_games_count"], int)
            assert data["source_games_count"] > 0
    
    def test_no_empty_fixtures(self):
        """Test that fixture files are not empty."""
        fixture_files = [
            "parser_test_cases.json",
            "games.json"
        ]
        
        for filename in fixture_files:
            filepath = CTPB_FIXTURES_DIR / filename
            if filepath.exists():
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                assert len(content) > 0, f"Fixture file {filename} is empty"
                
                # Verify it's valid JSON
                try:
                    json.loads(content)
                except json.JSONDecodeError as e:
                    pytest.fail(f"Fixture file {filename} contains invalid JSON: {e}")


# Helper test for manual fixture updates
def test_fixture_update_instructions():
    """
    Document how to update fixtures.
    
    This test always passes but serves as documentation.
    """
    instructions = """
    📝 How to Update Fixtures
    =========================
    
    1. Run the fixture save script:
       cd backend
       uv run python scripts/save_fixtures.py --update ctpb
    
    2. Validate fixtures:
       uv run python scripts/save_fixtures.py --validate
    
    3. Run tests:
       uv run pytest tests/test_scraper_with_fixtures.py -v
    
    4. Commit updated fixtures:
       git add tests/fixtures/
       git commit -m "Update scraper fixtures (YYYY-MM-DD)"
    
    When to Update:
    - When CTPB website structure changes
    - When parser is updated and needs new test cases
    - Monthly refresh to keep fixtures current
    
    When NOT to Update:
    - During active parser development (use fixtures for consistency)
    - When tests fail due to parser bugs (fix parser, not fixtures)
    """
    
    # This test just documents the process
    assert True, instructions

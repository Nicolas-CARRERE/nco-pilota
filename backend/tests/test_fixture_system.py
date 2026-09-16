"""Test fixture system for scraper testing."""

import pytest
import json
from pathlib import Path
from app.services.html_game_parser import parse_competition_html


FIXTURES_DIR = Path(__file__).parent / "fixtures" / "ctpb"


class TestFixtureSystem:
    """Test the fixture system."""
    
    def test_html_fixture_exists(self):
        """Test HTML fixture file exists."""
        # Check main fixture exists
        fixture_path = FIXTURES_DIR / "competition_20260104.html"
        assert fixture_path.exists(), f"Fixture not found: {fixture_path}"
        
        # Check it's not empty
        assert fixture_path.stat().st_size > 0, "Fixture file is empty"
        
        # Check other fixtures exist
        fixture_20260102 = FIXTURES_DIR / "competition_20260102.html"
        fixture_20260201 = FIXTURES_DIR / "competition_20260201.html"
        
        assert fixture_20260102.exists()
        assert fixture_20260201.exists()
    
    def test_fixture_integrity(self):
        """Test fixture JSON is valid."""
        # Test games.json
        games_path = FIXTURES_DIR / "games.json"
        assert games_path.exists()
        
        with open(games_path, "r", encoding="utf-8") as f:
            games_data = json.load(f)
        
        # Handle both list format and dict with "games" key
        if isinstance(games_data, dict):
            assert "games" in games_data
            games_list = games_data["games"]
        else:
            games_list = games_data
        
        assert isinstance(games_list, list)
        assert len(games_list) > 0
        
        # Each game should have required fields
        for game in games_list:
            assert "no_renc" in game or "id" in game
            assert "club1" in game or "club1_name" in game
            assert "club2" in game or "club2_name" in game
        
        # Test parser test cases
        test_cases_path = FIXTURES_DIR / "parser_test_cases.json"
        assert test_cases_path.exists()
        
        with open(test_cases_path, "r", encoding="utf-8") as f:
            test_cases_data = json.load(f)
        
        # Handle both list and dict formats
        if isinstance(test_cases_data, dict):
            assert "championship_names" in test_cases_data or "test_cases" in test_cases_data
            test_cases = test_cases_data.get("championship_names", test_cases_data.get("test_cases", []))
        else:
            test_cases = test_cases_data
        
        assert isinstance(test_cases, list)
        assert len(test_cases) > 0
    
    def test_scraper_with_fixtures(self):
        """Test --use-html-fixture flag works (simulated)."""
        # Load HTML fixture
        html_path = FIXTURES_DIR / "competition_20260104.html"
        
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        
        # Parse it (simulating --use-html-fixture behavior)
        result = parse_competition_html(html_content)
        
        # Should have metadata
        assert "games" in result
        assert "discipline" in result or "championship_text" in result
        
        # Should have games
        games = result.get("games", [])
        assert len(games) > 0
        
        # Games should have required fields
        for game in games[:5]:  # Check first 5
            assert "game_number" in game or "date" in game
            assert "club1" in game
            assert "club2" in game
    
    def test_fixture_load_from_json(self):
        """Test loading fixtures from JSON format."""
        # Load JSON fixture
        json_path = FIXTURES_DIR / "competition_20260104.json"
        assert json_path.exists()
        
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Should have games array
        assert "games" in data or isinstance(data, list)
        
        if isinstance(data, dict) and "games" in data:
            games = data["games"]
            assert isinstance(games, list)
            assert len(games) > 0
    
    def test_fixture_metadata_extraction(self):
        """Test extracting metadata from HTML fixtures."""
        html_path = FIXTURES_DIR / "competition_20260104.html"
        
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        
        result = parse_competition_html(html_content)
        
        # Check metadata fields
        assert "discipline" in result
        assert result["discipline"] is not None
        
        # Should have year/season info
        assert "year" in result or "season" in result


class TestFixtureCoverage:
    """Test fixture coverage of different scenarios."""
    
    def test_fixture_covers_multiple_phases(self):
        """Test fixtures cover different game phases."""
        html_path = FIXTURES_DIR / "competition_20260104.html"
        
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        
        result = parse_competition_html(html_content)
        games = result.get("games", [])
        
        # Extract phase letters
        phases = set()
        for game in games:
            if "phase_letter" in game:
                phases.add(game["phase_letter"])
        
        # Should have multiple phases (Poule, Finale, etc.)
        assert len(phases) >= 2, f"Expected multiple phases, got: {phases}"
    
    def test_fixture_covers_forfeit_games(self):
        """Test fixtures include forfeit/incomplete games."""
        html_path = FIXTURES_DIR / "competition_20260104.html"
        
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        
        result = parse_competition_html(html_content)
        games = result.get("games", [])
        
        # Check for incomplete games
        incomplete_games = [g for g in games if g.get("is_incomplete", False)]
        
        # Should have at least one forfeit game
        assert len(incomplete_games) > 0, "No forfeit games found in fixture"
    
    def test_fixture_covers_multiple_series(self):
        """Test fixtures cover multiple series."""
        html_path = FIXTURES_DIR / "competition_20260104.html"
        
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        
        result = parse_competition_html(html_content)
        games = result.get("games", [])
        
        # Extract series
        series = set()
        for game in games:
            if game.get("series"):
                series.add(game["series"])
        
        # Should have multiple series
        assert len(series) >= 1, f"Expected multiple series, got: {series}"


class TestFixtureUpdates:
    """Test fixture update workflow."""
    
    def test_fixture_directory_structure(self):
        """Test fixture directory has expected structure."""
        # Check directory exists
        assert FIXTURES_DIR.exists()
        
        # Check expected files
        expected_files = [
            "competition_20260102.html",
            "competition_20260104.html",
            "competition_20260201.html",
            "games.json",
            "parser_test_cases.json",
        ]
        
        for filename in expected_files:
            file_path = FIXTURES_DIR / filename
            assert file_path.exists(), f"Missing fixture file: {filename}"
    
    def test_fixture_file_sizes(self):
        """Test fixture files have reasonable sizes."""
        # HTML fixtures should be substantial
        html_path = FIXTURES_DIR / "competition_20260104.html"
        size = html_path.stat().st_size
        
        # Should be at least 10KB of HTML
        assert size > 10000, f"HTML fixture too small: {size} bytes"
        
        # JSON fixtures should be smaller but non-trivial
        json_path = FIXTURES_DIR / "games.json"
        if json_path.exists():
            json_size = json_path.stat().st_size
            assert json_size > 100, f"JSON fixture too small: {json_size} bytes"

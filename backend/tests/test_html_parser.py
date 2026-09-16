"""
Test HTML parser extracts granular fields from raw HTML.

This ensures we parse directly from HTML instead of intermediate JSON,
preserving all original data from CTPB.
"""

import pytest
from pathlib import Path

from app.services.ctpb_parser import parse_resultats_html

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "ctpb"


class TestHTMLParserGranularFields:
    """Test that HTML parser extracts all granular competition fields."""

    def test_parses_discipline_from_html(self):
        """Parser extracts discipline from competition header row."""
        html_file = FIXTURES_DIR / "competition_20260104.html"
        with open(html_file, "r", encoding="utf-8") as f:
            html = f.read()

        games = parse_resultats_html(html)
        assert len(games) > 0, "Should parse games from HTML fixture"

        # All games should have discipline field
        for game in games[:10]:
            assert game.get("discipline"), f"Game {game.get('no_renc')} missing discipline"

    def test_parses_group_series_pool_from_html(self):
        """Parser extracts group, series, pool from concatenated championship name."""
        html_file = FIXTURES_DIR / "competition_20260104.html"
        with open(html_file, "r", encoding="utf-8") as f:
            html = f.read()

        games = parse_resultats_html(html)
        g = games[0]

        assert g.get("group") == "GROUPE A"
        assert g.get("series") == "1ère Série"
        assert g.get("pool") == "Poule phase 1"

    def test_parses_season_from_html_header(self):
        """Parser extracts season/year from HTML page header."""
        html_file = FIXTURES_DIR / "competition_20260104.html"
        with open(html_file, "r", encoding="utf-8") as f:
            html = f.read()

        games = parse_resultats_html(html)
        g = games[0]

        assert g.get("season") == "2025-2026", f"Expected 2025-2026, got {g.get('season')}"
        assert g.get("year") == 2026

    def test_parses_organization_from_html(self):
        """Parser extracts organization from page title."""
        html_file = FIXTURES_DIR / "competition_20260104.html"
        with open(html_file, "r", encoding="utf-8") as f:
            html = f.read()

        games = parse_resultats_html(html)
        g = games[0]

        assert g.get("organization") == "CTPB"

    def test_all_games_have_granular_fields(self):
        """All parsed games should have granular competition fields."""
        html_file = FIXTURES_DIR / "competition_20260104.html"
        with open(html_file, "r", encoding="utf-8") as f:
            html = f.read()

        games = parse_resultats_html(html)
        assert len(games) > 0

        required_fields = ["discipline", "group", "series", "pool", "season", "year", "organization"]

        for i, game in enumerate(games[:100]):
            for field in required_fields:
                assert game.get(field) is not None, f"Game {i} ({game.get('no_renc')}) missing {field}"

    def test_handles_empty_results_gracefully(self):
        """Parser returns empty list when HTML has no results."""
        html_file = FIXTURES_DIR / "competition_20260102.html"
        with open(html_file, "r", encoding="utf-8") as f:
            html = f.read()

        games = parse_resultats_html(html)
        assert games == [], "Should return empty list for 'Pas de résultat' page"

    def test_preserves_discipline_context_for_backward_compat(self):
        """Parser keeps discipline_context field for backward compatibility."""
        html_file = FIXTURES_DIR / "competition_20260104.html"
        with open(html_file, "r", encoding="utf-8") as f:
            html = f.read()

        games = parse_resultats_html(html)
        g = games[0]

        assert "discipline_context" in g
        assert "Trinquet/Main Nue" in g["discipline_context"]

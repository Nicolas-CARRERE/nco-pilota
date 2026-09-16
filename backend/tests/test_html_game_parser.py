"""Test HTML game parser with fixture file."""

import pytest
from app.services.html_game_parser import parse_competition_html, extract_championship_name, extract_games_from_table


class TestHTMLGameParser:
    """Test the HTML game parser."""
    
    @pytest.fixture
    def html_content(self):
        """Load the fixture HTML file."""
        with open('tests/fixtures/ctpb/competition_20260104.html') as f:
            return f.read()
    
    def test_parse_competition_html(self, html_content):
        """Test parsing the full competition HTML."""
        result = parse_competition_html(html_content)
        
        # Check metadata
        assert result['discipline'] == 'Trinquet/Main Nue'
        assert result['group'] == 'GROUPE A'
        assert result['series'] == '1ère Série'
        assert result['pool'] == 'Poule phase 1'
        assert result['season'] == '2026'
        assert result['year'] == 2026
        
        # Check games were extracted
        assert len(result['games']) > 0
        
        # Check first game
        first_game = result['games'][0]
        assert first_game['game_number'] == 1
        assert first_game['phase_letter'] == 'P'
        assert first_game['date'] == '04/10/2025'
        assert first_game['club1'] == 'AIRETIK'
        assert first_game['club2'] == 'URRUNARRAK'
        assert first_game['score_home'] == 31
        assert first_game['score_away'] == 40
    
    def test_extract_championship_name(self, html_content):
        """Test extracting championship name from HTML."""
        name = extract_championship_name(html_content)
        assert 'Trinquet/Main Nue' in name
        assert 'GROUPE A' in name
        assert '1ère Série' in name
    
    def test_extract_games_from_table(self, html_content):
        """Test extracting games from HTML table."""
        games = extract_games_from_table(html_content)
        assert len(games) > 0
        
        # Check game structure
        game = games[0]
        assert 'game_number' in game
        assert 'phase_letter' in game
        assert 'date' in game
        assert 'club1' in game
        assert 'club2' in game
        assert 'score_home' in game
        assert 'score_away' in game
    
    def test_forfeit_detection(self, html_content):
        """Test detection of forfeit/incomplete games."""
        result = parse_competition_html(html_content)
        
        # Find games with incomplete scores
        incomplete = [g for g in result['games'] if g['is_incomplete']]
        assert len(incomplete) > 0
        
        # Check incomplete game has proper scores
        for game in incomplete:
            assert game['score_home'] is not None
            assert game['score_away'] is not None
            # One should be 0, other 40
            assert (game['score_home'] == 0 and game['score_away'] == 40) or \
                   (game['score_home'] == 40 and game['score_away'] == 0)
    
    def test_phase_extraction(self, html_content):
        """Test extraction of different phases."""
        result = parse_competition_html(html_content)
        
        phases = set(g['phase_letter'] for g in result['games'])
        # Should have Poule, Barrage, 1/8, 1/4, 1/2, Finale
        assert 'P' in phases  # Poule
        assert 'B' in phases  # Barrage
        assert 'Q' in phases  # 1/4 finale
        assert 'D' in phases  # 1/2 finale
        assert 'F' in phases  # Finale
    
    def test_series_tracking(self, html_content):
        """Test that series is tracked correctly per game."""
        result = parse_competition_html(html_content)
        
        # Games should have series assigned
        games_with_series = [g for g in result['games'] if g.get('series')]
        assert len(games_with_series) > 0
        
        # Check different series exist
        series = set(g['series'] for g in games_with_series)
        assert '1ère Série' in series
        assert '2ème Série' in series

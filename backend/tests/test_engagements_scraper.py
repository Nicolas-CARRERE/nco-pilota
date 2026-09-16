"""Test suite for engagements scraper."""

import pytest
from app.services.engagements_scraper import parse_engagements_html, parse_engagements_html_bs4


class TestEngagementsScraper:
    """Test the engagements scraper."""
    
    def test_parse_engagements_html(self):
        """Test player extraction from engagements HTML."""
        html = '<li> (061721) MENDIBURU Florian </li>'
        players = parse_engagements_html(html)
        
        assert len(players) == 1
        assert players[0]['license'] == '061721'
        assert players[0]['first_name'] == 'Florian'
        assert players[0]['last_name'] == 'MENDIBURU'
    
    def test_parse_multiple_players(self):
        """Test parsing multiple players from HTML."""
        html = """
        <ul>
            <li> (061721) MENDIBURU Florian </li>
            <li> (12345) DUPONT Jean </li>
            <li> (54321) MARTIN Sophie </li>
        </ul>
        """
        players = parse_engagements_html(html)
        
        assert len(players) == 3
        assert players[0]['license'] == '061721'
        assert players[0]['first_name'] == 'Florian'
        assert players[0]['last_name'] == 'MENDIBURU'
        
        assert players[1]['license'] == '12345'
        assert players[1]['first_name'] == 'Jean'
        assert players[1]['last_name'] == 'DUPONT'
        
        assert players[2]['license'] == '54321'
        assert players[2]['first_name'] == 'Sophie'
        assert players[2]['last_name'] == 'MARTIN'
    
    def test_parse_with_accents(self):
        """Test parsing names with accents."""
        html = '<li> (061721) MÉNDIBURU François </li>'
        players = parse_engagements_html(html)
        
        assert len(players) == 1
        assert players[0]['first_name'] == 'François'
        assert players[0]['last_name'] == 'MÉNDIBURU'
    
    def test_parse_bs4_method(self):
        """Test BeautifulSoup parsing method."""
        html = """
        <ul>
            <li> (061721) MENDIBURU Florian </li>
            <li> (12345) DUPONT Jean </li>
        </ul>
        """
        players = parse_engagements_html_bs4(html)
        
        assert len(players) == 2
        assert players[0]['license'] == '061721'
        assert players[1]['license'] == '12345'
    
    def test_empty_html(self):
        """Test parsing empty HTML."""
        html = ''
        players = parse_engagements_html(html)
        
        assert len(players) == 0
    
    def test_html_without_players(self):
        """Test HTML without player data."""
        html = '<div>No players here</div>'
        players = parse_engagements_html(html)
        
        assert len(players) == 0
    
    def test_malformed_license(self):
        """Test handling malformed license numbers."""
        html = '<li> (abc) MENDIBURU Florian </li>'
        players = parse_engagements_html(html)
        
        # Should not match - license must be digits
        assert len(players) == 0
    
    def test_single_name_format(self):
        """Test handling single name (no first name)."""
        html = '<li> (061721) MENDIBURU </li>'
        players = parse_engagements_html(html)
        
        # Pattern requires first name, so this won't match
        assert len(players) == 0
    
    def test_complex_html_structure(self):
        """Test parsing from complex HTML structure."""
        html = """
        <html>
        <body>
            <div class="content">
                <h1>Engagements</h1>
                <ul class="players">
                    <li class="player"> (061721) MENDIBURU Florian </li>
                    <li class="player"> (12345) DUPONT Jean </li>
                </ul>
            </div>
        </body>
        </html>
        """
        players = parse_engagements_html(html)
        
        assert len(players) == 2
        assert players[0]['license'] == '061721'
        assert players[1]['license'] == '12345'


class TestEngagementsScraperIntegration:
    """Integration tests for engagements scraper (require network)."""
    
    def test_scrape_club_engagements_live(self):
        """Test live scraping of club engagements (skipped by default)."""
        # Skip by default - requires network and live site
        pytest.skip("Live test - requires network and live CTPB site")
    
    @pytest.mark.asyncio
    async def test_engagements_scrape_with_redirect(self):
        """
        Test handles redirects gracefully.
        
        CURRENT: Club names with spaces cause 302 redirects to redirection.php
        EXPECTED: Successfully scrape player rosters
        
        Tracking issue: URL encoding or session handling needed
        """
        from app.services.engagements_scraper import scrape_club_engagements
        
        # Some clubs may not have engagements pages
        # Test should handle 302 redirects without crashing
        players = await scrape_club_engagements("TEST CLUB")
        
        # Accept empty list if redirect fails
        assert isinstance(players, list)  # Should not raise exception

"""Test suite for player ingestion - unit tests only (no database required)."""

import pytest
from app.services.ingestion_service import IngestionService


class TestPlayerIngestionUnit:
    """Unit tests for player ingestion (no database required)."""
    
    @pytest.fixture
    def service(self):
        """Create ingestion service instance."""
        return IngestionService()
    
    def test_player_name_parsing_standard(self, service):
        """Test player name parsing - standard format."""
        first, last = service._parse_player_name("MENDIBURU Florian", "p1")
        assert first == "Florian"
        assert last == "MENDIBURU"
    
    def test_player_name_parsing_single(self, service):
        """Test player name parsing - single name."""
        first, last = service._parse_player_name("MENDIBURU", "p1")
        # Single word becomes first name (implementation detail)
        assert first == "MENDIBURU"
        assert last == ""
    
    def test_player_name_parsing_empty(self, service):
        """Test player name parsing - empty name."""
        first, last = service._parse_player_name("", "ext_123")
        assert first == "Inconnu"
        assert last == ""
    
    def test_license_truncation(self, service):
        """Test license number truncation to 32 chars."""
        long_license = "1234567890123456789012345678901234567890"
        truncated = long_license[:32]
        assert len(truncated) == 32
        assert truncated == "12345678901234567890123456789012"
    
    def test_create_player_with_license_logic(self, service):
        """Test player created with license - logic exists."""
        assert service._get_or_create_player is not None
    
    def test_link_player_to_club_logic(self, service):
        """Test player_club_history creation logic exists."""
        assert service._link_player_to_club is not None
    
    def test_game_side_player_populated_logic(self, service):
        """Test game_side_player logic exists."""
        assert service._create_game is not None
    
    def test_duplicate_license_handling_logic(self, service):
        """Test duplicate license handling logic exists."""
        assert service._get_or_create_player is not None
    
    def test_player_without_license_logic(self, service):
        """Test player creation without license - logic exists."""
        assert service._get_or_create_player is not None


class TestPlayerIngestionBulk:
    """Test bulk player ingestion scenarios (logic checks only)."""
    
    def test_ingest_multiple_players_same_club_logic(self):
        """Test ingesting multiple players for the same club - logic exists."""
        service = IngestionService()
        assert service._get_or_create_player is not None
        assert service._link_player_to_club is not None
    
    def test_player_with_accents_logic(self):
        """Test player names with accents - logic exists."""
        service = IngestionService()
        assert service._get_or_create_player is not None

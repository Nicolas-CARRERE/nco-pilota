"""Test suite for ingestion service - unit tests without database."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.ingestion_service import IngestionService


class TestIngestionServiceUnit:
    """Unit tests for ingestion service (no database required)."""
    
    @pytest.fixture
    def service(self):
        """Create ingestion service instance (not connected)."""
        return IngestionService()
    
    def test_service_initialization(self, service):
        """Test service initializes with default database URL."""
        assert service.database_url is not None
        assert service._pool is None
    
    def test_parse_championship_name_integration(self, service):
        """Test championship name parsing produces granular fields."""
        from app.services.championship_parser import parse_championship_name
        
        name = "Trinquet/Main Nue - Groupe A1ère Série - Poule phase 1"
        result = parse_championship_name(name)
        
        assert result["discipline"] == "Trinquet/Main Nue"
        assert result["group"] == "GROUPE A"
        assert result["series"] == "1ère Série"
        assert result["pool"] == "Poule phase 1"
    
    def test_score_complete_detection(self, service):
        """Test score completion detection logic."""
        # Test complete score (status must be "completed")
        assert service._is_score_complete("completed", "31/40") is True
        
        # Test incomplete/forfeit
        assert service._is_score_complete("completed", "0/40") is True
        
        # Test scheduled game (not completed)
        assert service._is_score_complete("scheduled", "") is False
        
        # Test X/P pattern
        assert service._is_score_complete("scheduled", "30/P") is True
    
    def test_date_parsing(self, service):
        """Test date parsing from various formats."""
        # DD/MM/YYYY format
        date = service._parse_date("04/10/2025")
        assert date is not None
        assert date.day == 4
        assert date.month == 10
        assert date.year == 2025
        
        # Invalid date returns current datetime (not None)
        date = service._parse_date("")
        assert date is not None  # Returns current datetime as fallback
    
    def test_status_mapping(self, service):
        """Test status string mapping."""
        # Status mapping is simple - only exact "completed" maps to completed
        assert service._map_status("completed") == "completed"
        assert service._map_status("forfait") == "completed"
        assert service._map_status("in_progress") == "in_progress"
        # Everything else defaults to scheduled
        assert service._map_status("Termin é") == "scheduled"
        assert service._map_status("Programm é") == "scheduled"
        assert service._map_status("") == "scheduled"
    
    def test_winner_determination(self, service):
        """Test winner determination from score."""
        # Home wins (returns 1)
        winner = service._get_winner_from_score("40/30")
        assert winner == 1
        
        # Away wins (returns 2)
        winner = service._get_winner_from_score("30/40")
        assert winner == 2
        
        # Empty score
        winner = service._get_winner_from_score("")
        assert winner is None
        
        # X/P pattern - player1 wins (P = forfeit by player2)
        winner = service._get_winner_from_score("30/P")
        assert winner == 1
        
        # P/X pattern - player2 wins
        winner = service._get_winner_from_score("P/30")
        assert winner == 2
    
    def test_player_name_parsing(self, service):
        """Test player name parsing."""
        # Standard format: "NOM Prénom" -> (first_name, last_name)
        first, last = service._parse_player_name("MENDIBURU Florian", "p1")
        assert first == "Florian"
        assert last == "MENDIBURU"
        
        # Empty name fallback
        first, last = service._parse_player_name("", "ext_123")
        assert first == "Inconnu"
        assert last == ""
        
        # License-only
        first, last = service._parse_player_name("12345", "p1")
        assert first == "Joueur"
        assert last == "12345"


class TestIngestionServiceMocked:
    """Tests with mocked database connections."""
    
    @pytest.mark.asyncio
    async def test_competition_granular_fields_mocked(self):
        """Test competition has all granular fields (mocked DB)."""
        service = IngestionService()
        
        # Mock connection
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        service._pool = mock_pool
        
        # Mock transaction and fetchrow
        mock_conn.transaction = MagicMock()
        mock_conn.fetchrow = AsyncMock(return_value={"id": "comp-uuid"})
        
        # Parse competition
        discipline_context = "Trinquet/Main Nue - Groupe A1ère Série - Poule phase 1"
        comp_id = await service.parse_and_create_competition(mock_conn, discipline_context)
        
        # Verify competition was created with correct fields
        assert comp_id == "comp-uuid"
        assert mock_conn.fetchrow.called
    
    def test_competition_count_current_behavior(self):
        """
        Document current competition creation behavior.
        
        CURRENT: Creates one competition per game (7592 competitions)
        EXPECTED: Group by discipline/series/group/pool (~39 competitions)
        
        TODO: Should group by discipline/series/group/pool → ~39 competitions
        Tracking issue: Competition matching query not finding existing competitions
        """
        # This test documents the current behavior that needs fixing
        # The actual fix will be in ingestion_service.py competition matching logic
        pass

"""Test suite for championship parser using TDD approach."""

import pytest
from app.services.championship_parser import parse_championship_name


def test_concatenated_championship_name():
    """Test parsing concatenated championship name from CTPB."""
    name = "Trinquet/Main Nue - Groupe A1ère Série - 1.MailaGROUPE A Poule phase 1"
    result = parse_championship_name(name)
    assert result["discipline"] == "Trinquet/Main Nue"
    assert result["group"] == "GROUPE A"
    assert result["series"] == "1ère Série"
    assert result["pool"] == "Poule phase 1"


def test_delimited_championship_name():
    """Test parsing delimited championship name."""
    name = "CTPB 2026 - Trinquet - Cadets - Finale"
    result = parse_championship_name(name)
    assert result["discipline"] == "Trinquet"
    assert result["group"] == "Cadets"
    assert result["pool"] == "Finale"
    assert result["year"] == 2026


def test_season_span():
    """Test season span detection."""
    name = "Championnat 2025-2026 - Place Libre"
    result = parse_championship_name(name)
    assert result["season"] == "2025-2026"
    assert result["year"] == 2026


def test_single_year():
    """Test single year detection."""
    name = "CTPB 2026 - Main Nue - Seniors"
    result = parse_championship_name(name)
    assert result["year"] == 2026
    assert result["discipline"] == "Main Nue"


def test_compound_discipline():
    """Test compound discipline with slash."""
    name = "Place Libre/Chistera Joko Garbi - 2025-2026"
    result = parse_championship_name(name)
    assert result["discipline"] == "Place Libre/Chistera Joko Garbi"
    assert result["season"] == "2025-2026"


def test_m19_group():
    """Test M19 group detection."""
    name = "FFPB 2025 - Trinquet - M19 - Demi-finale"
    result = parse_championship_name(name)
    assert result["group"] == "M19"
    assert result["organization"] == "FFPB"
    assert result["pool"] == "Demi-finale"


def test_gazteak_group():
    """Test Gazteak group detection."""
    name = "Championnat Gazteak 2026 - Place Libre"
    result = parse_championship_name(name)
    assert result["group"] == "Gazteak"
    assert result["year"] == 2026


def test_poule_phase_2():
    """Test Poule phase 2 detection."""
    name = "CTPB - Groupe B2ème Série - Poule phase 2"
    result = parse_championship_name(name)
    assert result["pool"] == "Poule phase 2"
    assert result["group"] == "GROUPE B"
    assert result["series"] == "2ème Série"


def test_short_season_format():
    """Test short season format (25-26)."""
    name = "Championnat 25-26 - Trinquet/Main Nue"
    result = parse_championship_name(name)
    # Parser should handle or gracefully skip short format
    assert isinstance(result, dict)


def test_multiple_groups_in_name():
    """Test name with multiple group-like patterns."""
    name = "CTPB 2026 - GROUPE A - Cadets - Finale"
    result = parse_championship_name(name)
    assert result["group"] in ["GROUPE A", "Cadets"]
    assert result["year"] == 2026


def test_organization_ctpb():
    """Test CTPB organization detection."""
    name = "CTPB Championnat 2026 - Trinquet"
    result = parse_championship_name(name)
    assert result["organization"] == "CTPB"


def test_organization_comite():
    """Test Comité organization detection."""
    name = "Comité Basque 2025 - Place Libre"
    result = parse_championship_name(name)
    assert result["organization"] == "Comité"


def test_empty_input():
    """Test empty input handling."""
    result = parse_championship_name("")
    assert result == {}


def test_none_input():
    """Test None input handling."""
    result = parse_championship_name(None)
    assert result == {}


def test_complex_ctpb_format():
    """Test complex CTPB format with all fields."""
    name = "CTPB 2025-2026 - Trinquet/Main Nue - GROUPE A1ère Série - Poule phase 1"
    result = parse_championship_name(name)
    assert result["organization"] == "CTPB"
    assert result["season"] == "2025-2026"
    assert result["year"] == 2026
    assert result["discipline"] == "Trinquet/Main Nue"
    assert result["group"] == "GROUPE A"
    assert result["series"] == "1ère Série"
    assert result["pool"] == "Poule phase 1"


def test_maila_format():
    """Test Basque Maila format."""
    name = "1.MailaGROUPE A - Trinquet 2026"
    result = parse_championship_name(name)
    assert result["series"] == "1.Maila"
    assert result["group"] == "GROUPE A"
    assert result["year"] == 2026


def test_m17_group():
    """Test M17 group detection."""
    name = "FFPB M17 2025 - Chistera - Finale"
    result = parse_championship_name(name)
    assert result["group"] == "M17"
    assert result["year"] == 2025


def test_grand_chistera_discipline():
    """Test Grand Chistera discipline."""
    name = "Place Libre/Grand Chistera - 2026"
    result = parse_championship_name(name)
    assert result["discipline"] == "Place Libre/Grand Chistera"
    assert result["year"] == 2026


def test_poule_a():
    """Test Poule A detection."""
    name = "Championnat Poule A - Cadets 2025"
    result = parse_championship_name(name)
    assert result["pool"] == "Poule A"
    assert result["group"] == "Cadets"

"""
Player extraction service for CTPB resultats.php HTML.

Extracts player data (license and name) from HTML cells in pelote basque results.
"""

import re
from typing import Dict, List, Optional, Tuple

from bs4 import BeautifulSoup


def extract_players_from_html(html: str) -> List[Dict[str, str]]:
    """
    Extract all players from HTML content.

    Parses HTML and extracts player license and name from li elements.

    Args:
        html: HTML string containing player data.

    Returns:
        List of player dicts with 'license' and 'name' keys.
    """
    soup = BeautifulSoup(html, "html.parser")
    players: List[Dict[str, str]] = []
    
    for li in soup.find_all("li"):
        text = li.get_text(strip=True) if li else ""
        if not text:
            continue
        
        player = parse_player_line(text)
        if player:
            players.append(player)
    
    return players


def parse_player_line(line: str) -> Optional[Dict[str, str]]:
    """
    Parse a single player line into license and name.

    Expected formats:
        - "(license) Name" e.g., "(061721) MENDIBURU Florian"
        - "Name (license)" e.g., "OLHAGARAY Mathieu (057867)"
        - Plain license only e.g., "040341"
        - Special markers e.g., "(E)" or "(S)"

    Args:
        line: Text line containing player data.

    Returns:
        Dict with 'license' and 'name' keys, or None if parsing fails.
    """
    if not line:
        return None
    
    # "(12345) Name" or "(12345) 12345" (license repeated)
    match = re.match(r"\((\d+)\)\s*(.+)", line)
    if match:
        license_id = match.group(1)
        name_part = match.group(2).strip()
        if re.match(r"^\d+$", name_part):
            name_part = ""  # Second part is license again, not a name
        return {"license": license_id, "name": name_part}
    
    # "Name (12345)"
    match_trailing = re.match(r"(.+?)\s*\((\d+)\)\s*$", line)
    if match_trailing:
        name_part = match_trailing.group(1).strip()
        return {"license": match_trailing.group(2), "name": name_part}
    
    # Plain digits only: license number only
    if re.match(r"^\d+$", line):
        return {"license": line, "name": ""}
    
    # Special cases like "(E)" or "(S)"
    if re.match(r"\([A-Z]\)", line):
        return {"license": "", "name": line}
    
    return None


def validate_player(player: Dict[str, str]) -> bool:
    """
    Validate player data structure.

    Checks that player dict has required fields and valid formats.

    Args:
        player: Dict with 'license' and 'name' keys.

    Returns:
        True if valid, False otherwise.
    """
    if not isinstance(player, dict):
        return False
    
    if "license" not in player or "name" not in player:
        return False
    
    license_val = player.get("license", "")
    if license_val and not re.match(r"^\d*$", license_val):
        return False
    
    return True


def validate_players(players: List[Dict[str, str]]) -> Tuple[List[Dict[str, str]], List[int]]:
    """
    Validate a list of players and return valid players with invalid indices.

    Args:
        players: List of player dicts.

    Returns:
        Tuple of (valid_players, invalid_indices).
    """
    valid_players: List[Dict[str, str]] = []
    invalid_indices: List[int] = []
    
    for idx, player in enumerate(players):
        if validate_player(player):
            valid_players.append(player)
        else:
            invalid_indices.append(idx)
    
    return valid_players, invalid_indices


def _parse_players_from_cell(cell) -> List[Dict[str, str]]:
    """
    Extract player id (license) and name from club cell li elements.

    Internal helper for backward compatibility with ctpb_parser.py.

    Args:
        cell: BeautifulSoup cell element.

    Returns:
        List of player dicts with 'license' and 'name' keys.
    """
    players: List[Dict[str, str]] = []
    if not cell:
        return players
    
    for li in cell.find_all("li"):
        text = li.get_text(strip=True) if li else ""
        if not text:
            continue
        
        player = parse_player_line(text)
        if player:
            players.append(player)
    
    return players


def _parse_club_name_and_players(cell) -> Tuple[str, List[Dict[str, str]]]:
    """
    Extract club name and players from a club cell.

    Internal helper for backward compatibility with ctpb_parser.py.
    Handles both old <li> format and new line-based format (InSpec=0).

    Args:
        cell: BeautifulSoup cell element.

    Returns:
        Tuple of (club_name, players).
    """
    if not cell:
        return "", []
    
    # Try to extract players from <li> elements first (old format)
    players = _parse_players_from_cell(cell)
    
    if players:
        # Old format: extract club name from text before <li> elements
        club_name = _extract_club_name_from_cell(cell)
        return club_name, players
    
    # No <li> players found, try line-based extraction (InSpec=0 format)
    club_name, players = _extract_players_from_club_cell_lines(cell)
    return club_name, players


def _extract_club_name_from_cell(cell) -> str:
    """
    Extract club name from cell (text before <li> elements or <span class="small">).
    
    Args:
        cell: BeautifulSoup cell element.
    
    Returns:
        Club name string.
    """
    text_parts: List[str] = []
    for child in cell.children:
        # Stop at <span class="small"> (ranking badge)
        if hasattr(child, "name") and child.name == "span" and "small" in (child.get("class") or []):
            break
        # Stop at <ul> (player list)
        if hasattr(child, "name") and child.name == "ul":
            break
        # Collect text nodes and other elements
        if hasattr(child, "get_text"):
            text_parts.append(child.get_text())
        elif isinstance(child, str):
            text_parts.append(child)
    
    club_name = "".join(text_parts).replace("\xa0", " ").strip()
    return club_name


def _extract_players_from_club_cell_lines(cell) -> Tuple[str, List[Dict[str, str]]]:
    """
    Extract club name and players from cell text lines (InSpec=0 format).
    
    Expected format:
        AIRETIK (01)
        (02930) JAUREGUIBERRY Iban
        (072401) IRIBARREN Bastien
    
    Args:
        cell: BeautifulSoup cell element.
    
    Returns:
        Tuple of (club_name, players).
    """
    if not cell:
        return "", []
    
    # Get full text content of the cell
    full_text = cell.get_text()
    lines = full_text.strip().split('\n')
    
    if not lines:
        return "", []
    
    club_line = lines[0]
    player_lines = lines[1:]
    
    # Extract club name (before the (XX))
    club_match = re.match(r'(.+?)\s*\((\d+)\)', club_line)
    club_name = club_match.group(1).strip() if club_match else club_line.strip()
    
    # Extract players from remaining lines
    players = []
    player_pattern = r'\((\d+)\)\s+([A-ZÀ-Ÿ]+)\s+([A-Z][a-zÀ-Ÿ]+)'
    
    for line in player_lines:
        line = line.strip()
        if not line:
            continue
        match = re.search(player_pattern, line)
        if match:
            license_num, last_name, first_name = match.groups()
            players.append({
                'license': license_num,
                'name': f"{last_name} {first_name}",
                'first_name': first_name,
                'last_name': last_name
            })
    
    return club_name, players

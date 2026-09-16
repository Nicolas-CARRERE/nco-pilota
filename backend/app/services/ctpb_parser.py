"""
CTPB resultats.php HTML parser.

Parses pelote basque results from CTPB (Comité Territorial Pays Basque)
resultats.php pages into structured game rows.
"""

import re
from typing import Any, Dict, List, Optional, Tuple

from bs4 import BeautifulSoup

from app.services.player_extraction import _parse_club_name_and_players, _parse_players_from_cell
from app.services.championship_parser import parse_championship_name


# -----------------------
# Helper functions
# -----------------------

def _extract_no_renc_from_link(anchor) -> Optional[str]:
    """Extract no_renc from resultats2.php link href."""
    if not anchor or not hasattr(anchor, "get"):
        return None
    href = anchor.get("href") or ""
    match = re.search(r"no_renc=(\d+)", href)
    return match.group(1) if match else None


def _normalize_score(raw: str) -> str:
    """Normalize score string."""
    return (raw or "").replace("\xa0", " ").strip()


def _infer_status(raw_score: str) -> str:
    """Infer game status from raw score."""
    s = (raw_score or "").strip()
    if not s:
        return "unknown"
    if "FG" in s.upper():
        return "forfait"
    if "/P" in s or "P/" in s:
        return "incomplete"
    if re.match(r"^\d+/\d+$", s):
        return "completed"
    return "unknown"


def _extract_season_from_html(soup: BeautifulSoup) -> Dict[str, Any]:
    """Extract season/year/organization info from HTML page header."""
    result: Dict[str, Any] = {}
    
    # Extract organization from page title
    title = soup.find("title")
    if title:
        title_text = title.get_text()
        if "CTPB" in title_text or "Comité Territorial Pays Basque" in title_text:
            result["organization"] = "CTPB"
        elif "FFPB" in title_text:
            result["organization"] = "FFPB"
    
    # Look for "SAISON 2026" or "2025/2026" patterns in the page
    header = soup.find("h1")
    if header:
        text = header.get_text()
        # Pattern: SAISON 2026
        season_match = re.search(r"SAISON\s*(\d{4})", text)
        if season_match:
            year = int(season_match.group(1))
            result["year"] = year
            result["season"] = str(year)
    
    # Look for competition selector with season info (e.g., "Championnat d'Hiver 2025/2026")
    for option in soup.find_all("option", selected=True):
        text = option.get_text()
        # Pattern: 2025/2026
        span_match = re.search(r"(\d{4})/(\d{4})", text)
        if span_match:
            start_year = int(span_match.group(1))
            end_year = int(span_match.group(2))
            result["season"] = f"{start_year}-{end_year}"
            result["year"] = end_year
            break
    
    return result


def _extract_competition_context(soup: BeautifulSoup) -> Dict[str, Any]:
    """Extract competition context from HTML including discipline headers."""
    result: Dict[str, Any] = {}
    
    # Find the competition info row (colspan >= 7 with discipline text)
    table = soup.find("table", class_="mBloc")
    if not table:
        return result
    
    for row in table.find_all("tr"):
        cells = row.find_all("td")
        if not cells:
            continue
        
        first_cell = cells[0]
        colspan = first_cell.get("colspan")
        if colspan and int(colspan) >= 7:
            text = first_cell.get_text(strip=True)
            if text:
                text_lower = text.lower()
                if (
                    "Place Libre" in text
                    or "Chistera" in text
                    or "Main Nue" in text
                    or "trinquet" in text_lower
                    or "mur à gauche" in text_lower
                    or "mur a gauche" in text_lower
                    or "paleta" in text_lower
                ):
                    # Parse the discipline_context using championship parser
                    parsed = parse_championship_name(text)
                    result.update(parsed)
                    result["discipline_context"] = text
                    break
    
    return result


# -----------------------
# Resultats HTML parser
# -----------------------

def parse_resultats_html(html: str) -> List[Dict[str, Any]]:
    """Parse CTPB resultats.php HTML into structured game rows."""
    soup = BeautifulSoup(html, "html.parser")
    games: List[Dict[str, Any]] = []
    
    # Extract season/year from page header
    page_context = _extract_season_from_html(soup)
    
    # Extract competition context (discipline, group, series, pool, etc.)
    competition_context = _extract_competition_context(soup)
    
    table = soup.find("table", class_="mBloc")
    if not table:
        return games

    for row in table.find_all("tr"):
        cells = row.find_all("td")
        if not cells:
            continue

        first_cell = cells[0]
        colspan = first_cell.get("colspan")
        if colspan and int(colspan) >= 7:
            # Skip header rows - context already extracted above
            continue

        if first_cell.get("class") and "mTitreSmall" in first_cell.get("class", []):
            continue

        link_cell = first_cell.find("a", href=re.compile(r"resultats2\.php"))
        no_renc = _extract_no_renc_from_link(link_cell) if link_cell else None
        if not no_renc:
            continue

        if len(cells) < 6:
            continue

        date_cell, club1_cell, club2_cell, score_cell = cells[1:5]
        comment_cell = cells[5] if len(cells) > 5 else None

        date_text = date_cell.get_text(strip=True).replace("\xa0", " ")
        club1_name, club1_players = _parse_club_name_and_players(club1_cell)
        club2_name, club2_players = _parse_club_name_and_players(club2_cell)
        raw_score = _normalize_score(score_cell.get_text())
        comment = _normalize_score(comment_cell.get_text()) if comment_cell else ""

        # Build game record with all granular fields from HTML
        game: Dict[str, Any] = {
            "no_renc": no_renc,
            "date": date_text,
            "club1_name": club1_name,
            "club2_name": club2_name,
            "club1_players": club1_players,
            "club2_players": club2_players,
            "raw_score": raw_score,
            "comment": comment,
            "status": _infer_status(raw_score),
        }
        
        # Add parsed championship fields
        game.update(competition_context)
        
        # Add season/year from page context
        game.update(page_context)

        games.append(game)

    return games
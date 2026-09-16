"""
Engagements scraper for CTPB club player rosters.

Scrapes player license and name data from engagements.php for each club.
"""

import re
import logging
from typing import Dict, List, Optional

import httpx

logger = logging.getLogger("pelota.engagements")


async def scrape_club_engagements(club_name: str) -> List[Dict[str, str]]:
    """
    Scrape player roster for a club from engagements.php.

    Args:
        club_name: Club name (used in URL parameter).

    Returns:
        List of player dicts with 'license', 'first_name', 'last_name' keys.
    """
    url = f"https://ctpb.euskalpilota.fr/engagements.php?club={club_name}"
    
    logger.info("Scraping engagements for club %s: %s", club_name, url)
    
    try:
        # CTPB requires session cookies - first visit main site, then engagements
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            # First hit the main site to establish session
            await client.get('https://ctpb.euskalpilota.fr')
            
            # Now fetch engagements
            response = await client.get(url)
            response.raise_for_status()
            html = response.text
    except httpx.HTTPError as e:
        logger.error("Failed to fetch engagements for club %s: %s", club_name, e)
        return []
    except Exception as e:
        logger.error("Unexpected error scraping club %s: %s", club_name, e)
        return []
    
    players = parse_engagements_html(html)
    logger.info("Found %d players for club %s", len(players), club_name)
    
    return players


def parse_engagements_html(html: str) -> List[Dict[str, str]]:
    """
    Parse player list from engagements HTML.

    Expected HTML format:
        <li> (061721) MENDIBURU Florian </li>
        <li> (12345) DUPONT Jean </li>

    Args:
        html: HTML string containing player list.

    Returns:
        List of player dicts with 'license', 'first_name', 'last_name' keys.
    """
    players: List[Dict[str, str]] = []
    
    # Pattern: (license) LASTNAME Firstname
    # Matches: (061721) MENDIBURU Florian
    pattern = r'\((\d+)\)\s+([A-ZÀ-Ÿ]+)\s+([A-ZÀ-Ÿ][a-zà-ÿ]+)'
    
    matches = re.findall(pattern, html)
    
    for license_num, last_name, first_name in matches:
        players.append({
            'license': license_num,
            'first_name': first_name.strip(),
            'last_name': last_name.strip()
        })
    
    return players


def parse_engagements_html_bs4(html: str) -> List[Dict[str, str]]:
    """
    Parse player list from engagements HTML using BeautifulSoup.

    More robust parsing for complex HTML structures.

    Args:
        html: HTML string containing player list.

    Returns:
        List of player dicts with 'license', 'first_name', 'last_name' keys.
    """
    from bs4 import BeautifulSoup
    
    players: List[Dict[str, str]] = []
    soup = BeautifulSoup(html, "html.parser")
    
    for li in soup.find_all("li"):
        text = li.get_text(strip=True)
        if not text:
            continue
        
        # Try regex pattern
        match = re.search(r'\((\d+)\)\s+([A-ZÀ-Ÿ]+)\s+([A-ZÀ-Ÿ][a-zà-ÿ]+)', text)
        if match:
            license_num, last_name, first_name = match.groups()
            players.append({
                'license': license_num,
                'first_name': first_name.strip(),
                'last_name': last_name.strip()
            })
    
    return players


async def scrape_all_clubs_engagements(club_names: List[str]) -> Dict[str, List[Dict[str, str]]]:
    """
    Scrape engagements for multiple clubs.

    Args:
        club_names: List of club names.

    Returns:
        Dict mapping club_name to list of players.
    """
    all_players: Dict[str, List[Dict[str, str]]] = {}
    
    for club_name in club_names:
        players = await scrape_club_engagements(club_name)
        all_players[club_name] = players
    
    return all_players

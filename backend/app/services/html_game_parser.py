"""HTML competition parser for extracting game data from CTPB HTML fixtures."""

import re
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
from .championship_parser import parse_championship_name


def extract_championship_name(html: str) -> str:
    """Extract championship header text from HTML."""
    soup = BeautifulSoup(html, 'html.parser')
    
    # Look for the competition info block
    # Structure: <td colspan="7">Trinquet/Main Nue - Groupe A<span>1ère Série...</span></td>
    info_cells = soup.find_all('td', colspan='7')
    
    for cell in info_cells:
        # Get all text content from this cell
        text = cell.get_text(separator=' ', strip=True)
        if text and ('Trinquet' in text or 'Place Libre' in text or 'Main Nue' in text or 'Groupe' in text):
            # Clean up the text - normalize whitespace
            text = ' '.join(text.split())
            return text
    
    return ""


def extract_games_from_table(html: str) -> List[Dict]:
    """Extract all games from the results table with proper competition context."""
    soup = BeautifulSoup(html, 'html.parser')
    games = []
    
    # Track current competition context
    current_discipline = ""
    current_series = ""
    current_group = ""
    current_pool = ""
    
    # Find all elements in document order
    for element in soup.find_all(['tr', 'td']):
        # Check for competition header row (7 colspan cells with discipline info)
        if element.name == 'td' and element.get('colspan') == '7':
            text = element.get_text(separator=' ', strip=True)
            # Normalize whitespace
            text = ' '.join(text.split())
            if text and ('Trinquet' in text or 'Place Libre' in text or 'Main Nue' in text or 'Groupe' in text):
                # Parse this header to get context
                current_discipline = ""
                current_series = ""
                current_group = ""
                current_pool = ""
                
                # Extract discipline (first part before span)
                if 'Trinquet/Main Nue' in text:
                    current_discipline = "Trinquet/Main Nue"
                elif 'Place Libre' in text:
                    current_discipline = "Place Libre"
                elif 'Main Nue' in text:
                    current_discipline = "Main Nue"
                
                # Extract series
                for series in ["1ère Série", "2ème Série", "3ème Série", "4ème série", "1.Maila", "2.Maila", "3.Maila", "4.Maila"]:
                    if series in text:
                        current_series = series
                        break
                
                # Extract group
                for group in ["GROUPE A", "GROUPE B", "GROUPE C"]:
                    if group in text:
                        current_group = group
                        break
                
                # Extract pool
                for pool in ["Poule phase 1", "Poule phase 2", "Barrage", "1/8ème de finale", "1/4 de finale", "1/2 finale", "Finale"]:
                    if pool in text:
                        current_pool = pool
                        break
        
        # Check for game row
        if element.name == 'tr':
            cells = element.find_all('td', class_='L0')
            if len(cells) < 5:
                continue
            
            # Extract game number and phase from first cell
            first_cell = cells[0]
            cell_text = first_cell.get_text()
            phase_match = re.search(r'([PBHQDF])\s+(\d+)', cell_text)
            if not phase_match:
                continue
            
            phase_letter = phase_match.group(1)
            game_number = int(phase_match.group(2))
            
            # Extract date from second cell
            date_cell = cells[1]
            date_text = date_cell.get_text(strip=True)
            
            # Extract club 1 from third cell
            club1_cell = cells[2]
            club1_text = club1_cell.get_text(separator=' ', strip=True)
            # Remove the ranking number in parentheses
            club1 = re.sub(r'\s*\(\d+\)\s*$', '', club1_text)
            
            # Check if club1 is a forfait
            club1_forfait = 'forfait' in club1_cell.get('class', [])
            
            # Extract club 2 from fourth cell
            club2_cell = cells[3]
            club2_text = club2_cell.get_text(separator=' ', strip=True)
            club2 = re.sub(r'\s*\(\d+\)\s*$', '', club2_text)
            
            # Check if club2 is a forfait
            club2_forfait = 'forfait' in club2_cell.get('class', [])
            
            # Extract score from fifth cell
            score_cell = cells[4]
            score_text = score_cell.get_text(strip=True)
            
            # Handle special scores like "FG/", "/FG", "40/P", "P/40"
            score_home = None
            score_away = None
            is_forfeit = False
            is_incomplete = False
            
            if '/' in score_text:
                parts = score_text.split('/')
                if len(parts) == 2:
                    home_str, away_str = parts
                    
                    # Check for forfeit (FG = Forfait Gagnant, F = Forfait)
                    if home_str.upper() == 'FG':
                        score_home = 40  # Default winning score
                        score_away = 0
                        is_forfeit = True
                    elif away_str.upper() == 'FG':
                        score_home = 0
                        score_away = 40
                        is_forfeit = True
                    elif home_str.upper() == 'F' or home_str.upper() == 'P':
                        score_home = 0
                        score_away = 40
                        is_incomplete = True
                    elif away_str.upper() == 'F' or away_str.upper() == 'P':
                        score_home = 40
                        score_away = 0
                        is_incomplete = True
                    else:
                        try:
                            score_home = int(home_str)
                            score_away = int(away_str)
                        except ValueError:
                            continue
            
            # Extract comment from sixth cell if present
            comment = ""
            if len(cells) > 5:
                comment_cell = cells[5]
                comment = comment_cell.get_text(strip=True)
            
            game = {
                'game_number': game_number,
                'phase_letter': phase_letter,
                'date': date_text,
                'club1_name': club1.strip(),
                'club2_name': club2.strip(),
                'score_home': score_home,
                'score_away': score_away,
                'is_forfeit': is_forfeit,
                'is_incomplete': is_incomplete,
                'comment': comment,
                'club1_forfait': club1_forfait,
                'club2_forfait': club2_forfait,
                'discipline': current_discipline,
                'series': current_series,
                'group': current_group,
                'pool': current_pool,
            }
            
            games.append(game)
    
    return games


def parse_competition_html(html: str) -> dict:
    """Parse competition HTML to extract all fields."""
    # Extract championship name
    championship_text = extract_championship_name(html)
    
    # Parse it with existing parser
    parsed = parse_championship_name(championship_text)
    
    # Default organization to CTPB if not found in championship text
    if 'organization' not in parsed:
        parsed['organization'] = 'CTPB'
    
    # Extract games from table
    games = extract_games_from_table(html)
    
    # Determine phase mapping
    phase_map = {
        'P': 'Poule',
        'B': 'Barrage',
        'H': '1/8ème de finale',
        'Q': '1/4 de finale',
        'D': '1/2 finale',
        'F': 'Finale',
    }
    
    # Add phase names and organization to games
    for game in games:
        phase_letter = game.get('phase_letter', '')
        game['phase'] = phase_map.get(phase_letter, phase_letter)
        game['organization'] = parsed.get('organization', 'CTPB')
    
    # Extract season from HTML header if not in championship text
    soup = BeautifulSoup(html, 'html.parser')
    if 'season' not in parsed:
        season_match = re.search(r'SAISON\s*(20\d{2})', html)
        if season_match:
            year = season_match.group(1)
            parsed['season'] = year
            parsed['year'] = int(year)
    
    return {
        **parsed,
        'games': games,
        'championship_text': championship_text,
    }


if __name__ == '__main__':
    # Test with the fixture file
    import sys
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
    else:
        filepath = 'tests/fixtures/ctpb/competition_20260104.html'
    
    with open(filepath) as f:
        html = f.read()
    
    result = parse_competition_html(html)
    print('Discipline:', result.get('discipline'))
    print('Group:', result.get('group'))
    print('Series:', result.get('series'))
    print('Pool:', result.get('pool'))
    print('Season:', result.get('season'))
    print('Year:', result.get('year'))
    print('Games:', len(result['games']))
    if result['games']:
        print('First game:', result['games'][0])

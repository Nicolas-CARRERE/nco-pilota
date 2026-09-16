"""Championship name parser."""

import re
from typing import Dict, List, Optional, Set

DISCIPLINE_PATTERNS = [
    r"Place\s*Libre\s*/\s*Chistera\s*Joko\s*Garbi",
    r"Place\s*Libre\s*/\s*Grand\s*Chistera",
    r"Trinquet\s*/\s*Main\s*Nue",
    r"Place\s*Libre", r"Trinquet", r"Main\s*Nue", r"Chistera", r"Joko\s*Garbi",
]

ORGANIZATION_KEYWORDS = ["CTPB", "FFPB", "Comité", "Fédération"]

GROUP_KEYWORDS = ["GROUPE A", "GROUPE B", "GROUPE C", "M19", "M17", "Cadets", "Gazteak"]

POOL_KEYWORDS = ["Poule phase 1", "Poule phase 2", "Poule A", "Finale", "Demi-finale"]

SERIES_KEYWORDS = ["1ère Série", "2ème Série", "1.Maila", "2.Maila"]


def parse_championship_name(name: str) -> Dict[str, Optional[str]]:
    """Parse championship name into structured fields."""
    if not name or not isinstance(name, str):
        return {}
    
    result: Dict[str, Optional[str]] = {}
    normalized = name.strip()
    
    # Organization
    for org in ORGANIZATION_KEYWORDS:
        if org.upper() in normalized.upper():
            result["organization"] = org
            break
    
    # Year/Season
    full_season = re.search(r"\b(20\d{2})-(20\d{2})\b", normalized)
    single_year = re.search(r"\b(20\d{2})\b", normalized)
    if full_season:
        result["season"] = f"{full_season.group(1)}-{full_season.group(2)}"
        result["year"] = int(full_season.group(2))
    elif single_year:
        result["season"] = single_year.group(1)
        result["year"] = int(single_year.group(1))
    
    # Discipline
    for pattern in DISCIPLINE_PATTERNS:
        match = re.search(pattern, normalized, re.IGNORECASE)
        if match:
            result["discipline"] = match.group(0).strip()
            break
    
    # Pool (exact match)
    for pool in sorted(POOL_KEYWORDS, key=len, reverse=True):
        if pool in normalized:
            result["pool"] = pool
            break
    
    # Series
    for series in sorted(SERIES_KEYWORDS, key=len, reverse=True):
        if series in normalized:
            result["series"] = series
            break
    
    # Group - handle concatenated formats like "Groupe A1ère" or "GROUPE A1.Maila"
    for group in sorted(GROUP_KEYWORDS, key=len, reverse=True):
        # Try exact match first
        if group in normalized:
            result["group"] = group
            break
        # Try with word boundary (for space-separated)
        if re.search(rf"\b{re.escape(group)}\b", normalized, re.IGNORECASE):
            result["group"] = group
            break
        # Try without space before next element (e.g., "GROUPE A1ère" or "GROUPE A1.Maila")
        group_pattern = rf"{re.escape(group)}(?=\d|\.|ère|ème)"
        if re.search(group_pattern, normalized, re.IGNORECASE):
            result["group"] = group
            break
    
    return result


def extract_filter_options(names: List[str]) -> Dict[str, List[str]]:
    """Extract distinct filter options."""
    options: Dict[str, Set[str]] = {k: set() for k in ["disciplines", "seasons", "years", "series", "groups", "pools", "organizations"]}
    for name in names:
        parsed = parse_championship_name(name)
        for key in options:
            if parsed.get(key):
                options[key].add(str(parsed[key]))
    return {k: sorted(list(v)) for k, v in options.items()}

"""Pydantic schemas for scraping request/response contract."""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Union
from urllib.parse import urlencode, urlunparse

from pydantic import BaseModel, Field, HttpUrl

CTPB_BASE_URL: str = "https://ctpb.euskalpilota.fr/resultats.php"


def build_resultats_base_url() -> str:
    """Build CTPB resultats.php URL with minimal params for filter discovery."""
    return build_resultats_filters_url(competition_value="")


def build_resultats_filters_url(competition_value: str = "") -> str:
    """Build CTPB resultats.php URL for filter discovery, optionally for one competition.

    When competition_value is set, the server returns InSpec options for that competition.
    Use for fetching specialties per competition.

    Args:
        competition_value: InCompet form value; use "" for default/first page.

    Returns:
        Full URL with query string.
    """
    return urlunparse(
        (
            "https",
            "ctpb.euskalpilota.fr",
            "/resultats.php",
            "",
            urlencode(
                {
                    "InSel": "",
                    "InCompet": competition_value or "",
                    "InSpec": "0",
                    "InVille": "",
                    "InClub": "",
                    "InDate": "",
                    "InDatef": "",
                    "InCat": "0",
                    "InPhase": "0",
                    "InVoir": "Voir les résultats",
                }
            ),
            "",
        )
    )


def build_resultats_url(filters: "CTPBResultatsRequest") -> str:
    """
    Build CTPB resultats.php URL with optional filter params.

    Args:
        filters: CTPBResultatsRequest with optional competition, specialty, etc.

    Returns:
        Full URL with query string.
    """
    params: Dict[str, str] = {
        "InSel": "",
        "InCompet": filters.competition or "",
        "InSpec": filters.specialty or "0",
        "InVille": filters.ville or "",
        "InClub": filters.club or "",
        "InDate": filters.date_from or "",
        "InDatef": filters.date_to or "",
        "InCat": filters.category or "0",
        "InPhase": filters.phase or "0",
        "InVoir": "Voir les résultats",
    }
    query = urlencode(params)
    return urlunparse(("https", "ctpb.euskalpilota.fr", "/resultats.php", "", query, ""))


class ScrapeRunRequest(BaseModel):
    """Request to trigger a scrape for a single source."""

    url: HttpUrl = Field(..., description="Source URL to scrape")
    source_id: Optional[str] = Field(None, description="Optional source identifier for logging")
    timeout_seconds: Optional[float] = Field(None, description="Override default timeout")


class ScrapeRunItem(BaseModel):
    """Single item in a batch scrape request."""

    url: HttpUrl = Field(..., description="Source URL to scrape")
    source_id: Optional[str] = Field(None, description="Optional source identifier")


class ScrapeBatchRequest(BaseModel):
    """Request to trigger batch scrape for multiple sources."""

    urls: List[ScrapeRunItem] = Field(..., description="List of sources to scrape")


class ScrapeError(BaseModel):
    """Structured error from a scrape attempt."""

    url: str = Field(..., description="URL that failed")
    code: str = Field(..., description="Error code: timeout, network, parse, rate_limit, not_found")
    message: str = Field(..., description="Human-readable error message")


class CTPBPlayerRow(BaseModel):
    """Single player in a CTPB game row."""

    id: str = Field(..., description="Player ID or empty for (E)/(S)")
    name: str = Field(..., description="Player name")


class CTPBGameRow(BaseModel):
    """Parsed game row from CTPB resultats.php."""

    no_renc: str = Field(..., description="External game ID from resultats2.php link")
    date: str = Field(..., description="Date dd/mm/yyyy")
    club1_name: str = Field(..., description="Club 1 name")
    club2_name: str = Field(..., description="Club 2 name")
    club1_players: List[CTPBPlayerRow] = Field(default_factory=list)
    club2_players: List[CTPBPlayerRow] = Field(default_factory=list)
    raw_score: str = Field(..., description="Score string e.g. 30/13, FG/, 30/P")
    comment: str = Field(default="")
    status: str = Field(..., description="completed, forfait, incomplete, unknown")
    discipline_context: str = Field(default="")
    phase: Optional[str] = Field(None, description="Competition phase label e.g. Poules, 1/2 finale, Finale")


class CTPBResultatsRequest(BaseModel):
    """Request filters for CTPB resultats.php."""

    competition: Optional[str] = Field(None, description="InCompet e.g. 20240102")
    specialty: Optional[str] = Field(None, description="InSpec e.g. 2, 0=all")
    ville: Optional[str] = Field(None, description="InVille city filter")
    club: Optional[str] = Field(None, description="InClub club ID")
    date_from: Optional[str] = Field(None, description="InDate dd/mm/yyyy")
    date_to: Optional[str] = Field(None, description="InDatef dd/mm/yyyy")
    category: Optional[str] = Field(None, description="InCat e.g. 8, 0=all")
    phase: Optional[str] = Field(None, description="InPhase e.g. 0=all, 1=Poules, 12=Finale")


class ScrapeRunResponse(BaseModel):
    """Response from a scrape run."""

    status: str = Field(..., description="success, partial, or failed")
    raw_content: Optional[dict] = Field(None, description="Scraped JSON payload")
    total_items: Optional[int] = Field(None, description="Number of items found")
    items_with_scores: Optional[int] = Field(None, description="Items that include scores")
    errors: List[ScrapeError] = Field(default_factory=list, description="Errors encountered")
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: Optional[datetime] = None



class CTPBPipelineRequest(BaseModel):
    """Request to run the full CTPB scraping pipeline."""

    already_scraped_urls: List[str] = Field(
        default_factory=list,
        description="URLs already successfully scraped; used for deduplication",
    )
    max_combinations: Optional[int] = Field(
        None,
        description="Safety cap on how many pending combinations to process",
    )
    request_delay_seconds: float = Field(
        default=1.5,
        ge=1.0,
        le=5.0,
        description="Seconds to wait between HTTP requests (1-5). CTPB requires >= 1s.",
    )
    # Optional filters: restrict combinations and/or fix URL params (InCompet, InCat, etc.)
    competition: Optional[str] = Field(None, description="InCompet e.g. 20260104; only this competition")
    category: Optional[str] = Field(None, description="InCat e.g. 7; applied to every URL")
    specialty: Optional[str] = Field(None, description="InSpec; only this specialty per competition")
    phase: Optional[str] = Field(None, description="InPhase; applied to every URL")
    ville: Optional[str] = Field(None, description="InVille; applied to every URL")
    club: Optional[str] = Field(None, description="InClub; applied to every URL")
    date_from: Optional[str] = Field(None, description="InDate dd/mm/yyyy; applied to every URL")
    date_to: Optional[str] = Field(None, description="InDatef dd/mm/yyyy; applied to every URL")


class CTPBPipelineCombinationResult(BaseModel):
    """Scrape result for a single (competition × specialty) combination."""

    url: str = Field(..., description="Canonical CTPB URL that was scraped")
    competition: str = Field(..., description="Competition value (InCompet)")
    specialty: str = Field(..., description="Specialty value (InSpec)")
    status: str = Field(..., description="success or failed")
    games_count: int = Field(..., description="Number of game rows parsed")
    raw_content: Optional[Dict] = Field(
        None, description="Full parsed payload including games list"
    )
    errors: List[ScrapeError] = Field(default_factory=list)


class CTPBPipelineResponse(BaseModel):
    """Response from the full CTPB scraping pipeline."""

    filters_fetched: bool = Field(..., description="Whether live filters were fetched successfully")
    combinations_total: int = Field(..., description="Total competition × specialty combinations")
    combinations_pending: int = Field(..., description="Combinations not yet scraped in this run")
    combinations_scraped: int = Field(..., description="Combinations successfully scraped in this run")
    results: List[CTPBPipelineCombinationResult]


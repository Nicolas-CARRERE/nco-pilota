"""The two schema modules the service uses.

`app/schemas/` held seventeen modules mirroring the Prisma models, and the Node API
owns that database, not this service. Fifteen of them were imported by nothing, and
seven could not be imported at all: six did `from enums import ...` where the module
is `app/schemas/enums.py`, and `game_score.py` used `ScoreEntry` without importing
it. They were removed. What is left is what the scraper's request and response path
uses, and it is imported here on purpose — a schema that cannot be imported is not a
schema, and nothing was catching that.
"""

import pytest
from pydantic import ValidationError

from app.schemas.ffpb import (
    FFPB_BASE_URL,
    FFPBFiltersResponse,
    FFPBGameRow,
    FFPBResultatsRequest,
)
from app.schemas.scraping import (
    CTPBGameRow,
    ScrapeError,
    ScrapeRunResponse,
    build_resultats_filters_url,
)


def test_ffpb_request_takes_its_filters_as_optional():
    """Every FFPB filter is optional: the form can be sent empty."""
    assert FFPBResultatsRequest().year is None
    assert FFPBResultatsRequest(year="2026", competition_type="Championnat").year == "2026"


def test_ffpb_game_row_needs_a_date_and_defaults_the_rest():
    """The date is the one field a normalized FFPB row cannot be built without."""
    row = FFPBGameRow(date="15/03/2026 à 14:00")
    assert row.status == "unknown"
    assert row.team1_player_ids == []
    with pytest.raises(ValidationError):
        FFPBGameRow()


def test_ffpb_filters_response_starts_empty():
    """No options yet, and no error: what the form gets before anything is scraped."""
    response = FFPBFiltersResponse()
    assert response.years == []
    assert response.error is None
    assert FFPB_BASE_URL.startswith("https://")


def test_ctpb_game_row_uses_the_names_the_parser_emits():
    """club1_name and club2_name: the same keys the HTML parser produces."""
    row = CTPBGameRow(
        no_renc="151699",
        date="04/10/2025",
        club1_name="AIRETIK",
        club2_name="URRUNARRAK",
        raw_score="31/40",
        status="completed",
    )
    assert row.club1_players == []
    assert row.phase is None


def test_the_filters_url_carries_the_competition_it_was_given():
    """The competition value is what the server reads to return its specialties."""
    url = build_resultats_filters_url("20260104")
    assert url.startswith("https://ctpb.euskalpilota.fr/resultats.php?")
    assert "InCompet=20260104" in url
    assert "InVoir=Voir+les+r%C3%A9sultats" in url


def test_a_scrape_error_is_carried_in_the_response():
    """A failed scrape reports which URL failed and why, not just that it failed."""
    error = ScrapeError(url="https://example.test/x", code="timeout", message="timed out")
    response = ScrapeRunResponse(status="failed", errors=[error])
    assert response.errors[0].code == "timeout"
    assert response.raw_content is None

"""Scraper and database configuration."""

import os
from dataclasses import dataclass
from functools import lru_cache

# The two names the codebase reads for the database URL, in the order it reads them.
# Spelled out once so the error below can name both, and so a caller looking for the
# convention finds it in one place.
DATABASE_URL_VARIABLES = ("DATABASE_URL", "PELOTA_POSTGRES_DATABASE_URL")


@dataclass(frozen=True)
class ScraperSettings:
    """Scraper timeouts, retries and rate limiting.

    Deliberately no database URL: the scraper service opens no connection, and
    carrying one here is what let a local default stand in for a real database.
    The ingestion path asks for its URL separately, with get_database_url().
    """

    timeout_seconds: float
    max_retries: int
    retry_backoff_factor: float

    # Rate limiting (DEV/TEST ONLY - respect robots.txt)
    ctpb_request_delay_min: float = 5.0
    ctpb_request_delay_max: float = 10.0
    ctpb_max_combinations_per_run: int = 5
    ctpb_rate_limit_per_minute: int = 10
    ctpb_dev_mode: bool = True


@lru_cache
def get_settings() -> ScraperSettings:
    """Return cached scraper settings."""
    return ScraperSettings(
        timeout_seconds=float(os.getenv("PELOTA_SCRAPER_HTTP_TIMEOUT_SECONDS", "30.0")),
        max_retries=int(os.getenv("PELOTA_SCRAPER_MAX_RETRY_ATTEMPTS", "3")),
        retry_backoff_factor=float(os.getenv("PELOTA_SCRAPER_RETRY_BACKOFF_FACTOR", "1.5")),
        ctpb_request_delay_min=float(os.getenv("CTPB_REQUEST_DELAY_MIN_SECONDS", "5.0")),
        ctpb_request_delay_max=float(os.getenv("CTPB_REQUEST_DELAY_MAX_SECONDS", "10.0")),
        ctpb_max_combinations_per_run=int(os.getenv("CTPB_MAX_COMBINATIONS_PER_RUN", "5")),
        ctpb_rate_limit_per_minute=int(os.getenv("CTPB_RATE_LIMIT_PER_MINUTE", "10")),
        ctpb_dev_mode=os.getenv("CTPB_DEV_MODE", "true").lower() == "true",
    )


def get_database_url() -> str:
    """Return the PostgreSQL URL the ingestion path writes to.

    Raises instead of falling back to a local default. A default that looks real is
    how a script comes to write to a database nobody chose — and it puts a password
    in the source, where it is committed. A caller that needs a connection has to be
    told where to open it.
    """
    for name in DATABASE_URL_VARIABLES:
        value = os.getenv(name)
        if value:
            return value
    raise RuntimeError(
        "No database URL: set "
        + " or ".join(DATABASE_URL_VARIABLES)
        + " before running an ingestion. See backend/.env.example."
    )

"""Scraper and database configuration."""

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class ScraperSettings:
    """Scraper timeout, retries, and base URLs."""

    timeout_seconds: float
    max_retries: int
    retry_backoff_factor: float
    database_url: str
    
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
        database_url=os.getenv("DATABASE_URL") or os.getenv("PELOTA_POSTGRES_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/pilota"),
        ctpb_request_delay_min=float(os.getenv("CTPB_REQUEST_DELAY_MIN_SECONDS", "5.0")),
        ctpb_request_delay_max=float(os.getenv("CTPB_REQUEST_DELAY_MAX_SECONDS", "10.0")),
        ctpb_max_combinations_per_run=int(os.getenv("CTPB_MAX_COMBINATIONS_PER_RUN", "5")),
        ctpb_rate_limit_per_minute=int(os.getenv("CTPB_RATE_LIMIT_PER_MINUTE", "10")),
        ctpb_dev_mode=os.getenv("CTPB_DEV_MODE", "true").lower() == "true",
    )

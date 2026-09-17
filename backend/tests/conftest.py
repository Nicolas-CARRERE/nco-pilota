"""Pytest configuration and fixtures."""

import pytest

# No password: nothing in the suite connects, this only has to be a well-formed URL
# for a service that would otherwise have none.
TEST_DATABASE_URL = "postgresql://pilota@localhost:5432/pilota"


def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as an asyncio test."
    )


@pytest.fixture
def database_url() -> str:
    """A URL for the tests that build an IngestionService without connecting.

    Explicit because the service no longer falls back to a local default — a test
    that builds one has to say which database it would talk to.
    """
    return TEST_DATABASE_URL

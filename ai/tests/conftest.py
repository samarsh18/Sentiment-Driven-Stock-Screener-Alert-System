"""
ai/tests/conftest.py
---------------------
Shared pytest fixtures for the AI subsystem tests.
"""
from datetime import datetime, timezone

import pytest

from ai.schemas import NewsInput


@pytest.fixture
def sample_news() -> NewsInput:
    """Provide a deterministic sample NewsInput for AI subsystem unit tests."""
    return NewsInput(
        news_id="ACME-2024-001",
        symbol="ACME",
        company_name="Acme Corp",
        title="Acme reports quarterly financial results",
        content="Acme Corp announced its Q3 financial results today.",
        source="MockFinance",
        url="https://example.com/acme/q3",
        published_at=datetime(2024, 4, 25, 12, 0, 0, tzinfo=timezone.utc),
    )

"""
backend/app/providers/mock.py
------------------------------
MockNewsProvider — a deterministic, in-memory news provider for
development, testing, and integration demos.

This provider never makes network calls.  All data is hard-coded and
intentionally varied (positive, negative, neutral) to allow downstream
sentiment and decision-engine components to be exercised realistically.

Usage:
    from backend.app.providers.mock import MockNewsProvider

    provider = MockNewsProvider()
    items = provider.fetch_news("AAPL", "Apple Inc.", limit=5)
"""

from datetime import datetime, timezone

from backend.app.models.news import NewsItem
from backend.app.providers.base import NewsProvider

# ---------------------------------------------------------------------------
# Static mock corpus
# Each entry is a template dict; symbol / company_name are injected at
# fetch time so a single corpus works for any requested ticker.
# ---------------------------------------------------------------------------

_MOCK_CORPUS: list[dict] = [
    # --- Positive -----------------------------------------------------------
    {
        "news_id_suffix": "q-beat-001",
        "title": "{company} beats quarterly earnings expectations",
        "content": (
            "{company} reported earnings per share of $3.42, surpassing "
            "analyst consensus of $3.18. Revenue rose 12 % year-over-year "
            "to $94.8 billion, driven by strong services growth."
        ),
        "source": "MockFinancialTimes",
        "url": "https://mock-news.example.com/{symbol}/earnings-beat",
        "published_at": "2024-04-25T13:30:00+00:00",
    },
    {
        "news_id_suffix": "upgrade-002",
        "title": "Analyst upgrades {company} to Strong Buy",
        "content": (
            "Morgan Stanley upgraded {company} ({symbol}) from Neutral to "
            "Strong Buy, raising the 12-month price target from $180 to "
            "$210. The firm cited margin expansion and accelerating "
            "international revenue as key catalysts."
        ),
        "source": "MockStreetResearch",
        "url": "https://mock-news.example.com/{symbol}/analyst-upgrade",
        "published_at": "2024-04-22T09:15:00+00:00",
    },
    {
        "news_id_suffix": "buyback-003",
        "title": "{company} announces $90 billion share buyback programme",
        "content": (
            "{company} ({symbol}) announced a record $90 billion share "
            "repurchase authorisation, sending shares up 4 % in after-hours "
            "trading. The board also raised the quarterly dividend by 5 %."
        ),
        "source": "MockMarketWatch",
        "url": "https://mock-news.example.com/{symbol}/buyback",
        "published_at": "2024-04-20T16:00:00+00:00",
    },
    {
        "news_id_suffix": "product-launch-004",
        "title": "{company} unveils next-generation product line",
        "content": (
            "At its annual developer conference, {company} unveiled a "
            "next-generation hardware and software ecosystem. Pre-orders "
            "opened immediately, with the company reporting record "
            "first-day reservations."
        ),
        "source": "MockTechCrunch",
        "url": "https://mock-news.example.com/{symbol}/product-launch",
        "published_at": "2024-04-18T18:00:00+00:00",
    },
    # --- Negative -----------------------------------------------------------
    {
        "news_id_suffix": "miss-005",
        "title": "{company} misses revenue guidance for Q2",
        "content": (
            "{company} ({symbol}) reported Q2 revenue of $81.5 billion, "
            "falling short of the $83.9 billion consensus. Management "
            "cited macroeconomic headwinds and supply chain disruptions "
            "as primary factors. Shares fell 6 % in after-hours trading."
        ),
        "source": "MockFinancialTimes",
        "url": "https://mock-news.example.com/{symbol}/revenue-miss",
        "published_at": "2024-04-15T20:45:00+00:00",
    },
    {
        "news_id_suffix": "downgrade-006",
        "title": "Goldman downgrades {company} on slowing growth concerns",
        "content": (
            "Goldman Sachs downgraded {company} ({symbol}) from Buy to "
            "Neutral, trimming its price target from $195 to $170. "
            "Analysts flagged decelerating unit sales in key markets and "
            "rising competitive pressure."
        ),
        "source": "MockStreetResearch",
        "url": "https://mock-news.example.com/{symbol}/analyst-downgrade",
        "published_at": "2024-04-12T11:00:00+00:00",
    },
    {
        "news_id_suffix": "lawsuit-007",
        "title": "{company} faces antitrust investigation in EU",
        "content": (
            "The European Commission announced a formal antitrust "
            "investigation into {company} ({symbol}) over alleged "
            "anti-competitive practices in its app distribution platform. "
            "Legal analysts estimate potential fines of up to $5 billion."
        ),
        "source": "MockReutersWire",
        "url": "https://mock-news.example.com/{symbol}/eu-antitrust",
        "published_at": "2024-04-10T08:30:00+00:00",
    },
    {
        "news_id_suffix": "recall-008",
        "title": "{company} recalls 1.2 million units over safety defect",
        "content": (
            "{company} ({symbol}) issued a voluntary recall of 1.2 million "
            "units following reports of a battery safety defect. The company "
            "said replacement units would be shipped within 30 days. "
            "Analysts estimate the recall will cost approximately $800 million."
        ),
        "source": "MockMarketWatch",
        "url": "https://mock-news.example.com/{symbol}/product-recall",
        "published_at": "2024-04-08T14:20:00+00:00",
    },
    # --- Neutral ------------------------------------------------------------
    {
        "news_id_suffix": "agm-009",
        "title": "{company} holds annual general meeting",
        "content": (
            "{company} ({symbol}) held its annual general meeting today. "
            "Shareholders re-elected the full board and approved the "
            "executive compensation plan. No major strategic announcements "
            "were made."
        ),
        "source": "MockReutersWire",
        "url": "https://mock-news.example.com/{symbol}/agm",
        "published_at": "2024-04-05T10:00:00+00:00",
    },
    {
        "news_id_suffix": "exec-move-010",
        "title": "{company} CFO to retire; successor named",
        "content": (
            "{company} ({symbol}) announced that its Chief Financial Officer "
            "will retire at the end of the fiscal year. The board has named "
            "the current VP of Finance as successor. Analysts described the "
            "transition as orderly and unsurprising."
        ),
        "source": "MockFinancialTimes",
        "url": "https://mock-news.example.com/{symbol}/cfo-transition",
        "published_at": "2024-04-03T09:00:00+00:00",
    },
    {
        "news_id_suffix": "conf-011",
        "title": "{company} to present at industry technology summit",
        "content": (
            "{company} ({symbol}) confirmed it will present at the Global "
            "Technology Summit next month. The company plans to discuss "
            "its sustainability roadmap and supply chain initiatives. "
            "No product announcements are expected."
        ),
        "source": "MockTechCrunch",
        "url": "https://mock-news.example.com/{symbol}/summit-presentation",
        "published_at": "2024-04-01T07:30:00+00:00",
    },
    {
        "news_id_suffix": "reg-filing-012",
        "title": "{company} files annual 10-K report with SEC",
        "content": (
            "{company} ({symbol}) filed its annual 10-K report with the "
            "Securities and Exchange Commission. The filing disclosed no "
            "material changes from previously reported figures. "
            "Full documents are available on the SEC EDGAR database."
        ),
        "source": "MockSECWire",
        "url": "https://mock-news.example.com/{symbol}/10k-filing",
        "published_at": "2024-03-29T17:00:00+00:00",
    },
]


def _render(template: str, symbol: str, company: str) -> str:
    """Substitute {symbol} and {company} placeholders in a template string."""
    return template.replace("{symbol}", symbol).replace("{company}", company)


class MockNewsProvider(NewsProvider):
    """
    Deterministic in-memory news provider for testing and development.

    Returns a fixed corpus of realistic financial news items.
    No network calls are made.  Results are stable across runs.
    """

    def fetch_news(
        self,
        symbol: str,
        company_name: str,
        limit: int = 20,
    ) -> list[NewsItem]:
        """
        Return mock NewsItem objects for the requested symbol.

        Parameters
        ----------
        symbol : str
            Stock ticker (will be normalised to uppercase via NewsItem).
        company_name : str
            Company display name used to populate mock content.
        limit : int, optional
            Maximum number of items to return.  Defaults to 20.

        Returns
        -------
        list[NewsItem]
            Up to `limit` NewsItem objects, most recent first.
        """
        clean_symbol = symbol.strip().upper()
        clean_company = company_name.strip()

        items: list[NewsItem] = []
        for entry in _MOCK_CORPUS[:limit]:
            news_id = f"{clean_symbol}-{entry['news_id_suffix']}"
            item = NewsItem(
                news_id=news_id,
                symbol=clean_symbol,
                company_name=clean_company,
                title=_render(entry["title"], clean_symbol, clean_company),
                content=_render(entry["content"], clean_symbol, clean_company),
                source=entry["source"],
                url=_render(entry["url"], clean_symbol, clean_company),
                published_at=entry["published_at"],
            )
            items.append(item)

        return items

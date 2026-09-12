"""
backend/app/providers/base.py
-----------------------------
Abstract base class defining the NewsProvider interface.

Any concrete provider (GDELT, mock, future APIs) must subclass
NewsProvider and implement fetch_news().

Design principles:
- Zero coupling to FastAPI, database, or AI components.
- Zero network calls in this module.
- The contract is defined entirely through Python typing and ABC.

Usage:
    class MyProvider(NewsProvider):
        def fetch_news(
            self,
            symbol: str,
            company_name: str,
            limit: int = 20,
        ) -> list[NewsItem]:
            ...
"""

from abc import ABC, abstractmethod

from backend.app.models.news import NewsItem


class NewsProvider(ABC):
    """
    Abstract interface for financial news providers.

    Implementors must override fetch_news().  No other method is
    required — providers are free to add private helpers as needed.
    """

    @abstractmethod
    def fetch_news(
        self,
        symbol: str,
        company_name: str,
        limit: int = 20,
    ) -> list[NewsItem]:
        """
        Fetch recent financial news items for a stock symbol.

        Parameters
        ----------
        symbol : str
            Stock ticker symbol (e.g. "AAPL").  Implementations must
            normalise to uppercase before forwarding to any external
            service; the NewsItem validator will enforce uppercase on
            the returned objects.
        company_name : str
            Human-readable company name (e.g. "Apple Inc.").  Used
            to populate the company_name field on each NewsItem and
            optionally to refine provider queries.
        limit : int, optional
            Maximum number of NewsItem objects to return.
            Defaults to 20.  Implementations should respect this
            value but may return fewer items when fewer are available.

        Returns
        -------
        list[NewsItem]
            A list of validated NewsItem objects, ordered from most
            recent to oldest where possible.  Returns an empty list
            when no results are found.
        """
        ...  # pragma: no cover

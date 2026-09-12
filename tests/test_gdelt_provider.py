"""
tests/test_gdelt_provider.py
-----------------------------
Unit tests for GDELTNewsProvider.

Uses httpx.MockTransport so NO real network calls are made.
"""

import hashlib

from datetime import datetime, timezone

import httpx
import pytest

from backend.app.models.news import NewsItem
from backend.app.providers.base import NewsProvider
from backend.app.providers.gdelt import GDELTNewsProvider, parse_gdelt_date


def make_mock_client(handler_fn) -> httpx.Client:
    transport = httpx.MockTransport(handler_fn)
    return httpx.Client(transport=transport)


def sample_gdelt_payload():
    return {
        "articles": [
            {
                "url": "https://example.com/article1",
                "title": "Apple Inc. reports strong revenue",
                "snippet": "Apple Inc. reported quarterly revenue of $90B...",
                "domain": "finance.example.com",
                "seendate": "20240425133000",
            },
            {
                "url": "https://example.com/article2",
                "title": "Apple unveils new AI features",
                "content": "Tech giant Apple announced major updates...",
                "source": "tech.example.com",
                "seendate": "20240422T091500Z",
            },
        ]
    }


class TestGDELTProviderBasics:
    def test_is_news_provider_subclass(self):
        assert issubclass(GDELTNewsProvider, NewsProvider)

    def test_instance_is_news_provider(self):
        provider = GDELTNewsProvider()
        assert isinstance(provider, NewsProvider)


class TestGDELTFetchSuccess:
    def test_successful_response_becomes_news_items(self):
        payload = sample_gdelt_payload()

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=payload)

        client = make_mock_client(handler)
        provider = GDELTNewsProvider(client=client)

        items = provider.fetch_news("AAPL", "Apple Inc.", limit=10)

        assert isinstance(items, list)
        assert len(items) == 2
        assert all(isinstance(item, NewsItem) for item in items)

    def test_query_parameters_sent(self):
        captured_params = {}

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal captured_params
            captured_params = dict(request.url.params)
            return httpx.Response(200, json=sample_gdelt_payload())

        client = make_mock_client(handler)
        provider = GDELTNewsProvider(client=client)

        provider.fetch_news("aapl", "Apple Inc.", limit=5)

        assert captured_params.get("query") == '"Apple Inc." OR "AAPL"'
        assert captured_params.get("mode") == "artlist"
        assert captured_params.get("maxrecords") == "5"
        assert captured_params.get("format") == "json"

    def test_maxrecords_respects_limit(self):
        captured_params = {}

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal captured_params
            captured_params = dict(request.url.params)
            return httpx.Response(200, json=sample_gdelt_payload())

        client = make_mock_client(handler)
        provider = GDELTNewsProvider(client=client)

        provider.fetch_news("AAPL", "Apple Inc.", limit=15)
        assert captured_params.get("maxrecords") == "15"

    def test_maxrecords_capped_at_250(self):
        captured_params = {}

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal captured_params
            captured_params = dict(request.url.params)
            return httpx.Response(200, json=sample_gdelt_payload())

        client = make_mock_client(handler)
        provider = GDELTNewsProvider(client=client)

        provider.fetch_news("AAPL", "Apple Inc.", limit=500)
        assert captured_params.get("maxrecords") == "250"

    def test_limit_zero_returns_empty_list_without_network_request(self):
        requested = False

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal requested
            requested = True
            return httpx.Response(200, json=sample_gdelt_payload())

        client = make_mock_client(handler)
        provider = GDELTNewsProvider(client=client)

        items = provider.fetch_news("AAPL", "Apple Inc.", limit=0)
        assert items == []
        assert requested is False

    def test_negative_limit_returns_empty_list(self):
        provider = GDELTNewsProvider()
        items = provider.fetch_news("AAPL", "Apple Inc.", limit=-5)
        assert items == []

    def test_post_response_limit_enforced(self):
        payload = {
            "articles": [
                {
                    "url": f"https://example.com/article{i}",
                    "title": f"Title {i}",
                    "seendate": "20240425133000",
                }
                for i in range(5)
            ]
        }

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=payload)

        client = make_mock_client(handler)
        provider = GDELTNewsProvider(client=client)

        items = provider.fetch_news("AAPL", "Apple Inc.", limit=2)
        assert len(items) == 2


class TestGDELTFieldMapping:
    def test_symbol_normalized_to_uppercase(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=sample_gdelt_payload())

        client = make_mock_client(handler)
        provider = GDELTNewsProvider(client=client)

        items = provider.fetch_news("msft", "Microsoft Corporation")
        assert len(items) == 2
        for item in items:
            assert item.symbol == "MSFT"

    def test_fields_populated_correctly(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=sample_gdelt_payload())

        client = make_mock_client(handler)
        provider = GDELTNewsProvider(client=client)

        items = provider.fetch_news("AAPL", "Apple Inc.", limit=2)
        item1, item2 = items[0], items[1]

        assert item1.company_name == "Apple Inc."
        assert item1.title == "Apple Inc. reports strong revenue"
        assert item1.content == "Apple Inc. reported quarterly revenue of $90B..."
        assert item1.source == "finance.example.com"
        assert item1.url == "https://example.com/article1"
        assert item1.published_at == datetime(2024, 4, 25, 13, 30, 0, tzinfo=timezone.utc)

        assert item2.company_name == "Apple Inc."
        assert item2.title == "Apple unveils new AI features"
        assert item2.content == "Tech giant Apple announced major updates..."
        assert item2.source == "tech.example.com"
        assert item2.url == "https://example.com/article2"
        assert item2.published_at == datetime(2024, 4, 22, 9, 15, 0, tzinfo=timezone.utc)

    def test_date_parsing_formats(self):
        dt1 = parse_gdelt_date("20240425133000")
        assert dt1 == datetime(2024, 4, 25, 13, 30, 0, tzinfo=timezone.utc)

        dt2 = parse_gdelt_date("20240425T133000Z")
        assert dt2 == datetime(2024, 4, 25, 13, 30, 0, tzinfo=timezone.utc)

        dt3 = parse_gdelt_date("2024-04-25T13:30:00+00:00")
        assert dt3 == datetime(2024, 4, 25, 13, 30, 0, tzinfo=timezone.utc)

        # Timezone offset (+05:30) converted to UTC
        dt4 = parse_gdelt_date("2024-04-25T19:00:00+05:30")
        assert dt4 == datetime(2024, 4, 25, 13, 30, 0, tzinfo=timezone.utc)

        with pytest.raises(ValueError):
            parse_gdelt_date("invalid-date")

    def test_news_id_deterministic_and_unique(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=sample_gdelt_payload())

        client = make_mock_client(handler)
        provider = GDELTNewsProvider(client=client)

        items1 = provider.fetch_news("AAPL", "Apple Inc.", limit=2)
        items2 = provider.fetch_news("AAPL", "Apple Inc.", limit=2)

        # Same URL produces same news_id across calls
        assert items1[0].news_id == items2[0].news_id
        url_hash = hashlib.sha256(b"https://example.com/article1").hexdigest()[:16]
        assert items1[0].news_id == f"GDELT-{url_hash}"

        # Different URLs produce unique news_ids
        assert items1[0].news_id != items1[1].news_id


class TestGDELTResilience:
    def test_skips_malformed_individual_article(self):
        payload = {
            "articles": [
                {
                    "url": "https://example.com/valid",
                    "title": "Valid Headline",
                    "seendate": "20240425133000",
                },
                {
                    # Missing URL
                    "title": "Invalid Headline No URL",
                    "seendate": "20240425133000",
                },
                {
                    "url": "https://example.com/invalid-date",
                    "title": "Invalid Date Headline",
                    "seendate": "NOT_A_DATE",
                },
                {
                    "url": "https://example.com/empty-title",
                    "title": "   ",
                    "seendate": "20240425133000",
                },
            ]
        }

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=payload)

        client = make_mock_client(handler)
        provider = GDELTNewsProvider(client=client)

        items = provider.fetch_news("AAPL", "Apple Inc.")
        assert len(items) == 1
        assert items[0].url == "https://example.com/valid"

    def test_malformed_json_returns_empty_list(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, text="NOT VALID JSON {{{")

        client = make_mock_client(handler)
        provider = GDELTNewsProvider(client=client)

        items = provider.fetch_news("AAPL", "Apple Inc.")
        assert items == []

    def test_http_500_returns_empty_list(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, text="Internal Server Error")

        client = make_mock_client(handler)
        provider = GDELTNewsProvider(client=client)

        items = provider.fetch_news("AAPL", "Apple Inc.")
        assert items == []

    def test_timeout_returns_empty_list(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.TimeoutException("Connection timed out")

        client = make_mock_client(handler)
        provider = GDELTNewsProvider(client=client)

        items = provider.fetch_news("AAPL", "Apple Inc.")
        assert items == []

    def test_network_failure_returns_empty_list(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("Failed to connect")

        client = make_mock_client(handler)
        provider = GDELTNewsProvider(client=client)

        items = provider.fetch_news("AAPL", "Apple Inc.")
        assert items == []

    def test_returned_news_items_pass_validation(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=sample_gdelt_payload())

        client = make_mock_client(handler)
        provider = GDELTNewsProvider(client=client)

        items = provider.fetch_news("AAPL", "Apple Inc.")
        for item in items:
            d = item.model_dump()
            reconstructed = NewsItem(**d)
            assert reconstructed.news_id == item.news_id

    def test_user_agent_header_sent(self):
        captured_headers = {}

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal captured_headers
            captured_headers = dict(request.headers)
            return httpx.Response(200, json=sample_gdelt_payload())

        client = make_mock_client(handler)
        provider = GDELTNewsProvider(client=client, user_agent="CustomUserAgent/1.0", min_request_interval=0.0)

        provider.fetch_news("AAPL", "Apple Inc.")
        assert "user-agent" in captured_headers
        assert captured_headers["user-agent"] == "CustomUserAgent/1.0"

    def test_http_429_rate_limit_retry_and_success(self):
        call_count = 0
        slept_times = []

        def mock_sleep(duration: float):
            slept_times.append(duration)

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return httpx.Response(429, headers={"Retry-After": "2"})
            return httpx.Response(200, json=sample_gdelt_payload())

        client = make_mock_client(handler)
        provider = GDELTNewsProvider(
            client=client,
            max_retries=3,
            min_request_interval=0.0,
            sleep_fn=mock_sleep,
        )

        items = provider.fetch_news("AAPL", "Apple Inc.")
        assert len(items) == 2
        assert call_count == 2
        assert slept_times == [2.0]

    def test_http_429_retries_exhausted_returns_empty_list(self):
        call_count = 0
        slept_times = []

        def mock_sleep(duration: float):
            slept_times.append(duration)

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            return httpx.Response(429)

        client = make_mock_client(handler)
        provider = GDELTNewsProvider(
            client=client,
            max_retries=3,
            min_request_interval=0.0,
            sleep_fn=mock_sleep,
        )

        items = provider.fetch_news("AAPL", "Apple Inc.")
        assert items == []
        assert call_count == 3
        assert len(slept_times) == 2
        assert slept_times == [5.0, 10.0]
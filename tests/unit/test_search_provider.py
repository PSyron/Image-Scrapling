from pathlib import Path

import pytest

from svg_scrapling.search import (
    CandidatePage,
    DuckDuckGoHtmlSearchProvider,
    FakeSearchProvider,
    build_search_intent,
    parse_duckduckgo_results,
)


class FixtureSearchTransport:
    def __init__(self, html: str):
        self.html = html
        self.calls: list[str] = []

    def fetch_text(
        self,
        url: str,
        *,
        timeout_seconds: float,
        headers: dict[str, str],
    ) -> str:
        _ = timeout_seconds
        _ = headers
        self.calls.append(url)
        return self.html


def test_candidate_page_normalizes_domain_from_url() -> None:
    page = CandidatePage(
        url="https://example.com/results?q=tiger",
        query="tiger coloring page",
        provider_name="fake-provider",
        rank=1,
    )

    assert page.domain == "example.com"


def test_candidate_page_rejects_non_absolute_urls() -> None:
    with pytest.raises(ValueError, match="url must be an absolute URL"):
        CandidatePage(
            url="/relative/path",
            query="tiger coloring page",
            provider_name="fake-provider",
            rank=1,
        )


def test_fake_search_provider_returns_query_matches_in_rank_order() -> None:
    intent = build_search_intent(
        query="tiger coloring page",
        requested_count=10,
    )
    provider = FakeSearchProvider(
        name="fake-provider",
        pages=(
            CandidatePage(
                url="https://example.com/2",
                query="tiger coloring page outline",
                provider_name="fake-provider",
                rank=2,
            ),
            CandidatePage(
                url="https://example.com/1",
                query="tiger coloring page",
                provider_name="fake-provider",
                rank=1,
            ),
        ),
    )

    pages = provider.search(intent)

    assert [page.rank for page in pages] == [1, 2]
    assert [page.url for page in pages] == [
        "https://example.com/1",
        "https://example.com/2",
    ]


def test_fake_search_provider_falls_back_to_all_pages_if_no_match() -> None:
    intent = build_search_intent(
        query="dinosaur coloring page",
        requested_count=5,
    )
    provider = FakeSearchProvider(
        name="fake-provider",
        pages=(
            CandidatePage(
                url="https://example.com/fallback",
                query="other query",
                provider_name="fake-provider",
                rank=1,
            ),
        ),
    )

    pages = provider.search(intent)

    assert len(pages) == 1
    assert pages[0].url == "https://example.com/fallback"


def test_parse_duckduckgo_results_decodes_redirects_and_deduplicates() -> None:
    html = Path("tests/fixtures/search/duckduckgo_results.html").read_text(encoding="utf-8")

    pages = parse_duckduckgo_results(
        html,
        query="tiger coloring page",
        provider_name="duckduckgo_html",
    )

    assert [page.url for page in pages] == [
        "https://example.com/tiger-outline",
        "https://animals.example.org/tiger-coloring",
    ]
    assert pages[0].title == "Tiger outline printable SVG"
    assert pages[0].snippet == "Free tiger coloring page outline for kids."


def test_duckduckgo_provider_stops_after_requested_count() -> None:
    html = Path("tests/fixtures/search/duckduckgo_results.html").read_text(encoding="utf-8")
    intent = build_search_intent(
        query="tiger coloring page",
        requested_count=1,
    )
    transport = FixtureSearchTransport(html)
    provider = DuckDuckGoHtmlSearchProvider(
        transport=transport,
        max_queries_per_search=3,
    )

    pages = provider.search(intent)

    assert len(pages) == 1
    assert pages[0].url == "https://example.com/tiger-outline"
    assert len(transport.calls) == 1

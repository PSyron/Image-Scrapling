import pytest

from svg_scrapling.search import (
    CandidatePage,
    FakeSearchProvider,
    build_search_intent,
)


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

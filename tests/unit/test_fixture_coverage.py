from __future__ import annotations

import json
from pathlib import Path

from svg_scrapling.domain import AssetFormat, SearchIntent, SearchQuery
from svg_scrapling.extraction import ExtractedAssetHint, ExtractionInput, GenericAssetExtractor
from svg_scrapling.scraping import FetchRequest, StaticHtmlFetcher
from svg_scrapling.search import CandidatePage, FakeSearchProvider


class FixtureTransport:
    def __init__(self, html: str):
        self.html = html

    def fetch(self, url: str, timeout_seconds: float, headers: dict[str, str]):
        _ = timeout_seconds
        _ = headers
        return 200, self.html, {"content-type": "text/html"}, url


def test_search_fixture_covers_candidate_page_contract() -> None:
    fixture_path = Path("tests/fixtures/search/candidate_pages.json")
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    pages = tuple(CandidatePage(**page) for page in payload)
    provider = FakeSearchProvider(name="fixture-provider", pages=pages)
    intent = SearchIntent(
        search_query=SearchQuery(query="tiger coloring page", requested_count=5),
        expanded_queries=("tiger coloring page",),
        preferred_format=AssetFormat.SVG,
    )

    result = provider.search(intent)

    assert len(result) == 1
    assert result[0].title == "Tiger coloring pages"


def test_fetch_fixture_parses_static_html() -> None:
    fixture_path = Path("tests/fixtures/fetch/static_page.html")
    html = fixture_path.read_text(encoding="utf-8")
    fetcher = StaticHtmlFetcher(transport=FixtureTransport(html))

    response = fetcher.fetch(FetchRequest(url="https://example.com/page"))

    assert response.document.css("img").get() is not None
    assert response.document.css("title").get() == "<title>Tiger Coloring Page</title>"


def test_extraction_fixture_covers_generic_extractor_flow() -> None:
    fixture_path = Path("tests/fixtures/extraction/source_page.json")
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    extraction_input = ExtractionInput(
        source_page_url=payload["source_page_url"],
        query=payload["query"],
        domain=payload["domain"],
        title=payload["title"],
        extracted_assets=tuple(
            ExtractedAssetHint(
                asset_url=item["asset_url"],
                original_format=AssetFormat(item["original_format"]),
                style_tags=tuple(item["style_tags"]),
                notes=tuple(item["notes"]),
            )
            for item in payload["extracted_assets"]
        ),
    )

    result = GenericAssetExtractor().extract(extraction_input)

    assert len(result.candidates) == 1
    assert result.candidates[0].asset_url == "https://example.com/assets/tiger.svg"
    assert result.candidates[0].notes == ("fixture",)

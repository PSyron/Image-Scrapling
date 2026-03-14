"""Bing HTML provider for conservative live candidate-page discovery."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote_plus

from scrapling import Selector

from svg_scrapling.domain import SearchIntent
from svg_scrapling.search.duckduckgo_html import (
    ProviderSearchError,
    SearchHttpTransport,
    UrllibSearchHttpTransport,
)
from svg_scrapling.search.providers import CandidatePage, SearchProvider


def _node_text(document: Selector, selector: str) -> str | None:
    node = document.css(selector).first
    if node is None:
        return None
    return " ".join(node.css("::text").getall()).strip() or None


def parse_bing_results(
    html: str,
    *,
    query: str,
    provider_name: str,
    rank_offset: int = 0,
) -> tuple[CandidatePage, ...]:
    document = Selector(html)
    pages: list[CandidatePage] = []
    seen_urls: set[str] = set()

    for index, result in enumerate(document.css("li.b_algo"), start=1):
        anchor = result.css("h2 a").first
        if anchor is None:
            continue
        href = anchor.attrib.get("href", "").strip()
        if not href.startswith(("http://", "https://")):
            continue
        normalized_key = href.casefold()
        if normalized_key in seen_urls:
            continue
        seen_urls.add(normalized_key)
        pages.append(
            CandidatePage(
                url=href,
                query=query,
                provider_name=provider_name,
                rank=rank_offset + index,
                title=_node_text(result, "h2"),
                snippet=_node_text(result, ".b_caption p"),
            )
        )

    return tuple(pages)


@dataclass
class BingHtmlSearchProvider(SearchProvider):
    """A conservative Bing HTML provider with deterministic parsing."""

    transport: SearchHttpTransport | None = None
    timeout_seconds: float = 10.0
    retries: int = 1
    max_queries_per_search: int = 3
    name: str = "bing_html"

    def __post_init__(self) -> None:
        if self.transport is None:
            self.transport = UrllibSearchHttpTransport()

    def search(self, intent: SearchIntent) -> tuple[CandidatePage, ...]:
        if self.max_queries_per_search < 1:
            raise ValueError("max_queries_per_search must be greater than zero")
        transport = self.transport
        assert transport is not None

        collected: list[CandidatePage] = []
        seen_urls: set[str] = set()
        executed_queries = 0
        next_rank = 1

        for expanded_query in intent.expanded_queries:
            if executed_queries >= self.max_queries_per_search:
                break
            if len(collected) >= intent.search_query.requested_count:
                break
            html = self._fetch_results_page(expanded_query)
            for page in parse_bing_results(
                html,
                query=expanded_query,
                provider_name=self.name,
                rank_offset=next_rank - 1,
            ):
                normalized_key = page.url.casefold()
                if normalized_key in seen_urls:
                    continue
                seen_urls.add(normalized_key)
                collected.append(page)
                next_rank += 1
                if len(collected) >= intent.search_query.requested_count:
                    break
            executed_queries += 1

        return tuple(collected)

    def _fetch_results_page(self, query: str) -> str:
        transport = self.transport
        assert transport is not None
        url = self._results_url(query)
        headers = {
            "Accept": "text/html,application/xhtml+xml",
            "User-Agent": "svg-scrapling/0.1.0",
        }
        last_error: ProviderSearchError | None = None
        for _attempt in range(1, self.retries + 2):
            try:
                return transport.fetch_text(
                    url,
                    timeout_seconds=self.timeout_seconds,
                    headers=headers,
                )
            except ProviderSearchError as exc:
                last_error = exc
        raise last_error or ProviderSearchError("Bing provider failed without an explicit error")

    def _results_url(self, query: str) -> str:
        return f"https://www.bing.com/search?q={quote_plus(query)}&setlang=en-US"

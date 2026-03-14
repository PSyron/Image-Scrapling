"""DuckDuckGo HTML provider for live candidate page discovery."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol, cast
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote_plus, unquote, urlparse
from urllib.request import Request, urlopen

from scrapling import Selector

from svg_scrapling.domain import SearchIntent
from svg_scrapling.search.providers import CandidatePage, SearchProvider, SearchProviderError

_WHITESPACE_PATTERN = re.compile(r"\s+")
_TAG_PATTERN = re.compile(r"<[^>]+>")


class ProviderSearchError(SearchProviderError):
    """Raised when live provider discovery cannot complete safely."""


class SearchHttpTransport(Protocol):
    def fetch_text(
        self,
        url: str,
        *,
        timeout_seconds: float,
        headers: dict[str, str],
    ) -> str:
        """Return HTML for one search result page."""


class UrllibSearchHttpTransport:
    def fetch_text(
        self,
        url: str,
        *,
        timeout_seconds: float,
        headers: dict[str, str],
    ) -> str:
        request = Request(url, headers=headers)
        try:
            with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
                payload = response.read()
        except HTTPError as exc:
            _ = exc.read()
            raise ProviderSearchError(
                f"DuckDuckGo provider request failed with HTTP {exc.code}"
            ) from exc
        except URLError as exc:
            raise ProviderSearchError(f"DuckDuckGo provider request failed: {exc.reason}") from exc
        return cast(bytes, payload).decode("utf-8", errors="replace")


def _normalize_text(fragment: str | None) -> str | None:
    if fragment is None:
        return None
    normalized = _WHITESPACE_PATTERN.sub(" ", fragment).strip()
    return normalized or None


def _text_from_node(node: Selector | None) -> str | None:
    if node is None:
        return None
    return _normalize_text(_TAG_PATTERN.sub(" ", node.get()))


def _decode_result_url(href: str) -> str | None:
    normalized_href = href.strip()
    if not normalized_href:
        return None
    if normalized_href.startswith("//"):
        normalized_href = f"https:{normalized_href}"
    parsed = urlparse(normalized_href)
    if parsed.scheme in {"http", "https"} and parsed.netloc.endswith("duckduckgo.com"):
        redirect_url = parse_qs(parsed.query).get("uddg", [None])[0]
        if redirect_url is not None:
            decoded = unquote(redirect_url)
            decoded_parts = urlparse(decoded)
            if decoded_parts.scheme in {"http", "https"} and decoded_parts.netloc:
                return decoded
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return normalized_href
    return None


def parse_duckduckgo_results(
    html: str,
    *,
    query: str,
    provider_name: str,
    rank_offset: int = 0,
) -> tuple[CandidatePage, ...]:
    document = Selector(html)
    pages: list[CandidatePage] = []
    seen_urls: set[str] = set()

    for index, result in enumerate(document.css("div.result"), start=1):
        anchor = result.css("a.result__a").first
        if anchor is None:
            continue
        asset_page_url = _decode_result_url(anchor.attrib.get("href", ""))
        if asset_page_url is None:
            continue
        normalized_key = asset_page_url.casefold()
        if normalized_key in seen_urls:
            continue
        seen_urls.add(normalized_key)
        snippet = _text_from_node(result.css(".result__snippet").first)
        pages.append(
            CandidatePage(
                url=asset_page_url,
                query=query,
                provider_name=provider_name,
                rank=rank_offset + index,
                title=_text_from_node(anchor),
                snippet=snippet,
            )
        )

    return tuple(pages)


@dataclass
class DuckDuckGoHtmlSearchProvider(SearchProvider):
    """A conservative live provider built on DuckDuckGo's HTML endpoint."""

    transport: SearchHttpTransport | None = None
    timeout_seconds: float = 10.0
    retries: int = 1
    max_queries_per_search: int = 3
    name: str = "duckduckgo_html"

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
            for page in parse_duckduckgo_results(
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
        raise last_error or ProviderSearchError(
            "DuckDuckGo provider failed without an explicit error"
        )

    def _results_url(self, query: str) -> str:
        return f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"

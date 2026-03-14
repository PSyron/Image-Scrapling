"""Search intent building and provider abstractions."""

from svg_scrapling.search.bing_html import BingHtmlSearchProvider, parse_bing_results
from svg_scrapling.search.duckduckgo_html import (
    DuckDuckGoHtmlSearchProvider,
    ProviderSearchError,
    SearchHttpTransport,
    parse_duckduckgo_results,
)
from svg_scrapling.search.providers import (
    CandidatePage,
    FakeSearchProvider,
    FallbackSearchProvider,
    SearchProvider,
    SearchProviderError,
)
from svg_scrapling.search.query_expansion import build_search_intent, expand_query_terms

__all__ = [
    "BingHtmlSearchProvider",
    "CandidatePage",
    "DuckDuckGoHtmlSearchProvider",
    "FallbackSearchProvider",
    "FakeSearchProvider",
    "ProviderSearchError",
    "SearchHttpTransport",
    "SearchProvider",
    "SearchProviderError",
    "build_search_intent",
    "expand_query_terms",
    "parse_bing_results",
    "parse_duckduckgo_results",
]

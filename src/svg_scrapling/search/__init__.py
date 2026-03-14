"""Search intent building and provider abstractions."""

from svg_scrapling.search.duckduckgo_html import (
    DuckDuckGoHtmlSearchProvider,
    ProviderSearchError,
    SearchHttpTransport,
    parse_duckduckgo_results,
)
from svg_scrapling.search.providers import (
    CandidatePage,
    FakeSearchProvider,
    SearchProvider,
)
from svg_scrapling.search.query_expansion import build_search_intent, expand_query_terms

__all__ = [
    "CandidatePage",
    "DuckDuckGoHtmlSearchProvider",
    "FakeSearchProvider",
    "ProviderSearchError",
    "SearchHttpTransport",
    "SearchProvider",
    "build_search_intent",
    "expand_query_terms",
    "parse_duckduckgo_results",
]

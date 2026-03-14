"""Search provider contracts and a fake provider for tests."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from svg_scrapling.domain import SearchIntent


@dataclass(frozen=True)
class CandidatePage:
    """A typed search hit pointing to a page worth fetching later."""

    url: str
    query: str
    provider_name: str
    rank: int
    title: str | None = None
    snippet: str | None = None
    domain: str | None = None

    def __post_init__(self) -> None:
        normalized_url = self.url.strip()
        normalized_query = self.query.strip()
        normalized_provider = self.provider_name.strip()
        if not normalized_url:
            raise ValueError("url must not be blank")
        if not normalized_query:
            raise ValueError("query must not be blank")
        if not normalized_provider:
            raise ValueError("provider_name must not be blank")
        if self.rank < 1:
            raise ValueError("rank must be greater than or equal to 1")

        parsed = urlparse(normalized_url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError("url must be an absolute URL")

        if self.domain is None:
            object.__setattr__(self, "domain", parsed.netloc)


class SearchProvider:
    """Source-agnostic interface for candidate-page discovery."""

    name: str

    def search(self, intent: SearchIntent) -> tuple[CandidatePage, ...]:
        raise NotImplementedError


@dataclass(frozen=True)
class FakeSearchProvider(SearchProvider):
    """Simple deterministic provider for tests and local development."""

    name: str
    pages: tuple[CandidatePage, ...]

    def search(self, intent: SearchIntent) -> tuple[CandidatePage, ...]:
        matching_pages = [page for page in self.pages if page.query in intent.expanded_queries]
        if matching_pages:
            return tuple(sorted(matching_pages, key=lambda page: page.rank))
        return self.pages

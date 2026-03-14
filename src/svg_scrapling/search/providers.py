"""Search provider contracts and runtime composition helpers."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from svg_scrapling.domain import SearchIntent


class SearchProviderError(RuntimeError):
    """Explicit provider failure that may trigger an ordered fallback."""


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
class FallbackSearchProvider(SearchProvider):
    """Execute providers in order and continue on explicit provider failures."""

    providers: tuple[SearchProvider, ...]
    name: str = "fallback_search"

    def __post_init__(self) -> None:
        if not self.providers:
            raise ValueError("providers must not be empty")
        ordered_names = "->".join(provider.name for provider in self.providers)
        object.__setattr__(self, "name", ordered_names)

    def search(self, intent: SearchIntent) -> tuple[CandidatePage, ...]:
        collected: list[CandidatePage] = []
        seen_urls: set[str] = set()
        errors: list[str] = []

        for provider in self.providers:
            try:
                pages = provider.search(intent)
            except SearchProviderError as exc:
                errors.append(f"{provider.name}: {exc}")
                continue

            for page in pages:
                normalized_key = page.url.casefold()
                if normalized_key in seen_urls:
                    continue
                seen_urls.add(normalized_key)
                collected.append(
                    CandidatePage(
                        url=page.url,
                        query=page.query,
                        provider_name=page.provider_name,
                        rank=len(collected) + 1,
                        title=page.title,
                        snippet=page.snippet,
                        domain=page.domain,
                    )
                )
                if len(collected) >= intent.search_query.requested_count:
                    return tuple(collected)

        if collected:
            return tuple(collected)

        if errors:
            raise SearchProviderError("all configured providers failed: " + "; ".join(errors))
        return ()


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

from svg_scrapling.config import FindAssetsConfig
from svg_scrapling.runtime import (
    RuntimeFactories,
    build_default_pipeline_dependencies,
    default_runtime_factories,
)
from svg_scrapling.scraping import FetchOrchestrator, StaticHtmlFetcher
from svg_scrapling.search import CandidatePage, FakeSearchProvider


class FakeFetchTransport:
    def fetch(self, url: str, timeout_seconds: float, headers: dict[str, str]):
        _ = timeout_seconds
        _ = headers
        return 200, "<html><body>ok</body></html>", {}, url


def test_default_runtime_factories_include_live_provider_and_fetch_defaults() -> None:
    config = FindAssetsConfig(query="tiger coloring page")

    dependencies = build_default_pipeline_dependencies(
        config,
        factories=default_runtime_factories(),
    )

    assert dependencies.search_provider.name == "duckduckgo_html"
    assert dependencies.fetch_orchestrator is not None


def test_default_runtime_builder_accepts_test_factories() -> None:
    config = FindAssetsConfig(query="tiger coloring page")

    dependencies = build_default_pipeline_dependencies(
        config,
        factories=RuntimeFactories(
            provider_factory=lambda _config: FakeSearchProvider(
                name="fake-provider",
                pages=(
                    CandidatePage(
                        url="https://example.com/page",
                        query="tiger coloring page",
                        provider_name="fake-provider",
                        rank=1,
                    ),
                ),
            ),
            fetch_orchestrator_factory=lambda _config: FetchOrchestrator(
                static_fetcher=StaticHtmlFetcher(transport=FakeFetchTransport(), retries=0)
            ),
        ),
    )

    assert dependencies.search_provider.name == "fake-provider"

from svg_scrapling.config import FindAssetsConfig
from svg_scrapling.pipeline import PipelineDependencies
from svg_scrapling.runtime import (
    RuntimeCompositionError,
    RuntimeFactories,
    build_pipeline_dependencies,
)
from svg_scrapling.scraping import FetchOrchestrator, StaticHtmlFetcher
from svg_scrapling.search import CandidatePage, FakeSearchProvider


class FakeFetchTransport:
    def fetch(self, url: str, timeout_seconds: float, headers: dict[str, str]):
        _ = timeout_seconds
        _ = headers
        return 200, "<html><body>ok</body></html>", {}, url


def test_runtime_composition_builds_pipeline_dependencies() -> None:
    config = FindAssetsConfig(query="tiger coloring page")

    dependencies = build_pipeline_dependencies(
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

    assert isinstance(dependencies, PipelineDependencies)
    assert dependencies.search_provider.name == "fake-provider"
    assert isinstance(dependencies.fetch_orchestrator, FetchOrchestrator)


def test_runtime_composition_fails_clearly_when_required_factories_are_missing() -> None:
    config = FindAssetsConfig(query="tiger coloring page")

    try:
        build_pipeline_dependencies(
            config,
            factories=RuntimeFactories(),
        )
    except RuntimeCompositionError as exc:
        assert "provider_factory" in str(exc)
        assert "fetch_orchestrator_factory" in str(exc)
    else:
        raise AssertionError("Expected RuntimeCompositionError for missing factories")


def test_runtime_composition_wraps_factory_failures() -> None:
    config = FindAssetsConfig(query="tiger coloring page")

    try:
        build_pipeline_dependencies(
            config,
            factories=RuntimeFactories(
                provider_factory=lambda _config: FakeSearchProvider(name="fake", pages=()),
                fetch_orchestrator_factory=lambda _config: (_ for _ in ()).throw(
                    RuntimeError("boom")
                ),
            ),
        )
    except RuntimeCompositionError as exc:
        assert "Runtime composition failed: boom" in str(exc)
    else:
        raise AssertionError("Expected RuntimeCompositionError for factory failure")

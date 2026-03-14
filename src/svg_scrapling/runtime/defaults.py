"""Default runtime assembly for CLI-driven pipeline execution."""

from __future__ import annotations

from svg_scrapling.config import FindAssetsConfig
from svg_scrapling.download import AssetDownloader
from svg_scrapling.pipeline import PipelineDependencies
from svg_scrapling.runtime.composition import (
    RuntimeFactories,
    build_pipeline_dependencies,
)
from svg_scrapling.runtime.fetching import build_default_fetch_orchestrator
from svg_scrapling.runtime.providers import build_default_search_provider
from svg_scrapling.scraping import FetchOrchestrator
from svg_scrapling.search import SearchProvider


def _default_provider_factory(config: FindAssetsConfig) -> SearchProvider:
    return build_default_search_provider(config)


def _default_fetch_orchestrator_factory(_config: FindAssetsConfig) -> FetchOrchestrator:
    return build_default_fetch_orchestrator(_config)


def default_runtime_factories() -> RuntimeFactories:
    return RuntimeFactories(
        provider_factory=_default_provider_factory,
        fetch_orchestrator_factory=_default_fetch_orchestrator_factory,
    )


def build_default_pipeline_dependencies(
    config: FindAssetsConfig,
    *,
    factories: RuntimeFactories | None = None,
) -> PipelineDependencies:
    dependencies = build_pipeline_dependencies(
        config,
        factories=factories or default_runtime_factories(),
    )
    if isinstance(dependencies.downloader, AssetDownloader):
        dependencies.downloader.skip_existing = config.skip_existing_downloads
    return dependencies

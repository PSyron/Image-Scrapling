"""Default runtime assembly for CLI-driven pipeline execution."""

from __future__ import annotations

from svg_scrapling.config import FindAssetsConfig
from svg_scrapling.pipeline import PipelineDependencies
from svg_scrapling.runtime.composition import (
    RuntimeCompositionError,
    RuntimeFactories,
    build_pipeline_dependencies,
)
from svg_scrapling.runtime.fetching import build_default_fetch_orchestrator
from svg_scrapling.scraping import FetchOrchestrator
from svg_scrapling.search import SearchProvider


def _default_provider_factory(_config: FindAssetsConfig) -> SearchProvider:
    raise RuntimeCompositionError(
        "No default discovery provider is configured yet. "
        "Implement the first live provider before using the default CLI runtime."
    )


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
    return build_pipeline_dependencies(
        config,
        factories=factories or default_runtime_factories(),
    )

"""Centralized runtime dependency composition for `assets find`."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from svg_scrapling.config import FindAssetsConfig
from svg_scrapling.conversion import SvgPostProcessor, VTracerConverter
from svg_scrapling.download import AssetDownloader
from svg_scrapling.extraction import HtmlHeuristicExtractor
from svg_scrapling.licensing import LicensingPolicyEngine
from svg_scrapling.pipeline import PipelineDependencies
from svg_scrapling.quality import HeuristicQualityScorer
from svg_scrapling.ranking import CandidateDeduper
from svg_scrapling.scraping import FetchOrchestrator
from svg_scrapling.search import SearchProvider


class RuntimeCompositionError(RuntimeError):
    """Raised when runtime dependency assembly cannot complete safely."""


@dataclass(frozen=True)
class RuntimeFactories:
    provider_factory: Callable[[FindAssetsConfig], SearchProvider] | None = None
    fetch_orchestrator_factory: Callable[[FindAssetsConfig], FetchOrchestrator] | None = None
    extractor_factory: Callable[[], HtmlHeuristicExtractor] = HtmlHeuristicExtractor
    quality_scorer_factory: Callable[[], HeuristicQualityScorer] = HeuristicQualityScorer
    deduper_factory: Callable[[], CandidateDeduper] = CandidateDeduper
    licensing_engine_factory: Callable[[], LicensingPolicyEngine] = LicensingPolicyEngine
    downloader_factory: Callable[[], AssetDownloader] = AssetDownloader
    converter_factory: Callable[[], VTracerConverter] = VTracerConverter
    svg_post_processor_factory: Callable[[], SvgPostProcessor] = SvgPostProcessor


def build_pipeline_dependencies(
    config: FindAssetsConfig,
    *,
    factories: RuntimeFactories,
) -> PipelineDependencies:
    missing_requirements: list[str] = []
    if factories.provider_factory is None:
        missing_requirements.append("provider_factory")
    if factories.fetch_orchestrator_factory is None:
        missing_requirements.append("fetch_orchestrator_factory")
    if missing_requirements:
        raise RuntimeCompositionError(
            "Runtime composition is incomplete; missing " + ", ".join(sorted(missing_requirements))
        )
    provider_factory = factories.provider_factory
    fetch_orchestrator_factory = factories.fetch_orchestrator_factory
    assert provider_factory is not None
    assert fetch_orchestrator_factory is not None

    try:
        return PipelineDependencies(
            search_provider=provider_factory(config),
            fetch_orchestrator=fetch_orchestrator_factory(config),
            extractor=factories.extractor_factory(),
            quality_scorer=factories.quality_scorer_factory(),
            deduper=factories.deduper_factory(),
            licensing_engine=factories.licensing_engine_factory(),
            downloader=factories.downloader_factory(),
            converter=factories.converter_factory(),
            svg_post_processor=factories.svg_post_processor_factory(),
        )
    except Exception as exc:  # noqa: BLE001
        raise RuntimeCompositionError(f"Runtime composition failed: {exc}") from exc

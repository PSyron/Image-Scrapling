"""Happy-path pipeline orchestration from query to manifest output."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path

from svg_scrapling.config import FindAssetsConfig
from svg_scrapling.conversion import (
    ConversionPreset,
    SvgPostProcessor,
    VTracerConverter,
)
from svg_scrapling.domain import (
    AssetCandidate,
    AssetFormat,
    ConversionStatus,
    DownloadedAsset,
    DownloadStatus,
    ManifestRecord,
    PipelineRunSummary,
)
from svg_scrapling.download import AssetDownloader
from svg_scrapling.extraction import HtmlExtractionInput, HtmlHeuristicExtractor
from svg_scrapling.licensing import LicensingPolicyEngine, assess_candidate_license
from svg_scrapling.manifests import ManifestWriter
from svg_scrapling.manifests.writer import build_manifest_record
from svg_scrapling.quality import HeuristicQualityScorer
from svg_scrapling.ranking import CandidateDeduper
from svg_scrapling.reporting import build_manifest_summary
from svg_scrapling.scraping import FetchOrchestrator, FetchRequest
from svg_scrapling.search import SearchProvider, build_search_intent
from svg_scrapling.storage import RunLayout, create_run_layout, generate_run_id


class PipelineStageError(RuntimeError):
    """Explicit stage failure with context."""

    def __init__(self, stage: str, message: str):
        super().__init__(f"{stage}: {message}")
        self.stage = stage


@dataclass(frozen=True)
class PipelineRunResult:
    run_layout: RunLayout
    manifest_path: Path
    summary_path: Path
    log_path: Path
    summary: PipelineRunSummary
    records: tuple[ManifestRecord, ...]


@dataclass(frozen=True)
class PipelineDependencies:
    search_provider: SearchProvider
    fetch_orchestrator: FetchOrchestrator
    extractor: HtmlHeuristicExtractor
    quality_scorer: HeuristicQualityScorer
    deduper: CandidateDeduper
    licensing_engine: LicensingPolicyEngine
    downloader: AssetDownloader
    converter: VTracerConverter
    svg_post_processor: SvgPostProcessor


def run_find_assets(
    config: FindAssetsConfig,
    *,
    dependencies: PipelineDependencies,
) -> PipelineRunResult:
    run_layout = create_run_layout(config.output_root, generate_run_id())
    stage_logs: list[str] = []

    def log(stage: str, message: str) -> None:
        stage_logs.append(f"{stage}: {message}")

    try:
        search_intent = build_search_intent(
            query=config.query,
            requested_count=config.count,
            preferred_format=config.preferred_format,
            fallback_format=config.fallback_format,
            convert_to=config.convert_to,
        )
        log("search_intent", f"expanded_queries={len(search_intent.expanded_queries)}")

        pages = dependencies.search_provider.search(search_intent)
        log("search", f"candidate_pages={len(pages)} provider={dependencies.search_provider.name}")

        extracted_candidates: list[AssetCandidate] = []
        for page in pages:
            fetch_response = dependencies.fetch_orchestrator.fetch(
                FetchRequest(url=page.url, strategy=config.fetch_strategy)
            )
            extraction_result = dependencies.extractor.extract_page(
                HtmlExtractionInput(
                    source_page_url=page.url,
                    query=page.query,
                    domain=page.domain or dependencies.search_provider.name,
                    html=fetch_response.html,
                )
            )
            extracted_candidates.extend(extraction_result.candidates)
        log("extract", f"candidates={len(extracted_candidates)}")

        dedupe_result = dependencies.deduper.dedupe(tuple(extracted_candidates))
        kept_candidates = tuple(item.candidate for item in dedupe_result.kept)
        log(
            "dedupe",
            f"kept={len(kept_candidates)} duplicates_removed={dedupe_result.duplicates_removed}",
        )

        records: list[ManifestRecord] = []
        for candidate in kept_candidates:
            quality = dependencies.quality_scorer.score(candidate)
            license_assessment = assess_candidate_license(candidate)
            policy_decision = dependencies.licensing_engine.evaluate(
                license_assessment,
                mode=config.mode,
                allowed_licenses=config.allowed_licenses,
            )

            downloaded_asset: DownloadedAsset | None = None
            converted_asset = None
            record_notes = list(candidate.notes)
            record_notes.append(f"policy:{policy_decision.reason}")
            if policy_decision.requires_manual_review:
                record_notes.append("manual_review_required")

            if policy_decision.keep:
                downloaded_asset = dependencies.downloader.download(candidate, run_layout)
                if (
                    config.convert_to == config.preferred_format.SVG
                    and candidate.original_format != AssetFormat.SVG
                    and downloaded_asset.download_status == DownloadStatus.DOWNLOADED
                ):
                    converted_asset = dependencies.converter.convert(
                        downloaded_asset,
                        run_layout,
                        preset=ConversionPreset.LINE_ART_FAST,
                    )
                    if converted_asset.derived_svg_path is not None:
                        cleanup_result = dependencies.svg_post_processor.process(
                            converted_asset.derived_svg_path
                        )
                        record_notes.extend(cleanup_result.notes)
                        record_notes.append(
                            f"svg_elements:{int(cleanup_result.complexity_metrics['element_count'])}"
                        )
                        record_notes.append(
                            f"svg_paths:{int(cleanup_result.complexity_metrics['path_count'])}"
                        )
                    if converted_asset.conversion_status != ConversionStatus.CONVERTED:
                        record_notes.extend(converted_asset.notes)

            record = build_manifest_record(
                candidate,
                downloaded_asset=downloaded_asset,
                converted_asset=converted_asset,
                license_assessment=license_assessment,
                quality_assessment=quality,
                scraped_at=datetime.now(timezone.utc),
            )
            if not policy_decision.keep:
                record = replace(record, download_status=DownloadStatus.SKIPPED)
            records.append(replace(record, notes=tuple(record_notes)))

        manifest_path = ManifestWriter(run_layout.manifests / "manifest.jsonl").write(
            tuple(records)
        )
        summary = build_manifest_summary(manifest_path, tuple(records))
        summary_path = run_layout.manifests / "summary.json"
        summary_path.write_text(json.dumps(summary.to_dict(), sort_keys=True), encoding="utf-8")
        log(
            "manifest",
            f"records={len(records)} downloaded={summary.total_downloaded} "
            f"converted={summary.total_converted}",
        )
    except Exception as exc:  # noqa: BLE001
        stage = "pipeline"
        if isinstance(exc, PipelineStageError):
            stage = exc.stage
        log(stage, f"failed={exc}")
        _write_log(run_layout.logs / "pipeline.log", stage_logs)
        if isinstance(exc, PipelineStageError):
            raise
        raise PipelineStageError(stage, str(exc)) from exc

    log("done", f"run_id={run_layout.run_id}")
    log_path = run_layout.logs / "pipeline.log"
    _write_log(log_path, stage_logs)
    return PipelineRunResult(
        run_layout=run_layout,
        manifest_path=manifest_path,
        summary_path=summary_path,
        log_path=log_path,
        summary=summary,
        records=tuple(records),
    )


def _write_log(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

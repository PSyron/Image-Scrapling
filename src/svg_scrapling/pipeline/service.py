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
    ConvertedAsset,
    DownloadedAsset,
    DownloadStatus,
    ManifestRecord,
    PipelineRunSummary,
)
from svg_scrapling.download import AssetDownloader, BlockedAssetDownloadError
from svg_scrapling.extraction import HtmlExtractionInput, HtmlHeuristicExtractor
from svg_scrapling.licensing import LicensingPolicyEngine, assess_candidate_license
from svg_scrapling.manifests import ManifestWriter, load_manifest_records
from svg_scrapling.manifests.writer import build_manifest_record
from svg_scrapling.quality import HeuristicQualityScorer
from svg_scrapling.ranking import CandidateDeduper
from svg_scrapling.reporting import build_manifest_summary, render_summary_text
from svg_scrapling.scraping import FetchError, FetchOrchestrator, FetchRequest
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
    summary_text_path: Path
    log_path: Path
    rejected_report_path: Path
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
    run_id = config.run_id or generate_run_id()
    run_layout = create_run_layout(config.output_root, run_id)
    manifest_path = run_layout.manifests / "manifest.jsonl"
    summary_path = run_layout.manifests / "summary.json"
    summary_text_path = run_layout.manifests / "summary.txt"
    log_path = run_layout.logs / "pipeline.log"
    rejected_report_path = run_layout.manifests / "rejected_candidates.jsonl"
    stage_logs: list[str] = []
    rejected_events: list[dict[str, object]] = []
    fetch_failure_count = 0
    reused_existing_count = 0

    def log(stage: str, message: str) -> None:
        stage_logs.append(f"{stage}: {message}")

    existing_records: tuple[ManifestRecord, ...] = ()
    existing_records_by_id: dict[str, ManifestRecord] = {}
    if config.run_id is not None and manifest_path.exists():
        existing_records = load_manifest_records(manifest_path)
        existing_records_by_id = {record.id: record for record in existing_records}
        reused_existing_count = len(existing_records)
        log("resume", f"loaded_existing_records={len(existing_records)}")

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
            try:
                fetch_response = dependencies.fetch_orchestrator.fetch(
                    FetchRequest(url=page.url, strategy=config.fetch_strategy)
                )
            except FetchError as exc:
                fetch_failure_count += 1
                rejected_events.append(
                    {
                        "kind": "fetch_failed",
                        "query": page.query,
                        "source_page_url": page.url,
                        "provider_name": page.provider_name,
                        "reason": str(exc),
                    }
                )
                log("fetch", f"failed_page={page.url} reason={exc}")
                continue
            extraction_result = dependencies.extractor.extract_page(
                HtmlExtractionInput(
                    source_page_url=page.url,
                    query=page.query,
                    domain=page.domain or dependencies.search_provider.name,
                    html=fetch_response.html,
                )
            )
            extracted_candidates.extend(extraction_result.candidates)
            for rejected_hint in extraction_result.rejected:
                rejected_events.append(
                    {
                        "kind": "extract_rejected",
                        "query": page.query,
                        "source_page_url": page.url,
                        "asset_url": rejected_hint.asset_url,
                        "reason": rejected_hint.reason,
                    }
                )
        log("extract", f"candidates={len(extracted_candidates)}")

        dedupe_result = dependencies.deduper.dedupe(tuple(extracted_candidates))
        kept_candidates = tuple(item.candidate for item in dedupe_result.kept)
        log(
            "dedupe",
            f"kept={len(kept_candidates)} duplicates_removed={dedupe_result.duplicates_removed}",
        )

        records: list[ManifestRecord] = list(existing_records)
        for candidate in kept_candidates:
            if candidate.id in existing_records_by_id:
                continue
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
            for rejection_reason in quality.rejection_reasons:
                record_notes.append(f"rejection:{rejection_reason}")

            if policy_decision.keep:
                try:
                    downloaded_asset = dependencies.downloader.download(candidate, run_layout)
                except Exception as exc:  # noqa: BLE001
                    rejection_kind = (
                        "download_blocked"
                        if isinstance(exc, BlockedAssetDownloadError)
                        else "download_failed"
                    )
                    rejected_events.append(
                        {
                            "kind": rejection_kind,
                            "query": candidate.query,
                            "source_page_url": candidate.source_page_url,
                            "asset_url": candidate.asset_url,
                            "reason": str(exc),
                        }
                    )
                    record_notes.append(f"rejection:{rejection_kind}")
                    record_notes.append(f"rejection:{rejection_kind}:{type(exc).__name__}")
                    failed_record = build_manifest_record(
                        candidate,
                        downloaded_asset=None,
                        converted_asset=None,
                        license_assessment=license_assessment,
                        quality_assessment=quality,
                        scraped_at=datetime.now(timezone.utc),
                    )
                    records.append(
                        replace(
                            failed_record,
                            download_status=DownloadStatus.FAILED,
                            notes=tuple(record_notes),
                        )
                    )
                    continue
                if downloaded_asset.downloaded_at is None and config.skip_existing_downloads:
                    reused_existing_count += 1
                    record_notes.append("download:reused_existing_file")
                if (
                    config.convert_to == config.preferred_format.SVG
                    and candidate.original_format != AssetFormat.SVG
                    and downloaded_asset.download_status == DownloadStatus.DOWNLOADED
                ):
                    try:
                        converted_asset = dependencies.converter.convert(
                            downloaded_asset,
                            run_layout,
                            preset=ConversionPreset.LINE_ART_FAST,
                        )
                    except Exception as exc:  # noqa: BLE001
                        rejected_events.append(
                            {
                                "kind": "conversion_failed",
                                "query": candidate.query,
                                "source_page_url": candidate.source_page_url,
                                "asset_url": candidate.asset_url,
                                "reason": str(exc),
                            }
                        )
                        converted_asset = ConvertedAsset(
                            asset_id=downloaded_asset.asset_id,
                            source_raster_path=downloaded_asset.stored_original_path,
                            derived_svg_path=None,
                            conversion_status=ConversionStatus.FAILED,
                            preset=ConversionPreset.LINE_ART_FAST.value,
                            notes=(str(exc),),
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
            else:
                rejected_events.append(
                    {
                        "kind": "policy_rejected",
                        "query": candidate.query,
                        "source_page_url": candidate.source_page_url,
                        "asset_url": candidate.asset_url,
                        "reason": policy_decision.reason,
                    }
                )

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

        manifest_path = ManifestWriter(manifest_path).write(tuple(records))
        summary = build_manifest_summary(manifest_path, tuple(records))
        summary = replace(
            summary,
            total_candidate_pages=len(pages),
            total_extracted_candidates=len(extracted_candidates),
            total_rejected_candidates=len(rejected_events),
            total_fetch_failures=fetch_failure_count,
            total_reused_existing=reused_existing_count,
        )
        summary_path.write_text(json.dumps(summary.to_dict(), sort_keys=True), encoding="utf-8")
        summary_text_path.write_text(render_summary_text(summary) + "\n", encoding="utf-8")
        _write_jsonl(rejected_report_path, rejected_events)
        log(
            "manifest",
            f"records={len(records)} downloaded={summary.total_downloaded} "
            f"converted={summary.total_converted} rejected_events={len(rejected_events)}",
        )
    except Exception as exc:  # noqa: BLE001
        stage = "pipeline"
        if isinstance(exc, PipelineStageError):
            stage = exc.stage
        log(stage, f"failed={exc}")
        _write_log(log_path, stage_logs)
        _write_jsonl(rejected_report_path, rejected_events)
        if isinstance(exc, PipelineStageError):
            raise
        raise PipelineStageError(stage, f"{exc}. See log: {log_path}") from exc

    log("done", f"run_id={run_layout.run_id}")
    _write_log(log_path, stage_logs)
    return PipelineRunResult(
        run_layout=run_layout,
        manifest_path=manifest_path,
        summary_path=summary_path,
        summary_text_path=summary_text_path,
        log_path=log_path,
        rejected_report_path=rejected_report_path,
        summary=summary,
        records=tuple(records),
    )


def _write_log(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, payloads: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for payload in payloads:
            handle.write(json.dumps(payload, sort_keys=True))
            handle.write("\n")

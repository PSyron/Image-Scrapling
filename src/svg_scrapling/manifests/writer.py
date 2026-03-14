"""Manifest creation and summary helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from svg_scrapling.domain import (
    AssetCandidate,
    ConversionStatus,
    ConvertedAsset,
    DownloadedAsset,
    DownloadStatus,
    LicenseAssessment,
    LicenseNormalized,
    ManifestRecord,
    PipelineRunSummary,
    QualityAssessment,
    ReuseStatus,
)


def build_manifest_record(
    candidate: AssetCandidate,
    *,
    downloaded_asset: DownloadedAsset | None = None,
    converted_asset: ConvertedAsset | None = None,
    license_assessment: LicenseAssessment | None = None,
    quality_assessment: QualityAssessment | None = None,
    scraped_at: datetime | None = None,
) -> ManifestRecord:
    return ManifestRecord(
        id=candidate.id,
        query=candidate.query,
        source_page_url=candidate.source_page_url,
        asset_url=candidate.asset_url,
        original_format=candidate.original_format,
        stored_original_path=downloaded_asset.stored_original_path if downloaded_asset else None,
        derived_svg_path=converted_asset.derived_svg_path if converted_asset else None,
        title=candidate.title,
        alt_text=candidate.alt_text,
        domain=candidate.domain,
        license_raw=(
            license_assessment.license_raw if license_assessment else candidate.license_hint
        ),
        license_normalized=(
            license_assessment.license_normalized
            if license_assessment
            else LicenseNormalized.UNKNOWN
        ),
        reuse_status=license_assessment.reuse_status if license_assessment else ReuseStatus.UNKNOWN,
        author_or_owner=candidate.author_or_owner,
        attribution_required=(
            license_assessment.attribution_required if license_assessment else False
        ),
        scraped_at=scraped_at or datetime.now(timezone.utc),
        download_status=(
            downloaded_asset.download_status if downloaded_asset else DownloadStatus.PENDING
        ),
        conversion_status=(
            converted_asset.conversion_status if converted_asset else ConversionStatus.NOT_REQUESTED
        ),
        quality_score=quality_assessment.quality_score if quality_assessment else None,
        style_tags=quality_assessment.style_tags if quality_assessment else candidate.style_tags,
        is_outline_like=quality_assessment.is_outline_like if quality_assessment else False,
        is_black_and_white_like=(
            quality_assessment.is_black_and_white_like if quality_assessment else False
        ),
        is_kids_friendly_candidate=(
            quality_assessment.is_kids_friendly_candidate if quality_assessment else False
        ),
        dedupe_hash=quality_assessment.dedupe_hash if quality_assessment else None,
        notes=candidate.notes,
    )


@dataclass
class ManifestWriter:
    output_path: Path

    def write(self, records: tuple[ManifestRecord, ...]) -> Path:
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        with self.output_path.open("w", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record.to_dict(), sort_keys=True))
                handle.write("\n")
        return self.output_path


def build_run_summary(
    run_id: str,
    query: str,
    records: tuple[ManifestRecord, ...],
) -> PipelineRunSummary:
    totals_by_format: dict[str, int] = {}
    totals_by_domain: dict[str, int] = {}
    totals_by_reuse_status: dict[str, int] = {}
    conversion_failures: dict[str, int] = {}

    total_downloaded = 0
    total_converted = 0

    for record in records:
        totals_by_format[record.original_format.value] = (
            totals_by_format.get(record.original_format.value, 0) + 1
        )
        totals_by_domain[record.domain] = totals_by_domain.get(record.domain, 0) + 1
        reuse_key = record.reuse_status.value
        totals_by_reuse_status[reuse_key] = totals_by_reuse_status.get(reuse_key, 0) + 1
        if record.download_status == DownloadStatus.DOWNLOADED:
            total_downloaded += 1
        if record.conversion_status == ConversionStatus.CONVERTED:
            total_converted += 1
        if record.conversion_status == ConversionStatus.FAILED:
            conversion_failures[record.id] = conversion_failures.get(record.id, 0) + 1

    total_rejected = sum(
        1
        for record in records
        if record.download_status in {DownloadStatus.FAILED, DownloadStatus.SKIPPED}
    )
    total_accepted = len(records) - total_rejected

    return PipelineRunSummary(
        run_id=run_id,
        query=query,
        total_discovered=len(records),
        total_downloaded=total_downloaded,
        total_accepted=total_accepted,
        total_rejected=total_rejected,
        total_converted=total_converted,
        totals_by_format=totals_by_format,
        totals_by_domain=totals_by_domain,
        totals_by_reuse_status=totals_by_reuse_status,
        rejection_reasons={},
        conversion_failures=conversion_failures,
        duplicate_counts={},
    )

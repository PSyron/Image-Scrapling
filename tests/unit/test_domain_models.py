from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from svg_scrapling.domain import (
    AssetCandidate,
    AssetFormat,
    ConversionStatus,
    DownloadStatus,
    LicenseAssessment,
    LicenseNormalized,
    ManifestRecord,
    PipelineRunSummary,
    QualityAssessment,
    ReuseStatus,
    SearchIntent,
    SearchQuery,
)


def test_search_query_validates_input() -> None:
    with pytest.raises(ValueError, match="query must not be blank"):
        SearchQuery(query="   ", requested_count=10)


def test_search_intent_requires_expanded_queries() -> None:
    search_query = SearchQuery(query="tiger", requested_count=10)

    with pytest.raises(ValueError, match="expanded_queries must contain at least one query"):
        SearchIntent(
            search_query=search_query,
            expanded_queries=(),
            preferred_format=AssetFormat.SVG,
        )


def test_license_assessment_serializes_enum_values() -> None:
    assessment = LicenseAssessment(
        asset_id="asset-1",
        license_raw="CC BY",
        license_normalized=LicenseNormalized.CC_BY,
        reuse_status=ReuseStatus.ALLOWED_WITH_ATTRIBUTION,
        attribution_required=True,
        confidence=0.85,
    )

    assert assessment.to_dict() == {
        "asset_id": "asset-1",
        "license_raw": "CC BY",
        "license_normalized": "cc_by",
        "reuse_status": "allowed_with_attribution",
        "attribution_required": True,
        "confidence": 0.85,
        "notes": [],
    }


def test_manifest_record_contains_required_canonical_fields() -> None:
    record = ManifestRecord(
        id="asset-1",
        query="tiger coloring page",
        source_page_url="https://example.com/page",
        asset_url="https://example.com/asset.svg",
        original_format=AssetFormat.SVG,
        stored_original_path=Path("data/runs/run-1/originals/asset.svg"),
        derived_svg_path=None,
        title="Tiger outline",
        alt_text="Tiger outline for kids",
        domain="example.com",
        license_raw="CC0",
        license_normalized=LicenseNormalized.CC0,
        reuse_status=ReuseStatus.ALLOWED,
        author_or_owner="Example Author",
        attribution_required=False,
        scraped_at=datetime(2026, 3, 14, 12, 0, tzinfo=timezone.utc),
        download_status=DownloadStatus.DOWNLOADED,
        conversion_status=ConversionStatus.NOT_REQUESTED,
        quality_score=0.92,
        style_tags=("outline", "black_and_white"),
        is_outline_like=True,
        is_black_and_white_like=True,
        is_kids_friendly_candidate=True,
        dedupe_hash="hash-1",
        notes=("kept",),
    )

    serialized = record.to_dict()

    assert set(serialized) >= {
        "id",
        "query",
        "source_page_url",
        "asset_url",
        "original_format",
        "stored_original_path",
        "derived_svg_path",
        "title",
        "alt_text",
        "domain",
        "license_raw",
        "license_normalized",
        "reuse_status",
        "author_or_owner",
        "attribution_required",
        "scraped_at",
        "download_status",
        "conversion_status",
        "quality_score",
        "style_tags",
        "is_outline_like",
        "is_black_and_white_like",
        "is_kids_friendly_candidate",
        "dedupe_hash",
        "notes",
    }
    assert serialized["original_format"] == "svg"
    assert serialized["stored_original_path"] == "data/runs/run-1/originals/asset.svg"
    assert serialized["scraped_at"] == "2026-03-14T12:00:00+00:00"
    assert json.dumps(serialized, sort_keys=True)


def test_asset_candidate_rejects_blank_identifiers() -> None:
    with pytest.raises(ValueError, match="id must not be blank"):
        AssetCandidate(
            id="   ",
            query="tiger",
            source_page_url="https://example.com/page",
            asset_url="https://example.com/asset.svg",
            original_format=AssetFormat.SVG,
            domain="example.com",
        )


def test_pipeline_run_summary_rejects_negative_counters() -> None:
    with pytest.raises(ValueError, match="total_discovered must not be negative"):
        PipelineRunSummary(
            run_id="run-1",
            query="tiger",
            total_discovered=-1,
            total_downloaded=0,
            total_accepted=0,
            total_rejected=0,
            total_converted=0,
        )


def test_quality_assessment_serializes_cleanly() -> None:
    assessment = QualityAssessment(
        asset_id="asset-1",
        quality_score=0.9,
        style_tags=("outline", "printable"),
        is_outline_like=True,
        is_black_and_white_like=True,
        is_kids_friendly_candidate=True,
        dedupe_hash="hash-1",
        notes=("high confidence",),
    )

    assert assessment.to_dict() == {
        "asset_id": "asset-1",
        "quality_score": 0.9,
        "style_tags": ["outline", "printable"],
        "is_outline_like": True,
        "is_black_and_white_like": True,
        "is_kids_friendly_candidate": True,
        "dedupe_hash": "hash-1",
        "component_scores": {},
        "rejection_reasons": [],
        "notes": ["high confidence"],
    }

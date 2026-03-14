from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from svg_scrapling.domain import (
    AssetCandidate,
    AssetFormat,
    DownloadedAsset,
    DownloadStatus,
)
from svg_scrapling.manifests import build_manifest_record
from svg_scrapling.reporting import build_manifest_summary, render_summary_text


def test_manifest_record_matches_golden_fixture() -> None:
    candidate = AssetCandidate(
        id="asset-golden-1",
        query="tiger coloring page",
        source_page_url="https://example.com/page",
        asset_url="https://assets.example.com/tiger.png",
        original_format=AssetFormat.PNG,
        domain="assets.example.com",
        title="Tiger outline",
        alt_text="Printable tiger outline for kids",
        style_tags=("outline",),
    )
    downloaded = DownloadedAsset(
        asset_id="asset-golden-1",
        source_page_url=candidate.source_page_url,
        asset_url=candidate.asset_url,
        original_format=AssetFormat.PNG,
        stored_original_path=Path("originals/tiger.png"),
        download_status=DownloadStatus.DOWNLOADED,
    )
    record = build_manifest_record(
        candidate,
        downloaded_asset=downloaded,
        scraped_at=datetime(2026, 3, 14, 12, 0, tzinfo=timezone.utc),
    )
    fixture_path = Path("tests/fixtures/manifests/golden_manifest.jsonl")

    assert (
        json.dumps(record.to_dict(), sort_keys=True)
        == fixture_path.read_text(encoding="utf-8").strip()
    )


def test_manifest_summary_matches_golden_fixture() -> None:
    candidate = AssetCandidate(
        id="asset-golden-1",
        query="tiger coloring page",
        source_page_url="https://example.com/page",
        asset_url="https://assets.example.com/tiger.png",
        original_format=AssetFormat.PNG,
        domain="assets.example.com",
        title="Tiger outline",
        alt_text="Printable tiger outline for kids",
        style_tags=("outline",),
    )
    downloaded = DownloadedAsset(
        asset_id="asset-golden-1",
        source_page_url=candidate.source_page_url,
        asset_url=candidate.asset_url,
        original_format=AssetFormat.PNG,
        stored_original_path=Path("originals/tiger.png"),
        download_status=DownloadStatus.DOWNLOADED,
    )
    record = build_manifest_record(
        candidate,
        downloaded_asset=downloaded,
        scraped_at=datetime(2026, 3, 14, 12, 0, tzinfo=timezone.utc),
    )
    summary = build_manifest_summary(Path("runs/run-fixture/manifests/manifest.jsonl"), (record,))
    fixture_path = Path("tests/fixtures/manifests/golden_summary.txt")

    assert render_summary_text(summary) == fixture_path.read_text(encoding="utf-8").strip()

from __future__ import annotations

import binascii
import importlib.util
import struct
import zlib
from datetime import datetime, timezone
from pathlib import Path

import pytest
from typer.testing import CliRunner

from svg_scrapling.cli import app
from svg_scrapling.domain import (
    AssetCandidate,
    AssetFormat,
    DownloadedAsset,
    DownloadStatus,
)
from svg_scrapling.manifests import ManifestWriter, build_manifest_record
from svg_scrapling.storage import create_run_layout

runner = CliRunner()
VTRACER_AVAILABLE = importlib.util.find_spec("vtracer") is not None


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    checksum = binascii.crc32(chunk_type + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", checksum)


def _write_fixture_png(path: Path) -> None:
    width = 4
    height = 4
    rows: list[bytes] = []
    black = b"\x00\x00\x00"
    white = b"\xff\xff\xff"

    for y in range(height):
        row = bytearray([0])
        for x in range(width):
            row.extend(black if 1 <= x <= 2 and 1 <= y <= 2 else white)
        rows.append(bytes(row))

    path.write_bytes(
        b"".join(
            (
                b"\x89PNG\r\n\x1a\n",
                _png_chunk(
                    b"IHDR",
                    struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0),
                ),
                _png_chunk(b"IDAT", zlib.compress(b"".join(rows))),
                _png_chunk(b"IEND", b""),
            )
        )
    )


def _candidate(asset_id: str, asset_url: str) -> AssetCandidate:
    return AssetCandidate(
        id=asset_id,
        query="tiger coloring page",
        source_page_url=f"https://example.com/pages/{asset_id}",
        asset_url=asset_url,
        original_format=AssetFormat.PNG,
        domain="assets.example.com",
        title="Tiger outline",
        alt_text="Printable tiger outline for kids",
    )


def _manifest_path(tmp_path: Path, *, duplicate: bool = False) -> Path:
    run_layout = create_run_layout(tmp_path / "runs", "run-1")
    original_path = run_layout.originals / "tiger.png"
    _write_fixture_png(original_path)
    downloaded = DownloadedAsset(
        asset_id="asset-1",
        source_page_url="https://example.com/pages/asset-1",
        asset_url="https://assets.example.com/tiger.png",
        original_format=AssetFormat.PNG,
        stored_original_path=original_path,
        download_status=DownloadStatus.DOWNLOADED,
    )
    records = [
        build_manifest_record(
            _candidate("asset-1", "https://assets.example.com/tiger.png"),
            downloaded_asset=downloaded,
            scraped_at=datetime(2026, 3, 14, 12, 0, tzinfo=timezone.utc),
        )
    ]
    if duplicate:
        records.append(
            build_manifest_record(
                _candidate("asset-2", "https://assets.example.com/tiger.png"),
                downloaded_asset=DownloadedAsset(
                    asset_id="asset-2",
                    source_page_url="https://example.com/pages/asset-2",
                    asset_url="https://assets.example.com/tiger.png",
                    original_format=AssetFormat.PNG,
                    stored_original_path=original_path,
                    download_status=DownloadStatus.DOWNLOADED,
                ),
                scraped_at=datetime(2026, 3, 14, 12, 5, tzinfo=timezone.utc),
            )
        )
    manifest_path = run_layout.manifests / "manifest.jsonl"
    ManifestWriter(manifest_path).write(tuple(records))
    return manifest_path


def test_inspect_manifest_prints_summary(tmp_path: Path) -> None:
    manifest_path = _manifest_path(tmp_path)

    result = runner.invoke(app, ["inspect-manifest", str(manifest_path)])

    assert result.exit_code == 0
    assert "total_discovered: 1" in result.stdout
    assert "totals_by_format: {'png': 1}" in result.stdout


def test_re_score_updates_manifest_quality_fields(tmp_path: Path) -> None:
    manifest_path = _manifest_path(tmp_path)

    result = runner.invoke(app, ["re-score", str(manifest_path)])

    assert result.exit_code == 0
    payload = manifest_path.read_text(encoding="utf-8")
    assert '"quality_score":' in payload


def test_dedupe_rewrites_manifest_with_unique_records(tmp_path: Path) -> None:
    manifest_path = _manifest_path(tmp_path, duplicate=True)

    result = runner.invoke(app, ["dedupe", str(manifest_path)])

    assert result.exit_code == 0
    lines = manifest_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    assert "removed 1 duplicates" in result.stdout


@pytest.mark.skipif(not VTRACER_AVAILABLE, reason="vtracer extra is not installed")
def test_convert_manifest_generates_svg_derivatives(tmp_path: Path) -> None:
    manifest_path = _manifest_path(tmp_path)

    result = runner.invoke(app, ["convert", str(manifest_path)])

    assert result.exit_code == 0
    payload = manifest_path.read_text(encoding="utf-8")
    assert '"conversion_status": "converted"' in payload
    assert "--line_art_fast.svg" in payload


def test_export_report_writes_optional_outputs(tmp_path: Path) -> None:
    manifest_path = _manifest_path(tmp_path)
    csv_output = tmp_path / "manifest.csv"
    markdown_output = tmp_path / "summary.md"

    result = runner.invoke(
        app,
        [
            "export-report",
            str(manifest_path),
            "--csv-output",
            str(csv_output),
            "--markdown-output",
            str(markdown_output),
        ],
    )

    assert result.exit_code == 0
    assert csv_output.exists()
    assert markdown_output.exists()
    assert "asset_url" in csv_output.read_text(encoding="utf-8")
    assert "# Manifest Summary" in markdown_output.read_text(encoding="utf-8")

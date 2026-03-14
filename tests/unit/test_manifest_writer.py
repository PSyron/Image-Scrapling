import json
from datetime import datetime, timezone
from pathlib import Path

from svg_scrapling.domain import AssetCandidate, AssetFormat
from svg_scrapling.download import AssetDownloader
from svg_scrapling.manifests import ManifestWriter, build_manifest_record, build_run_summary
from svg_scrapling.storage import create_run_layout


class FakeDownloadTransport:
    def download(self, url: str, *, headers: dict[str, str]) -> bytes:
        _ = url
        _ = headers
        return b"<svg></svg>"


def _candidate() -> AssetCandidate:
    return AssetCandidate(
        id="asset-1",
        query="tiger coloring page",
        source_page_url="https://example.com/page",
        asset_url="https://assets.example.com/tiger.svg",
        original_format=AssetFormat.SVG,
        domain="assets.example.com",
        title="Tiger outline",
    )


def test_manifest_writer_outputs_jsonl(tmp_path: Path) -> None:
    run_layout = create_run_layout(tmp_path / "runs", "run-1")
    candidate = _candidate()
    downloaded = AssetDownloader(transport=FakeDownloadTransport()).download(candidate, run_layout)
    record = build_manifest_record(
        candidate,
        downloaded_asset=downloaded,
        scraped_at=datetime(2026, 3, 14, 12, 0, tzinfo=timezone.utc),
    )
    writer = ManifestWriter(run_layout.manifests / "manifest.jsonl")

    output_path = writer.write((record,))

    payload = output_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(payload) == 1
    serialized = json.loads(payload[0])
    assert serialized["id"] == "asset-1"
    assert serialized["stored_original_path"].endswith(".svg")


def test_build_run_summary_aggregates_manifest_records(tmp_path: Path) -> None:
    run_layout = create_run_layout(tmp_path / "runs", "run-1")
    candidate = _candidate()
    downloaded = AssetDownloader(transport=FakeDownloadTransport()).download(candidate, run_layout)
    record = build_manifest_record(candidate, downloaded_asset=downloaded)

    summary = build_run_summary("run-1", candidate.query, (record,))

    assert summary.total_discovered == 1
    assert summary.total_downloaded == 1
    assert summary.total_accepted == 1
    assert summary.totals_by_format == {"svg": 1}

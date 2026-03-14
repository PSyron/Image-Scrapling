from pathlib import Path

from svg_scrapling.domain import AssetCandidate, AssetFormat
from svg_scrapling.download import AssetDownloader, build_original_asset_path
from svg_scrapling.storage import create_run_layout


class FakeDownloadTransport:
    def __init__(self, payload: bytes):
        self.payload = payload

    def download(self, url: str) -> bytes:
        _ = url
        return self.payload


def _candidate() -> AssetCandidate:
    return AssetCandidate(
        id="asset-1",
        query="Tiger Coloring Page",
        source_page_url="https://example.com/page",
        asset_url="https://assets.example.com/path/tiger.svg?ref=1",
        original_format=AssetFormat.SVG,
        domain="assets.example.com",
    )


def test_build_original_asset_path_is_deterministic(tmp_path: Path) -> None:
    run_layout = create_run_layout(tmp_path / "runs", "run-1")
    candidate = _candidate()

    output_path = build_original_asset_path(run_layout, candidate)

    assert output_path.name.startswith("tiger-coloring-page--assets-example-com--")
    assert output_path.suffix == ".svg"


def test_downloader_writes_original_asset(tmp_path: Path) -> None:
    run_layout = create_run_layout(tmp_path / "runs", "run-1")
    candidate = _candidate()
    downloader = AssetDownloader(transport=FakeDownloadTransport(b"<svg></svg>"))

    downloaded = downloader.download(candidate, run_layout)

    assert downloaded.stored_original_path.exists()
    assert downloaded.stored_original_path.read_bytes() == b"<svg></svg>"

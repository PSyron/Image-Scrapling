from pathlib import Path

from svg_scrapling.domain import AssetCandidate, AssetFormat
from svg_scrapling.download import AssetDownloader, build_original_asset_path
from svg_scrapling.storage import create_run_layout


class FakeDownloadTransport:
    def __init__(self, payload: bytes):
        self.payload = payload
        self.calls = 0

    def download(self, url: str) -> bytes:
        _ = url
        self.calls += 1
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
    transport = FakeDownloadTransport(b"<svg></svg>")
    downloader = AssetDownloader(transport=transport)

    downloaded = downloader.download(candidate, run_layout)

    assert downloaded.stored_original_path.exists()
    assert downloaded.stored_original_path.read_bytes() == b"<svg></svg>"
    assert transport.calls == 1


def test_downloader_reuses_existing_asset_when_enabled(tmp_path: Path) -> None:
    run_layout = create_run_layout(tmp_path / "runs", "run-1")
    candidate = _candidate()
    output_path = build_original_asset_path(run_layout, candidate)
    output_path.write_bytes(b"<svg>cached</svg>")
    transport = FakeDownloadTransport(b"<svg>fresh</svg>")
    downloader = AssetDownloader(transport=transport, skip_existing=True)

    downloaded = downloader.download(candidate, run_layout)

    assert downloaded.stored_original_path.read_bytes() == b"<svg>cached</svg>"
    assert downloaded.downloaded_at is None
    assert transport.calls == 0

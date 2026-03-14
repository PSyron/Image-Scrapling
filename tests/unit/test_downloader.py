from pathlib import Path

import pytest

from svg_scrapling.domain import AssetCandidate, AssetFormat
from svg_scrapling.download import (
    AssetDownloader,
    BlockedAssetDownloadError,
    build_download_headers,
    build_original_asset_path,
)
from svg_scrapling.storage import create_run_layout


class FakeDownloadTransport:
    def __init__(self, payload: bytes):
        self.payload = payload
        self.calls = 0
        self.last_headers: dict[str, str] | None = None

    def download(self, url: str, *, headers: dict[str, str]) -> bytes:
        _ = url
        self.calls += 1
        self.last_headers = dict(headers)
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
    assert transport.last_headers is not None
    assert transport.last_headers["User-Agent"] == "svg-scrapling/0.1.0"
    assert transport.last_headers["Referer"] == "https://example.com/page"
    assert transport.last_headers["Origin"] == "https://example.com"


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


def test_build_download_headers_include_provenance_context() -> None:
    headers = build_download_headers(_candidate())

    assert headers["User-Agent"] == "svg-scrapling/0.1.0"
    assert headers["Referer"] == "https://example.com/page"
    assert headers["Origin"] == "https://example.com"
    assert headers["Accept"].startswith("image/")


def test_downloader_surfaces_blocked_media_failures(tmp_path: Path) -> None:
    class BlockingTransport:
        def download(self, url: str, *, headers: dict[str, str]) -> bytes:
            _ = url
            _ = headers
            raise BlockedAssetDownloadError("Blocked by host with HTTP 403")

    run_layout = create_run_layout(tmp_path / "runs", "run-1")

    with pytest.raises(BlockedAssetDownloadError, match="Blocked by host"):
        AssetDownloader(transport=BlockingTransport()).download(_candidate(), run_layout)

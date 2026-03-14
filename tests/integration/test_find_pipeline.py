from __future__ import annotations

import binascii
import json
import struct
import zlib
from pathlib import Path

from typer.testing import CliRunner

import svg_scrapling.cli as cli_module
from svg_scrapling.cli import app
from svg_scrapling.config import FetchStrategy
from svg_scrapling.conversion import SvgPostProcessor, VTracerConverter
from svg_scrapling.download import AssetDownloader
from svg_scrapling.extraction import HtmlHeuristicExtractor
from svg_scrapling.licensing import LicensingPolicyEngine
from svg_scrapling.pipeline import PipelineDependencies
from svg_scrapling.quality import HeuristicQualityScorer
from svg_scrapling.ranking import CandidateDeduper
from svg_scrapling.scraping import FetchOrchestrator, StaticHtmlFetcher
from svg_scrapling.search import CandidatePage, FakeSearchProvider

runner = CliRunner()


class FixtureFetchTransport:
    def __init__(self, html: str):
        self.html = html

    def fetch(self, url: str, timeout_seconds: float, headers: dict[str, str]):
        _ = timeout_seconds
        _ = headers
        return 200, self.html, {"content-type": "text/html"}, url


class FixtureDownloadTransport:
    def __init__(self, payloads: dict[str, bytes]):
        self.payloads = payloads

    def download(self, url: str) -> bytes:
        return self.payloads[url]


def _write_fixture_png() -> bytes:
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

    def png_chunk(chunk_type: bytes, data: bytes) -> bytes:
        checksum = binascii.crc32(chunk_type + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", checksum)

    return b"".join(
        (
            b"\x89PNG\r\n\x1a\n",
            png_chunk(
                b"IHDR",
                struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0),
            ),
            png_chunk(b"IDAT", zlib.compress(b"".join(rows))),
            png_chunk(b"IEND", b""),
        )
    )


def test_assets_find_runs_happy_path_with_controlled_dependencies(
    tmp_path: Path,
    monkeypatch,
) -> None:
    html = """
    <html>
      <head><title>Tiger Page</title></head>
      <body>
        <figure>
          <img src="https://assets.example.com/tiger-outline.png" alt="Tiger outline printable" />
          <figcaption>Public domain tiger coloring page</figcaption>
        </figure>
      </body>
    </html>
    """

    def build_dependencies(_config):
        provider = FakeSearchProvider(
            name="fixture-provider",
            pages=(
                CandidatePage(
                    url="https://example.com/tiger-page",
                    query="tiger coloring page",
                    provider_name="fixture-provider",
                    rank=1,
                ),
            ),
        )
        fetcher = StaticHtmlFetcher(transport=FixtureFetchTransport(html), retries=0)
        return PipelineDependencies(
            search_provider=provider,
            fetch_orchestrator=FetchOrchestrator(static_fetcher=fetcher),
            extractor=HtmlHeuristicExtractor(),
            quality_scorer=HeuristicQualityScorer(),
            deduper=CandidateDeduper(),
            licensing_engine=LicensingPolicyEngine(),
            downloader=AssetDownloader(
                transport=FixtureDownloadTransport(
                    {"https://assets.example.com/tiger-outline.png": _write_fixture_png()}
                )
            ),
            converter=VTracerConverter(),
            svg_post_processor=SvgPostProcessor(),
        )

    monkeypatch.setattr(cli_module, "_build_pipeline_dependencies", build_dependencies)

    result = runner.invoke(
        app,
        [
            "find",
            "--query",
            "tiger coloring page",
            "--count",
            "1",
            "--preferred-format",
            "png",
            "--convert-to",
            "svg",
            "--mode",
            "licensed_only",
            "--allowed-licenses",
            "public_domain",
            "--fetch-strategy",
            FetchStrategy.STATIC_FIRST.value,
            "--output",
            str(tmp_path / "runs"),
        ],
    )

    assert result.exit_code == 0
    assert "Find pipeline completed" in result.stderr

    run_root = next((tmp_path / "runs").iterdir())
    manifest_path = run_root / "manifests" / "manifest.jsonl"
    summary_path = run_root / "manifests" / "summary.json"
    log_path = run_root / "logs" / "pipeline.log"

    assert manifest_path.exists()
    assert summary_path.exists()
    assert log_path.exists()

    manifest_payload = manifest_path.read_text(encoding="utf-8")
    assert '"license_normalized": "public_domain"' in manifest_payload
    assert '"conversion_status": "converted"' in manifest_payload

    summary_payload = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary_payload["total_discovered"] == 1
    assert summary_payload["total_downloaded"] == 1
    assert summary_payload["total_converted"] == 1
    assert "search:" in log_path.read_text(encoding="utf-8")

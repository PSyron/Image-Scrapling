"""Original asset download and deterministic path generation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha1
from pathlib import Path
from typing import Protocol, cast
from urllib.parse import urlparse
from urllib.request import urlopen

from svg_scrapling.domain import AssetCandidate, DownloadedAsset, DownloadStatus
from svg_scrapling.storage import RunLayout


def _slugify(value: str) -> str:
    normalized = "".join(character.lower() if character.isalnum() else "-" for character in value)
    compact = "-".join(part for part in normalized.split("-") if part)
    return compact or "asset"


def _extension_for(candidate: AssetCandidate) -> str:
    parsed = urlparse(candidate.asset_url)
    suffix = Path(parsed.path).suffix.lstrip(".").lower()
    if suffix:
        return suffix
    return candidate.original_format.value


def build_original_asset_path(run_layout: RunLayout, candidate: AssetCandidate) -> Path:
    query_slug = _slugify(candidate.query)
    domain_slug = _slugify(candidate.domain)
    stable_hash = sha1(candidate.asset_url.encode()).hexdigest()[:10]
    extension = _extension_for(candidate)
    filename = f"{query_slug}--{domain_slug}--{stable_hash}.{extension}"
    return run_layout.originals / filename


class DownloadTransport(Protocol):
    def download(self, url: str) -> bytes:
        """Download binary content for one asset URL."""


class UrlopenDownloadTransport:
    def download(self, url: str) -> bytes:
        with urlopen(url) as response:  # noqa: S310
            return cast(bytes, response.read())


@dataclass
class AssetDownloader:
    transport: DownloadTransport | None = None

    def __post_init__(self) -> None:
        if self.transport is None:
            self.transport = UrlopenDownloadTransport()

    def download(self, candidate: AssetCandidate, run_layout: RunLayout) -> DownloadedAsset:
        output_path = build_original_asset_path(run_layout, candidate)
        transport = self.transport
        assert transport is not None
        payload = transport.download(candidate.asset_url)
        output_path.write_bytes(payload)
        return DownloadedAsset(
            asset_id=candidate.id,
            source_page_url=candidate.source_page_url,
            asset_url=candidate.asset_url,
            original_format=candidate.original_format,
            stored_original_path=output_path,
            download_status=DownloadStatus.DOWNLOADED,
            downloaded_at=datetime.now(timezone.utc),
        )

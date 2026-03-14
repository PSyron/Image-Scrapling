"""Original asset download and deterministic path generation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha1
from pathlib import Path
from typing import Protocol, cast
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

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
    def download(self, url: str, *, headers: dict[str, str]) -> bytes:
        """Download binary content for one asset URL."""


class DownloadError(RuntimeError):
    """Explicit download failure."""


class BlockedAssetDownloadError(DownloadError):
    """Raised when a host blocks direct media retrieval."""


class MissingAssetDownloadError(DownloadError):
    """Raised when a referenced media asset no longer exists."""


def build_download_headers(candidate: AssetCandidate) -> dict[str, str]:
    parsed_source = urlparse(candidate.source_page_url)
    headers = {
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        "User-Agent": "svg-scrapling/0.1.0",
    }
    if parsed_source.scheme in {"http", "https"} and parsed_source.netloc:
        source_origin = f"{parsed_source.scheme}://{parsed_source.netloc}"
        headers["Referer"] = candidate.source_page_url
        headers["Origin"] = source_origin
    return headers


class UrlopenDownloadTransport:
    def download(self, url: str, *, headers: dict[str, str]) -> bytes:
        request = Request(url, headers=headers)
        try:
            with urlopen(request) as response:  # noqa: S310
                return cast(bytes, response.read())
        except HTTPError as exc:
            _ = exc.read()
            if exc.code in {401, 403}:
                raise BlockedAssetDownloadError(
                    f"Blocked by host with HTTP {exc.code} for {url}"
                ) from exc
            if exc.code in {404, 410}:
                raise MissingAssetDownloadError(
                    f"Asset not found with HTTP {exc.code} for {url}"
                ) from exc
            raise DownloadError(f"HTTP {exc.code} while downloading {url}") from exc
        except URLError as exc:
            raise DownloadError(f"Request failed while downloading {url}: {exc.reason}") from exc


@dataclass
class AssetDownloader:
    transport: DownloadTransport | None = None
    skip_existing: bool = True

    def __post_init__(self) -> None:
        if self.transport is None:
            self.transport = UrlopenDownloadTransport()

    def download(self, candidate: AssetCandidate, run_layout: RunLayout) -> DownloadedAsset:
        output_path = build_original_asset_path(run_layout, candidate)
        if self.skip_existing and output_path.exists():
            return DownloadedAsset(
                asset_id=candidate.id,
                source_page_url=candidate.source_page_url,
                asset_url=candidate.asset_url,
                original_format=candidate.original_format,
                stored_original_path=output_path,
                download_status=DownloadStatus.DOWNLOADED,
            )
        transport = self.transport
        assert transport is not None
        payload = transport.download(
            candidate.asset_url,
            headers=build_download_headers(candidate),
        )
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

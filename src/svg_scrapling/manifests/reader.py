"""Manifest JSONL loading helpers."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from svg_scrapling.domain import (
    AssetFormat,
    ConversionStatus,
    DownloadStatus,
    LicenseNormalized,
    ManifestRecord,
    ReuseStatus,
)


def _optional_path(value: str | None) -> Path | None:
    if value is None:
        return None
    return Path(value)


def load_manifest_records(path: Path) -> tuple[ManifestRecord, ...]:
    records: list[ManifestRecord] = []
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            normalized_line = raw_line.strip()
            if not normalized_line:
                continue
            payload = json.loads(normalized_line)
            records.append(
                ManifestRecord(
                    id=payload["id"],
                    query=payload["query"],
                    source_page_url=payload["source_page_url"],
                    asset_url=payload["asset_url"],
                    original_format=AssetFormat(payload["original_format"]),
                    stored_original_path=_optional_path(payload["stored_original_path"]),
                    derived_svg_path=_optional_path(payload["derived_svg_path"]),
                    title=payload["title"],
                    alt_text=payload["alt_text"],
                    domain=payload["domain"],
                    license_raw=payload["license_raw"],
                    license_normalized=LicenseNormalized(payload["license_normalized"]),
                    reuse_status=ReuseStatus(payload["reuse_status"]),
                    author_or_owner=payload["author_or_owner"],
                    attribution_required=payload["attribution_required"],
                    scraped_at=datetime.fromisoformat(payload["scraped_at"]),
                    download_status=DownloadStatus(payload["download_status"]),
                    conversion_status=ConversionStatus(payload["conversion_status"]),
                    quality_score=payload["quality_score"],
                    style_tags=tuple(payload["style_tags"]),
                    is_outline_like=payload["is_outline_like"],
                    is_black_and_white_like=payload["is_black_and_white_like"],
                    is_kids_friendly_candidate=payload["is_kids_friendly_candidate"],
                    dedupe_hash=payload["dedupe_hash"],
                    notes=tuple(payload["notes"]),
                )
            )
    return tuple(records)

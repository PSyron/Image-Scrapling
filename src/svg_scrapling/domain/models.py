"""Strongly typed domain contracts shared across the pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, cast


class _StringEnum(str, Enum):
    """Compatibility helper for string-valued enums on Python 3.9+."""


class AssetFormat(_StringEnum):
    SVG = "svg"
    PNG = "png"
    JPG = "jpg"
    JPEG = "jpeg"
    WEBP = "webp"
    UNKNOWN = "unknown"


class LicenseNormalized(_StringEnum):
    PUBLIC_DOMAIN = "public_domain"
    CC0 = "cc0"
    CC_BY = "cc_by"
    CC_BY_SA = "cc_by_sa"
    ROYALTY_FREE = "royalty_free"
    COMMERCIAL_UNKNOWN = "commercial_unknown"
    ALL_RIGHTS_RESERVED = "all_rights_reserved"
    UNKNOWN = "unknown"


class ReuseStatus(_StringEnum):
    ALLOWED = "allowed"
    ALLOWED_WITH_ATTRIBUTION = "allowed_with_attribution"
    RESTRICTED = "restricted"
    UNKNOWN = "unknown"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"


class DownloadStatus(_StringEnum):
    PENDING = "pending"
    DOWNLOADED = "downloaded"
    FAILED = "failed"
    SKIPPED = "skipped"


class ConversionStatus(_StringEnum):
    NOT_REQUESTED = "not_requested"
    CONVERTED = "converted"
    FAILED = "failed"
    SKIPPED = "skipped"


def _serialize(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_serialize(item) for item in value]
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if isinstance(value, set):
        return sorted(_serialize(item) for item in value)
    if isinstance(value, frozenset):
        return sorted(_serialize(item) for item in value)
    return value


class SerializableModel:
    """Small JSON-safe serialization helper for dataclass models."""

    def to_dict(self) -> dict[str, Any]:
        return {
            model_field.name: _serialize(getattr(self, model_field.name))
            for model_field in fields(cast(Any, self))
        }


@dataclass(frozen=True)
class SearchQuery(SerializableModel):
    query: str
    requested_count: int
    preferred_format: AssetFormat = AssetFormat.SVG
    language_hints: tuple[str, ...] = ()
    style_hints: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        normalized_query = self.query.strip()
        if not normalized_query:
            raise ValueError("query must not be blank")
        if self.requested_count <= 0:
            raise ValueError("requested_count must be greater than zero")
        object.__setattr__(self, "query", normalized_query)


@dataclass(frozen=True)
class SearchIntent(SerializableModel):
    search_query: SearchQuery
    expanded_queries: tuple[str, ...]
    preferred_format: AssetFormat
    fallback_format: AssetFormat | None = None
    convert_to: AssetFormat | None = None

    def __post_init__(self) -> None:
        if not self.expanded_queries:
            raise ValueError("expanded_queries must contain at least one query")


@dataclass(frozen=True)
class AssetCandidate(SerializableModel):
    id: str
    query: str
    source_page_url: str
    asset_url: str
    original_format: AssetFormat
    domain: str
    title: str | None = None
    alt_text: str | None = None
    author_or_owner: str | None = None
    attribution_hint: str | None = None
    license_hint: str | None = None
    style_tags: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("id must not be blank")
        if not self.query.strip():
            raise ValueError("query must not be blank")
        if not self.source_page_url.strip():
            raise ValueError("source_page_url must not be blank")
        if not self.asset_url.strip():
            raise ValueError("asset_url must not be blank")
        if not self.domain.strip():
            raise ValueError("domain must not be blank")


@dataclass(frozen=True)
class DownloadedAsset(SerializableModel):
    asset_id: str
    source_page_url: str
    asset_url: str
    original_format: AssetFormat
    stored_original_path: Path
    download_status: DownloadStatus
    downloaded_at: datetime | None = None


@dataclass(frozen=True)
class ConvertedAsset(SerializableModel):
    asset_id: str
    source_raster_path: Path
    derived_svg_path: Path | None
    conversion_status: ConversionStatus
    preset: str | None = None
    conversion_score: float | None = None
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class LicenseAssessment(SerializableModel):
    asset_id: str
    license_raw: str | None
    license_normalized: LicenseNormalized
    reuse_status: ReuseStatus
    attribution_required: bool
    confidence: float | None = None
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class QualityAssessment(SerializableModel):
    asset_id: str
    quality_score: float
    style_tags: tuple[str, ...]
    is_outline_like: bool
    is_black_and_white_like: bool
    is_kids_friendly_candidate: bool
    dedupe_hash: str | None = None
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class ManifestRecord(SerializableModel):
    id: str
    query: str
    source_page_url: str
    asset_url: str
    original_format: AssetFormat
    stored_original_path: Path | None
    derived_svg_path: Path | None
    title: str | None
    alt_text: str | None
    domain: str
    license_raw: str | None
    license_normalized: LicenseNormalized
    reuse_status: ReuseStatus
    author_or_owner: str | None
    attribution_required: bool
    scraped_at: datetime
    download_status: DownloadStatus
    conversion_status: ConversionStatus
    quality_score: float | None
    style_tags: tuple[str, ...]
    is_outline_like: bool
    is_black_and_white_like: bool
    is_kids_friendly_candidate: bool
    dedupe_hash: str | None
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("id must not be blank")
        if not self.query.strip():
            raise ValueError("query must not be blank")
        if not self.source_page_url.strip():
            raise ValueError("source_page_url must not be blank")
        if not self.asset_url.strip():
            raise ValueError("asset_url must not be blank")
        if not self.domain.strip():
            raise ValueError("domain must not be blank")


@dataclass(frozen=True)
class PipelineRunSummary(SerializableModel):
    run_id: str
    query: str
    total_discovered: int
    total_downloaded: int
    total_accepted: int
    total_rejected: int
    total_converted: int
    totals_by_format: dict[str, int] = field(default_factory=dict)
    totals_by_domain: dict[str, int] = field(default_factory=dict)
    totals_by_reuse_status: dict[str, int] = field(default_factory=dict)
    rejection_reasons: dict[str, int] = field(default_factory=dict)
    conversion_failures: dict[str, int] = field(default_factory=dict)
    duplicate_counts: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.run_id.strip():
            raise ValueError("run_id must not be blank")
        if not self.query.strip():
            raise ValueError("query must not be blank")
        for field_name in (
            "total_discovered",
            "total_downloaded",
            "total_accepted",
            "total_rejected",
            "total_converted",
        ):
            if getattr(self, field_name) < 0:
                raise ValueError(f"{field_name} must not be negative")

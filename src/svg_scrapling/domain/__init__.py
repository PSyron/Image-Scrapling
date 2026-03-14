"""Typed domain models shared across the pipeline."""

from svg_scrapling.domain.models import (
    AssetCandidate,
    AssetFormat,
    ConversionStatus,
    ConvertedAsset,
    DownloadedAsset,
    DownloadStatus,
    LicenseAssessment,
    LicenseNormalized,
    ManifestRecord,
    PipelineRunSummary,
    QualityAssessment,
    ReuseStatus,
    SearchIntent,
    SearchQuery,
)

__all__ = [
    "AssetCandidate",
    "AssetFormat",
    "ConversionStatus",
    "ConvertedAsset",
    "DownloadStatus",
    "DownloadedAsset",
    "LicenseAssessment",
    "LicenseNormalized",
    "ManifestRecord",
    "PipelineRunSummary",
    "QualityAssessment",
    "ReuseStatus",
    "SearchIntent",
    "SearchQuery",
]

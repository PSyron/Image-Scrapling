"""Typed configuration models for CLI and pipeline entrypoints."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

SUPPORTED_LICENSE_LABELS = frozenset(
    {
        "public_domain",
        "cc0",
        "cc_by",
        "cc_by_sa",
        "royalty_free",
        "commercial_unknown",
        "all_rights_reserved",
        "unknown",
    }
)


class _StringEnum(str, Enum):
    @classmethod
    def values(cls) -> tuple[str, ...]:
        return tuple(member.value for member in cls)


class LicenseMode(_StringEnum):
    LICENSED_ONLY = "licensed_only"
    PROVENANCE_ONLY = "provenance_only"


class OutputFormat(_StringEnum):
    SVG = "svg"
    PNG = "png"


class FetchStrategy(_StringEnum):
    STATIC_FIRST = "static_first"
    DYNAMIC_ON_FAILURE = "dynamic_on_failure"
    DYNAMIC_ONLY = "dynamic_only"


@dataclass(frozen=True)
class FindAssetsConfig:
    """Core config shared by CLI parsing and pipeline orchestration."""

    query: str
    count: int = 100
    preferred_format: OutputFormat = OutputFormat.SVG
    fallback_format: OutputFormat | None = None
    convert_to: OutputFormat | None = None
    mode: LicenseMode = LicenseMode.PROVENANCE_ONLY
    allowed_licenses: frozenset[str] = field(default_factory=frozenset)
    fetch_strategy: FetchStrategy = FetchStrategy.STATIC_FIRST
    output_root: Path = Path("data/runs")

    def __post_init__(self) -> None:
        normalized_query = self.query.strip()
        if not normalized_query:
            raise ValueError("query must not be blank")
        if self.count <= 0:
            raise ValueError("count must be greater than zero")

        normalized_output_root = self.output_root.expanduser()
        object.__setattr__(self, "query", normalized_query)
        object.__setattr__(self, "output_root", normalized_output_root)

        normalized_licenses = frozenset(label.strip().lower() for label in self.allowed_licenses)
        if "" in normalized_licenses:
            raise ValueError("allowed_licenses must not contain blank values")

        unknown_licenses = normalized_licenses.difference(SUPPORTED_LICENSE_LABELS)
        if unknown_licenses:
            supported_labels = ", ".join(sorted(SUPPORTED_LICENSE_LABELS))
            invalid_labels = ", ".join(sorted(unknown_licenses))
            raise ValueError(
                "allowed_licenses contains unsupported values: "
                f"{invalid_labels}. Supported values: {supported_labels}"
            )

        if self.mode == LicenseMode.LICENSED_ONLY and not normalized_licenses:
            raise ValueError("allowed_licenses must be provided when mode is licensed_only")

        object.__setattr__(self, "allowed_licenses", normalized_licenses)

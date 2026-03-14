"""Extractor contracts, registry, and generic extraction flow."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1
from urllib.parse import urlparse

from svg_scrapling.domain import AssetCandidate, AssetFormat


@dataclass(frozen=True)
class ExtractedAssetHint:
    """Raw extraction evidence ready to be normalized into an asset candidate."""

    asset_url: str
    original_format: AssetFormat
    title: str | None = None
    alt_text: str | None = None
    author_or_owner: str | None = None
    attribution_hint: str | None = None
    license_hint: str | None = None
    style_tags: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class RejectedAssetHint:
    """Structured rejection for unsupported or incomplete extracted evidence."""

    asset_url: str
    reason: str


@dataclass(frozen=True)
class ExtractionInput:
    """Fetched page material handed to extractors."""

    source_page_url: str
    query: str
    domain: str
    title: str | None = None
    extracted_assets: tuple[ExtractedAssetHint, ...] = ()


@dataclass(frozen=True)
class ExtractionResult:
    """Normalized extraction output."""

    candidates: tuple[AssetCandidate, ...]
    rejected: tuple[RejectedAssetHint, ...]


class GenericAssetExtractor:
    """Common extractor flow for already-discovered asset hints."""

    def extract(self, extraction_input: ExtractionInput) -> ExtractionResult:
        candidates: list[AssetCandidate] = []
        rejected: list[RejectedAssetHint] = []

        for hint in extraction_input.extracted_assets:
            asset_url = hint.asset_url.strip()
            if not asset_url:
                rejected.append(
                    RejectedAssetHint(
                        asset_url="",
                        reason="asset_url must not be blank",
                    )
                )
                continue

            parsed = urlparse(asset_url)
            if not parsed.scheme or not parsed.netloc:
                rejected.append(
                    RejectedAssetHint(
                        asset_url=asset_url,
                        reason="asset_url must be an absolute URL",
                    )
                )
                continue

            candidate_id = sha1(
                f"{extraction_input.source_page_url}|{asset_url}".encode()
            ).hexdigest()[:12]
            candidates.append(
                AssetCandidate(
                    id=candidate_id,
                    query=extraction_input.query,
                    source_page_url=extraction_input.source_page_url,
                    asset_url=asset_url,
                    original_format=hint.original_format,
                    domain=extraction_input.domain,
                    title=hint.title or extraction_input.title,
                    alt_text=hint.alt_text,
                    author_or_owner=hint.author_or_owner,
                    attribution_hint=hint.attribution_hint,
                    license_hint=hint.license_hint,
                    style_tags=hint.style_tags,
                    notes=hint.notes,
                )
            )

        return ExtractionResult(
            candidates=tuple(candidates),
            rejected=tuple(rejected),
        )


class ExtractionRegistry:
    """Registry for source-specific extractor overrides."""

    def __init__(self, default_extractor: GenericAssetExtractor | None = None) -> None:
        self._default_extractor = default_extractor or GenericAssetExtractor()
        self._extractors: dict[str, GenericAssetExtractor] = {}

    def register(self, domain: str, extractor: GenericAssetExtractor) -> None:
        normalized_domain = domain.strip().casefold()
        if not normalized_domain:
            raise ValueError("domain must not be blank")
        self._extractors[normalized_domain] = extractor

    def resolve(self, domain: str) -> GenericAssetExtractor:
        normalized_domain = domain.strip().casefold()
        return self._extractors.get(normalized_domain, self._default_extractor)

    def extract(self, extraction_input: ExtractionInput) -> ExtractionResult:
        extractor = self.resolve(extraction_input.domain)
        return extractor.extract(extraction_input)

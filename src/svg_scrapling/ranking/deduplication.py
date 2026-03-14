"""Layered deduplication with provenance preservation."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qsl, urlparse, urlunparse

from svg_scrapling.domain import AssetCandidate


@dataclass(frozen=True)
class DedupedCandidate:
    """Canonical candidate with merged provenance."""

    candidate: AssetCandidate
    dedupe_key: str
    provenance_page_urls: tuple[str, ...]
    asset_urls: tuple[str, ...]


@dataclass(frozen=True)
class DedupeResult:
    """Deduplication result with summary counts."""

    kept: tuple[DedupedCandidate, ...]
    duplicates_removed: int


class CandidateDeduper:
    """Apply layered duplicate detection and preserve provenance."""

    def dedupe(
        self,
        candidates: tuple[AssetCandidate, ...],
        content_hashes: dict[str, str] | None = None,
        perceptual_hashes: dict[str, str] | None = None,
        structure_hashes: dict[str, str] | None = None,
    ) -> DedupeResult:
        content_hashes = content_hashes or {}
        perceptual_hashes = perceptual_hashes or {}
        structure_hashes = structure_hashes or {}

        kept: list[DedupedCandidate] = []
        by_key: dict[str, int] = {}
        duplicates_removed = 0

        for candidate in candidates:
            dedupe_key = self._dedupe_key(
                candidate,
                content_hashes=content_hashes,
                perceptual_hashes=perceptual_hashes,
                structure_hashes=structure_hashes,
            )
            if dedupe_key in by_key:
                duplicates_removed += 1
                existing_index = by_key[dedupe_key]
                existing = kept[existing_index]
                kept[existing_index] = DedupedCandidate(
                    candidate=existing.candidate,
                    dedupe_key=existing.dedupe_key,
                    provenance_page_urls=tuple(
                        sorted(
                            {
                                *existing.provenance_page_urls,
                                candidate.source_page_url,
                            }
                        )
                    ),
                    asset_urls=tuple(
                        sorted(
                            {
                                *existing.asset_urls,
                                candidate.asset_url,
                            }
                        )
                    ),
                )
                continue

            by_key[dedupe_key] = len(kept)
            kept.append(
                DedupedCandidate(
                    candidate=candidate,
                    dedupe_key=dedupe_key,
                    provenance_page_urls=(candidate.source_page_url,),
                    asset_urls=(candidate.asset_url,),
                )
            )

        return DedupeResult(
            kept=tuple(kept),
            duplicates_removed=duplicates_removed,
        )

    def _dedupe_key(
        self,
        candidate: AssetCandidate,
        *,
        content_hashes: dict[str, str],
        perceptual_hashes: dict[str, str],
        structure_hashes: dict[str, str],
    ) -> str:
        if candidate.id in content_hashes:
            return f"content:{content_hashes[candidate.id]}"
        if candidate.id in structure_hashes:
            return f"structure:{structure_hashes[candidate.id]}"
        if candidate.id in perceptual_hashes:
            return f"perceptual:{perceptual_hashes[candidate.id]}"

        normalized_url = self._normalize_url(candidate.asset_url)
        return f"normalized_url:{normalized_url}"

    def _normalize_url(self, url: str) -> str:
        parsed = urlparse(url)
        normalized_query = parse_qsl(parsed.query, keep_blank_values=False)
        normalized = parsed._replace(
            scheme=parsed.scheme.lower(),
            netloc=parsed.netloc.lower(),
            query="&".join(f"{key}={value}" for key, value in sorted(normalized_query)),
            fragment="",
        )
        return urlunparse(normalized)

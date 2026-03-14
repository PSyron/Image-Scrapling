"""License normalization, assessment, and policy evaluation."""

from __future__ import annotations

import re
from dataclasses import dataclass

from svg_scrapling.config import LicenseMode
from svg_scrapling.domain import AssetCandidate, LicenseAssessment, LicenseNormalized, ReuseStatus

_NORMALIZATION_RULES: tuple[tuple[LicenseNormalized, tuple[str, ...]], ...] = (
    (
        LicenseNormalized.PUBLIC_DOMAIN,
        ("public domain", "public-domain"),
    ),
    (
        LicenseNormalized.CC0,
        ("cc0", "creative commons zero"),
    ),
    (
        LicenseNormalized.CC_BY,
        ("cc by", "cc-by", "creative commons attribution"),
    ),
    (
        LicenseNormalized.CC_BY_SA,
        ("cc by sa", "cc-by-sa", "creative commons attribution sharealike"),
    ),
    (
        LicenseNormalized.ROYALTY_FREE,
        ("royalty free", "royalty-free"),
    ),
    (
        LicenseNormalized.COMMERCIAL_UNKNOWN,
        ("commercial use unknown", "license unclear", "licensing unclear"),
    ),
    (
        LicenseNormalized.ALL_RIGHTS_RESERVED,
        ("all rights reserved",),
    ),
)


@dataclass(frozen=True)
class LicensePolicyDecision:
    asset_id: str
    keep: bool
    reason: str
    requires_manual_review: bool


def _canonicalize(text: str) -> str:
    lowered = text.casefold().strip()
    lowered = lowered.replace("_", " ").replace("-", " ")
    return " ".join(lowered.split())


def normalize_license_hint(
    raw_hint: str | None,
) -> tuple[LicenseNormalized, float, tuple[str, ...]]:
    if raw_hint is None or not raw_hint.strip():
        return LicenseNormalized.UNKNOWN, 0.0, ("no_license_hint",)

    normalized_hint = _canonicalize(raw_hint)
    for normalized_license, markers in _NORMALIZATION_RULES:
        for marker in markers:
            canonical_marker = _canonicalize(marker)
            if normalized_hint == canonical_marker:
                return (
                    normalized_license,
                    0.98,
                    (f"normalized_exact:{canonical_marker}",),
                )
            if canonical_marker in normalized_hint:
                return (
                    normalized_license,
                    0.82,
                    (f"normalized_partial:{canonical_marker}",),
                )

    if re.search(r"\bcc\b|\blicense\b|\battribution\b", normalized_hint):
        return (
            LicenseNormalized.COMMERCIAL_UNKNOWN,
            0.45,
            ("manual_review:license_like_text_without_supported_match",),
        )

    return LicenseNormalized.UNKNOWN, 0.15, ("unrecognized_license_hint",)


def map_reuse_status(
    normalized_license: LicenseNormalized,
    *,
    confidence: float,
) -> tuple[ReuseStatus, bool]:
    if normalized_license in {LicenseNormalized.PUBLIC_DOMAIN, LicenseNormalized.CC0}:
        return ReuseStatus.ALLOWED, False
    if normalized_license in {LicenseNormalized.CC_BY, LicenseNormalized.CC_BY_SA}:
        return ReuseStatus.ALLOWED_WITH_ATTRIBUTION, False
    if normalized_license == LicenseNormalized.ROYALTY_FREE:
        if confidence < 0.7:
            return ReuseStatus.MANUAL_REVIEW_REQUIRED, True
        return ReuseStatus.ALLOWED, False
    if normalized_license == LicenseNormalized.COMMERCIAL_UNKNOWN:
        return ReuseStatus.MANUAL_REVIEW_REQUIRED, True
    if normalized_license == LicenseNormalized.ALL_RIGHTS_RESERVED:
        return ReuseStatus.RESTRICTED, False
    return ReuseStatus.UNKNOWN, confidence < 0.7


def assess_candidate_license(candidate: AssetCandidate) -> LicenseAssessment:
    raw_hint = candidate.license_hint or candidate.attribution_hint
    normalized_license, confidence, notes = normalize_license_hint(raw_hint)
    reuse_status, requires_manual_review = map_reuse_status(
        normalized_license,
        confidence=confidence,
    )
    if requires_manual_review and reuse_status != ReuseStatus.RESTRICTED:
        reuse_status = ReuseStatus.MANUAL_REVIEW_REQUIRED

    attribution_required = reuse_status == ReuseStatus.ALLOWED_WITH_ATTRIBUTION
    return LicenseAssessment(
        asset_id=candidate.id,
        license_raw=raw_hint,
        license_normalized=normalized_license,
        reuse_status=reuse_status,
        attribution_required=attribution_required,
        confidence=confidence,
        notes=notes,
    )


class LicensingPolicyEngine:
    """Apply the configured licensing mode without upgrading weak evidence."""

    def evaluate(
        self,
        assessment: LicenseAssessment,
        *,
        mode: LicenseMode,
        allowed_licenses: frozenset[str],
    ) -> LicensePolicyDecision:
        if mode == LicenseMode.PROVENANCE_ONLY:
            return LicensePolicyDecision(
                asset_id=assessment.asset_id,
                keep=True,
                reason="retained_for_provenance",
                requires_manual_review=assessment.reuse_status
                == ReuseStatus.MANUAL_REVIEW_REQUIRED,
            )

        if assessment.reuse_status == ReuseStatus.ALLOWED and (
            assessment.license_normalized.value in allowed_licenses
        ):
            return LicensePolicyDecision(
                asset_id=assessment.asset_id,
                keep=True,
                reason="allowed_license",
                requires_manual_review=False,
            )
        if assessment.reuse_status == ReuseStatus.ALLOWED_WITH_ATTRIBUTION and (
            assessment.license_normalized.value in allowed_licenses
        ):
            return LicensePolicyDecision(
                asset_id=assessment.asset_id,
                keep=True,
                reason="allowed_with_attribution",
                requires_manual_review=False,
            )
        if assessment.reuse_status == ReuseStatus.MANUAL_REVIEW_REQUIRED:
            return LicensePolicyDecision(
                asset_id=assessment.asset_id,
                keep=False,
                reason="manual_review_required",
                requires_manual_review=True,
            )
        if assessment.reuse_status == ReuseStatus.RESTRICTED:
            return LicensePolicyDecision(
                asset_id=assessment.asset_id,
                keep=False,
                reason="restricted_license",
                requires_manual_review=False,
            )
        return LicensePolicyDecision(
            asset_id=assessment.asset_id,
            keep=False,
            reason="unsupported_or_unknown_license",
            requires_manual_review=assessment.reuse_status == ReuseStatus.UNKNOWN,
        )

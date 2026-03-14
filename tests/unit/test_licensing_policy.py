from svg_scrapling.config import LicenseMode
from svg_scrapling.domain import AssetCandidate, AssetFormat, LicenseNormalized, ReuseStatus
from svg_scrapling.licensing import (
    LicensingPolicyEngine,
    assess_candidate_license,
    normalize_license_hint,
)


def _candidate(license_hint: str | None) -> AssetCandidate:
    return AssetCandidate(
        id="asset-1",
        query="tiger coloring page",
        source_page_url="https://example.com/page",
        asset_url="https://assets.example.com/tiger.svg",
        original_format=AssetFormat.SVG,
        domain="assets.example.com",
        license_hint=license_hint,
    )


def test_normalize_license_hint_supports_representative_labels() -> None:
    normalized, confidence, notes = normalize_license_hint("CC BY 4.0 attribution required")

    assert normalized == LicenseNormalized.CC_BY
    assert confidence >= 0.8
    assert notes == ("normalized_partial:cc by",)


def test_assess_candidate_license_marks_unknown_without_upgrading_safety() -> None:
    assessment = assess_candidate_license(_candidate(None))

    assert assessment.license_normalized == LicenseNormalized.UNKNOWN
    assert assessment.reuse_status == ReuseStatus.MANUAL_REVIEW_REQUIRED
    assert assessment.confidence == 0.0


def test_policy_engine_allows_allowlisted_license_for_licensed_only() -> None:
    assessment = assess_candidate_license(_candidate("public domain"))
    decision = LicensingPolicyEngine().evaluate(
        assessment,
        mode=LicenseMode.LICENSED_ONLY,
        allowed_licenses=frozenset({"public_domain"}),
    )

    assert decision.keep is True
    assert decision.reason == "allowed_license"


def test_policy_engine_rejects_unknown_license_for_licensed_only() -> None:
    assessment = assess_candidate_license(_candidate("license info not provided"))
    decision = LicensingPolicyEngine().evaluate(
        assessment,
        mode=LicenseMode.LICENSED_ONLY,
        allowed_licenses=frozenset({"cc0", "public_domain"}),
    )

    assert decision.keep is False
    assert decision.reason == "manual_review_required"
    assert decision.requires_manual_review is True


def test_policy_engine_retains_provenance_without_claiming_safety() -> None:
    assessment = assess_candidate_license(_candidate("all rights reserved"))
    decision = LicensingPolicyEngine().evaluate(
        assessment,
        mode=LicenseMode.PROVENANCE_ONLY,
        allowed_licenses=frozenset(),
    )

    assert decision.keep is True
    assert decision.reason == "retained_for_provenance"

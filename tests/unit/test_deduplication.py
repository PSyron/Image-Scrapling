from svg_scrapling.domain import AssetCandidate, AssetFormat
from svg_scrapling.ranking import CandidateDeduper


def _candidate(candidate_id: str, source_page_url: str, asset_url: str) -> AssetCandidate:
    return AssetCandidate(
        id=candidate_id,
        query="tiger coloring page",
        source_page_url=source_page_url,
        asset_url=asset_url,
        original_format=AssetFormat.SVG,
        domain="example.com",
    )


def test_deduper_merges_exact_duplicates_and_preserves_provenance() -> None:
    deduper = CandidateDeduper()
    result = deduper.dedupe(
        (
            _candidate("asset-1", "https://example.com/page-1", "https://example.com/a.svg"),
            _candidate("asset-2", "https://example.com/page-2", "https://example.com/a.svg"),
        )
    )

    assert len(result.kept) == 1
    assert result.duplicates_removed == 1
    assert result.kept[0].provenance_page_urls == (
        "https://example.com/page-1",
        "https://example.com/page-2",
    )


def test_deduper_merges_normalized_url_duplicates() -> None:
    deduper = CandidateDeduper()
    result = deduper.dedupe(
        (
            _candidate(
                "asset-1", "https://example.com/page-1", "https://example.com/a.svg?b=2&a=1"
            ),
            _candidate(
                "asset-2", "https://example.com/page-2", "https://example.com/a.svg?a=1&b=2"
            ),
        )
    )

    assert len(result.kept) == 1
    assert result.kept[0].dedupe_key.startswith("normalized_url:")


def test_deduper_prefers_hash_based_keys_when_available() -> None:
    deduper = CandidateDeduper()
    result = deduper.dedupe(
        (
            _candidate("asset-1", "https://example.com/page-1", "https://example.com/a.svg"),
            _candidate("asset-2", "https://example.com/page-2", "https://different.com/other.svg"),
        ),
        content_hashes={
            "asset-1": "same-hash",
            "asset-2": "same-hash",
        },
    )

    assert len(result.kept) == 1
    assert result.kept[0].dedupe_key == "content:same-hash"

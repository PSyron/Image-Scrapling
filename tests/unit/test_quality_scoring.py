from svg_scrapling.domain import AssetCandidate, AssetFormat
from svg_scrapling.quality import HeuristicQualityScorer


def test_quality_scorer_exposes_component_scores() -> None:
    scorer = HeuristicQualityScorer()
    candidate = AssetCandidate(
        id="asset-1",
        query="tiger coloring page",
        source_page_url="https://example.org/page",
        asset_url="https://example.org/tiger.svg",
        original_format=AssetFormat.SVG,
        domain="example.org",
        title="Tiger outline",
        alt_text="Black and white tiger outline for kids",
        style_tags=("outline", "black_and_white"),
    )

    assessment = scorer.score(candidate)

    assert assessment.component_scores["format_score"] == 1.0
    assert assessment.component_scores["source_trust_score"] == 0.8
    assert assessment.is_outline_like is True
    assert assessment.is_black_and_white_like is True
    assert assessment.is_kids_friendly_candidate is True


def test_quality_scorer_records_negative_signals() -> None:
    scorer = HeuristicQualityScorer()
    candidate = AssetCandidate(
        id="asset-2",
        query="busy photo tiger",
        source_page_url="https://example.com/page",
        asset_url="https://example.com/tiger.png",
        original_format=AssetFormat.PNG,
        domain="example.com",
        title="Busy photo tiger thumbnail",
        style_tags=(),
    )

    assessment = scorer.score(candidate)

    assert "contains_negative_signal:photo" in assessment.rejection_reasons
    assert "contains_negative_signal:thumbnail" in assessment.rejection_reasons

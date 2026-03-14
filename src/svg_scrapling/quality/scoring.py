"""Heuristic quality scoring for coloring-style assets."""

from __future__ import annotations

from dataclasses import dataclass

from svg_scrapling.domain import AssetCandidate, AssetFormat, QualityAssessment

POSITIVE_KEYWORDS = {
    "outline": ("outline", "kontur", "line art", "line-art", "coloring", "kolorowanka"),
    "black_and_white": (
        "black and white",
        "black_and_white",
        "czarno-biale",
        "bw",
        "monochrome",
    ),
    "kids": ("kids", "for kids", "dla dzieci", "printable", "do druku"),
}

NEGATIVE_KEYWORDS = ("watermark", "photo", "thumbnail", "textured", "busy")


@dataclass(frozen=True)
class HeuristicQualityScorer:
    """Simple, inspectable v1 heuristic scorer."""

    svg_format_score: float = 1.0
    png_format_score: float = 0.7
    default_format_score: float = 0.35

    def score(self, candidate: AssetCandidate) -> QualityAssessment:
        searchable_text = " ".join(
            filter(
                None,
                (
                    candidate.query,
                    candidate.title,
                    candidate.alt_text,
                    " ".join(candidate.style_tags),
                    " ".join(candidate.notes),
                ),
            )
        ).casefold()
        style_tags = tuple(tag.casefold() for tag in candidate.style_tags)

        component_scores = {
            "format_score": self._format_score(candidate.original_format),
            "source_trust_score": self._source_trust_score(candidate.domain),
            "outline_likelihood": self._keyword_score(
                searchable_text,
                POSITIVE_KEYWORDS["outline"],
            ),
            "black_and_white_likelihood": self._keyword_score(
                searchable_text, POSITIVE_KEYWORDS["black_and_white"]
            ),
            "kids_coloring_suitability": self._keyword_score(
                searchable_text, POSITIVE_KEYWORDS["kids"]
            ),
            "conversion_suitability": self._conversion_suitability(
                candidate.original_format, searchable_text
            ),
        }

        rejection_reasons: list[str] = []
        for keyword in NEGATIVE_KEYWORDS:
            if keyword in searchable_text:
                rejection_reasons.append(f"contains_negative_signal:{keyword}")

        quality_score = round(sum(component_scores.values()) / len(component_scores), 3)
        return QualityAssessment(
            asset_id=candidate.id,
            quality_score=quality_score,
            style_tags=style_tags,
            is_outline_like=component_scores["outline_likelihood"] >= 0.75,
            is_black_and_white_like=component_scores["black_and_white_likelihood"] >= 0.75,
            is_kids_friendly_candidate=component_scores["kids_coloring_suitability"] >= 0.6,
            dedupe_hash=None,
            component_scores=component_scores,
            rejection_reasons=tuple(rejection_reasons),
            notes=(),
        )

    def _format_score(self, asset_format: AssetFormat) -> float:
        if asset_format == AssetFormat.SVG:
            return self.svg_format_score
        if asset_format == AssetFormat.PNG:
            return self.png_format_score
        return self.default_format_score

    def _source_trust_score(self, domain: str) -> float:
        normalized = domain.casefold()
        if normalized.endswith(".edu") or normalized.endswith(".gov"):
            return 0.9
        if normalized.endswith(".org"):
            return 0.8
        if normalized.endswith(".com"):
            return 0.6
        return 0.5

    def _keyword_score(self, searchable_text: str, keywords: tuple[str, ...]) -> float:
        matches = sum(1 for keyword in keywords if keyword in searchable_text)
        if matches == 0:
            return 0.2
        return min(1.0, 0.2 + 0.3 * matches)

    def _conversion_suitability(self, asset_format: AssetFormat, searchable_text: str) -> float:
        if asset_format == AssetFormat.SVG:
            return 1.0
        if asset_format == AssetFormat.PNG and "outline" in searchable_text:
            return 0.8
        if asset_format == AssetFormat.PNG:
            return 0.55
        return 0.3

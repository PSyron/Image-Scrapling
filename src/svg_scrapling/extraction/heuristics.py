"""Heuristic HTML extraction for direct SVG, raster, and embedded SVG assets."""

from __future__ import annotations

import re
from dataclasses import dataclass
from html import unescape
from urllib.parse import urljoin, urlparse

from scrapling import Selector

from svg_scrapling.domain import AssetFormat
from svg_scrapling.extraction.contracts import (
    ExtractedAssetHint,
    ExtractionInput,
    ExtractionResult,
    GenericAssetExtractor,
    RejectedAssetHint,
)

_SVG_SUFFIXES = (".svg", ".svgz")
_RASTER_SUFFIXES = {
    ".png": AssetFormat.PNG,
    ".jpg": AssetFormat.JPG,
    ".jpeg": AssetFormat.JPEG,
    ".webp": AssetFormat.WEBP,
}
_AUTHOR_PATTERN = re.compile(r"\bby\s+([a-z][a-z]+(?:\s+[a-z][a-z]+)*)", re.IGNORECASE)
_NEGATIVE_HINTS = ("thumbnail", "watermark", "sprite", "icon", "avatar")


def _html_to_text(fragment: str) -> str:
    collapsed = re.sub(r"<[^>]+>", " ", fragment)
    return " ".join(unescape(collapsed).split())


def _normalize_title(fragment: str | None) -> str | None:
    if fragment is None:
        return None
    normalized = _html_to_text(fragment).strip()
    return normalized or None


def _format_for_url(url: str) -> AssetFormat | None:
    path = urlparse(url).path.lower()
    if path.endswith(_SVG_SUFFIXES):
        return AssetFormat.SVG
    for suffix, asset_format in _RASTER_SUFFIXES.items():
        if path.endswith(suffix):
            return asset_format
    return None


@dataclass(frozen=True)
class HtmlExtractionInput:
    source_page_url: str
    query: str
    domain: str
    html: str


class HtmlHeuristicExtractor:
    """Heuristic extractor for direct links, raster images, and inline SVG."""

    def __init__(self, generic_extractor: GenericAssetExtractor | None = None) -> None:
        self._generic_extractor = generic_extractor or GenericAssetExtractor()

    def extract_page(self, extraction_input: HtmlExtractionInput) -> ExtractionResult:
        document = Selector(content=extraction_input.html)
        page_title = _normalize_title(document.css("title").get())

        hints: list[ExtractedAssetHint] = []
        rejected: list[RejectedAssetHint] = []

        for link in document.css("a[href]"):
            href = link.attrib.get("href", "").strip()
            if not href:
                continue
            resolved_url = urljoin(extraction_input.source_page_url, href)
            asset_format = _format_for_url(resolved_url)
            if asset_format is None:
                continue
            self._append_candidate_or_rejection(
                hints,
                rejected,
                asset_url=resolved_url,
                asset_format=asset_format,
                node_html=link.get(),
                context_html=self._context_html(link),
                fallback_title=page_title,
            )

        for image in document.css("img[src]"):
            source = image.attrib.get("src", "").strip()
            if not source:
                continue
            resolved_url = urljoin(extraction_input.source_page_url, source)
            asset_format = _format_for_url(resolved_url)
            if asset_format is None:
                continue
            self._append_candidate_or_rejection(
                hints,
                rejected,
                asset_url=resolved_url,
                asset_format=asset_format,
                node_html=image.get(),
                context_html=self._context_html(image),
                fallback_title=page_title,
                alt_text=image.attrib.get("alt"),
            )

        for index, inline_svg in enumerate(document.css("svg"), start=1):
            embedded_url = f"{extraction_input.source_page_url}#embedded-svg-{index}"
            context_html = self._context_html(inline_svg)
            hints.append(
                ExtractedAssetHint(
                    asset_url=embedded_url,
                    original_format=AssetFormat.SVG,
                    title=_normalize_title(inline_svg.attrib.get("aria-label")) or page_title,
                    alt_text=_normalize_title(inline_svg.attrib.get("aria-label")),
                    author_or_owner=self._author_hint(context_html),
                    attribution_hint=self._attribution_hint(context_html),
                    license_hint=self._license_hint(context_html),
                    style_tags=("embedded_svg",),
                    notes=("embedded_svg",),
                )
            )

        normalized = self._generic_extractor.extract(
            ExtractionInput(
                source_page_url=extraction_input.source_page_url,
                query=extraction_input.query,
                domain=extraction_input.domain,
                title=page_title,
                extracted_assets=tuple(hints),
            )
        )
        return ExtractionResult(
            candidates=normalized.candidates,
            rejected=tuple((*rejected, *normalized.rejected)),
        )

    def _append_candidate_or_rejection(
        self,
        hints: list[ExtractedAssetHint],
        rejected: list[RejectedAssetHint],
        *,
        asset_url: str,
        asset_format: AssetFormat,
        node_html: str,
        context_html: str,
        fallback_title: str | None,
        alt_text: str | None = None,
    ) -> None:
        signal_text = " ".join(
            filter(
                None,
                (
                    asset_url,
                    _html_to_text(node_html),
                    _html_to_text(context_html),
                    alt_text,
                ),
            )
        ).casefold()
        matched_negative = next((hint for hint in _NEGATIVE_HINTS if hint in signal_text), None)
        if matched_negative is not None:
            rejected.append(
                RejectedAssetHint(
                    asset_url=asset_url,
                    reason=f"low_value_signal:{matched_negative}",
                )
            )
            return

        notes: list[str] = []
        if "outline" in signal_text:
            notes.append("positive:outline_signal")
        if "attribution" in signal_text:
            notes.append("attribution_signal")

        hints.append(
            ExtractedAssetHint(
                asset_url=asset_url,
                original_format=asset_format,
                title=fallback_title,
                alt_text=_normalize_title(alt_text),
                author_or_owner=self._author_hint(context_html),
                attribution_hint=self._attribution_hint(context_html),
                license_hint=self._license_hint(context_html),
                style_tags=(
                    ("direct_svg",) if asset_format == AssetFormat.SVG else ("direct_image",)
                ),
                notes=tuple(notes),
            )
        )

    def _context_html(self, node: Selector) -> str:
        context_candidates = node.xpath(
            "ancestor-or-self::*[self::figure or self::article or self::section or self::div][1]"
        )
        if context_candidates:
            return context_candidates[0].get()
        return node.get()

    def _author_hint(self, context_html: str) -> str | None:
        text = _html_to_text(context_html)
        match = _AUTHOR_PATTERN.search(text)
        if match is None:
            return None
        return " ".join(part.capitalize() for part in match.group(1).split())

    def _attribution_hint(self, context_html: str) -> str | None:
        text = _html_to_text(context_html)
        if "attribution" not in text.casefold():
            return None
        return text

    def _license_hint(self, context_html: str) -> str | None:
        text = _html_to_text(context_html)
        lowered = text.casefold()
        for hint in ("cc-by", "cc by", "cc0", "public domain", "royalty free"):
            if hint in lowered:
                return text
        return None

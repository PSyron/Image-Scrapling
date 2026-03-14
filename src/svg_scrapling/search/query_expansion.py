"""Deterministic multilingual query expansion helpers."""

from __future__ import annotations

from collections.abc import Iterable

from svg_scrapling.config import OutputFormat
from svg_scrapling.domain import AssetFormat, SearchIntent, SearchQuery

FORMAT_SUFFIXES: dict[OutputFormat, tuple[str, ...]] = {
    OutputFormat.SVG: ("svg",),
    OutputFormat.PNG: ("png",),
}

STYLE_HINTS: dict[str, tuple[str, ...]] = {
    "outline": ("outline", "kontur"),
    "line_art": ("line art", "line art for kids"),
    "coloring_page": ("coloring page", "kolorowanka"),
    "printable": ("printable", "do druku"),
    "kids_friendly": ("for kids", "dla dzieci"),
    "black_and_white": ("black and white", "czarno-biale"),
}

QUERY_PATTERNS: dict[str, tuple[str, ...]] = {
    "pl": (
        "{query} svg",
        "{query} kolorowanka",
        "{query} kontur",
        "{query} do druku",
        "{query} dla dzieci",
    ),
    "en": (
        "{query} svg",
        "{query} coloring page",
        "{query} outline",
        "{query} line art",
        "{query} printable",
        "{query} for kids",
    ),
}


def _normalize(value: str) -> str:
    return " ".join(value.strip().split())


def _ordered_unique(values: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        normalized = _normalize(value)
        if not normalized:
            continue
        lowered = normalized.casefold()
        if lowered in seen:
            continue
        seen.add(lowered)
        ordered.append(normalized)
    return tuple(ordered)


def expand_query_terms(
    query: str,
    preferred_format: OutputFormat,
    fallback_format: OutputFormat | None = None,
    languages: tuple[str, ...] = ("pl", "en"),
    style_bias: tuple[str, ...] = (
        "outline",
        "line_art",
        "coloring_page",
        "printable",
        "kids_friendly",
        "black_and_white",
    ),
) -> tuple[str, ...]:
    normalized_query = _normalize(query)
    if not normalized_query:
        raise ValueError("query must not be blank")

    expanded_terms: list[str] = [normalized_query]
    format_sequence = (
        (preferred_format, fallback_format)
        if fallback_format
        else (preferred_format,)
    )

    for language in languages:
        language_templates = QUERY_PATTERNS.get(language, ())
        for template in language_templates:
            expanded_terms.append(template.format(query=normalized_query))

    for style_name in style_bias:
        for style_term in STYLE_HINTS.get(style_name, ()):
            expanded_terms.append(f"{normalized_query} {style_term}")

    for output_format in format_sequence:
        if output_format is None:
            continue
        for suffix in FORMAT_SUFFIXES[output_format]:
            expanded_terms.append(f"{normalized_query} {suffix}")

    return _ordered_unique(expanded_terms)


def build_search_intent(
    query: str,
    requested_count: int,
    preferred_format: OutputFormat = OutputFormat.SVG,
    fallback_format: OutputFormat | None = None,
    convert_to: OutputFormat | None = None,
    languages: tuple[str, ...] = ("pl", "en"),
) -> SearchIntent:
    search_query = SearchQuery(
        query=query,
        requested_count=requested_count,
        preferred_format=AssetFormat(preferred_format.value),
        language_hints=languages,
        style_hints=tuple(STYLE_HINTS),
    )
    expanded_queries = expand_query_terms(
        query=query,
        preferred_format=preferred_format,
        fallback_format=fallback_format,
        languages=languages,
    )
    return SearchIntent(
        search_query=search_query,
        expanded_queries=expanded_queries,
        preferred_format=AssetFormat(preferred_format.value),
        fallback_format=AssetFormat(fallback_format.value) if fallback_format else None,
        convert_to=AssetFormat(convert_to.value) if convert_to else None,
    )

import pytest

from svg_scrapling.config import OutputFormat
from svg_scrapling.search import build_search_intent, expand_query_terms


def test_expand_query_terms_is_deterministic_and_unique() -> None:
    expanded_once = expand_query_terms(
        query="tiger coloring page",
        preferred_format=OutputFormat.SVG,
        fallback_format=OutputFormat.PNG,
    )
    expanded_twice = expand_query_terms(
        query="tiger coloring page",
        preferred_format=OutputFormat.SVG,
        fallback_format=OutputFormat.PNG,
    )

    assert expanded_once == expanded_twice
    assert len(expanded_once) == len(set(term.casefold() for term in expanded_once))


def test_expand_query_terms_covers_polish_and_english_patterns() -> None:
    expanded = expand_query_terms(
        query="tygryski do kolorowania",
        preferred_format=OutputFormat.SVG,
    )

    assert "tygryski do kolorowania kolorowanka" in expanded
    assert "tygryski do kolorowania outline" in expanded
    assert "tygryski do kolorowania svg" in expanded


def test_build_search_intent_sets_formats_and_languages() -> None:
    intent = build_search_intent(
        query="black and white tiger outline",
        requested_count=25,
        preferred_format=OutputFormat.SVG,
        fallback_format=OutputFormat.PNG,
        convert_to=OutputFormat.SVG,
        languages=("en",),
    )

    assert intent.search_query.query == "black and white tiger outline"
    assert intent.search_query.requested_count == 25
    assert intent.preferred_format.value == "svg"
    assert intent.fallback_format is not None
    assert intent.fallback_format.value == "png"
    assert intent.convert_to is not None
    assert intent.convert_to.value == "svg"
    assert intent.search_query.language_hints == ("en",)


def test_expand_query_terms_rejects_blank_query() -> None:
    with pytest.raises(ValueError, match="query must not be blank"):
        expand_query_terms(query="   ", preferred_format=OutputFormat.SVG)

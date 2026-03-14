from svg_scrapling.domain import AssetFormat
from svg_scrapling.extraction import (
    ExtractedAssetHint,
    ExtractionInput,
    ExtractionRegistry,
    GenericAssetExtractor,
)


def test_generic_extractor_maps_asset_hints_to_candidates() -> None:
    extractor = GenericAssetExtractor()
    extraction_input = ExtractionInput(
        source_page_url="https://example.com/page",
        query="tiger coloring page",
        domain="example.com",
        title="Tiger page",
        extracted_assets=(
            ExtractedAssetHint(
                asset_url="https://example.com/assets/tiger.svg",
                original_format=AssetFormat.SVG,
                style_tags=("outline",),
            ),
        ),
    )

    result = extractor.extract(extraction_input)

    assert len(result.candidates) == 1
    assert result.candidates[0].asset_url == "https://example.com/assets/tiger.svg"
    assert result.candidates[0].title == "Tiger page"
    assert result.candidates[0].style_tags == ("outline",)
    assert result.rejected == ()


def test_generic_extractor_returns_structured_rejections() -> None:
    extractor = GenericAssetExtractor()
    extraction_input = ExtractionInput(
        source_page_url="https://example.com/page",
        query="tiger coloring page",
        domain="example.com",
        extracted_assets=(
            ExtractedAssetHint(asset_url="", original_format=AssetFormat.SVG),
            ExtractedAssetHint(asset_url="/relative/path.svg", original_format=AssetFormat.SVG),
        ),
    )

    result = extractor.extract(extraction_input)

    assert result.candidates == ()
    assert [rejection.reason for rejection in result.rejected] == [
        "asset_url must not be blank",
        "asset_url must be an absolute URL",
    ]


def test_extraction_registry_prefers_registered_domain_extractor() -> None:
    registry = ExtractionRegistry()
    custom_extractor = GenericAssetExtractor()
    registry.register("example.com", custom_extractor)

    assert registry.resolve("example.com") is custom_extractor


def test_extraction_registry_uses_default_for_unknown_domain() -> None:
    registry = ExtractionRegistry()
    extraction_input = ExtractionInput(
        source_page_url="https://unknown.example/page",
        query="lion outline",
        domain="unknown.example",
        extracted_assets=(
            ExtractedAssetHint(
                asset_url="https://unknown.example/assets/lion.svg",
                original_format=AssetFormat.SVG,
            ),
        ),
    )

    result = registry.extract(extraction_input)

    assert len(result.candidates) == 1
    assert result.candidates[0].domain == "unknown.example"

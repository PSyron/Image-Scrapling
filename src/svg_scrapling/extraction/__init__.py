"""Extraction contracts and source-specific extractors."""

from svg_scrapling.extraction.contracts import (
    ExtractedAssetHint,
    ExtractionInput,
    ExtractionRegistry,
    ExtractionResult,
    GenericAssetExtractor,
    RejectedAssetHint,
)
from svg_scrapling.extraction.heuristics import (
    HtmlExtractionInput,
    HtmlHeuristicExtractor,
)

__all__ = [
    "ExtractedAssetHint",
    "ExtractionInput",
    "ExtractionRegistry",
    "ExtractionResult",
    "GenericAssetExtractor",
    "HtmlExtractionInput",
    "HtmlHeuristicExtractor",
    "RejectedAssetHint",
]

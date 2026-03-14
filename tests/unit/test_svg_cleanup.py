from pathlib import Path

import pytest

from svg_scrapling.conversion import SvgCleanupError, SvgPostProcessor


class FakeOptimizer:
    def optimize(self, svg_text: str) -> str:
        return svg_text.replace("metadata", "desc")


def test_svg_post_processor_normalizes_dimensions_and_viewbox(tmp_path: Path) -> None:
    svg_path = tmp_path / "input.svg"
    svg_path.write_text(
        '<svg width="120px" height="80px"><title>Tiger</title><path d="M0 0 L10 10"/></svg>',
        encoding="utf-8",
    )

    result = SvgPostProcessor().process(svg_path)
    cleaned_svg = result.cleaned_svg_path.read_text(encoding="utf-8")

    assert result.view_box == "0 0 120 80"
    assert result.width == "120"
    assert result.height == "80"
    assert "<title>" not in cleaned_svg
    assert result.complexity_metrics["path_count"] == 1.0


def test_svg_post_processor_uses_viewbox_when_dimensions_are_missing(tmp_path: Path) -> None:
    svg_path = tmp_path / "input.svg"
    svg_path.write_text(
        '<svg viewBox="0 0 24 24"><g><path d="M0 0 L10 10"/></g></svg>',
        encoding="utf-8",
    )

    result = SvgPostProcessor().process(svg_path)

    assert result.width == "24"
    assert result.height == "24"
    assert result.complexity_metrics["max_depth"] == 3.0


def test_svg_post_processor_rejects_invalid_svg(tmp_path: Path) -> None:
    svg_path = tmp_path / "invalid.svg"
    svg_path.write_text("<svg><path></svg", encoding="utf-8")

    with pytest.raises(SvgCleanupError, match="invalid_svg"):
        SvgPostProcessor().process(svg_path)


def test_svg_post_processor_supports_optional_optimizer_hook(tmp_path: Path) -> None:
    svg_path = tmp_path / "optimized.svg"
    svg_path.write_text(
        '<svg viewBox="0 0 10 10"><metadata>drop me</metadata><path d="M0 0"/></svg>',
        encoding="utf-8",
    )

    result = SvgPostProcessor(optimizer=FakeOptimizer()).process(svg_path)

    assert "optimized:svgo" in result.notes

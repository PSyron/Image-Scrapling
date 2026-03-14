import binascii
import struct
import zlib
from pathlib import Path

import pytest

from svg_scrapling.conversion import (
    ConversionPreset,
    VTracerConverter,
    VTracerRunResult,
    build_derived_svg_path,
    preset_options_for,
)
from svg_scrapling.domain import (
    AssetFormat,
    ConversionStatus,
    DownloadedAsset,
    DownloadStatus,
)
from svg_scrapling.storage import create_run_layout


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    checksum = binascii.crc32(chunk_type + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", checksum)


def _write_fixture_png(path: Path) -> None:
    width = 4
    height = 4
    rows: list[bytes] = []
    black = b"\x00\x00\x00"
    white = b"\xff\xff\xff"

    for y in range(height):
        row = bytearray([0])
        for x in range(width):
            row.extend(black if 1 <= x <= 2 and 1 <= y <= 2 else white)
        rows.append(bytes(row))

    image_data = zlib.compress(b"".join(rows))
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    payload = b"".join(
        (
            b"\x89PNG\r\n\x1a\n",
            _png_chunk(b"IHDR", ihdr),
            _png_chunk(b"IDAT", image_data),
            _png_chunk(b"IEND", b""),
        )
    )
    path.write_bytes(payload)


def _downloaded_asset(
    path: Path,
    original_format: AssetFormat = AssetFormat.PNG,
) -> DownloadedAsset:
    return DownloadedAsset(
        asset_id="asset-1",
        source_page_url="https://example.com/page",
        asset_url="https://assets.example.com/sample.png",
        original_format=original_format,
        stored_original_path=path,
        download_status=DownloadStatus.DOWNLOADED,
    )


class FakeFailingRunner:
    def run(self, invocation: object) -> VTracerRunResult:
        _ = invocation
        return VTracerRunResult(return_code=9, error_message="backend exploded")


def test_preset_options_are_explicit() -> None:
    fast = preset_options_for(ConversionPreset.LINE_ART_FAST)
    clean = preset_options_for(ConversionPreset.LINE_ART_CLEAN)
    general_bw = preset_options_for(ConversionPreset.GENERAL_BW)
    general_color = preset_options_for(ConversionPreset.GENERAL_COLOR)

    assert fast.colormode == "binary"
    assert fast.path_precision == 4
    assert clean.hierarchical == "cutout"
    assert general_bw.colormode == "binary"
    assert general_color.colormode == "color"


def test_build_derived_svg_path_is_deterministic(tmp_path: Path) -> None:
    run_layout = create_run_layout(tmp_path / "runs", "run-1")
    original_path = run_layout.originals / "sample.png"
    original_path.write_bytes(b"png")

    output_path = build_derived_svg_path(
        run_layout,
        _downloaded_asset(original_path),
        ConversionPreset.LINE_ART_FAST,
    )

    assert output_path == run_layout.derived / "sample--line_art_fast.svg"


def test_vtracer_converter_records_backend_failure(tmp_path: Path) -> None:
    run_layout = create_run_layout(tmp_path / "runs", "run-1")
    original_path = run_layout.originals / "sample.png"
    original_path.write_bytes(b"png")
    converter = VTracerConverter(runner=FakeFailingRunner())

    converted = converter.convert(
        _downloaded_asset(original_path),
        run_layout,
        preset=ConversionPreset.LINE_ART_FAST,
    )

    assert converted.conversion_status == ConversionStatus.FAILED
    assert converted.derived_svg_path is None
    assert converted.notes == ("backend exploded",)


def test_vtracer_converter_converts_png_fixture(tmp_path: Path) -> None:
    run_layout = create_run_layout(tmp_path / "runs", "run-1")
    original_path = run_layout.originals / "fixture.png"
    _write_fixture_png(original_path)
    converter = VTracerConverter()

    converted = converter.convert(
        _downloaded_asset(original_path),
        run_layout,
        preset=ConversionPreset.LINE_ART_FAST,
    )

    assert converted.conversion_status == ConversionStatus.CONVERTED
    assert converted.derived_svg_path is not None
    assert converted.derived_svg_path.exists()
    assert "<svg" in converted.derived_svg_path.read_text(encoding="utf-8")
    assert converted.preset == "line_art_fast"


def test_vtracer_converter_rejects_non_raster_inputs(tmp_path: Path) -> None:
    run_layout = create_run_layout(tmp_path / "runs", "run-1")
    svg_path = run_layout.originals / "sample.svg"
    svg_path.write_text("<svg/>", encoding="utf-8")
    converter = VTracerConverter(runner=FakeFailingRunner())

    with pytest.raises(ValueError, match="only supports raster input formats"):
        converter.convert(
            _downloaded_asset(svg_path, original_format=AssetFormat.SVG),
            run_layout,
            preset=ConversionPreset.LINE_ART_FAST,
        )

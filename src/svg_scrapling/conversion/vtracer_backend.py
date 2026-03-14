"""VTracer-backed raster-to-SVG conversion interfaces."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Protocol

from svg_scrapling.domain import AssetFormat, ConversionStatus, ConvertedAsset, DownloadedAsset
from svg_scrapling.storage import RunLayout


class ConversionPreset(str, Enum):
    LINE_ART_FAST = "line_art_fast"
    LINE_ART_CLEAN = "line_art_clean"
    GENERAL_BW = "general_bw"
    GENERAL_COLOR = "general_color"


@dataclass(frozen=True)
class VTracerPresetOptions:
    colormode: str
    hierarchical: str
    mode: str
    filter_speckle: int
    color_precision: int
    layer_difference: int
    corner_threshold: int
    length_threshold: float
    max_iterations: int
    splice_threshold: int
    path_precision: int


def preset_options_for(preset: ConversionPreset) -> VTracerPresetOptions:
    if preset == ConversionPreset.LINE_ART_FAST:
        return VTracerPresetOptions(
            colormode="binary",
            hierarchical="stacked",
            mode="spline",
            filter_speckle=8,
            color_precision=6,
            layer_difference=16,
            corner_threshold=70,
            length_threshold=5.5,
            max_iterations=6,
            splice_threshold=55,
            path_precision=4,
        )
    if preset == ConversionPreset.LINE_ART_CLEAN:
        return VTracerPresetOptions(
            colormode="binary",
            hierarchical="cutout",
            mode="spline",
            filter_speckle=4,
            color_precision=6,
            layer_difference=12,
            corner_threshold=60,
            length_threshold=4.0,
            max_iterations=10,
            splice_threshold=45,
            path_precision=6,
        )
    if preset == ConversionPreset.GENERAL_BW:
        return VTracerPresetOptions(
            colormode="binary",
            hierarchical="stacked",
            mode="spline",
            filter_speckle=4,
            color_precision=6,
            layer_difference=16,
            corner_threshold=60,
            length_threshold=4.0,
            max_iterations=10,
            splice_threshold=45,
            path_precision=6,
        )
    return VTracerPresetOptions(
        colormode="color",
        hierarchical="stacked",
        mode="spline",
        filter_speckle=4,
        color_precision=6,
        layer_difference=16,
        corner_threshold=60,
        length_threshold=4.0,
        max_iterations=10,
        splice_threshold=45,
        path_precision=6,
    )


@dataclass(frozen=True)
class VTracerInvocation:
    input_path: Path
    output_path: Path
    options: VTracerPresetOptions


@dataclass(frozen=True)
class VTracerRunResult:
    return_code: int
    error_message: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.return_code == 0


class VTracerRunner(Protocol):
    def run(self, invocation: VTracerInvocation) -> VTracerRunResult:
        """Execute one VTracer conversion request."""


@dataclass
class SubprocessVTracerRunner:
    python_executable: str = sys.executable

    def run(self, invocation: VTracerInvocation) -> VTracerRunResult:
        command = [
            self.python_executable,
            "-m",
            "svg_scrapling.conversion.vtracer_runner",
            "--input-path",
            str(invocation.input_path),
            "--output-path",
            str(invocation.output_path),
            "--colormode",
            invocation.options.colormode,
            "--hierarchical",
            invocation.options.hierarchical,
            "--mode",
            invocation.options.mode,
            "--filter-speckle",
            str(invocation.options.filter_speckle),
            "--color-precision",
            str(invocation.options.color_precision),
            "--layer-difference",
            str(invocation.options.layer_difference),
            "--corner-threshold",
            str(invocation.options.corner_threshold),
            "--length-threshold",
            str(invocation.options.length_threshold),
            "--max-iterations",
            str(invocation.options.max_iterations),
            "--splice-threshold",
            str(invocation.options.splice_threshold),
            "--path-precision",
            str(invocation.options.path_precision),
        ]
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        error_message = completed.stderr.strip() or completed.stdout.strip() or None
        return VTracerRunResult(
            return_code=completed.returncode,
            error_message=error_message,
        )


def build_derived_svg_path(
    run_layout: RunLayout,
    downloaded_asset: DownloadedAsset,
    preset: ConversionPreset,
) -> Path:
    input_stem = downloaded_asset.stored_original_path.stem
    return run_layout.derived / f"{input_stem}--{preset.value}.svg"


class RasterToSvgConverter(Protocol):
    def convert(
        self,
        downloaded_asset: DownloadedAsset,
        run_layout: RunLayout,
        *,
        preset: ConversionPreset,
    ) -> ConvertedAsset:
        """Convert one raster asset into an SVG derivative."""


@dataclass
class VTracerConverter:
    runner: VTracerRunner | None = None

    def __post_init__(self) -> None:
        if self.runner is None:
            self.runner = SubprocessVTracerRunner()

    def convert(
        self,
        downloaded_asset: DownloadedAsset,
        run_layout: RunLayout,
        *,
        preset: ConversionPreset,
    ) -> ConvertedAsset:
        if downloaded_asset.original_format not in {
            AssetFormat.PNG,
            AssetFormat.JPG,
            AssetFormat.JPEG,
            AssetFormat.WEBP,
        }:
            raise ValueError("VTracerConverter only supports raster input formats")
        if not downloaded_asset.stored_original_path.exists():
            raise FileNotFoundError(downloaded_asset.stored_original_path)

        output_path = build_derived_svg_path(run_layout, downloaded_asset, preset)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        runner = self.runner
        assert runner is not None
        result = runner.run(
            VTracerInvocation(
                input_path=downloaded_asset.stored_original_path,
                output_path=output_path,
                options=preset_options_for(preset),
            )
        )
        if not result.succeeded:
            return ConvertedAsset(
                asset_id=downloaded_asset.asset_id,
                source_raster_path=downloaded_asset.stored_original_path,
                derived_svg_path=None,
                conversion_status=ConversionStatus.FAILED,
                preset=preset.value,
                notes=(
                    result.error_message
                    or f"vtracer runner failed with exit code {result.return_code}",
                ),
            )
        if not output_path.exists():
            return ConvertedAsset(
                asset_id=downloaded_asset.asset_id,
                source_raster_path=downloaded_asset.stored_original_path,
                derived_svg_path=None,
                conversion_status=ConversionStatus.FAILED,
                preset=preset.value,
                notes=("vtracer completed without writing an SVG output",),
            )
        return ConvertedAsset(
            asset_id=downloaded_asset.asset_id,
            source_raster_path=downloaded_asset.stored_original_path,
            derived_svg_path=output_path,
            conversion_status=ConversionStatus.CONVERTED,
            preset=preset.value,
            notes=("backend=vtracer",),
        )

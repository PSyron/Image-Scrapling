"""Raster-to-vector conversion interfaces and backends."""

from svg_scrapling.conversion.vtracer_backend import (
    ConversionPreset,
    RasterToSvgConverter,
    SubprocessVTracerRunner,
    VTracerConverter,
    VTracerInvocation,
    VTracerPresetOptions,
    VTracerRunResult,
    build_derived_svg_path,
    preset_options_for,
)

__all__ = [
    "ConversionPreset",
    "RasterToSvgConverter",
    "SubprocessVTracerRunner",
    "VTracerConverter",
    "VTracerInvocation",
    "VTracerPresetOptions",
    "VTracerRunResult",
    "build_derived_svg_path",
    "preset_options_for",
]

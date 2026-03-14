"""Subprocess entrypoint for one VTracer conversion call."""

from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m svg_scrapling.conversion.vtracer_runner",
    )
    parser.add_argument("--input-path", required=True)
    parser.add_argument("--output-path", required=True)
    parser.add_argument("--colormode", required=True)
    parser.add_argument("--hierarchical", required=True)
    parser.add_argument("--mode", required=True)
    parser.add_argument("--filter-speckle", required=True, type=int)
    parser.add_argument("--color-precision", required=True, type=int)
    parser.add_argument("--layer-difference", required=True, type=int)
    parser.add_argument("--corner-threshold", required=True, type=int)
    parser.add_argument("--length-threshold", required=True, type=float)
    parser.add_argument("--max-iterations", required=True, type=int)
    parser.add_argument("--splice-threshold", required=True, type=int)
    parser.add_argument("--path-precision", required=True, type=int)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        from vtracer import convert_image_to_svg_py  # type: ignore[import-untyped]
    except ModuleNotFoundError as err:
        raise SystemExit(
            "The optional 'conversion' dependency group is required for raster-to-SVG "
            "conversion. Install svg-scrapling[conversion] to enable VTracer."
        ) from err
    convert_image_to_svg_py(
        args.input_path,
        args.output_path,
        colormode=args.colormode,
        hierarchical=args.hierarchical,
        mode=args.mode,
        filter_speckle=args.filter_speckle,
        color_precision=args.color_precision,
        layer_difference=args.layer_difference,
        corner_threshold=args.corner_threshold,
        length_threshold=args.length_threshold,
        max_iterations=args.max_iterations,
        splice_threshold=args.splice_threshold,
        path_precision=args.path_precision,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

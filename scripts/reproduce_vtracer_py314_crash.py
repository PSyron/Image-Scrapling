from __future__ import annotations

from vtracer import convert_pixels_to_svg  # type: ignore[import-untyped]


def main() -> int:
    pixels = []
    for y in range(16):
        for x in range(16):
            if 4 <= x <= 11 and 4 <= y <= 11:
                pixels.append((0, 0, 0, 255))
            else:
                pixels.append((255, 255, 255, 255))

    svg = convert_pixels_to_svg(
        pixels,
        (16, 16),
        colormode="binary",
        hierarchical="stacked",
        mode="spline",
    )
    print(svg[:120])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

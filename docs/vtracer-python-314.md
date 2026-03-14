# VTracer Python 3.14 Compatibility

## Current Status

As of March 14, 2026, the repository keeps `vtracer` behind a Python runtime ceiling of `>=3.10,<3.14`.

That limit is intentional. The repo verified that `vtracer==0.6.12` succeeds on CPython `3.13.12` and crashes on CPython `3.14.3` when calling the Python binding for raster-to-SVG conversion.

## Reproduction

The project environment intentionally blocks Python `3.14` because the repo metadata already reflects the known incompatibility. To reproduce the upstream binding failure outside the project environment:

```bash
uvx --python 3.14 --from vtracer python - <<'PY'
from vtracer import convert_pixels_to_svg

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
PY
```

Observed result on March 14, 2026, on Python `3.14.3`:

- the process exits with code `139`
- the crash happens during `convert_pixels_to_svg`
- no stable SVG string is returned

Control check on a supported runtime:

```bash
uv run --python 3.13 python scripts/reproduce_vtracer_py314_crash.py
```

Expected current result on Python `3.13.12`:

- the script prints the opening SVG bytes
- the process exits successfully

## Repo Policy

- The repo metadata and docs must not claim Python `3.14` compatibility for conversion while this crash remains reproducible.
- The subprocess boundary in the conversion layer prevents the main pipeline process from crashing if the binding fails in a child process.
- Removing the `<3.14` ceiling should only happen after rerunning the reproduction and the conversion fixture tests successfully on Python `3.14`.

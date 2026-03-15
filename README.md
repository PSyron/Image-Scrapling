# Image-Scrapling

Public repository for discovering, evaluating, converting, and cataloging coloring-style image assets.

Repository name:
- `Image-Scrapling`

Published package and import names:
- package: `svg-scrapling`
- import: `svg_scrapling`

## Install From PyPI

Install the published package:

```bash
uv pip install svg-scrapling==0.1.0
```

or with `pip`:

```bash
python -m pip install svg-scrapling==0.1.0
```

If you want PNG-to-SVG conversion through VTracer, install the optional conversion extra:

```bash
uv pip install "svg-scrapling[conversion]==0.1.0"
```

or:

```bash
python -m pip install "svg-scrapling[conversion]==0.1.0"
```

Verify the install:

```bash
python -c "import svg_scrapling; print(svg_scrapling.__version__)"
assets --help
```

Upgrade to a newer published release:

```bash
uv pip install --upgrade svg-scrapling
```

or:

```bash
python -m pip install --upgrade svg-scrapling
```

## Bootstrap

Run the standard project commands from the repository root:

```bash
uv sync --group dev
uv run ruff check .
uv run ruff format --check .
uv run mypy src apps
uv run pytest
```

## First Real CLI Run

The CLI now assembles a default runtime without manual dependency wiring in code.

Install dependencies first:

```bash
uv sync --group dev
```

If you want PNG-to-SVG conversion through VTracer in the development environment, install the optional conversion extra:

```bash
uv sync --group dev --extra conversion
```

See the available commands:

```bash
uv run assets --help
```

Start with a real search run:

```bash
uv run assets find \
  --query "tygryski do kolorowania" \
  --count 10 \
  --preferred-format svg \
  --fallback-format png \
  --convert-to svg \
  --mode provenance_only \
  --provider duckduckgo_html \
  --run-id demo-run \
  --output ./data/runs
```

This writes a deterministic run directory under `./data/runs/demo-run`.

Useful operational flags:

- `--provider duckduckgo_html` or `--provider bing_html` selects the preferred live discovery provider.
- non-disabled providers are tried in ordered fallback after the preferred provider
- `--disable-provider ...` explicitly blocks a provider for one run.
- `--run-id ...` resumes or reuses a stable run directory.
- `--skip-existing-downloads` is enabled by default and reuses deterministic asset paths when possible.
- `--fetch-strategy static_first|dynamic_on_failure|dynamic_only` controls fetch escalation.

Example with Bing as the preferred provider:

```bash
uv run assets find \
  --query "tiger coloring page" \
  --count 5 \
  --preferred-format png \
  --provider bing_html \
  --disable-provider duckduckgo_html \
  --output ./data/runs/live-bing
```

Example resume run:

```bash
uv run assets find \
  --query "tiger coloring page" \
  --count 5 \
  --preferred-format png \
  --run-id demo-run \
  --output ./data/runs
```

Inspect a manifest after the run:

```bash
uv run assets inspect-manifest ./data/runs/demo-run/manifests/manifest.jsonl
```

Export CSV and Markdown reports:

```bash
uv run assets export-report \
  ./data/runs/demo-run/manifests/manifest.jsonl \
  --csv-output ./data/runs/demo-run/manifests/report.csv \
  --markdown-output ./data/runs/demo-run/manifests/report.md
```

Successful runs now write:

- `manifests/manifest.jsonl` as the canonical machine-readable output
- `manifests/summary.json` and `manifests/summary.txt` for operator-facing summaries
- `manifests/rejected_candidates.jsonl` for fetch, extraction, policy, and download rejections
- `logs/pipeline.log` for stage-level execution details

## Dynamic Fetching

Static fetching is the default and should be preferred for normal runs.

If you have a Lightpanda-compatible wrapper, expose it through:

```bash
export SVG_SCRAPLING_LIGHTPANDA_CMD="/path/to/lightpanda-wrapper"
```

The wrapper must support:

```text
<wrapper> fetch <url> <timeout_seconds>
```

and print JSON to stdout:

```json
{"html":"<html>...</html>","final_url":"https://example.com/final"}
```

Then you can enable dynamic fallback:

```bash
uv run assets find \
  --query "tiger coloring page" \
  --count 5 \
  --fetch-strategy dynamic_on_failure \
  --output ./data/runs/dynamic-demo
```

## Library Usage

Supported library entrypoints are exposed from stable package surfaces:

- `svg_scrapling`
- `svg_scrapling.config`
- `svg_scrapling.pipeline`
- `svg_scrapling.runtime`

Example:

```python
from svg_scrapling import (
    FetchStrategy,
    FindAssetsConfig,
    LicenseMode,
    OutputFormat,
    build_default_pipeline_dependencies,
    run_find_assets,
)

config = FindAssetsConfig(
    query="tiger coloring page",
    count=5,
    preferred_format=OutputFormat.SVG,
    fallback_format=OutputFormat.PNG,
    mode=LicenseMode.PROVENANCE_ONLY,
    fetch_strategy=FetchStrategy.STATIC_FIRST,
)

result = run_find_assets(
    config,
    dependencies=build_default_pipeline_dependencies(config),
)

print(result.manifest_path)
```

Deep internal module imports outside those entrypoints should be treated as unstable.

## Versioning

- distribution version comes from `project.version` in `pyproject.toml`
- runtime version is read from the installed package metadata
- release tags should use the format `vX.Y.Z`
- public releases are published to PyPI from the guarded GitHub Actions release workflow

## Current Limitations

- Live discovery currently uses `duckduckgo_html` and `bing_html`.
- Static asset downloading now uses conservative provenance-aware request headers, but some hosts may still block media retrieval.
- Dynamic fetching still fails loudly when no Lightpanda-compatible client is configured.
- License handling stays conservative: `licensed_only` requires an explicit allowlist and `provenance_only` preserves uncertain cases rather than silently allowing reuse.
- The VTracer conversion backend is currently supported on Python `>=3.10,<3.14`.
- Raster-to-SVG conversion is optional and requires installing the `conversion` extra.

## Current Runtime Note

The Python `3.14` compatibility follow-up is tracked in GitHub issue `#20`.

Reproduction details for the current Python `3.14` blocker live in [docs/vtracer-python-314.md](docs/vtracer-python-314.md).

## Developer Workflow

Repository workflow, validation expectations, and run output conventions are documented in [docs/developer-workflow.md](docs/developer-workflow.md).

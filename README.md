# SVG Scrapling

Repository for discovering, evaluating, converting, and cataloging coloring-style image assets.

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

Example:

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

Useful operational flags:

- `--provider duckduckgo_html` selects the current live discovery provider.
- `--disable-provider ...` explicitly blocks a provider for one run.
- `--run-id ...` resumes or reuses a stable run directory.
- `--skip-existing-downloads` is enabled by default and reuses deterministic asset paths when possible.

Successful runs now write:

- `manifests/manifest.jsonl` as the canonical machine-readable output
- `manifests/summary.json` and `manifests/summary.txt` for operator-facing summaries
- `manifests/rejected_candidates.jsonl` for fetch, extraction, policy, and download rejections
- `logs/pipeline.log` for stage-level execution details

## Current Limitations

- The first live provider is currently `duckduckgo_html`.
- Fetching is static-first; the dynamic path still fails loudly when no dynamic client is configured.
- License handling stays conservative: `licensed_only` requires an explicit allowlist and `provenance_only` preserves uncertain cases rather than silently allowing reuse.
- The VTracer conversion backend is currently supported on Python `>=3.10,<3.14`.

## Current Runtime Note

The Python `3.14` compatibility follow-up is tracked in GitHub issue `#20`.

Reproduction details for the current Python `3.14` blocker live in [docs/vtracer-python-314.md](docs/vtracer-python-314.md).

## Developer Workflow

Repository workflow, validation expectations, and run output conventions are documented in [docs/developer-workflow.md](docs/developer-workflow.md).

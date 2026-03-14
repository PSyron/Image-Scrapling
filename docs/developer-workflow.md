# Developer Workflow

## Setup

Run the project from the repository root:

```bash
uv sync --group dev
```

The conversion backend currently requires Python `>=3.10,<3.14` because the upstream VTracer binding is unstable on Python `3.14`. Follow-up work is tracked in GitHub issue `#20`.

## Validation

Run the full local validation set before push:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src apps
uv run pytest
```

Use targeted commands while implementing an issue, then rerun the full set before pushing to `main`.

## Run Output Layout

Run artifacts live under `data/runs/<run-id>/` or another explicitly chosen output root.

- `originals/` stores downloaded source assets.
- `derived/` stores converted SVG outputs.
- `manifests/manifest.jsonl` is the canonical machine-readable output.
- `logs/` stores run logs when the pipeline writes them.
- `debug/` is for temporary debugging artifacts that must not be committed.

## Working On Main

Non-trivial work starts from a GitHub issue. Commits should use the issue number first, for example `#17 add reporting commands and optional exports`.

Work directly on `main` unless a change is risky enough to justify a dedicated branch. Push only after the relevant validation passes.

## Debugging Expectations

- Fail loudly on unsupported states instead of silently skipping work.
- Keep runtime artifacts inside run directories, not in source directories.
- Prefer fixture-backed tests for fetch, extraction, conversion, and manifest behavior.
- Preserve canonical `manifest.jsonl` as the source of truth; reports and summaries are derived outputs.

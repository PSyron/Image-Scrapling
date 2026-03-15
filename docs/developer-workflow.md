# Developer Workflow

## Setup

Run the project from the repository root:

```bash
uv sync --group dev
```

If you need the raster-to-SVG conversion backend during development:

```bash
uv sync --group dev --extra conversion
```

The conversion backend currently requires Python `>=3.10,<3.14` because the upstream VTracer binding is unstable on Python `3.14`. Follow-up work is tracked in GitHub issue `#20`.

## Running The CLI

The default `assets find` command now assembles a real runtime by default.

Example:

```bash
uv run assets find \
  --query "tiger coloring page" \
  --count 10 \
  --preferred-format svg \
  --fallback-format png \
  --convert-to svg \
  --mode provenance_only \
  --provider duckduckgo_html \
  --run-id demo-run \
  --output ./data/runs
```

Operational notes:

- `--output` is the base directory that contains one or more run directories.
- `--run-id` makes the run resumable and reuses the same run directory on later executions.
- `--skip-existing-downloads` is enabled by default so deterministic original asset paths are not downloaded twice.
- `--disable-provider` can explicitly block a provider for a run and should fail loudly if it conflicts with the selected provider.

## Public Package Usage

Install the published package from PyPI:

```bash
uv pip install svg-scrapling==0.1.0
```

or:

```bash
python -m pip install svg-scrapling==0.1.0
```

Install with optional conversion support:

```bash
uv pip install "svg-scrapling[conversion]==0.1.0"
```

Smoke-check the installed package:

```bash
python -c "import svg_scrapling; print(svg_scrapling.__version__)"
assets --help
```

Upgrade a consumer environment:

```bash
uv pip install --upgrade svg-scrapling
```

## Validation

Run the full local validation set before push:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src apps
uv run pytest
```

Use targeted commands while implementing an issue, then rerun the full set before pushing to `main`.

## Release Security

Public package releases are intended to use a guarded `workflow_dispatch` flow instead of releasing on normal pushes.

Operational rules:

- start releases from `main` only
- keep release approval behind the GitHub `release` environment
- do not store long-lived publish tokens in the repository
- prefer PyPI Trusted Publisher / OIDC over API tokens when the public release path is enabled
- keep local credential files such as `.env`, `.pypirc`, `.netrc`, `.npmrc`, and `pip.conf` out of the repository

If local or CI credentials are ever needed for testing alternate registries, store them in:

- GitHub environment secrets
- CI secret storage
- local user-level config outside the repository root

## Public Release Flow

The public PyPI release flow is now verified by the successful `0.1.0` release.

Maintainer checklist:

1. Update `project.version` in `pyproject.toml`.
2. Run the full local validation set.
3. Push the release candidate to `main`.
4. Start the `Release` GitHub Actions workflow manually with `version=X.Y.Z`.
5. Approve the `release` environment when the workflow reaches the publish job.
6. Confirm that PyPI contains `svg-scrapling==X.Y.Z`.
7. Confirm that GitHub has tag `vX.Y.Z` and a matching GitHub Release.

Release invariants:

- do not publish from normal pushes
- do not create the release tag by hand before the workflow succeeds
- do not add long-lived PyPI API tokens to the repository
- keep Trusted Publisher as the publish path

## Run Output Layout

Run artifacts live under `data/runs/<run-id>/` or another explicitly chosen output root.

- `originals/` stores downloaded source assets.
- `derived/` stores converted SVG outputs.
- `manifests/manifest.jsonl` is the canonical machine-readable output.
- `manifests/summary.json` and `manifests/summary.txt` store operator-facing run summaries.
- `manifests/rejected_candidates.jsonl` stores structured rejection and failure diagnostics.
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

## Provider Extension Workflow

When adding a new discovery provider:

1. Add the provider implementation under `src/svg_scrapling/search/`.
2. Keep provider-specific HTTP behavior isolated from pipeline orchestration.
3. Add a new `DiscoveryProvider` enum value in `src/svg_scrapling/config/models.py`.
4. Wire the provider in `src/svg_scrapling/runtime/providers.py`.
5. Add fixture-backed unit tests for result parsing and runtime selection.
6. Update this document and `README.md` with the newly supported provider and any runtime constraints.

Provider changes should preserve:

- explicit provenance capture on discovered pages
- conservative failure behavior
- deterministic result normalization
- no silent fallback to unsupported provider states

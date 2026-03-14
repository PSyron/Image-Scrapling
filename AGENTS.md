# AGENTS.md

## Overview

This repository is `SVG Scrapling`, a Python project for discovering, collecting, evaluating, converting, and cataloging coloring-style image assets with strong provenance and explicit licensing behavior.

The repository is currently in planning/bootstrap stage. Until implementation lands, this file defines the intended operating model and the target repository layout that new work must follow.

Core model:

- Start from the repository and the current issue, not from assumptions.
- Non-trivial work starts from an explicit issue.
- Every implementation commit must reference the issue that authorized the work, with the issue number at the start of the subject line.
- Work directly on the current branch or `main` by default.
- Create a dedicated branch only for risky or potentially breaking work, or when explicitly requested.
- Push only after the relevant validation for the changed area passes.

Roles:

- The user defines product intent, scope, and acceptance.
- The agent acts as implementer, reviewer, and repository steward.
- The agent explores code, docs, and existing behavior first, and asks questions only when ambiguity materially affects correctness, safety, or sequencing.
- The agent must not delete, revert, or "clean up" user work without explicit instruction.

## Structure

Target repository layout for active development:

- Active work roots: `apps/cli/`, `src/svg_scrapling/`, `tests/`, `docs/`, `scripts/`
- Maintained source code: `apps/cli/`, `src/svg_scrapling/config/`, `src/svg_scrapling/domain/`, `src/svg_scrapling/search/`, `src/svg_scrapling/scraping/`, `src/svg_scrapling/browser/`, `src/svg_scrapling/extraction/`, `src/svg_scrapling/ranking/`, `src/svg_scrapling/licensing/`, `src/svg_scrapling/download/`, `src/svg_scrapling/conversion/`, `src/svg_scrapling/manifests/`, `src/svg_scrapling/storage/`, `src/svg_scrapling/quality/`, `src/svg_scrapling/pipeline/`, `src/svg_scrapling/utils/`
- Tests: `tests/unit/`, `tests/integration/`, `tests/fixtures/`
- Config and tooling: `pyproject.toml`, `uv.lock` or equivalent lockfile, `scripts/`, `docs/`
- Runtime, storage, cache, and generated outputs that must not be committed: `data/runs/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, local virtualenvs, generated CSV/JSONL/Markdown reports, debug snapshots, logs, downloaded assets, converted assets

Structure rules:

- Keep source-specific extraction rules inside source-specific modules, not in the core pipeline.
- Keep conversion code separate from discovery, scraping, and licensing.
- Keep licensing assessment separate from ranking and download.
- Treat `data/runs/` as runtime output only. It is for local execution artifacts, not normal source control history.
- If the actual layout changes, update this file in the same change.

## Where To Look

When starting work, inspect the nearest code and docs for the affected stage before editing.

Current planning anchors:

- Product brief and project scope: `README.md`
- External planning source currently driving the bootstrap: `/Users/syron/Downloads/README_codex_kids_coloring_asset_finder.md`
- Repo policy and workflow: `AGENTS.md`
- Planned issue breakdown: `docs/planning/github-issues-initial.md`
- Planned architecture and milestone map: `docs/planning/project-plan.md`

Target code entrypoints once scaffolded:

- Primary CLI entrypoint: `apps/cli/`, `src/svg_scrapling/__main__.py`
- Pipeline orchestration: `src/svg_scrapling/pipeline/`
- Typed models: `src/svg_scrapling/domain/`
- Config and policy resolution: `src/svg_scrapling/config/`
- Search expansion and provider interfaces: `src/svg_scrapling/search/`
- Fetch and browser execution: `src/svg_scrapling/scraping/`, `src/svg_scrapling/browser/`
- Extraction logic: `src/svg_scrapling/extraction/`
- Quality, ranking, and deduplication: `src/svg_scrapling/quality/`, `src/svg_scrapling/ranking/`
- Licensing and provenance: `src/svg_scrapling/licensing/`
- Download, conversion, manifest writing, and run storage: `src/svg_scrapling/download/`, `src/svg_scrapling/conversion/`, `src/svg_scrapling/manifests/`, `src/svg_scrapling/storage/`
- Automated validation: `tests/unit/`, `tests/integration/`

Search order:

1. Read the relevant issue.
2. Read the nearest applicable `AGENTS.md`.
3. Read the existing implementation for the affected subsystem.
4. Read tests and fixtures for the same behavior.
5. Read the config, CLI, and docs that constrain the change.
6. Make the smallest change that fits the architecture.

## Local Guides

Hierarchy rules:

- This root `AGENTS.md` applies repository-wide unless a deeper guide overrides part of it.
- Future subtree `AGENTS.md` files may narrow rules for directories such as `src/extraction/` or `tests/fixtures/`.
- Agents must prefer the nearest applicable `AGENTS.md`.
- A subtree guide applies only inside its own directory tree.
- If guidance conflicts, use the more specific guide for files in that subtree and this root guide everywhere else.

Current state:

- There are no subtree `AGENTS.md` files yet.
- If a subsystem becomes complex enough to need stricter local invariants, add a local guide as part of that subsystem work.

## Operating Rules

- Explore first. Do not implement from memory when the answer is discoverable from the repo or the active issue.
- Open or link an issue before starting non-trivial work.
- Keep issue scope narrow enough that one issue can be completed, validated, and committed cleanly on `main`.
- Reference the issue number at the start of every implementation commit, for example: `#5 add query expansion templates`.
- Prefer small, auditable commits over broad cleanup or speculative refactors.
- Default to working on `main`. Do not create branches for routine issue work in this repository.
- Consider a dedicated branch only if the change is potentially breaking, hard to integrate incrementally, or explicitly requested.
- Preserve the architecture described in the planning docs unless the issue explicitly changes it.
- Do not introduce source-specific hacks into shared abstractions without documenting why the abstraction needs to change.
- Keep docs, config, and runtime behavior aligned. If behavior changes, update the relevant docs in the same issue.

Issue workflow:

- Open an issue for features, bug fixes, refactors, migrations, and behavior changes.
- Use the issue to record objective, scope, constraints, dependencies, and validation expectations.
- Post concise progress comments when an issue spans multiple meaningful implementation steps or discoveries.
- If blocked, comment with the exact blocker and impact instead of hiding it behind a workaround.
- Split large work into linked issues that are independently reviewable and testable.

Commit workflow:

- One coherent issue per commit sequence.
- Every commit must be traceable to one issue.
- Put the issue reference first in the commit subject, for example: `#174 add Hermes frozen secure E2E benchmark workflow`.
- Avoid mixing unrelated cleanup into implementation commits.
- Do not push until the validation relevant to the touched subsystem passes locally.

## Subsystem Rules

- Subsystem: CLI
  Paths: `apps/cli/`
  Owner or steward: repository maintainers
  Purpose: expose the supported user workflows such as `assets find`, `assets inspect-manifest`, `assets re-score`, `assets convert`, `assets dedupe`, and `assets export-report`
  Invariants: commands map cleanly to pipeline stages; CLI flags mirror config models; error messages are explicit and actionable
  Integration boundaries: delegates to `src/` services and does not contain scraping, licensing, or conversion logic inline
  Required validation: CLI help output, command parsing tests, happy-path integration coverage

- Subsystem: Domain Models
  Paths: `src/svg_scrapling/domain/`
  Owner or steward: repository maintainers
  Purpose: define typed models such as `SearchQuery`, `SearchIntent`, `AssetCandidate`, `DownloadedAsset`, `ConvertedAsset`, `LicenseAssessment`, `QualityAssessment`, `ManifestRecord`, and `PipelineRunSummary`
  Invariants: models are strongly typed, serialization-safe, and shared across modules without circular coupling
  Integration boundaries: consumed by search, scraping, ranking, licensing, conversion, manifests, and pipeline orchestration
  Required validation: unit tests for parsing, normalization, and serialization

- Subsystem: Search
  Paths: `src/svg_scrapling/search/`
  Owner or steward: repository maintainers
  Purpose: build search intent, expand multilingual queries, and abstract search providers
  Invariants: provider interfaces stay decoupled from source-specific implementations; query expansion is deterministic for the same inputs
  Integration boundaries: outputs candidate page requests to scraping/fetch stages, not downloaded assets
  Required validation: unit tests for expansion templates and provider contract tests

- Subsystem: Scraping and Browser Fetch
  Paths: `src/svg_scrapling/scraping/`, `src/svg_scrapling/browser/`
  Owner or steward: repository maintainers
  Purpose: fetch candidate pages using static-first strategy with dynamic rendering only when needed
  Invariants: static extraction is preferred; retries and rate limits are explicit; domain concurrency controls are enforced; fetch strategy is visible in run metadata
  Integration boundaries: returns fetched page/materialized document inputs for extraction; does not rank or license assets
  Required validation: integration tests with fixtures, retry behavior tests, strategy resolver tests

- Subsystem: Extraction
  Paths: `src/svg_scrapling/extraction/`
  Owner or steward: repository maintainers
  Purpose: extract candidate assets, metadata, provenance hints, and source-specific signals from fetched content
  Invariants: source-specific rules remain isolated; extracted provenance is preserved; unsupported page states fail clearly
  Integration boundaries: consumes fetched content and emits `AssetCandidate` records for ranking/licensing
  Required validation: fixture-backed extractor tests and negative-case coverage

- Subsystem: Quality, Ranking, and Deduplication
  Paths: `src/svg_scrapling/quality/`, `src/svg_scrapling/ranking/`
  Owner or steward: repository maintainers
  Purpose: score coloring suitability, prioritize candidates, and remove duplicates while preserving provenance
  Invariants: heuristic scoring is versioned; duplicate handling preserves provenance links; rejection reasons are explicit
  Integration boundaries: consumes extracted/downloaded candidates and returns accepted/rejected assessments for downstream stages
  Required validation: unit tests for heuristic scoring and dedupe behavior; golden examples where feasible

- Subsystem: Licensing and Provenance
  Paths: `src/svg_scrapling/licensing/`
  Owner or steward: repository maintainers
  Purpose: detect, normalize, and evaluate license signals under `licensed_only` and `provenance_only`
  Invariants: unknown or restricted licenses are never silently upgraded to safe; mode behavior is explicit and testable
  Integration boundaries: consumes extracted hints and metadata; emits normalized license assessment and reuse status
  Required validation: policy tests for both modes and normalization tests for known license labels

- Subsystem: Download, Conversion, Manifests, and Storage
  Paths: `src/svg_scrapling/download/`, `src/svg_scrapling/conversion/`, `src/svg_scrapling/manifests/`, `src/svg_scrapling/storage/`
  Owner or steward: repository maintainers
  Purpose: store originals, convert PNG to SVG through separate interfaces, write manifests, and manage deterministic run directories
  Invariants: storage paths are deterministic per run; original and derived assets remain linked; manifest records preserve provenance and processing status
  Integration boundaries: consumes accepted assets and writes runtime outputs under `data/runs/<run_id>/`
  Required validation: integration tests covering run layout, manifest output, and conversion metadata linkage
  Preferred helper reference: `https://github.com/mikolaj92/svgo` may be used as an SVG helper during conversion, cleanup, or post-processing work when it fits the issue scope

- Subsystem: Pipeline
  Paths: `src/svg_scrapling/pipeline/`
  Owner or steward: repository maintainers
  Purpose: orchestrate the explicit pipeline stages from search intent through reporting
  Invariants: stages remain loosely coupled; failures surface clearly; stage boundaries remain observable in logs and summaries
  Integration boundaries: coordinates all subsystems without absorbing their internal logic
  Required validation: end-to-end tests with fixture-backed runs and summary assertions

## No Fallbacks, No Parallel Versions

- Do not silently fall back from unsupported or failing states.
- Unsupported states must fail loudly with explicit errors, explicit skips, or visible status markers in manifests and summaries.
- `preferred-format svg` may use PNG discovery only when the workflow explicitly enables fallback behavior.
- `licensed_only` must never retain assets unless the configured policy allows them.
- `provenance_only` may catalog broader results, but it must never imply those assets are automatically safe to reuse.
- Do not add shadow implementations such as `new_pipeline`, `legacy_pipeline`, `v2_extractors`, or duplicate command paths unless the issue explicitly requires a migration plan.
- If a replacement is needed, document the transition in the issue and remove the superseded path as soon as the migration is complete.
- Keep docs truthful. If something is planned but not implemented, say so plainly.

## Validation Standard

Every meaningful change requires validation proportional to risk.

Minimum standard:

- Run the tests closest to the changed subsystem.
- If no automated test exists yet, perform targeted manual validation and record what was checked in the issue or commit context.
- If behavior changes, add or update tests unless that is genuinely impractical at the current stage.
- If config, CLI, manifests, storage layout, or pipeline stage wiring changes, validate those paths directly.
- Do not push until relevant checks pass.

Expected validation by work type:

- Planning and doc-only changes: verify internal consistency, command examples, and path references.
- Domain/model changes: run unit tests for schema validation and serialization.
- CLI changes: run command parsing tests and a representative invocation.
- Search/scraping/extraction changes: run fixture-backed tests and the smallest useful integration path.
- Licensing and policy changes: run mode-specific policy tests.
- Conversion and manifest changes: run integration tests that verify output files and record linkage.
- Pipeline changes: run at least one end-to-end fixture-backed flow.

## Commands

Current repo status:

- The implementation scaffold does not exist yet.
- Issue 1 must introduce repo-root commands that satisfy the contract below.

Planned standard commands from the repository root:

- Install dependencies: `uv sync`
- Run the CLI locally: `uv run assets --help`
- Run targeted tests: `uv run pytest tests/unit`
- Run integration tests: `uv run pytest tests/integration`
- Run full test suite: `uv run pytest`
- Run linting: `uv run ruff check .`
- Run formatting check: `uv run ruff format --check .`
- Run type checks: `uv run mypy src apps`
- Build package artifacts if packaging is added: `uv build`

Command rules:

- Keep commands runnable from the repo root.
- Prefer project-managed commands over ad hoc shell pipelines.
- Use relative paths in docs and examples.
- If a slower full-suite command exists, document the targeted alternative for issue-level work.

## Done Means

Work is done only when all applicable items below are true:

- The change is covered by an explicit issue, unless it is a tiny doc fix or similarly trivial correction.
- The implementation follows this `AGENTS.md` and any deeper applicable guide.
- The change preserves the planned subsystem boundaries unless the issue explicitly changes them.
- No silent fallbacks or duplicate parallel flows were introduced.
- Runtime outputs, caches, logs, debug files, downloaded assets, converted assets, and generated reports are not committed by default.
- Relevant tests or targeted validation were completed and passed.
- Docs, config, and behavior tell the same story.
- Commits are small, auditable, and traceable to the issue.
- The change is ready to remain on `main` without hidden cleanup after review.

If any of these are not true, the work is not done yet.

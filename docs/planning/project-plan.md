# Image-Scrapling Project Plan

## Project Summary

`Image-Scrapling` is a Python CLI system that discovers coloring-style assets on the web, prefers SVG when possible, falls back to PNG when explicitly allowed, optionally converts raster assets to SVG, and writes provenance-rich manifests suitable for downstream review or ingestion.

The system is intended to be:

- modular
- strongly typed
- CLI-first
- provenance-first
- safe by default on licensing
- testable and resumable
- extensible through provider and backend abstractions

## Architecture

The implementation should follow a staged pipeline with clear subsystem boundaries.

### 1. CLI Layer

`apps/cli/`

Responsibilities:

- parse commands and flags
- build validated config objects
- start pipeline runs
- expose reporting and maintenance commands

Primary commands:

- `assets find`
- `assets inspect-manifest`
- `assets re-score`
- `assets convert`
- `assets dedupe`
- `assets export-report`

### 2. Config and Run Context

`src/config/`, `src/storage/`

Responsibilities:

- parse configuration from CLI and config files
- resolve licensing mode and fetch strategy
- create deterministic run directories under `data/runs/<run_id>/`
- keep output paths stable and predictable

### 3. Domain Models

`src/domain/`

Responsibilities:

- define strongly typed models shared across the codebase
- keep serialization format explicit
- prevent implicit, stringly typed contracts between modules

Core models:

- `SearchQuery`
- `SearchIntent`
- `AssetCandidate`
- `DownloadedAsset`
- `ConvertedAsset`
- `LicenseAssessment`
- `QualityAssessment`
- `ManifestRecord`
- `PipelineRunSummary`

### 4. Search Layer

`src/search/`

Responsibilities:

- expand multilingual user queries
- generate reusable templates for SVG-first, PNG fallback, outline, line-art, printable, and kids-friendly search intent
- provide source-agnostic search provider interfaces

### 5. Fetch and Browser Layer

`src/scraping/`, `src/browser/`

Responsibilities:

- fetch candidate pages
- prefer static extraction first
- escalate to dynamic rendering only when required
- apply retries, rate limiting, and domain-level concurrency controls

Technology direction:

- Scrapling for extraction-oriented scraping
- Lightpanda integration only where dynamic rendering is needed

### 6. Extraction Layer

`src/extraction/`

Responsibilities:

- extract direct SVG links
- extract direct image links
- detect embedded SVG
- collect nearby text, title, alt text, attribution hints, and license hints
- isolate source-specific extraction rules from core logic

### 7. Quality, Ranking, and Dedupe

`src/quality/`, `src/ranking/`

Responsibilities:

- rank candidates using heuristics
- assess coloring suitability
- detect duplicates at URL, normalized URL, content, perceptual, and SVG-structure levels where feasible
- preserve provenance when multiple pages point to the same asset

### 8. Licensing and Provenance

`src/licensing/`

Responsibilities:

- extract and normalize license hints
- map normalized values to reuse status
- support `licensed_only` and `provenance_only`
- never silently upgrade unknown or restricted assets to reusable

### 9. Download, Conversion, and Manifest Output

`src/download/`, `src/conversion/`, `src/manifests/`

Responsibilities:

- download accepted originals
- convert PNG to SVG through a separate backend interface
- validate and normalize derived SVG output
- write `manifest.jsonl` as the canonical output
- optionally export CSV and Markdown summary reports

Technology direction:

- VTracer as the primary PNG-to-SVG backend
- `https://github.com/mikolaj92/svgo` can be used as a preferred SVG helper reference for cleanup, optimization, or post-processing work

### 10. Pipeline Orchestration

`src/pipeline/`

Responsibilities:

- orchestrate explicit pipeline stages
- keep stage boundaries visible in logs and run summaries
- support later resumability without coupling everything together

Pipeline stages:

1. build search intent
2. expand query
3. search for candidate pages
4. fetch candidate pages
5. extract asset candidates
6. assess provenance and license
7. download originals
8. analyze quality and style
9. deduplicate
10. convert PNG to SVG when requested
11. re-score final outputs
12. write manifest and reports

## Milestones

### Milestone 1: Foundation

- repository bootstrap
- Python toolchain and lockfile
- package layout
- config system skeleton
- deterministic run storage
- typed domain models
- CLI skeleton

### Milestone 2: Search and Fetch Core

- query expansion
- provider abstraction
- fetch strategy resolver
- Scrapling integration skeleton
- Lightpanda integration boundary
- rate limiting and retry hooks

### Milestone 3: Extraction and Ranking

- extractor interfaces
- SVG and image candidate extraction
- style heuristics
- quality scoring
- deduplication

### Milestone 4: Licensing and Provenance

- license hint extraction
- normalization
- policy engine
- `licensed_only`
- `provenance_only`

### Milestone 5: Conversion and Output

- downloader
- converter interface
- VTracer integration
- SVG cleanup and validation
- manifest writer
- summary and report output

### Milestone 6: Hardening

- unit tests
- integration fixtures
- golden manifest coverage
- resilience improvements
- developer documentation

## Dependency Rules

- Do not start scraping implementation before config, run context, domain models, and CLI contracts exist.
- Do not start conversion before manifest/storage contracts exist.
- Do not add source-specific logic before extractor interfaces exist.
- Do not implement `licensed_only` or `provenance_only` as ad hoc conditionals inside unrelated modules; keep them behind a policy engine.
- Do not expand runtime output paths outside `data/runs/<run_id>/` without a dedicated issue.

## Implementation Order

1. repository bootstrap and toolchain
2. config and run storage
3. domain models
4. CLI skeleton
5. query expansion
6. search provider abstraction
7. fetch strategy and scraping layer
8. extractor framework
9. quality scoring and style heuristics
10. deduplication
11. licensing subsystem
12. downloader and manifest writer
13. conversion module
14. report generation
15. end-to-end pipeline wiring
16. hardening and developer docs

## Current Assumptions

- Implementation language is Python.
- Tooling should prefer `uv`, `pytest`, `ruff`, `mypy`, and a typed CLI framework such as `typer`.
- Work will land directly on `main` unless a specific issue is risky enough to justify a branch.
- The first coding issue should focus on scaffold and tooling, not provider integrations.
- GitHub issues drafted in `docs/planning/github-issues-initial.md` are proposals for review, not live issue IDs yet.

# Image-Scrapling Initial GitHub Issue Drafts

This file proposes the first issue set for `Image-Scrapling`. The goal is to turn the product README into small, dependency-ordered, implementation-ready issues that can be completed and committed directly on `main`.

Suggested issue format:

- one issue per coherent slice of work
- explicit dependencies
- explicit non-goals
- explicit acceptance criteria
- test plan included up front

Suggested labels:

- `type:foundation`
- `type:feature`
- `type:infra`
- `type:test`
- `area:cli`
- `area:domain`
- `area:search`
- `area:scraping`
- `area:extraction`
- `area:quality`
- `area:licensing`
- `area:conversion`
- `area:manifests`
- `priority:p0`
- `priority:p1`

Suggested milestones:

- `M1 Foundation`
- `M2 Search and Fetch Core`
- `M3 Extraction and Ranking`
- `M4 Licensing and Provenance`
- `M5 Conversion and Output`
- `M6 Hardening`

Recommended starting issues:

1. Issue 01
2. Issue 02
3. Issue 03
4. Issue 04

---

## Issue 01: Bootstrap Python workspace and repository skeleton

**Milestone:** `M1 Foundation`  
**Labels:** `type:foundation`, `type:infra`, `priority:p0`

**Objective**

Create the initial Python workspace, package layout, and development tooling so the repository has a stable base for all following issues.

**Scope**

- add `pyproject.toml`
- choose and configure package layout
- create top-level directories from the target architecture
- configure dependency management with a lockfile workflow
- configure linting, formatting, and type checking
- add `.gitignore` entries for runtime outputs and caches

**Non-goals**

- implementing pipeline behavior
- wiring provider integrations
- defining full domain models beyond scaffolding placeholders

**Implementation notes**

- prefer `uv` for dependency and command execution
- keep package layout aligned with `apps/cli` and `src/`
- establish repo-root commands that later issues can rely on

**Acceptance criteria**

- `pyproject.toml` exists and defines the project package
- scaffold directories exist for the main subsystems
- lint, format check, type check, and pytest commands are wired
- `.gitignore` blocks `data/runs/`, caches, logs, and generated outputs
- README or docs mention the bootstrap commands

**Dependencies**

- none

**Test plan**

- run the install/bootstrap command successfully
- run lint command
- run format-check command
- run type-check command
- run pytest with an empty or smoke test suite

---

## Issue 02: Add configuration models and deterministic run storage

**Milestone:** `M1 Foundation`  
**Labels:** `type:foundation`, `area:cli`, `priority:p0`

**Objective**

Define the configuration and run-context layer that all commands use, including deterministic output directories under `data/runs/<run_id>/`.

**Scope**

- create typed config models for mode, formats, fetch strategy, output path, and allowed licenses
- add run ID generation and path helpers
- define the canonical runtime directory structure
- ensure run metadata can be reused by later pipeline stages

**Non-goals**

- search provider implementation
- download or conversion logic
- manifest writing

**Implementation notes**

- keep config parsing separate from CLI presentation
- use deterministic and inspectable path generation
- make room for future resumability without implementing it yet

**Acceptance criteria**

- config models validate expected CLI fields
- run storage helpers create `originals`, `derived`, `manifests`, `logs`, and `debug` directories
- fetch strategy values support `static_first`, `dynamic_on_failure`, and `dynamic_only`
- licensing mode supports `licensed_only` and `provenance_only`

**Dependencies**

- Issue 01

**Test plan**

- unit tests for config validation
- unit tests for deterministic path generation
- integration-style test that creates a run directory tree in a temp location

---

## Issue 03: Define typed domain models and manifest schema contracts

**Milestone:** `M1 Foundation`  
**Labels:** `type:foundation`, `area:domain`, `priority:p0`

**Objective**

Create the shared typed models that define the contracts between the search, extraction, licensing, conversion, and manifest layers.

**Scope**

- implement the core domain models listed in the product README
- define enum or literal types for statuses and normalized license values
- define the minimum canonical `ManifestRecord` schema
- document serialization expectations for JSONL output

**Non-goals**

- writing the manifest to disk
- pipeline orchestration
- scoring heuristics

**Implementation notes**

- prefer explicit field names over nested untyped blobs
- keep models serialization-safe and easy to test
- avoid coupling models to any one provider implementation

**Acceptance criteria**

- all required domain models exist
- `ManifestRecord` includes the minimum required fields from the README
- normalized license values and reuse statuses are represented explicitly
- models support deterministic serialization for later manifest writing

**Dependencies**

- Issue 01
- Issue 02

**Test plan**

- unit tests for model validation
- serialization/deserialization tests for key models
- schema-focused tests for `ManifestRecord`

---

## Issue 04: Create CLI skeleton and command contract

**Milestone:** `M1 Foundation`  
**Labels:** `type:foundation`, `area:cli`, `priority:p0`

**Objective**

Introduce the CLI surface and command structure without implementing the full pipeline internals yet.

**Scope**

- create the root CLI app
- define `assets find`, `assets inspect-manifest`, `assets re-score`, `assets convert`, `assets dedupe`, and `assets export-report`
- validate CLI arguments into config/domain models
- print clear not-yet-implemented errors for commands not wired yet

**Non-goals**

- running a real search
- downloading assets
- conversion backend execution

**Implementation notes**

- use `typer` unless Issue 01 chooses a justified alternative
- keep CLI handlers thin and delegate to service entrypoints
- unsupported paths should fail clearly, not silently no-op

**Acceptance criteria**

- `assets --help` and subcommand help output are available
- `assets find` accepts the planned flags and validates them
- command handlers are wired to service boundaries or explicit placeholders
- unsupported behavior fails with explicit messages

**Dependencies**

- Issue 02
- Issue 03

**Test plan**

- CLI parser tests
- smoke tests for help output
- tests that invalid flags and invalid combinations fail clearly

---

## Issue 05: Implement multilingual query expansion and search intent builder

**Milestone:** `M2 Search and Fetch Core`  
**Labels:** `type:feature`, `area:search`, `priority:p0`

**Objective**

Turn a user query into a structured search intent plus deterministic expanded queries for SVG-first, PNG fallback, and coloring-style discovery.

**Scope**

- implement `SearchIntent` building
- add template-based query expansion
- support at least Polish and English patterns
- expose style-targeting terms such as outline, line art, coloring page, printable, and kids-friendly

**Non-goals**

- calling external search providers
- ranking final assets

**Implementation notes**

- expansion should be deterministic for the same input
- templates should be reusable and easy to extend
- keep language and style rules data-driven where practical

**Acceptance criteria**

- a base query expands into multiple targeted search strings
- SVG-first and PNG-fallback expansions can be generated separately
- style-bias terms are represented explicitly
- multilingual examples from the README are covered in tests

**Dependencies**

- Issue 03
- Issue 04

**Test plan**

- unit tests for query expansion output
- tests for Polish and English example queries
- tests for preferred-format and style-bias variations

---

## Issue 06: Add search provider abstraction and candidate page contract

**Milestone:** `M2 Search and Fetch Core`  
**Labels:** `type:feature`, `area:search`, `priority:p0`

**Objective**

Create a source-agnostic search provider interface that returns candidate pages without hardcoding provider behavior into the core domain.

**Scope**

- define provider protocol or interface
- define result contracts for candidate pages
- add a first test double or fixture-backed provider
- prepare extension points for later engines and public asset sources

**Non-goals**

- full production provider integrations
- page fetching

**Implementation notes**

- the contract should return candidate pages, not downloaded assets
- keep provider metadata rich enough for provenance and debugging
- start with a mockable contract so later provider work is testable

**Acceptance criteria**

- provider interface exists and is documented in code
- candidate page records are typed
- at least one fake provider can power tests or local development
- the CLI or pipeline layer can call the abstraction without provider-specific branching

**Dependencies**

- Issue 05

**Test plan**

- contract tests for a fake provider
- unit tests for candidate page normalization
- integration-style test that passes provider results into the next layer boundary

---

## Issue 07: Build fetch strategy resolver and Scrapling-based fetch layer

**Milestone:** `M2 Search and Fetch Core`  
**Labels:** `type:feature`, `area:scraping`, `priority:p0`

**Objective**

Implement the fetch layer that retrieves candidate pages using static-first behavior and only uses dynamic rendering when configured or necessary.

**Scope**

- build fetch strategy resolution
- wire Scrapling as the primary fetch/extraction layer
- add retry hooks
- add rate limiting hooks
- add domain-level concurrency controls
- define the Lightpanda browser boundary for later dynamic execution

**Non-goals**

- source-specific extraction
- ranking or licensing

**Implementation notes**

- keep dynamic rendering as an explicit escalation path
- do not make browser automation the default
- design the fetch result shape for extractor consumption

**Acceptance criteria**

- `static_first`, `dynamic_on_failure`, and `dynamic_only` are supported
- fetch responses are typed and include enough metadata for debugging
- retries and rate limit configuration are exposed at the API boundary
- Lightpanda integration point is defined even if minimal at first

**Dependencies**

- Issue 02
- Issue 06

**Test plan**

- unit tests for strategy resolution
- integration tests against fixture or fake HTTP responses
- tests for retry behavior and explicit failure propagation

---

## Issue 08: Create extractor framework and source-specific extractor contract

**Milestone:** `M3 Extraction and Ranking`  
**Labels:** `type:feature`, `area:extraction`, `priority:p0`

**Objective**

Define the extraction framework that turns fetched pages into typed asset candidates while isolating source-specific logic.

**Scope**

- define extractor interfaces
- add generic extractor flow
- add source-specific extractor registration or resolution
- define extracted metadata contracts

**Non-goals**

- quality scoring
- license normalization
- downloader behavior

**Implementation notes**

- generic extractors should cover common HTML cases
- source-specific extractors should be swappable and easy to test
- unsupported page states should fail explicitly or return structured rejections

**Acceptance criteria**

- extractor base interface exists
- extractor output maps cleanly into `AssetCandidate`
- extractor selection is extensible
- provenance and nearby metadata are preserved in the extracted result

**Dependencies**

- Issue 03
- Issue 07

**Test plan**

- unit tests for extractor selection
- fixture-backed extraction tests
- tests that unsupported inputs fail clearly

---

## Issue 09: Implement SVG and image candidate extraction heuristics

**Milestone:** `M3 Extraction and Ranking`  
**Labels:** `type:feature`, `area:extraction`, `priority:p0`

**Objective**

Extract direct SVG links, image links, embedded SVG, and nearby metadata signals needed for downstream ranking and licensing.

**Scope**

- direct SVG discovery
- direct image discovery
- embedded SVG extraction
- title, alt text, surrounding text, author, attribution, and nearby license hint extraction
- initial acceptance/rejection hints such as watermark suspicion or thumbnail suspicion

**Non-goals**

- final quality scoring
- final licensing decisions

**Implementation notes**

- bias toward standalone, outline-like, non-watermarked assets
- preserve raw evidence for later policy and ranking stages
- keep source-specific tweaks out of the generic extractor path

**Acceptance criteria**

- extractor returns typed candidates with provenance and metadata
- SVG and raster candidates are distinguished explicitly
- nearby descriptive and license hint fields are populated when present
- weak candidates can be marked with explicit rejection or penalty hints

**Dependencies**

- Issue 08

**Test plan**

- fixture-backed tests for SVG and raster extraction
- tests for embedded SVG capture
- negative tests for watermarked or low-value candidates

---

## Issue 10: Add quality scoring and coloring-suitability heuristics

**Milestone:** `M3 Extraction and Ranking`  
**Labels:** `type:feature`, `area:quality`, `priority:p0`

**Objective**

Rank candidates using a versioned heuristic scorer tuned for coloring-style assets.

**Scope**

- format score
- source trust score
- outline likelihood
- black-and-white likelihood
- kids coloring suitability
- conversion suitability
- duplicate penalty hook
- rejection reason reporting

**Non-goals**

- ML or CV-based scoring
- final dedupe implementation

**Implementation notes**

- keep scoring dimensions explicit and inspectable
- store enough detail for later manifest/debug output
- start with heuristics only

**Acceptance criteria**

- candidates receive structured quality assessments
- scoring dimensions are visible, not hidden in a single opaque number
- rejection reasons or penalties are explicit
- SVG-specific and PNG-specific heuristics are both represented

**Dependencies**

- Issue 09

**Test plan**

- unit tests for individual heuristics
- fixture-backed scoring tests
- tests for expected ranking order on curated examples

---

## Issue 11: Implement layered deduplication with provenance preservation

**Milestone:** `M3 Extraction and Ranking`  
**Labels:** `type:feature`, `area:quality`, `priority:p1`

**Objective**

Remove duplicate assets while preserving links to every known provenance source.

**Scope**

- URL-level dedupe
- normalized URL dedupe
- content hash dedupe
- raster perceptual hash support boundary
- SVG normalized structure hash boundary where feasible
- provenance merge behavior

**Non-goals**

- perfect near-duplicate vision matching
- irreversible source-lossy dedupe

**Implementation notes**

- dedupe should merge provenance, not discard it
- keep the approach layered so cheap checks happen before expensive ones
- document any deferred dedupe techniques explicitly

**Acceptance criteria**

- exact duplicates are collapsed
- provenance links survive dedupe
- dedupe metadata can be surfaced in manifests or reports
- duplicate counts are available for summaries

**Dependencies**

- Issue 09
- Issue 10

**Test plan**

- unit tests for normalized URL and hash-based dedupe
- tests that multiple sources merge into one kept asset record
- regression tests for false-positive-prone cases

---

## Issue 12: Build licensing extraction, normalization, and policy engine

**Milestone:** `M4 Licensing and Provenance`  
**Labels:** `type:feature`, `area:licensing`, `priority:p0`

**Objective**

Implement the licensing subsystem that extracts hints, normalizes them, maps reuse status, and enforces `licensed_only` and `provenance_only`.

**Scope**

- license hint extraction inputs
- normalized license values
- reuse status mapping
- confidence scoring
- policy engine for both supported modes
- manual-review-required handling

**Non-goals**

- unsafe pirate mode
- legal certainty beyond extracted evidence

**Implementation notes**

- unknown or restricted licenses must not be treated as safe
- policy behavior should live in one explicit module
- keep raw evidence alongside normalized outputs

**Acceptance criteria**

- normalized license values from the README are supported
- reuse statuses are explicit and typed
- `licensed_only` filters according to configuration
- `provenance_only` retains broader records without upgrading safety claims
- low-confidence cases can require manual review

**Dependencies**

- Issue 03
- Issue 09

**Test plan**

- normalization tests for representative labels
- policy tests for both modes
- tests proving unknown licenses are not silently approved

---

## Issue 13: Add downloader and deterministic manifest writer

**Milestone:** `M5 Conversion and Output`  
**Labels:** `type:feature`, `area:manifests`, `priority:p0`

**Objective**

Download accepted originals and write the canonical `manifest.jsonl` output with deterministic run-relative paths.

**Scope**

- original asset download flow
- filename normalization
- stored original path generation
- canonical manifest JSONL writer
- run summary metadata foundation

**Non-goals**

- PNG to SVG conversion
- CSV and Markdown export

**Implementation notes**

- preserve source URL and asset URL distinctly
- keep manifest rows append-friendly and deterministic
- store enough status detail to support debugging later

**Acceptance criteria**

- accepted assets can be downloaded into the run directory
- filenames are normalized using query, domain, stable hash, and extension
- `manifest.jsonl` records include required provenance and storage fields
- manifest writing is deterministic for stable inputs

**Dependencies**

- Issue 02
- Issue 03
- Issue 11
- Issue 12

**Test plan**

- integration tests for download path generation
- manifest serialization tests
- end-to-end test that writes a small JSONL manifest for fixture assets

---

## Issue 14: Implement PNG-to-SVG converter interface and VTracer backend

**Milestone:** `M5 Conversion and Output`  
**Labels:** `type:feature`, `area:conversion`, `priority:p1`

**Objective**

Add the conversion subsystem with a clean backend interface and a first VTracer implementation.

**Scope**

- converter protocol
- `VTracerConverter`
- conversion presets
- conversion result metadata
- linkage from original raster to derived SVG

**Non-goals**

- advanced image preprocessing chain
- alternative conversion backends

**Implementation notes**

- conversion stays separate from search, scraping, and licensing
- conversion presets should be explicit and testable
- record failures as data, not hidden logs

**Acceptance criteria**

- converter interface exists
- VTracer backend is callable through the interface
- presets include `line_art_fast`, `line_art_clean`, `general_bw`, and `general_color`
- conversion metadata links raster input and SVG output

**Dependencies**

- Issue 13

**Test plan**

- unit tests for converter configuration
- integration test for backend invocation on a small fixture PNG
- tests for conversion metadata serialization

---

## Issue 15: Add SVG cleanup, validation, and post-processing metrics

**Milestone:** `M5 Conversion and Output`  
**Labels:** `type:feature`, `area:conversion`, `priority:p1`

**Objective**

Validate and normalize produced SVG files so derived outputs are structurally usable and measurable.

**Scope**

- parse validation
- metadata cleanup
- dimension normalization
- viewBox normalization
- complexity estimation
- optional style normalization when safe

**Non-goals**

- artistic simplification beyond declared presets
- introducing silent fixes that hide invalid output

**Implementation notes**

- invalid SVG should fail clearly
- keep cleanup steps deterministic
- expose cleanup results in conversion metadata

**Acceptance criteria**

- invalid SVG outputs are detected explicitly
- valid outputs can be normalized consistently
- viewBox and basic dimension expectations are enforced
- complexity metrics are available for downstream scoring/reporting

**Dependencies**

- Issue 14

**Test plan**

- unit tests for SVG validation
- fixture tests for viewBox normalization
- tests for invalid SVG failure paths

---

## Issue 16: Wire end-to-end `assets find` happy path for manifest-first output

**Milestone:** `M5 Conversion and Output`  
**Labels:** `type:feature`, `area:cli`, `area:manifests`, `priority:p0`

**Objective**

Connect the implemented subsystems into a working `assets find` pipeline that produces a run directory and canonical manifest for a constrained happy path.

**Scope**

- pipeline orchestration through the defined stages
- happy-path execution from query to manifest
- summary output with core counts
- explicit failure reporting at stage boundaries

**Non-goals**

- broad provider coverage
- advanced resumability
- production-hardening of every failure mode

**Implementation notes**

- keep stage boundaries explicit in logs and summary output
- start with a constrained, testable happy path
- fail clearly when optional features are not yet supported

**Acceptance criteria**

- `assets find` can run against a fixture-backed or controlled provider flow
- run output includes manifest and basic summary data
- pipeline stages are observable in logs or summary structures
- errors surface with clear stage context

**Dependencies**

- Issue 05
- Issue 07
- Issue 09
- Issue 10
- Issue 11
- Issue 12
- Issue 13
- Issue 14

**Test plan**

- end-to-end integration test for a fixture-backed run
- assertions on run directory contents
- assertions on summary counts and manifest rows

---

## Issue 17: Add reporting commands and optional exports

**Milestone:** `M5 Conversion and Output`  
**Labels:** `type:feature`, `area:manifests`, `area:cli`, `priority:p1`

**Objective**

Provide secondary outputs and maintenance commands for inspecting manifests, re-scoring, deduping, converting, and exporting reports.

**Scope**

- `assets inspect-manifest`
- `assets re-score`
- `assets convert`
- `assets dedupe`
- `assets export-report`
- optional `manifest.csv`
- optional `summary.md`

**Non-goals**

- replacing the canonical JSONL manifest
- adding unrelated admin tooling

**Implementation notes**

- canonical output remains `manifest.jsonl`
- commands should reuse the same domain models and storage contracts
- report generation must stay derived from manifest data, not a separate truth source

**Acceptance criteria**

- each maintenance/reporting command exists and is documented
- optional exports are generated from the canonical manifest data
- summary output includes totals by format, domain, reuse status, rejection reasons, conversion failures, and duplicates

**Dependencies**

- Issue 13
- Issue 14
- Issue 16

**Test plan**

- command-level tests for each reporting command
- integration tests for CSV and Markdown export
- tests for summary totals consistency

---

## Issue 18: Add fixture suite, golden manifests, and hardening passes

**Milestone:** `M6 Hardening`  
**Labels:** `type:test`, `type:feature`, `priority:p1`

**Objective**

Strengthen the repository with realistic fixtures, regression coverage, and developer-facing documentation for ongoing issue-by-issue work on `main`.

**Scope**

- unit and integration fixture expansion
- golden manifest coverage
- resilience improvements for layout drift and partial failures
- contributor/developer documentation
- validation command documentation

**Non-goals**

- adding new product features unrelated to quality and maintainability
- broad provider expansion without dedicated issues

**Implementation notes**

- use fixtures to keep network-heavy logic testable
- golden manifests should lock down canonical output fields and summary behavior
- document debugging expectations and runtime artifact handling

**Acceptance criteria**

- representative fixture set exists for search, fetch, extraction, and manifest paths
- golden manifest tests protect canonical output
- developer docs explain setup, validation, and run output expectations
- key failure and retry paths have regression coverage

**Dependencies**

- Issue 16
- Issue 17

**Test plan**

- run full test suite
- verify golden manifest snapshots
- verify docs and validation commands against the implemented repo

"""CLI application contract for SVG Scrapling."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path
from typing import Annotated

import typer

from svg_scrapling import __version__
from svg_scrapling.config import FetchStrategy, FindAssetsConfig, LicenseMode, OutputFormat
from svg_scrapling.conversion import ConversionPreset, VTracerConverter
from svg_scrapling.domain import (
    AssetFormat,
    ConversionStatus,
    DownloadedAsset,
    DownloadStatus,
    SearchQuery,
)
from svg_scrapling.manifests import ManifestWriter, load_manifest_records
from svg_scrapling.pipeline import PipelineDependencies, PipelineStageError, run_find_assets
from svg_scrapling.quality import HeuristicQualityScorer
from svg_scrapling.ranking import CandidateDeduper
from svg_scrapling.reporting import (
    build_existing_run_layout,
    build_manifest_summary,
    export_manifest_csv,
    export_summary_markdown,
    manifest_record_to_candidate,
    render_summary_text,
)
from svg_scrapling.runtime import RuntimeFactories, build_pipeline_dependencies
from svg_scrapling.storage import RunLayout

app = typer.Typer(
    add_completion=False,
    help="SVG Scrapling command-line interface.",
    no_args_is_help=True,
)


def _parse_allowed_licenses(raw_value: str | None) -> frozenset[str]:
    if raw_value is None:
        return frozenset()
    return frozenset(part.strip() for part in raw_value.split(","))


def _to_asset_format(output_format: OutputFormat) -> AssetFormat:
    return AssetFormat(output_format.value)


def _build_find_models(
    query: str,
    count: int,
    preferred_format: OutputFormat,
    fallback_format: OutputFormat | None,
    convert_to: OutputFormat | None,
    mode: LicenseMode,
    allowed_licenses: str | None,
    fetch_strategy: FetchStrategy,
    output: Path,
) -> tuple[FindAssetsConfig, SearchQuery]:
    try:
        config = FindAssetsConfig(
            query=query,
            count=count,
            preferred_format=preferred_format,
            fallback_format=fallback_format,
            convert_to=convert_to,
            mode=mode,
            allowed_licenses=_parse_allowed_licenses(allowed_licenses),
            fetch_strategy=fetch_strategy,
            output_root=output,
        )
        search_query = SearchQuery(
            query=config.query,
            requested_count=config.count,
            preferred_format=_to_asset_format(config.preferred_format),
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc

    return config, search_query


def _not_implemented(command_name: str) -> typer.Exit:
    typer.echo(
        f"`assets {command_name}` validated successfully, but the underlying pipeline "
        "is not implemented yet.",
        err=True,
    )
    return typer.Exit(code=1)


def _resolve_output_path(source_path: Path, output: Path | None) -> Path:
    return output or source_path


def _asset_format_from_path(path: Path) -> AssetFormat:
    suffix = path.suffix.lower().lstrip(".")
    if suffix == "jpg":
        return AssetFormat.JPG
    if suffix == "jpeg":
        return AssetFormat.JPEG
    if suffix == "png":
        return AssetFormat.PNG
    if suffix == "webp":
        return AssetFormat.WEBP
    if suffix == "svg":
        return AssetFormat.SVG
    return AssetFormat.UNKNOWN


def _record_to_downloaded_asset(record_path: Path, record_id: str) -> DownloadedAsset:
    return DownloadedAsset(
        asset_id=record_id,
        source_page_url=record_path.as_posix(),
        asset_url=record_path.as_posix(),
        original_format=_asset_format_from_path(record_path),
        stored_original_path=record_path,
        download_status=DownloadStatus.DOWNLOADED,
    )


def _single_asset_layout(asset_path: Path) -> RunLayout:
    root = asset_path.parent
    return RunLayout(
        run_id=asset_path.stem,
        root=root,
        originals=root,
        derived=root,
        manifests=root,
        logs=root,
        debug=root,
    )


def _build_pipeline_dependencies(_config: FindAssetsConfig) -> PipelineDependencies:
    return build_pipeline_dependencies(
        _config,
        factories=RuntimeFactories(),
    )


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"assets {__version__}")
        raise typer.Exit()


def main(argv: Sequence[str] | None = None) -> None:
    app(args=list(argv) if argv is not None else None)


@app.callback()
def root(
    version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            callback=_version_callback,
            help="Show the CLI version and exit.",
            is_eager=True,
        ),
    ] = None,
) -> None:
    _ = version


@app.command("find")
def find_assets(
    query: Annotated[
        str,
        typer.Option("--query", help="Search query to expand and execute."),
    ],
    count: Annotated[
        int,
        typer.Option("--count", min=1, help="Requested asset count."),
    ] = 100,
    preferred_format: Annotated[
        OutputFormat,
        typer.Option("--preferred-format", help="Preferred original asset format."),
    ] = OutputFormat.SVG,
    fallback_format: Annotated[
        OutputFormat | None,
        typer.Option(
            "--fallback-format",
            help="Optional fallback format when preferred assets are scarce.",
        ),
    ] = None,
    convert_to: Annotated[
        OutputFormat | None,
        typer.Option("--convert-to", help="Optional derived output format."),
    ] = None,
    mode: Annotated[
        LicenseMode,
        typer.Option("--mode", help="Licensing/provenance retention mode."),
    ] = LicenseMode.PROVENANCE_ONLY,
    allowed_licenses: Annotated[
        str | None,
        typer.Option(
            "--allowed-licenses",
            help="Comma-separated allowlist used by licensed_only mode.",
        ),
    ] = None,
    fetch_strategy: Annotated[
        FetchStrategy,
        typer.Option("--fetch-strategy", help="Fetch escalation strategy."),
    ] = FetchStrategy.STATIC_FIRST,
    output: Annotated[
        Path,
        typer.Option(
            "--output",
            help="Base output directory for run artifacts.",
            dir_okay=True,
            file_okay=False,
            resolve_path=False,
        ),
    ] = Path("data/runs"),
) -> None:
    config, search_query = _build_find_models(
        query=query,
        count=count,
        preferred_format=preferred_format,
        fallback_format=fallback_format,
        convert_to=convert_to,
        mode=mode,
        allowed_licenses=allowed_licenses,
        fetch_strategy=fetch_strategy,
        output=output,
    )
    typer.echo(
        "Validated find request: "
        f"query={search_query.query!r}, count={search_query.requested_count}, "
        f"preferred_format={config.preferred_format.value}, mode={config.mode.value}.",
        err=True,
    )
    try:
        result = run_find_assets(
            config,
            dependencies=_build_pipeline_dependencies(config),
        )
    except RuntimeError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    except PipelineStageError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(
        "Find pipeline completed: "
        f"run_id={result.run_layout.run_id}, "
        f"manifest={result.manifest_path}, "
        f"summary={result.summary_path}",
        err=True,
    )


@app.command("inspect-manifest")
def inspect_manifest(
    manifest_path: Annotated[
        Path,
        typer.Argument(exists=False, help="Manifest file to inspect."),
    ],
) -> None:
    records = load_manifest_records(manifest_path)
    summary = build_manifest_summary(manifest_path, records)
    typer.echo(render_summary_text(summary))


@app.command("re-score")
def re_score(
    manifest_path: Annotated[
        Path,
        typer.Argument(exists=False, help="Manifest file to re-score."),
    ],
    output: Annotated[
        Path | None,
        typer.Option("--output", help="Optional output manifest path."),
    ] = None,
) -> None:
    records = load_manifest_records(manifest_path)
    scorer = HeuristicQualityScorer()
    rescored_records = []
    for record in records:
        assessment = scorer.score(manifest_record_to_candidate(record))
        rescored_records.append(
            replace(
                record,
                quality_score=assessment.quality_score,
                style_tags=assessment.style_tags,
                is_outline_like=assessment.is_outline_like,
                is_black_and_white_like=assessment.is_black_and_white_like,
                is_kids_friendly_candidate=assessment.is_kids_friendly_candidate,
                dedupe_hash=assessment.dedupe_hash,
            )
        )
    destination = _resolve_output_path(manifest_path, output)
    ManifestWriter(destination).write(tuple(rescored_records))
    typer.echo(f"Re-scored {len(rescored_records)} records into {destination}")


@app.command("convert")
def convert_assets(
    input_path: Annotated[
        Path,
        typer.Argument(exists=False, help="Asset or manifest to convert."),
    ],
    preset: Annotated[
        ConversionPreset,
        typer.Option("--preset", help="Conversion preset to apply."),
    ] = ConversionPreset.LINE_ART_FAST,
    output: Annotated[
        Path | None,
        typer.Option("--output", help="Optional output manifest path."),
    ] = None,
) -> None:
    converter = VTracerConverter()
    if input_path.suffix == ".jsonl":
        records = load_manifest_records(input_path)
        run_layout = build_existing_run_layout(input_path)
        converted_records = []
        converted_count = 0
        for record in records:
            if record.stored_original_path is None or record.original_format not in {
                AssetFormat.PNG,
                AssetFormat.JPG,
                AssetFormat.JPEG,
                AssetFormat.WEBP,
            }:
                converted_records.append(record)
                continue
            converted_asset = converter.convert(
                DownloadedAsset(
                    asset_id=record.id,
                    source_page_url=record.source_page_url,
                    asset_url=record.asset_url,
                    original_format=record.original_format,
                    stored_original_path=record.stored_original_path,
                    download_status=record.download_status,
                ),
                run_layout,
                preset=preset,
            )
            converted_records.append(
                replace(
                    record,
                    derived_svg_path=converted_asset.derived_svg_path,
                    conversion_status=converted_asset.conversion_status,
                    notes=tuple((*record.notes, *converted_asset.notes)),
                )
            )
            if converted_asset.conversion_status == ConversionStatus.CONVERTED:
                converted_count += 1
        destination = _resolve_output_path(input_path, output)
        ManifestWriter(destination).write(tuple(converted_records))
        typer.echo(f"Converted {converted_count} manifest records into {destination}")
        return

    downloaded_asset = _record_to_downloaded_asset(input_path, input_path.stem)
    converted_asset = converter.convert(
        downloaded_asset,
        _single_asset_layout(input_path),
        preset=preset,
    )
    if converted_asset.conversion_status != ConversionStatus.CONVERTED:
        typer.echo(f"Conversion failed: {converted_asset.notes}", err=True)
        raise typer.Exit(code=1)
    typer.echo(str(converted_asset.derived_svg_path))


@app.command("dedupe")
def dedupe_assets(
    manifest_path: Annotated[
        Path,
        typer.Argument(exists=False, help="Manifest file to deduplicate."),
    ],
    output: Annotated[
        Path | None,
        typer.Option("--output", help="Optional output manifest path."),
    ] = None,
) -> None:
    records = load_manifest_records(manifest_path)
    dedupe_result = CandidateDeduper().dedupe(
        tuple(manifest_record_to_candidate(record) for record in records)
    )
    record_by_id = {record.id: record for record in records}
    deduped_records = []
    for kept_candidate in dedupe_result.kept:
        original_record = record_by_id[kept_candidate.candidate.id]
        deduped_records.append(
            replace(
                original_record,
                dedupe_hash=kept_candidate.dedupe_key,
                notes=tuple(
                    (
                        *original_record.notes,
                        f"provenance_pages:{len(kept_candidate.provenance_page_urls)}",
                        f"asset_urls:{len(kept_candidate.asset_urls)}",
                    )
                ),
            )
        )
    destination = _resolve_output_path(manifest_path, output)
    ManifestWriter(destination).write(tuple(deduped_records))
    typer.echo(
        "Dedupe kept "
        f"{len(deduped_records)} records and removed "
        f"{dedupe_result.duplicates_removed} duplicates into {destination}"
    )


@app.command("export-report")
def export_report(
    manifest_path: Annotated[
        Path,
        typer.Argument(exists=False, help="Manifest file to summarize."),
    ],
    csv_output: Annotated[
        Path | None,
        typer.Option("--csv-output", help="Optional CSV export path."),
    ] = None,
    markdown_output: Annotated[
        Path | None,
        typer.Option("--markdown-output", help="Optional Markdown summary path."),
    ] = None,
) -> None:
    records = load_manifest_records(manifest_path)
    summary = build_manifest_summary(manifest_path, records)
    if csv_output is not None:
        export_manifest_csv(csv_output, records)
    if markdown_output is not None:
        export_summary_markdown(markdown_output, summary)
    typer.echo(render_summary_text(summary))

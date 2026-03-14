"""CLI application contract for SVG Scrapling."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Annotated

import typer

from svg_scrapling import __version__
from svg_scrapling.config import FetchStrategy, FindAssetsConfig, LicenseMode, OutputFormat
from svg_scrapling.domain import AssetFormat, SearchQuery

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
    raise _not_implemented("find")


@app.command("inspect-manifest")
def inspect_manifest(
    manifest_path: Annotated[
        Path,
        typer.Argument(exists=False, help="Manifest file to inspect."),
    ],
) -> None:
    _ = manifest_path
    raise _not_implemented("inspect-manifest")


@app.command("re-score")
def re_score(
    manifest_path: Annotated[
        Path,
        typer.Argument(exists=False, help="Manifest file to re-score."),
    ],
) -> None:
    _ = manifest_path
    raise _not_implemented("re-score")


@app.command("convert")
def convert_assets(
    input_path: Annotated[
        Path,
        typer.Argument(exists=False, help="Asset or manifest to convert."),
    ],
) -> None:
    _ = input_path
    raise _not_implemented("convert")


@app.command("dedupe")
def dedupe_assets(
    manifest_path: Annotated[
        Path,
        typer.Argument(exists=False, help="Manifest file to deduplicate."),
    ],
) -> None:
    _ = manifest_path
    raise _not_implemented("dedupe")


@app.command("export-report")
def export_report(
    manifest_path: Annotated[
        Path,
        typer.Argument(exists=False, help="Manifest file to summarize."),
    ],
) -> None:
    _ = manifest_path
    raise _not_implemented("export-report")

"""Stable public package entrypoints for SVG Scrapling."""

from importlib.metadata import version

from svg_scrapling.config import (
    DiscoveryProvider,
    FetchStrategy,
    FindAssetsConfig,
    LicenseMode,
    OutputFormat,
)
from svg_scrapling.pipeline import (
    PipelineDependencies,
    PipelineRunResult,
    PipelineStageError,
    run_find_assets,
)
from svg_scrapling.runtime import build_default_pipeline_dependencies

__all__ = [
    "__version__",
    "DiscoveryProvider",
    "FetchStrategy",
    "FindAssetsConfig",
    "LicenseMode",
    "OutputFormat",
    "PipelineDependencies",
    "PipelineRunResult",
    "PipelineStageError",
    "build_default_pipeline_dependencies",
    "run_find_assets",
]

__version__ = version("svg-scrapling")

from svg_scrapling import (
    DiscoveryProvider,
    FetchStrategy,
    FindAssetsConfig,
    LicenseMode,
    OutputFormat,
    PipelineDependencies,
    PipelineRunResult,
    PipelineStageError,
    build_default_pipeline_dependencies,
    run_find_assets,
)


def test_top_level_package_exports_stable_public_entrypoints() -> None:
    assert FindAssetsConfig is not None
    assert FetchStrategy is not None
    assert DiscoveryProvider is not None
    assert LicenseMode is not None
    assert OutputFormat is not None
    assert PipelineDependencies is not None
    assert PipelineRunResult is not None
    assert PipelineStageError is not None
    assert build_default_pipeline_dependencies is not None
    assert run_find_assets is not None

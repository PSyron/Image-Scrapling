"""Application runtime composition helpers."""

from svg_scrapling.runtime.composition import (
    RuntimeCompositionError,
    RuntimeFactories,
    build_pipeline_dependencies,
)
from svg_scrapling.runtime.defaults import (
    build_default_pipeline_dependencies,
    default_runtime_factories,
)
from svg_scrapling.runtime.fetching import (
    StaticFetchRuntimeSettings,
    build_default_fetch_orchestrator,
    static_fetch_runtime_settings_for,
)
from svg_scrapling.runtime.providers import (
    DiscoveryProviderRuntimeSettings,
    build_default_search_provider,
    discovery_provider_runtime_settings_for,
)

__all__ = [
    "RuntimeCompositionError",
    "RuntimeFactories",
    "DiscoveryProviderRuntimeSettings",
    "StaticFetchRuntimeSettings",
    "build_default_pipeline_dependencies",
    "build_default_fetch_orchestrator",
    "build_default_search_provider",
    "build_pipeline_dependencies",
    "discovery_provider_runtime_settings_for",
    "default_runtime_factories",
    "static_fetch_runtime_settings_for",
]

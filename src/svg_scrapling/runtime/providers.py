"""Default live-provider assembly for CLI runtime composition."""

from __future__ import annotations

from dataclasses import dataclass

from svg_scrapling.config import DiscoveryProvider, FindAssetsConfig
from svg_scrapling.runtime.composition import RuntimeCompositionError
from svg_scrapling.search import DuckDuckGoHtmlSearchProvider, SearchProvider


@dataclass(frozen=True)
class DiscoveryProviderRuntimeSettings:
    timeout_seconds: float
    retries: int
    max_queries_per_search: int


def discovery_provider_runtime_settings_for(
    config: FindAssetsConfig,
) -> DiscoveryProviderRuntimeSettings:
    return DiscoveryProviderRuntimeSettings(
        timeout_seconds=8.0,
        retries=1,
        max_queries_per_search=2 if config.count <= 10 else 3,
    )


def build_default_search_provider(config: FindAssetsConfig) -> SearchProvider:
    if config.provider in config.disabled_providers:
        raise RuntimeCompositionError(
            f"Selected provider {config.provider.value} is disabled for this run"
        )
    if config.provider == DiscoveryProvider.DUCKDUCKGO_HTML:
        settings = discovery_provider_runtime_settings_for(config)
        return DuckDuckGoHtmlSearchProvider(
            timeout_seconds=settings.timeout_seconds,
            retries=settings.retries,
            max_queries_per_search=settings.max_queries_per_search,
        )
    raise RuntimeCompositionError(f"Unsupported discovery provider {config.provider.value}")

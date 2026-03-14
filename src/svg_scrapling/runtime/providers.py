"""Default live-provider assembly for CLI runtime composition."""

from __future__ import annotations

from dataclasses import dataclass

from svg_scrapling.config import DiscoveryProvider, FindAssetsConfig
from svg_scrapling.runtime.composition import RuntimeCompositionError
from svg_scrapling.search import (
    BingHtmlSearchProvider,
    DuckDuckGoHtmlSearchProvider,
    FallbackSearchProvider,
    SearchProvider,
)


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


def ordered_discovery_providers_for(config: FindAssetsConfig) -> tuple[DiscoveryProvider, ...]:
    ordered = [config.provider]
    for provider in DiscoveryProvider:
        if provider == config.provider or provider in config.disabled_providers:
            continue
        ordered.append(provider)
    return tuple(ordered)


def build_default_search_provider(config: FindAssetsConfig) -> SearchProvider:
    if config.provider in config.disabled_providers:
        raise RuntimeCompositionError(
            f"Selected provider {config.provider.value} is disabled for this run"
        )
    settings = discovery_provider_runtime_settings_for(config)
    provider_instances: list[SearchProvider] = []
    for provider in ordered_discovery_providers_for(config):
        if provider == DiscoveryProvider.DUCKDUCKGO_HTML:
            provider_instances.append(
                DuckDuckGoHtmlSearchProvider(
                    timeout_seconds=settings.timeout_seconds,
                    retries=settings.retries,
                    max_queries_per_search=settings.max_queries_per_search,
                )
            )
            continue
        if provider == DiscoveryProvider.BING_HTML:
            provider_instances.append(
                BingHtmlSearchProvider(
                    timeout_seconds=settings.timeout_seconds,
                    retries=settings.retries,
                    max_queries_per_search=settings.max_queries_per_search,
                )
            )
            continue
        raise RuntimeCompositionError(f"Unsupported discovery provider {provider.value}")

    if not provider_instances:
        raise RuntimeCompositionError("No discovery providers remain enabled for this run")
    if len(provider_instances) == 1:
        return provider_instances[0]
    return FallbackSearchProvider(tuple(provider_instances))

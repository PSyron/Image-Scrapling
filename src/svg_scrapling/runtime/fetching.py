"""Default static-first fetch runtime assembly."""

from __future__ import annotations

from dataclasses import dataclass

from svg_scrapling.browser import build_lightpanda_command_client
from svg_scrapling.config import FetchStrategy, FindAssetsConfig
from svg_scrapling.scraping import (
    DomainConcurrencyController,
    FetchOrchestrator,
    StaticFetchTransport,
    StaticHtmlFetcher,
)


@dataclass(frozen=True)
class StaticFetchRuntimeSettings:
    retries: int
    retry_backoff_seconds: float
    domain_interval_seconds: float
    limit_per_domain: int
    request_timeout_seconds: float
    default_headers: tuple[tuple[str, str], ...]


def static_fetch_runtime_settings_for(config: FindAssetsConfig) -> StaticFetchRuntimeSettings:
    common_headers = (
        ("Accept", "text/html,application/xhtml+xml"),
        ("User-Agent", "svg-scrapling/0.1.0"),
    )
    if config.fetch_strategy == FetchStrategy.DYNAMIC_ON_FAILURE:
        return StaticFetchRuntimeSettings(
            retries=1,
            retry_backoff_seconds=0.4,
            domain_interval_seconds=0.4,
            limit_per_domain=2,
            request_timeout_seconds=8.0,
            default_headers=common_headers,
        )
    if config.fetch_strategy == FetchStrategy.DYNAMIC_ONLY:
        return StaticFetchRuntimeSettings(
            retries=0,
            retry_backoff_seconds=0.0,
            domain_interval_seconds=0.4,
            limit_per_domain=2,
            request_timeout_seconds=8.0,
            default_headers=common_headers,
        )
    return StaticFetchRuntimeSettings(
        retries=2,
        retry_backoff_seconds=0.6,
        domain_interval_seconds=0.5,
        limit_per_domain=2,
        request_timeout_seconds=10.0,
        default_headers=common_headers,
    )


def build_default_fetch_orchestrator(
    config: FindAssetsConfig,
    *,
    transport: StaticFetchTransport | None = None,
) -> FetchOrchestrator:
    settings = static_fetch_runtime_settings_for(config)
    static_fetcher = StaticHtmlFetcher(
        transport=transport,
        retries=settings.retries,
        retry_backoff_seconds=settings.retry_backoff_seconds,
        domain_interval_seconds=settings.domain_interval_seconds,
        concurrency=DomainConcurrencyController(settings.limit_per_domain),
        default_timeout_seconds=settings.request_timeout_seconds,
        default_headers=dict(settings.default_headers),
    )
    dynamic_client = build_lightpanda_command_client()
    return FetchOrchestrator(static_fetcher=static_fetcher, dynamic_client=dynamic_client)

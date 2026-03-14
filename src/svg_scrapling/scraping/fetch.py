"""Fetch orchestration with Scrapling parsing and optional dynamic fallback."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from threading import BoundedSemaphore
from time import monotonic, sleep
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from scrapling import Selector

from svg_scrapling.config import FetchStrategy


class FetchError(RuntimeError):
    """Explicit fetch failure."""


@dataclass(frozen=True)
class FetchRequest:
    url: str
    strategy: FetchStrategy = FetchStrategy.STATIC_FIRST
    timeout_seconds: float = 10.0
    headers: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class FetchResponse:
    url: str
    final_url: str
    status_code: int
    html: str
    headers: dict[str, str]
    fetched_via: str
    parser_name: str
    attempts: int
    document: Selector


class StaticFetchTransport(Protocol):
    def fetch(
        self,
        url: str,
        timeout_seconds: float,
        headers: dict[str, str],
    ) -> tuple[int, str, dict[str, str], str]:
        """Return status code, HTML body, headers, and final URL."""


class UrllibTransport:
    """Minimal sync HTTP transport."""

    def fetch(
        self,
        url: str,
        timeout_seconds: float,
        headers: dict[str, str],
    ) -> tuple[int, str, dict[str, str], str]:
        request = Request(url, headers=headers)
        try:
            with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
                body = response.read().decode("utf-8", errors="replace")
                response_headers = dict(response.headers.items())
                final_url = response.geturl()
                return response.status, body, response_headers, final_url
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise FetchError(f"HTTP {exc.code} for {url}: {body[:200]}") from exc
        except URLError as exc:
            raise FetchError(f"Request failed for {url}: {exc.reason}") from exc


class DomainConcurrencyController:
    """Per-domain concurrency slots for future parallel fetches."""

    def __init__(self, limit_per_domain: int = 2) -> None:
        if limit_per_domain < 1:
            raise ValueError("limit_per_domain must be greater than zero")
        self._limit_per_domain = limit_per_domain
        self._locks: dict[str, BoundedSemaphore] = {}

    @contextmanager
    def slot(self, domain: str) -> Iterator[None]:
        semaphore = self._locks.setdefault(domain, BoundedSemaphore(self._limit_per_domain))
        acquired = semaphore.acquire(timeout=5.0)
        if not acquired:
            raise FetchError(f"Timed out waiting for concurrency slot for domain {domain}")
        try:
            yield
        finally:
            semaphore.release()


class StaticHtmlFetcher:
    """Sync fetcher with retries, rate limiting, and Scrapling parsing."""

    def __init__(
        self,
        transport: StaticFetchTransport | None = None,
        *,
        retries: int = 2,
        domain_interval_seconds: float = 0.0,
        concurrency: DomainConcurrencyController | None = None,
        clock: Callable[[], float] = monotonic,
        sleeper: Callable[[float], None] = sleep,
    ) -> None:
        self._transport = transport or UrllibTransport()
        self._retries = retries
        self._domain_interval_seconds = domain_interval_seconds
        self._concurrency = concurrency or DomainConcurrencyController()
        self._clock = clock
        self._sleeper = sleeper
        self._last_request_at: dict[str, float] = {}

    def fetch(self, request: FetchRequest) -> FetchResponse:
        parsed_url = urlparse(request.url)
        domain = parsed_url.netloc or parsed_url.path
        last_error: FetchError | None = None

        with self._concurrency.slot(domain):
            self._apply_rate_limit(domain)
            for attempt in range(1, self._retries + 2):
                try:
                    status_code, html, headers, final_url = self._transport.fetch(
                        request.url,
                        request.timeout_seconds,
                        request.headers,
                    )
                    document = Selector(html, url=final_url)
                    self._last_request_at[domain] = self._clock()
                    return FetchResponse(
                        url=request.url,
                        final_url=final_url,
                        status_code=status_code,
                        html=html,
                        headers=headers,
                        fetched_via="static",
                        parser_name="scrapling.Selector",
                        attempts=attempt,
                        document=document,
                    )
                except FetchError as exc:
                    last_error = exc
                    if attempt == self._retries + 1:
                        break
            raise last_error or FetchError(f"Failed to fetch {request.url}")

    def _apply_rate_limit(self, domain: str) -> None:
        if self._domain_interval_seconds <= 0:
            return
        now = self._clock()
        previous = self._last_request_at.get(domain)
        if previous is None:
            return
        elapsed = now - previous
        remaining = self._domain_interval_seconds - elapsed
        if remaining > 0:
            self._sleeper(remaining)


class DynamicFetchClient(Protocol):
    def is_available(self) -> bool:
        """Return whether the dynamic client can currently run."""

    def fetch_html(self, url: str, timeout_seconds: float) -> tuple[str, str]:
        """Return HTML body and final URL."""


class NullDynamicFetchClient:
    """Explicit dynamic boundary until Lightpanda execution is wired."""

    def is_available(self) -> bool:
        return False

    def fetch_html(self, url: str, timeout_seconds: float) -> tuple[str, str]:
        _ = timeout_seconds
        raise FetchError(
            f"Dynamic fetch requested for {url}, but no Lightpanda-compatible client is configured"
        )


class FetchOrchestrator:
    """Resolve fetch strategy between static and dynamic paths."""

    def __init__(
        self,
        static_fetcher: StaticHtmlFetcher,
        dynamic_client: DynamicFetchClient | None = None,
    ) -> None:
        self._static_fetcher = static_fetcher
        self._dynamic_client = dynamic_client or NullDynamicFetchClient()

    def fetch(self, request: FetchRequest) -> FetchResponse:
        if request.strategy == FetchStrategy.DYNAMIC_ONLY:
            return self._fetch_dynamic(request, attempts=1)

        try:
            return self._static_fetcher.fetch(request)
        except FetchError:
            if request.strategy != FetchStrategy.DYNAMIC_ON_FAILURE:
                raise
            return self._fetch_dynamic(request, attempts=self._static_fetcher._retries + 2)

    def _fetch_dynamic(self, request: FetchRequest, attempts: int) -> FetchResponse:
        if not self._dynamic_client.is_available():
            raise FetchError(
                "Fetch strategy "
                f"{request.strategy.value} requires a dynamic client, but none is available"
            )

        html, final_url = self._dynamic_client.fetch_html(request.url, request.timeout_seconds)
        document = Selector(html, url=final_url)
        return FetchResponse(
            url=request.url,
            final_url=final_url,
            status_code=200,
            html=html,
            headers={},
            fetched_via="dynamic",
            parser_name="scrapling.Selector",
            attempts=attempts,
            document=document,
        )

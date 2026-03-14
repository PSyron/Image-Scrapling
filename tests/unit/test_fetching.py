from svg_scrapling.config import FetchStrategy
from svg_scrapling.scraping import (
    FetchError,
    FetchOrchestrator,
    FetchRequest,
    StaticHtmlFetcher,
)


class FakeTransport:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = 0

    def fetch(self, url: str, timeout_seconds: float, headers: dict[str, str]):
        _ = timeout_seconds
        _ = headers
        self.calls += 1
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class FakeDynamicClient:
    def __init__(self, html: str, available: bool = True):
        self._html = html
        self._available = available

    def is_available(self) -> bool:
        return self._available

    def fetch_html(self, url: str, timeout_seconds: float):
        _ = timeout_seconds
        return self._html, url


def test_static_fetcher_returns_scrapling_document() -> None:
    transport = FakeTransport(
        [
            (
                200,
                "<html><head><title>Tiger</title></head><body>ok</body></html>",
                {"content-type": "text/html"},
                "https://example.com/page",
            )
        ]
    )
    fetcher = StaticHtmlFetcher(transport=transport)

    response = fetcher.fetch(FetchRequest(url="https://example.com/page"))

    assert response.status_code == 200
    assert response.fetched_via == "static"
    assert response.parser_name == "scrapling.Selector"
    assert response.document.css("title").get() == "<title>Tiger</title>"


def test_static_fetcher_retries_before_success() -> None:
    transport = FakeTransport(
        [
            FetchError("temporary"),
            (
                200,
                "<html><body>ok</body></html>",
                {},
                "https://example.com/page",
            ),
        ]
    )
    fetcher = StaticHtmlFetcher(transport=transport, retries=1)

    response = fetcher.fetch(FetchRequest(url="https://example.com/page"))

    assert response.attempts == 2
    assert transport.calls == 2


def test_fetch_orchestrator_uses_dynamic_on_failure() -> None:
    transport = FakeTransport([FetchError("boom")])
    static_fetcher = StaticHtmlFetcher(transport=transport, retries=0)
    orchestrator = FetchOrchestrator(
        static_fetcher=static_fetcher,
        dynamic_client=FakeDynamicClient("<html><body>dynamic</body></html>"),
    )

    response = orchestrator.fetch(
        FetchRequest(
            url="https://example.com/page",
            strategy=FetchStrategy.DYNAMIC_ON_FAILURE,
        )
    )

    assert response.fetched_via == "dynamic"
    assert response.document.css("body").get() == "<body>dynamic</body>"


def test_dynamic_only_requires_available_client() -> None:
    transport = FakeTransport([])
    static_fetcher = StaticHtmlFetcher(transport=transport)
    orchestrator = FetchOrchestrator(
        static_fetcher=static_fetcher,
        dynamic_client=FakeDynamicClient("<html></html>", available=False),
    )

    try:
        orchestrator.fetch(
            FetchRequest(
                url="https://example.com/page",
                strategy=FetchStrategy.DYNAMIC_ONLY,
            )
        )
    except FetchError as exc:
        assert "requires a dynamic client" in str(exc)
    else:
        raise AssertionError("Expected FetchError for missing dynamic client")


def test_static_fetcher_applies_domain_interval() -> None:
    transport = FakeTransport(
        [
            (
                200,
                "<html><body>one</body></html>",
                {},
                "https://example.com/1",
            ),
            (
                200,
                "<html><body>two</body></html>",
                {},
                "https://example.com/2",
            ),
        ]
    )
    timestamps = iter([0.0, 0.0, 0.5, 1.0])
    sleeps: list[float] = []
    fetcher = StaticHtmlFetcher(
        transport=transport,
        domain_interval_seconds=1.0,
        clock=lambda: next(timestamps),
        sleeper=sleeps.append,
    )

    fetcher.fetch(FetchRequest(url="https://example.com/1"))
    fetcher.fetch(FetchRequest(url="https://example.com/2"))

    assert sleeps == [0.5]

from svg_scrapling.config import FetchStrategy, FindAssetsConfig
from svg_scrapling.runtime import (
    build_default_fetch_orchestrator,
    static_fetch_runtime_settings_for,
)
from svg_scrapling.scraping import FetchOrchestrator, FetchRequest


class FakeTransport:
    def __init__(self):
        self.calls = 0

    def fetch(self, url: str, timeout_seconds: float, headers: dict[str, str]):
        _ = timeout_seconds
        _ = headers
        self.calls += 1
        return 200, "<html><body>ok</body></html>", {}, url


def test_static_fetch_runtime_settings_change_with_strategy() -> None:
    static_first = static_fetch_runtime_settings_for(
        FindAssetsConfig(query="tiger", fetch_strategy=FetchStrategy.STATIC_FIRST)
    )
    dynamic_on_failure = static_fetch_runtime_settings_for(
        FindAssetsConfig(query="tiger", fetch_strategy=FetchStrategy.DYNAMIC_ON_FAILURE)
    )

    assert static_first.retries == 2
    assert static_first.request_timeout_seconds == 10.0
    assert dynamic_on_failure.retries == 1
    assert dynamic_on_failure.request_timeout_seconds == 8.0


def test_build_default_fetch_orchestrator_assembles_static_runtime() -> None:
    config = FindAssetsConfig(query="tiger", fetch_strategy=FetchStrategy.STATIC_FIRST)
    transport = FakeTransport()

    orchestrator = build_default_fetch_orchestrator(config, transport=transport)
    response = orchestrator.fetch(
        FetchRequest(
            url="https://example.com/page",
            strategy=config.fetch_strategy,
        )
    )

    assert isinstance(orchestrator, FetchOrchestrator)
    assert response.fetched_via == "static"
    assert transport.calls == 1

import json
import subprocess

import pytest

from svg_scrapling.browser import (
    LightpandaCommandClient,
    build_lightpanda_command_client,
    lightpanda_env_key,
)
from svg_scrapling.scraping import FetchError


def test_build_lightpanda_command_client_reads_environment() -> None:
    client = build_lightpanda_command_client(
        environment={lightpanda_env_key(): "/usr/bin/env lightpanda-wrapper"}
    )

    assert client is not None
    assert client.command == ("/usr/bin/env", "lightpanda-wrapper")


def test_lightpanda_client_returns_html_from_json_payload() -> None:
    def fake_runner(*args, **kwargs):
        _ = args
        _ = kwargs
        return subprocess.CompletedProcess(
            args=["lightpanda-wrapper"],
            returncode=0,
            stdout=json.dumps(
                {
                    "html": "<html><body>dynamic ok</body></html>",
                    "final_url": "https://example.com/final",
                }
            ),
            stderr="",
        )

    client = LightpandaCommandClient(
        command=("/bin/echo",),
        runner=fake_runner,
    )

    html, final_url = client.fetch_html("https://example.com/original", 4.0)

    assert "dynamic ok" in html
    assert final_url == "https://example.com/final"


def test_lightpanda_client_raises_on_invalid_json() -> None:
    def fake_runner(*args, **kwargs):
        _ = args
        _ = kwargs
        return subprocess.CompletedProcess(
            args=["lightpanda-wrapper"],
            returncode=0,
            stdout="not-json",
            stderr="",
        )

    client = LightpandaCommandClient(
        command=("/bin/echo",),
        runner=fake_runner,
    )

    with pytest.raises(FetchError, match="invalid JSON"):
        client.fetch_html("https://example.com/original", 4.0)

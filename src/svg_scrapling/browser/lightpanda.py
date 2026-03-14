"""Lightpanda-compatible subprocess client for dynamic HTML fetches."""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from svg_scrapling.scraping import FetchError

_LIGHTPANDA_ENV_KEY = "SVG_SCRAPLING_LIGHTPANDA_CMD"


@dataclass(frozen=True)
class LightpandaCommandClient:
    """Run a wrapper command that prints JSON with html and final_url."""

    command: tuple[str, ...]
    environment: Mapping[str, str] | None = None
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run

    def __post_init__(self) -> None:
        if not self.command:
            raise ValueError("command must not be empty")

    def is_available(self) -> bool:
        executable = self.command[0]
        if os.path.sep in executable:
            return os.path.exists(executable)
        return shutil.which(executable) is not None

    def fetch_html(self, url: str, timeout_seconds: float) -> tuple[str, str]:
        if not self.is_available():
            raise FetchError(
                "Dynamic fetch requested for "
                f"{url}, but command {self.command[0]!r} is unavailable",
                url=url,
                retryable=False,
            )

        command = [*self.command, "fetch", url, str(timeout_seconds)]
        try:
            completed = self.runner(
                command,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
                env=dict(self.environment) if self.environment is not None else None,
            )
        except subprocess.TimeoutExpired as exc:
            raise FetchError(
                f"Dynamic fetch timed out after {timeout_seconds:.1f}s for {url}",
                url=url,
            ) from exc
        except OSError as exc:
            raise FetchError(
                f"Dynamic fetch failed to launch for {url}: {exc}",
                url=url,
                retryable=False,
            ) from exc

        if completed.returncode != 0:
            stderr = completed.stderr.strip() or "no stderr"
            raise FetchError(
                f"Dynamic fetch command failed for {url}: {stderr}",
                url=url,
            )

        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise FetchError(
                f"Dynamic fetch returned invalid JSON for {url}",
                url=url,
                retryable=False,
            ) from exc

        html = payload.get("html")
        final_url = payload.get("final_url") or url
        if not isinstance(html, str) or not html.strip():
            raise FetchError(
                f"Dynamic fetch response did not include HTML for {url}",
                url=url,
                retryable=False,
            )
        if not isinstance(final_url, str) or not final_url.strip():
            raise FetchError(
                f"Dynamic fetch response did not include a valid final_url for {url}",
                url=url,
                retryable=False,
            )
        return html, final_url


def build_lightpanda_command_client(
    *,
    environment: Mapping[str, str] | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> LightpandaCommandClient | None:
    env = dict(os.environ if environment is None else environment)
    raw_command = env.get(_LIGHTPANDA_ENV_KEY, "").strip()
    if not raw_command:
        return None

    command = tuple(shlex.split(raw_command))
    if not command:
        return None
    return LightpandaCommandClient(command=command, environment=env, runner=runner)


def lightpanda_env_key() -> str:
    return _LIGHTPANDA_ENV_KEY


def lightpanda_command_from_environment(
    environment: Mapping[str, str] | None = None,
) -> Sequence[str] | None:
    client = build_lightpanda_command_client(environment=environment)
    if client is None:
        return None
    return client.command

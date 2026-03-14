"""Helpers for deterministic run directory creation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class RunLayout:
    """Concrete paths for one pipeline run."""

    run_id: str
    root: Path
    originals: Path
    derived: Path
    manifests: Path
    logs: Path
    debug: Path


def generate_run_id(now: datetime | None = None) -> str:
    """Generate a UTC-stamped run identifier."""

    timestamp = now or datetime.now(timezone.utc)
    normalized_timestamp = timestamp.astimezone(timezone.utc)
    return normalized_timestamp.strftime("run-%Y%m%dT%H%M%SZ")


def create_run_layout(base_dir: Path, run_id: str) -> RunLayout:
    """Create the canonical directory structure for a run."""

    normalized_run_id = run_id.strip()
    if not normalized_run_id:
        raise ValueError("run_id must not be blank")

    root = base_dir / normalized_run_id
    layout = RunLayout(
        run_id=normalized_run_id,
        root=root,
        originals=root / "originals",
        derived=root / "derived",
        manifests=root / "manifests",
        logs=root / "logs",
        debug=root / "debug",
    )

    for path in (
        layout.root,
        layout.originals,
        layout.derived,
        layout.manifests,
        layout.logs,
        layout.debug,
    ):
        path.mkdir(parents=True, exist_ok=True)

    return layout

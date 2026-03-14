from datetime import datetime, timezone
from pathlib import Path

import pytest

from svg_scrapling.storage import RunLayout, create_run_layout, generate_run_id


def test_generate_run_id_is_stable_for_given_timestamp() -> None:
    run_id = generate_run_id(datetime(2026, 3, 14, 12, 30, 0, tzinfo=timezone.utc))

    assert run_id == "run-20260314T123000Z"


def test_create_run_layout_returns_expected_paths(tmp_path: Path) -> None:
    layout = create_run_layout(tmp_path / "runs", "run-20260314T123000Z")

    assert layout == RunLayout(
        run_id="run-20260314T123000Z",
        root=tmp_path / "runs" / "run-20260314T123000Z",
        originals=tmp_path / "runs" / "run-20260314T123000Z" / "originals",
        derived=tmp_path / "runs" / "run-20260314T123000Z" / "derived",
        manifests=tmp_path / "runs" / "run-20260314T123000Z" / "manifests",
        logs=tmp_path / "runs" / "run-20260314T123000Z" / "logs",
        debug=tmp_path / "runs" / "run-20260314T123000Z" / "debug",
    )


def test_create_run_layout_creates_directories(tmp_path: Path) -> None:
    layout = create_run_layout(tmp_path / "runs", "run-20260314T123000Z")

    assert layout.root.is_dir()
    assert layout.originals.is_dir()
    assert layout.derived.is_dir()
    assert layout.manifests.is_dir()
    assert layout.logs.is_dir()
    assert layout.debug.is_dir()


def test_create_run_layout_rejects_blank_run_id(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="run_id must not be blank"):
        create_run_layout(tmp_path, "   ")

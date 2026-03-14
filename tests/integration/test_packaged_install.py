from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _venv_python(venv_root: Path) -> Path:
    if sys.platform == "win32":
        return venv_root / "Scripts" / "python.exe"
    return venv_root / "bin" / "python"


def _venv_assets(venv_root: Path) -> Path:
    if sys.platform == "win32":
        return venv_root / "Scripts" / "assets.exe"
    return venv_root / "bin" / "assets"


def test_built_wheel_installs_and_exposes_supported_library_and_cli_surface(
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    dist_dir = tmp_path / "dist"
    venv_root = tmp_path / "consumer-venv"

    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(dist_dir)],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    wheel_path = next(dist_dir.glob("svg_scrapling-*.whl"))

    subprocess.run(
        [sys.executable, "-m", "venv", str(venv_root)],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )

    venv_python = _venv_python(venv_root)
    subprocess.run(
        [str(venv_python), "-m", "pip", "install", str(wheel_path)],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )

    import_check = subprocess.run(
        [
            str(venv_python),
            "-c",
            (
                "from svg_scrapling import "
                "FindAssetsConfig, FetchStrategy, build_default_pipeline_dependencies; "
                "print(FindAssetsConfig.__name__); "
                "print(FetchStrategy.STATIC_FIRST.value); "
                "print(callable(build_default_pipeline_dependencies))"
            ),
        ],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )

    cli_help = subprocess.run(
        [str(_venv_assets(venv_root)), "--help"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "FindAssetsConfig" in import_check.stdout
    assert "static_first" in import_check.stdout
    assert "True" in import_check.stdout
    assert "SVG Scrapling command-line interface" in cli_help.stdout

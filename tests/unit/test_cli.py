from typer.testing import CliRunner

from svg_scrapling.cli import app

runner = CliRunner()


def test_root_help_lists_commands() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "find" in result.stdout
    assert "inspect-manifest" in result.stdout
    assert "export-report" in result.stdout


def test_find_validates_known_options_before_placeholder_exit() -> None:
    result = runner.invoke(
        app,
        [
            "find",
            "--query",
            "tiger coloring page",
            "--count",
            "5",
            "--preferred-format",
            "svg",
            "--mode",
            "provenance_only",
            "--fetch-strategy",
            "static_first",
        ],
    )

    assert result.exit_code == 1
    assert "Validated find request" in result.stderr
    assert "No pipeline dependencies are configured" in result.stderr


def test_find_rejects_invalid_license_combination() -> None:
    result = runner.invoke(
        app,
        [
            "find",
            "--query",
            "tiger coloring page",
            "--mode",
            "licensed_only",
        ],
    )

    assert result.exit_code != 0
    assert "allowed_licenses must be provided" in result.output


def test_find_rejects_unknown_allowed_license() -> None:
    result = runner.invoke(
        app,
        [
            "find",
            "--query",
            "tiger coloring page",
            "--allowed-licenses",
            "made_up",
        ],
    )

    assert result.exit_code != 0
    assert "unsupported values: made_up" in result.output


def test_version_flag_prints_version() -> None:
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.stdout.startswith("assets ")

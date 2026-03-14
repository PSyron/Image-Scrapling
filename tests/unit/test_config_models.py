from pathlib import Path

import pytest

from svg_scrapling.config import FetchStrategy, FindAssetsConfig, LicenseMode, OutputFormat


def test_find_assets_config_normalizes_values() -> None:
    config = FindAssetsConfig(
        query="  tiger coloring page  ",
        allowed_licenses=frozenset({"CC0", "public_domain"}),
        mode=LicenseMode.PROVENANCE_ONLY,
        preferred_format=OutputFormat.SVG,
        fetch_strategy=FetchStrategy.DYNAMIC_ON_FAILURE,
        output_root=Path("~/tmp/svg-scrapling"),
    )

    assert config.query == "tiger coloring page"
    assert config.allowed_licenses == frozenset({"cc0", "public_domain"})
    assert config.output_root == Path("~/tmp/svg-scrapling").expanduser()


def test_find_assets_config_rejects_blank_query() -> None:
    with pytest.raises(ValueError, match="query must not be blank"):
        FindAssetsConfig(query="   ")


def test_find_assets_config_requires_positive_count() -> None:
    with pytest.raises(ValueError, match="count must be greater than zero"):
        FindAssetsConfig(query="cats", count=0)


def test_find_assets_config_rejects_unknown_licenses() -> None:
    with pytest.raises(ValueError, match="unsupported values: made_up"):
        FindAssetsConfig(query="cats", allowed_licenses=frozenset({"made_up"}))


def test_find_assets_config_requires_allowlist_for_licensed_only() -> None:
    with pytest.raises(ValueError, match="allowed_licenses must be provided"):
        FindAssetsConfig(query="cats", mode=LicenseMode.LICENSED_ONLY)

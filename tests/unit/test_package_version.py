from importlib.metadata import version

import svg_scrapling


def test_package_version_matches_distribution_metadata() -> None:
    assert svg_scrapling.__version__ == version("svg-scrapling")

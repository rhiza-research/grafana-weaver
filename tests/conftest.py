"""Pytest configuration and shared fixtures."""

import tempfile
from pathlib import Path

import pytest


class TestDataHelper:
    """Helper class for accessing test data files with common patterns."""

    def __init__(self, base_path: Path):
        self.base_path = base_path

    def __call__(self, relative_path: str) -> Path:
        """Get path to test data file or directory."""
        return self.base_path / relative_path

    def dir(self, test_case: str) -> Path:
        """Get test data directory for a test case."""
        return self.base_path / test_case

    def input_json(self, test_case: str) -> Path:
        """Get input.json file for a test case."""
        return self.base_path / test_case / "input.json"

    def expected_jsonnet(self, test_case: str) -> Path:
        """Get expected.jsonnet file for a test case."""
        return self.base_path / test_case / "expected.jsonnet"

    def assets(self, test_case: str) -> Path:
        """Get assets directory for a test case."""
        return self.base_path / test_case / "assets"


@pytest.fixture
def test_data():
    """
    Fixture that provides helper methods to access test data files.

    Usage:
        # Get directory
        test_data_dir = test_data.dir("basic_extraction")

        # Get common files directly
        input_file = test_data.input_json("basic_extraction")
        expected_file = test_data.expected_jsonnet("basic_extraction")
        assets_dir = test_data.assets("basic_extraction")

        # Or get arbitrary paths
        dashboard_file = test_data("download_dashboards/sample_dashboard.json")
    """
    test_data_base = Path(__file__).parent / "test_data"
    return TestDataHelper(test_data_base)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def dashboards_structure(temp_dir):
    """Create a complete dashboards directory structure."""
    dashboards_base = temp_dir / "dashboards"
    src_dir = dashboards_base / "src"
    build_dir = dashboards_base / "build"
    assets_dir = src_dir / "assets"

    src_dir.mkdir(parents=True)
    build_dir.mkdir(parents=True)
    assets_dir.mkdir(parents=True)

    return {
        "base": dashboards_base,
        "src": src_dir,
        "build": build_dir,
        "assets": assets_dir,
    }

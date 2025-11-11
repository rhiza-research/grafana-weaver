#!/usr/bin/env python3
"""Jsonnet builder for Grafana dashboards."""

import json
import sys
from pathlib import Path

import _jsonnet


class JsonnetBuilder:
    """Builder for compiling Jsonnet templates to JSON."""

    def __init__(self, dashboards_dir: Path):
        """
        Initialize Jsonnet builder.

        Args:
            dashboards_dir: Base directory containing the dashboards
        """
        self.dashboards_dir = Path(dashboards_dir)
        self.src_dir = self.dashboards_dir / "src"
        self.build_dir = self.dashboards_dir / "build"

    def build_all(self) -> list[Path]:
        """
        Build all Jsonnet dashboard files to JSON.

        Searches for all .jsonnet files in src directory and builds them
        to corresponding locations in build directory.

        Returns:
            List of paths to built JSON files

        Raises:
            SystemExit: If any build fails
        """
        # Find all .jsonnet files
        jsonnet_files = list(self.src_dir.glob("**/*.jsonnet"))

        if not jsonnet_files:
            print(f"No .jsonnet files found in {self.src_dir}")
            return []

        built_files = []
        for dashboard_file in jsonnet_files:
            print(f"Building {dashboard_file}")
            output_file = self._build_one(dashboard_file)
            built_files.append(output_file)

        return built_files

    def _build_one(self, jsonnet_file: Path) -> Path:
        """
        Build a single Jsonnet file to JSON.

        Args:
            jsonnet_file: Path to the Jsonnet file

        Returns:
            Path to the output JSON file

        Raises:
            SystemExit: If build fails
        """
        # Get the relative path from src directory
        rel_path = jsonnet_file.relative_to(self.src_dir)

        # Create corresponding build directory
        build_path = self.build_dir / rel_path.parent
        build_path.mkdir(parents=True, exist_ok=True)

        # Output JSON file path
        output_file = build_path / f"{jsonnet_file.stem}.json"

        # Build jsonnet to JSON using Python jsonnet library
        try:
            # Evaluate jsonnet file
            json_str = _jsonnet.evaluate_file(str(jsonnet_file))

            # Parse and pretty-print the JSON
            json_data = json.loads(json_str)
            with open(output_file, "w") as f:
                json.dump(json_data, f, indent=2)

            return output_file

        except RuntimeError as e:
            print(f"Error building {jsonnet_file}: {e}")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON from {jsonnet_file}: {e}")
            sys.exit(1)

    def get_built_files(self) -> list[Path]:
        """
        Get all built JSON files from build directory.

        Returns:
            List of paths to JSON files in build directory
        """
        if not self.build_dir.exists():
            return []

        return list(self.build_dir.rglob("*.json"))

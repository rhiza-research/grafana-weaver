#!/usr/bin/env python3
"""Upload Grafana dashboards from Jsonnet templates to Grafana."""

import base64
import json
import os
import sys
from pathlib import Path

import _jsonnet
import requests

from .utils import get_grafana_config, get_grafana_context


def build_jsonnet_dashboards(dashboards_base_dir: Path) -> None:
    """
    Build all Jsonnet dashboard files to JSON.

    Args:
        dashboards_base_dir: Base directory containing the dashboards
    """
    src_dir = dashboards_base_dir / "src"

    # Find all .jsonnet files
    jsonnet_files = list(src_dir.glob("**/*.jsonnet"))

    if not jsonnet_files:
        print(f"No .jsonnet files found in {src_dir}")
        return

    for dashboard_file in jsonnet_files:
        print(f"Building {dashboard_file}")

        # Get the relative path from src directory
        rel_path = dashboard_file.relative_to(src_dir)

        # Create corresponding build directory
        build_path = dashboards_base_dir / "build" / rel_path.parent
        build_path.mkdir(parents=True, exist_ok=True)

        # Output JSON file path
        output_file = build_path / f"{dashboard_file.stem}.json"

        # Build jsonnet to JSON using Python jsonnet library
        try:
            # Evaluate jsonnet file
            json_str = _jsonnet.evaluate_file(str(dashboard_file))

            # Parse and pretty-print the JSON
            json_data = json.loads(json_str)
            with open(output_file, "w") as f:
                json.dump(json_data, f, indent=2)

        except RuntimeError as e:
            print(f"Error building {dashboard_file}: {e}")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON from {dashboard_file}: {e}")
            sys.exit(1)


def upload_dashboards_to_grafana(dashboards_base_dir: Path, context_name: str) -> None:
    """
    Upload built dashboards to Grafana using the Grafana API.

    Args:
        dashboards_base_dir: Base directory containing built dashboards
        context_name: grafanactl context name (e.g., 'myproject-1')
    """
    print("\nUploading dashboards to Grafana...")

    # Get Grafana config from grafanactl config file
    grafana_config = get_grafana_config(context_name)

    grafana_url = grafana_config["server"].rstrip("/")
    username = grafana_config["user"]
    password = grafana_config["password"]

    # Use Basic auth
    credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
    headers = {
        "Authorization": f"Basic {credentials}",
        "Content-Type": "application/json",
    }

    # Find all built JSON files
    build_dir = dashboards_base_dir / "build"
    if not build_dir.exists():
        print(f"Error: build directory not found at {build_dir}")
        sys.exit(1)

    json_files = list(build_dir.rglob("*.json"))
    if not json_files:
        print(f"No JSON files found in {build_dir}")
        return

    print(f"Found {len(json_files)} dashboards to upload")

    success_count = 0
    error_count = 0

    for json_file in json_files:
        # Read the dashboard JSON
        with open(json_file) as f:
            dashboard_json = json.load(f)

        # Prepare the dashboard payload
        payload = {
            "dashboard": dashboard_json,
            "overwrite": True,
            "message": "Updated by grafana-weaver",
        }

        # Get folder name if dashboard is in a subdirectory
        rel_path = json_file.relative_to(build_dir)
        if rel_path.parent != Path("."):
            # TODO: We might want to create/find the folder ID and add it to payload
            # For now, dashboards will go to General folder
            pass

        # Upload the dashboard
        response = requests.post(f"{grafana_url}/api/dashboards/db", headers=headers, json=payload)

        if response.status_code in [200, 201]:
            print(f"  ✓ Uploaded: {dashboard_json.get('title', json_file.name)}")
            success_count += 1
        else:
            print(f"  ✗ Failed to upload {json_file.name}: {response.status_code} {response.text}")
            error_count += 1

    print(f"\nUpload complete: {success_count} succeeded, {error_count} failed")

    if error_count > 0:
        sys.exit(1)


def main():
    """Main entry point for uploading dashboards."""
    # Get or prompt for grafanactl context name
    context_name = get_grafana_context()

    # Get dashboards directory from environment or use default
    dashboard_dir_str = os.environ.get("DASHBOARD_DIR")
    if dashboard_dir_str:
        dashboards_base_dir = Path(dashboard_dir_str)
    else:
        # Default: dashboards directory in current working directory
        dashboards_base_dir = Path.cwd() / "dashboards"

    if not dashboards_base_dir.exists():
        print(f"Error: dashboards directory not found at {dashboards_base_dir}")
        sys.exit(1)

    print("=" * 42)
    print("Uploading Grafana dashboards...")
    print("=" * 42)
    print(f"Using dashboards directory: {dashboards_base_dir}")

    # Build all jsonnet files
    build_jsonnet_dashboards(dashboards_base_dir)

    # Upload dashboards to Grafana
    upload_dashboards_to_grafana(dashboards_base_dir, context_name)

    print("\n" + "=" * 42)
    print("Dashboards uploaded successfully!")
    print("=" * 42)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Download Grafana dashboards and extract external content."""

import base64
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import requests

from .extract_external_content import process_json_file
from .utils import get_grafana_config, get_grafana_context


def download_dashboards_from_grafana(downloaded_dir: Path, context_name: str) -> None:
    """
    Download dashboards from Grafana using the Grafana API.

    Args:
        downloaded_dir: Directory to download dashboards to
        context_name: grafanactl context name (e.g., 'myproject-1')
    """
    print("\nStep 1: Downloading dashboards from Grafana...")

    # Get Grafana config from grafanactl config file
    grafana_config = get_grafana_config(context_name)

    grafana_url = grafana_config["server"].rstrip("/")
    username = grafana_config["user"]
    password = grafana_config["password"]

    # Use Basic auth
    credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
    headers = {"Authorization": f"Basic {credentials}"}

    # Fetch all dashboards
    print("Fetching dashboard list...")
    response = requests.get(f"{grafana_url}/api/search?type=dash-db", headers=headers)
    if response.status_code != 200:
        print(f"Error fetching dashboard list: {response.status_code} {response.text}")
        sys.exit(1)

    dashboards = response.json()
    print(f"Found {len(dashboards)} dashboards")

    # Create download directory
    downloaded_dir.mkdir(parents=True, exist_ok=True)

    # Sanitize names for file paths
    def sanitize(name):
        return name.lower().replace(" ", "-").replace("/", "-")

    # Download each dashboard
    for dash in dashboards:
        uid = dash["uid"]
        folder_title = dash.get("folderTitle", "")

        # Fetch full dashboard JSON
        dash_response = requests.get(f"{grafana_url}/api/dashboards/uid/{uid}", headers=headers)
        if dash_response.status_code != 200:
            print(f"Warning: Failed to fetch dashboard {uid}: {dash_response.status_code}")
            continue

        dashboard_data = dash_response.json()
        dashboard_json = dashboard_data["dashboard"]

        # Try to get folder info from the dashboard metadata
        meta = dashboard_data.get("meta", {})
        if not folder_title and meta.get("folderTitle"):
            folder_title = meta["folderTitle"]

        title = sanitize(dashboard_json["title"])

        # Build file path with optional folder
        if folder_title and folder_title != "General":
            folder = sanitize(folder_title)
            file_path = downloaded_dir / folder / f"{title}.json"
            file_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            file_path = downloaded_dir / f"{title}.json"

        # Write dashboard JSON
        with open(file_path, "w") as f:
            json.dump(dashboard_json, f, indent=2)

        print(f"  Downloaded: {file_path.relative_to(downloaded_dir.parent)}")

    print(f"\nDashboard download complete! ({len(dashboards)} dashboards)")


def process_dashboards(downloaded_dir: Path, output_dir: Path) -> None:
    """
    Process downloaded dashboards to extract external content.

    Args:
        downloaded_dir: Directory containing downloaded JSON files
        output_dir: Base output directory for processed dashboards (e.g., ./dashboards)
    """
    print("\nStep 2: Processing dashboards to extract external content...")

    # Find all JSON files in the downloaded directory
    json_files = list(downloaded_dir.rglob("*.json"))

    if not json_files:
        print(f"No JSON files found in {downloaded_dir}")
        return

    for json_file in json_files:
        print(f"Processing: {json_file}")

        # Process the JSON file directly as a Python function call
        # - pass downloaded_dir as base_dir to preserve folder structure
        # - pass output_dir to specify where to write the jsonnet files
        success = process_json_file(str(json_file), base_dir=str(downloaded_dir), output_dir=str(output_dir))

        if not success:
            print(f"Error processing {json_file}")
            sys.exit(1)


def main():
    """Main entry point for downloading dashboards."""
    # Get or prompt for grafanactl context name
    context_name = get_grafana_context()

    # Get dashboards directory from environment or use default
    dashboard_dir_str = os.environ.get("DASHBOARD_DIR")
    if dashboard_dir_str:
        dashboards_base_dir = Path(dashboard_dir_str)
    else:
        # Default: dashboards directory in current working directory
        dashboards_base_dir = Path.cwd() / "dashboards"

    print("=" * 42)
    print("Downloading Grafana dashboards...")
    print("=" * 42)
    print(f"Output directory: {dashboards_base_dir}")

    # Create temporary directory for downloads
    downloaded_dir = Path(tempfile.mkdtemp())

    try:
        # Download dashboards from Grafana
        download_dashboards_from_grafana(downloaded_dir, context_name)

        # Process dashboards to extract external content (outputs to dashboards/src/)
        process_dashboards(downloaded_dir, dashboards_base_dir)

        print("\n" + "=" * 42)
        print("Dashboard download complete!")
        print("=" * 42)
        print(f"  - Jsonnet templates: {dashboards_base_dir}/src/")
        print(f"  - Assets: {dashboards_base_dir}/src/assets/")

    finally:
        # Clean up temporary directory
        if downloaded_dir.exists():
            shutil.rmtree(downloaded_dir)


if __name__ == "__main__":
    main()

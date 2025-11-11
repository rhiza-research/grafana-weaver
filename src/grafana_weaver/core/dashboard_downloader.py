#!/usr/bin/env python3
"""Download dashboards from Grafana to local filesystem."""

import json
from pathlib import Path

from grafana_weaver.core.client import GrafanaClient


class DashboardDownloader:
    """
    Downloads dashboards from Grafana and saves them to disk.

    This class handles fetching dashboards from Grafana, organizing them
    by folder structure, and writing them as JSON files.
    """

    def __init__(self, client: GrafanaClient):
        """
        Initialize the dashboard downloader.

        Args:
            client: GrafanaClient instance for API access
        """
        self.client = client

    @staticmethod
    def _sanitize_name(name: str) -> str:
        """
        Sanitize a name for use as a file or directory name.

        Args:
            name: The name to sanitize

        Returns:
            Sanitized name suitable for filesystem use
        """
        return name.lower().replace(" ", "-").replace("/", "-")

    def download_all(self, output_dir: Path) -> list[Path]:
        """
        Download all dashboards from Grafana to the specified directory.

        Dashboards are organized by folder structure, with folders becoming
        subdirectories (except for the "General" folder).

        Args:
            output_dir: Directory to save downloaded dashboards

        Returns:
            List of paths to downloaded dashboard files
        """
        print("\nDownloading dashboards from Grafana...")
        print("Fetching dashboard list...")
        dashboards = self.client.list_dashboards()
        print(f"Found {len(dashboards)} dashboards")

        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        downloaded_files = []

        # Download each dashboard
        for dash in dashboards:
            uid = dash["uid"]
            folder_title = dash.get("folderTitle", "")

            # Fetch full dashboard JSON
            try:
                dashboard_data = self.client.get_dashboard(uid)
            except Exception as e:
                print(f"Warning: Failed to fetch dashboard {uid}: {e}")
                continue

            dashboard_json = dashboard_data["dashboard"]

            # Try to get folder info from the dashboard metadata
            meta = dashboard_data.get("meta", {})
            if not folder_title and meta.get("folderTitle"):
                folder_title = meta["folderTitle"]

            title = self._sanitize_name(dashboard_json["title"])

            # Build file path with optional folder
            if folder_title and folder_title != "General":
                folder = self._sanitize_name(folder_title)
                file_path = output_dir / folder / f"{title}.json"
                file_path.parent.mkdir(parents=True, exist_ok=True)
            else:
                file_path = output_dir / f"{title}.json"

            # Write dashboard JSON
            with open(file_path, "w") as f:
                json.dump(dashboard_json, f, indent=2)

            downloaded_files.append(file_path)
            print(f"  Downloaded: {file_path.relative_to(output_dir.parent)}")

        print(f"\nDashboard download complete! ({len(dashboards)} dashboards)")
        return downloaded_files

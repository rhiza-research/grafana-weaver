#!/usr/bin/env python3
"""Grafana API client."""

import base64

import requests


class GrafanaClient:
    """Client for interacting with Grafana API."""

    def __init__(self, server: str, user: str, password: str, org_id: int = 1):
        """
        Initialize Grafana client.

        Args:
            server: Grafana server URL
            user: Grafana username
            password: Grafana password
            org_id: Grafana organization ID
        """
        self.server = server.rstrip("/")
        self.org_id = org_id

        credentials = base64.b64encode(f"{user}:{password}".encode()).decode()
        self._headers = {
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/json",
        }
        # Set organization context if org_id is specified
        if org_id:
            self._headers["X-Grafana-Org-Id"] = str(org_id)

    def list_dashboards(self) -> list[dict]:
        """
        Fetch all dashboards from Grafana.

        Returns:
            List of dashboard metadata dictionaries

        Raises:
            requests.HTTPError: If the request fails
        """
        response = requests.get(f"{self.server}/api/search?type=dash-db", headers=self._headers)
        response.raise_for_status()
        return response.json()

    def get_dashboard(self, uid: str) -> dict:
        """
        Fetch a specific dashboard by UID.

        Args:
            uid: Dashboard UID

        Returns:
            Dashboard data including metadata and dashboard JSON

        Raises:
            requests.HTTPError: If the request fails
        """
        response = requests.get(f"{self.server}/api/dashboards/uid/{uid}", headers=self._headers)
        response.raise_for_status()
        return response.json()

    def get_folder_by_title(self, title: str) -> dict | None:
        """
        Get folder by title.

        Args:
            title: Folder title

        Returns:
            Folder data if found, None otherwise

        Raises:
            requests.HTTPError: If the request fails
        """
        response = requests.get(f"{self.server}/api/folders", headers=self._headers)
        response.raise_for_status()
        folders = response.json()

        for folder in folders:
            if folder.get("title") == title:
                return folder
        return None

    def create_folder(self, title: str) -> dict:
        """
        Create a folder in Grafana.

        Args:
            title: Folder title

        Returns:
            Created folder data

        Raises:
            requests.HTTPError: If the request fails
        """
        payload = {"title": title}
        response = requests.post(f"{self.server}/api/folders", headers=self._headers, json=payload)
        response.raise_for_status()
        return response.json()

    def get_or_create_folder(self, title: str) -> dict:
        """
        Get folder by title, creating it if it doesn't exist.

        Args:
            title: Folder title

        Returns:
            Folder data

        Raises:
            requests.HTTPError: If the request fails
        """
        folder = self.get_folder_by_title(title)
        if folder:
            return folder
        return self.create_folder(title)

    def upload_dashboard(
        self, dashboard_json: dict, folder_uid: str | None = None, overwrite: bool = True, message: str = None
    ) -> dict:
        """
        Upload a dashboard to Grafana.

        Args:
            dashboard_json: Dashboard JSON structure
            folder_uid: UID of the folder to place the dashboard in (None for General folder)
            overwrite: Whether to overwrite existing dashboard
            message: Commit message for the dashboard update

        Returns:
            Response from Grafana API containing dashboard metadata

        Raises:
            requests.HTTPError: If the request fails
        """
        payload = {
            "dashboard": dashboard_json,
            "overwrite": overwrite,
            "message": message or "Updated by grafana-weaver",
        }

        # Add folder UID if specified
        if folder_uid:
            payload["folderUid"] = folder_uid

        response = requests.post(f"{self.server}/api/dashboards/db", headers=self._headers, json=payload)
        response.raise_for_status()
        return response.json()

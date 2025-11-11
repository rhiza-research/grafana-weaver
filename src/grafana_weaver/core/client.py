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
        self._headers = self._build_auth_headers(user, password)

    def _build_auth_headers(self, user: str, password: str) -> dict:
        """
        Build Basic auth headers.

        Args:
            user: Grafana username
            password: Grafana password

        Returns:
            Dictionary of HTTP headers
        """
        credentials = base64.b64encode(f"{user}:{password}".encode()).decode()
        return {
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/json",
        }

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

    def upload_dashboard(self, dashboard_json: dict, overwrite: bool = True, message: str = None) -> dict:
        """
        Upload a dashboard to Grafana.

        Args:
            dashboard_json: Dashboard JSON structure
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

        response = requests.post(f"{self.server}/api/dashboards/db", headers=self._headers, json=payload)
        response.raise_for_status()
        return response.json()

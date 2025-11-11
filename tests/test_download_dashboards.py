"""Tests for download_dashboards command."""

from types import SimpleNamespace
from unittest.mock import Mock, patch

from grafana_weaver.main import download_dashboards
from grafana_weaver.core.client import GrafanaClient
from grafana_weaver.core.dashboard_downloader import DashboardDownloader


class TestDashboardDownloader:
    """Tests for DashboardDownloader class."""

    def test_successful_download(self, tmp_path):
        """Successful download should download all dashboards."""
        client = GrafanaClient("https://grafana.example.com", "admin", "secret")

        with patch.object(client, "list_dashboards") as mock_list:
            with patch.object(client, "get_dashboard") as mock_get:
                # Mock list response
                mock_list.return_value = [
                    {"uid": "dash1", "title": "Dashboard 1", "folderTitle": ""},
                    {"uid": "dash2", "title": "Dashboard 2", "folderTitle": "MyFolder"},
                ]

                # Mock dashboard responses
                def get_dashboard_side_effect(uid):
                    if uid == "dash1":
                        return {
                            "dashboard": {"title": "Dashboard 1", "panels": []},
                            "meta": {"folderTitle": ""},
                        }
                    else:
                        return {
                            "dashboard": {"title": "Dashboard 2", "panels": []},
                            "meta": {"folderTitle": "MyFolder"},
                        }

                mock_get.side_effect = get_dashboard_side_effect

                downloader = DashboardDownloader(client)
                downloaded_files = downloader.download_all(tmp_path)

                # Verify dashboards were downloaded
                assert (tmp_path / "dashboard-1.json").exists()
                assert (tmp_path / "myfolder" / "dashboard-2.json").exists()
                assert len(downloaded_files) == 2

    def test_download_api_error(self, tmp_path):
        """API error should be handled gracefully."""
        client = GrafanaClient("https://grafana.example.com", "admin", "secret")

        with patch.object(client, "list_dashboards") as mock_list:
            with patch.object(client, "get_dashboard") as mock_get:
                mock_list.return_value = [{"uid": "dash1", "title": "Dashboard 1", "folderTitle": ""}]

                # Mock failed dashboard fetch
                mock_get.side_effect = Exception("API Error")

                downloader = DashboardDownloader(client)
                downloaded_files = downloader.download_all(tmp_path)

                # Should continue despite error
                # Dashboard should not be created
                assert not (tmp_path / "dashboard-1.json").exists()
                assert len(downloaded_files) == 0

    def test_skip_general_folder(self, tmp_path):
        """Dashboards in General folder should not be in subfolder."""
        client = GrafanaClient("https://grafana.example.com", "admin", "secret")

        with patch.object(client, "list_dashboards") as mock_list:
            with patch.object(client, "get_dashboard") as mock_get:
                mock_list.return_value = [{"uid": "dash1", "title": "Dashboard", "folderTitle": "General"}]

                mock_get.return_value = {
                    "dashboard": {"title": "Dashboard", "panels": []},
                    "meta": {"folderTitle": "General"},
                }

                downloader = DashboardDownloader(client)
                downloader.download_all(tmp_path)

                # Dashboard should be in root, not in general/ subfolder
                assert (tmp_path / "dashboard.json").exists()
                assert not (tmp_path / "general").exists()

    def test_sanitize_name(self):
        """Sanitize name should handle special characters."""
        assert DashboardDownloader._sanitize_name("My Dashboard") == "my-dashboard"
        assert DashboardDownloader._sanitize_name("Test/Folder") == "test-folder"
        assert DashboardDownloader._sanitize_name("Mixed Case Test") == "mixed-case-test"


class TestRun:
    """Tests for CLI run function."""

    @patch("grafana_weaver.main.DashboardExtractor")
    @patch("grafana_weaver.main.DashboardDownloader")
    @patch("grafana_weaver.main.GrafanaClient")
    @patch("grafana_weaver.main.GrafanaConfigManager")
    @patch("grafana_weaver.main.tempfile.mkdtemp")
    def test_main_success(self, mock_mkdtemp, mock_config_mgr, mock_client, mock_downloader, mock_extractor, tmp_path):
        """Main should orchestrate download and extraction."""
        dashboards_dir = tmp_path / "dashboards"
        dashboards_dir.mkdir()

        # Mock config manager
        mock_manager = Mock()
        mock_manager.get_context.return_value = {
            "server": "https://grafana.example.com",
            "user": "admin",
            "password": "secret",
            "org-id": 1,
        }
        mock_config_mgr.return_value = mock_manager

        # Mock temp directory
        temp_dir = tmp_path / "temp"
        temp_dir.mkdir()
        mock_mkdtemp.return_value = str(temp_dir)

        # Mock client
        mock_client_instance = Mock()
        mock_client.return_value = mock_client_instance

        # Mock downloader
        mock_downloader_instance = Mock()
        mock_downloader_instance.download_all.return_value = []
        mock_downloader.return_value = mock_downloader_instance

        # Mock extractor
        mock_extractor_instance = Mock()
        mock_extractor.return_value = mock_extractor_instance

        args = SimpleNamespace(
            dashboard_dir=dashboards_dir,
            grafana_context="test-context"
        )
        download_dashboards(args)

        # Verify workflow was called
        mock_config_mgr.assert_called_once_with(context="test-context")
        mock_manager.get_context.assert_called_once_with()
        mock_downloader_instance.download_all.assert_called_once()

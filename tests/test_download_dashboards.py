"""Tests for download_dashboards.py module."""

from unittest.mock import Mock, patch

import pytest

from grafana_weaver.download_dashboards import (
    download_dashboards_from_grafana,
    main,
    process_dashboards,
)


class TestDownloadDashboardsFromGrafana:
    """Tests for download_dashboards_from_grafana function."""

    @patch("grafana_weaver.download_dashboards.requests.get")
    @patch("grafana_weaver.download_dashboards.get_grafana_config")
    def test_successful_download(self, mock_get_config, mock_requests_get, tmp_path):
        """Successful download should download all dashboards."""
        # Mock config
        mock_get_config.return_value = {"server": "https://grafana.example.com", "user": "admin", "password": "secret"}

        # Mock search API response
        search_response = Mock()
        search_response.status_code = 200
        search_response.json.return_value = [
            {"uid": "dash1", "title": "Dashboard 1", "folderTitle": ""},
            {"uid": "dash2", "title": "Dashboard 2", "folderTitle": "MyFolder"},
        ]

        # Mock dashboard API responses
        dash1_response = Mock()
        dash1_response.status_code = 200
        dash1_response.json.return_value = {
            "dashboard": {"title": "Dashboard 1", "panels": []},
            "meta": {"folderTitle": ""},
        }

        dash2_response = Mock()
        dash2_response.status_code = 200
        dash2_response.json.return_value = {
            "dashboard": {"title": "Dashboard 2", "panels": []},
            "meta": {"folderTitle": "MyFolder"},
        }

        mock_requests_get.side_effect = [search_response, dash1_response, dash2_response]

        download_dashboards_from_grafana(tmp_path, "test-context")

        # Verify dashboards were downloaded
        assert (tmp_path / "dashboard-1.json").exists()
        assert (tmp_path / "myfolder" / "dashboard-2.json").exists()

    @patch("grafana_weaver.download_dashboards.requests.get")
    @patch("grafana_weaver.download_dashboards.get_grafana_config")
    def test_download_api_error(self, mock_get_config, mock_requests_get, tmp_path):
        """API error should exit with error code."""
        mock_get_config.return_value = {"server": "https://grafana.example.com", "user": "admin", "password": "secret"}

        # Mock failed API response
        search_response = Mock()
        search_response.status_code = 401
        search_response.text = "Unauthorized"
        mock_requests_get.return_value = search_response

        with pytest.raises(SystemExit) as exc_info:
            download_dashboards_from_grafana(tmp_path, "test-context")
        assert exc_info.value.code == 1

    @patch("grafana_weaver.download_dashboards.requests.get")
    @patch("grafana_weaver.download_dashboards.get_grafana_config")
    def test_skip_general_folder(self, mock_get_config, mock_requests_get, tmp_path):
        """Dashboards in General folder should not be in subfolder."""
        mock_get_config.return_value = {"server": "https://grafana.example.com", "user": "admin", "password": "secret"}

        search_response = Mock()
        search_response.status_code = 200
        search_response.json.return_value = [
            {"uid": "dash1", "title": "Dashboard", "folderTitle": "General"},
        ]

        dash_response = Mock()
        dash_response.status_code = 200
        dash_response.json.return_value = {
            "dashboard": {"title": "Dashboard", "panels": []},
            "meta": {"folderTitle": "General"},
        }

        mock_requests_get.side_effect = [search_response, dash_response]

        download_dashboards_from_grafana(tmp_path, "test-context")

        # Dashboard should be in root, not in general/ subfolder
        assert (tmp_path / "dashboard.json").exists()
        assert not (tmp_path / "general").exists()


class TestProcessDashboards:
    """Tests for process_dashboards function."""

    @patch("grafana_weaver.download_dashboards.process_json_file")
    def test_process_single_dashboard(self, mock_process_json, tmp_path):
        """Single dashboard should be processed correctly."""
        downloaded_dir = tmp_path / "downloaded"
        downloaded_dir.mkdir()
        output_dir = tmp_path / "output"

        # Create a test dashboard file
        dashboard_file = downloaded_dir / "test-dashboard.json"
        dashboard_file.write_text('{"title": "Test Dashboard"}')

        # Mock successful processing
        mock_process_json.return_value = True

        process_dashboards(downloaded_dir, output_dir)

        # Verify process_json_file was called with correct arguments
        assert mock_process_json.called
        call_args = mock_process_json.call_args
        assert call_args[1]["base_dir"] == str(downloaded_dir)
        assert call_args[1]["output_dir"] == str(output_dir)

    @patch("grafana_weaver.download_dashboards.process_json_file")
    def test_process_nested_dashboards(self, mock_process_json, tmp_path):
        """Nested dashboards should be processed with correct base-dir."""
        downloaded_dir = tmp_path / "downloaded"
        downloaded_dir.mkdir()
        nested_dir = downloaded_dir / "subfolder"
        nested_dir.mkdir()
        output_dir = tmp_path / "output"

        # Create nested dashboard
        dashboard_file = nested_dir / "nested-dashboard.json"
        dashboard_file.write_text('{"title": "Nested Dashboard"}')

        # Mock successful processing
        mock_process_json.return_value = True

        process_dashboards(downloaded_dir, output_dir)

        # Verify base-dir points to downloaded_dir (not nested folder)
        assert mock_process_json.called
        call_args = mock_process_json.call_args
        assert call_args[1]["base_dir"] == str(downloaded_dir)

    @patch("grafana_weaver.download_dashboards.process_json_file")
    def test_process_extraction_error(self, mock_process_json, tmp_path):
        """Extraction error should exit with error code."""
        downloaded_dir = tmp_path / "downloaded"
        downloaded_dir.mkdir()
        output_dir = tmp_path / "output"

        dashboard_file = downloaded_dir / "test.json"
        dashboard_file.write_text("{}")

        # Mock failed extraction
        mock_process_json.return_value = False

        with pytest.raises(SystemExit) as exc_info:
            process_dashboards(downloaded_dir, output_dir)
        assert exc_info.value.code == 1

    def test_no_dashboards_found(self, tmp_path, capsys):
        """Empty directory should complete without error."""
        downloaded_dir = tmp_path / "downloaded"
        downloaded_dir.mkdir()
        output_dir = tmp_path / "output"

        process_dashboards(downloaded_dir, output_dir)

        captured = capsys.readouterr()
        assert "No JSON files found" in captured.out


class TestMain:
    """Tests for main function."""

    @patch("grafana_weaver.download_dashboards.process_dashboards")
    @patch("grafana_weaver.download_dashboards.download_dashboards_from_grafana")
    @patch("grafana_weaver.download_dashboards.get_grafana_context")
    def test_main_success(self, mock_get_grafana_context, mock_download, mock_process, tmp_path, monkeypatch):
        """Main should orchestrate download and processing."""
        mock_get_grafana_context.return_value = "test-context"
        monkeypatch.chdir(tmp_path)

        main()

        # Verify workflow was called
        mock_get_grafana_context.assert_called_once()
        mock_download.assert_called_once()
        mock_process.assert_called_once()

    @patch("grafana_weaver.download_dashboards.download_dashboards_from_grafana")
    @patch("grafana_weaver.download_dashboards.get_grafana_context")
    def test_main_uses_dashboard_dir_env(self, mock_get_grafana_context, mock_download, tmp_path, monkeypatch):
        """Main should use DASHBOARD_DIR environment variable."""
        mock_get_grafana_context.return_value = "test-context"
        dashboard_dir = tmp_path / "custom-dashboards"
        monkeypatch.setenv("DASHBOARD_DIR", str(dashboard_dir))

        with patch("grafana_weaver.download_dashboards.process_dashboards"):
            main()

        # The processing should be called (which means it got past directory setup)
        assert mock_download.called

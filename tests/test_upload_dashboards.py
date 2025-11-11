"""Tests for upload_dashboards command."""

from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from grafana_weaver.main import upload_dashboards
from grafana_weaver.core.client import GrafanaClient
from grafana_weaver.core.jsonnet_builder import JsonnetBuilder


class TestJsonnetBuilder:
    """Tests for JsonnetBuilder class."""

    @patch("grafana_weaver.core.jsonnet_builder._jsonnet.evaluate_file")
    def test_build_single_dashboard(self, mock_evaluate, tmp_path):
        """Single dashboard should be built correctly."""
        # Create dashboards structure
        src_dir = tmp_path / "src"
        src_dir.mkdir()

        jsonnet_file = src_dir / "test.jsonnet"
        jsonnet_file.write_text('{"uid": "test", "title": "Test Dashboard"}')

        # Mock jsonnet evaluation to return valid JSON
        mock_evaluate.return_value = '{"uid": "test", "title": "Test Dashboard"}'

        builder = JsonnetBuilder(tmp_path)
        built_files = builder.build_all()

        # Check that jsonnet evaluate_file was called
        assert mock_evaluate.called
        assert str(jsonnet_file) in str(mock_evaluate.call_args)

        # Check that output file was created
        output_file = tmp_path / "build" / "test.json"
        assert output_file.exists()
        assert len(built_files) == 1

    @patch("grafana_weaver.core.jsonnet_builder._jsonnet.evaluate_file")
    def test_build_nested_dashboard(self, mock_evaluate, tmp_path):
        """Nested dashboard should preserve folder structure."""
        src_dir = tmp_path / "src"
        nested_dir = src_dir / "folder1" / "folder2"
        nested_dir.mkdir(parents=True)

        jsonnet_file = nested_dir / "nested.jsonnet"
        jsonnet_file.write_text('{"uid": "nested"}')

        # Mock jsonnet evaluation
        mock_evaluate.return_value = '{"uid": "nested"}'

        builder = JsonnetBuilder(tmp_path)
        builder.build_all()

        # Check that nested output directory was created
        output_file = tmp_path / "build" / "folder1" / "folder2" / "nested.json"
        assert output_file.exists()

    @patch("grafana_weaver.core.jsonnet_builder._jsonnet.evaluate_file")
    def test_build_jsonnet_error(self, mock_evaluate, tmp_path):
        """Jsonnet build error should exit with error code."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()

        jsonnet_file = src_dir / "bad.jsonnet"
        jsonnet_file.write_text("invalid jsonnet")

        # Mock failed jsonnet execution
        mock_evaluate.side_effect = RuntimeError("Syntax error")

        builder = JsonnetBuilder(tmp_path)
        with pytest.raises(SystemExit) as exc_info:
            builder.build_all()
        assert exc_info.value.code == 1

    def test_no_jsonnet_files(self, tmp_path, capsys):
        """Empty src directory should complete without error."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()

        builder = JsonnetBuilder(tmp_path)
        built_files = builder.build_all()

        captured = capsys.readouterr()
        assert "No .jsonnet files found" in captured.out
        assert len(built_files) == 0


class TestGrafanaClient:
    """Tests for GrafanaClient class."""

    def test_upload_dashboard_success(self):
        """Successful upload should return response."""
        client = GrafanaClient("https://grafana.example.com", "admin", "secret")

        with patch("grafana_weaver.core.client.requests.post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "success", "uid": "dash1"}
            mock_post.return_value = mock_response

            result = client.upload_dashboard({"uid": "dash1", "title": "Dashboard 1"})

            assert result["status"] == "success"
            assert mock_post.called
            # Verify the URL and auth
            call_args = mock_post.call_args
            assert call_args[0][0] == "https://grafana.example.com/api/dashboards/db"
            assert "Authorization" in call_args[1]["headers"]

    def test_upload_dashboard_error(self):
        """Failed upload should raise HTTPError."""
        client = GrafanaClient("https://grafana.example.com", "admin", "secret")

        with patch("grafana_weaver.core.client.requests.post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.raise_for_status.side_effect = Exception("Server error")
            mock_post.return_value = mock_response

            with pytest.raises(Exception):
                client.upload_dashboard({"uid": "dash", "title": "Dashboard"})

    def test_list_dashboards(self):
        """List dashboards should return dashboard list."""
        client = GrafanaClient("https://grafana.example.com", "admin", "secret")

        with patch("grafana_weaver.core.client.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = [{"uid": "dash1"}, {"uid": "dash2"}]
            mock_get.return_value = mock_response

            dashboards = client.list_dashboards()

            assert len(dashboards) == 2
            assert dashboards[0]["uid"] == "dash1"

    def test_get_dashboard(self):
        """Get dashboard should return specific dashboard."""
        client = GrafanaClient("https://grafana.example.com", "admin", "secret")

        with patch("grafana_weaver.core.client.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"dashboard": {"uid": "dash1", "title": "Dashboard 1"}}
            mock_get.return_value = mock_response

            result = client.get_dashboard("dash1")

            assert result["dashboard"]["uid"] == "dash1"


class TestMain:
    """Tests for main function."""

    @patch("grafana_weaver.main.GrafanaClient")
    @patch("grafana_weaver.main.JsonnetBuilder")
    @patch("grafana_weaver.main.GrafanaConfigManager")
    def test_main_success(self, mock_config_mgr, mock_builder, mock_client, tmp_path, monkeypatch):
        """Main should orchestrate build and upload."""
        # Set environment variable
        monkeypatch.setenv("GRAFANA_CONTEXT", "test-context")

        # Create dashboard directory structure
        dashboards_dir = tmp_path / "dashboards"
        dashboards_dir.mkdir(exist_ok=True)
        build_dir = dashboards_dir / "build"
        build_dir.mkdir(parents=True)
        dashboard_file = build_dir / "test.json"
        dashboard_file.write_text('{"uid": "test", "title": "Test"}')

        # Mock config manager
        mock_manager = Mock()
        mock_manager.get_context.return_value = {
            "server": "https://grafana.example.com",
            "user": "admin",
            "password": "secret",
            "org-id": 1,
        }
        mock_config_mgr.return_value = mock_manager

        # Mock builder - return the actual file path we created
        mock_builder_instance = Mock()
        mock_builder_instance.build_all.return_value = [dashboard_file]
        mock_builder.return_value = mock_builder_instance

        # Mock client
        mock_client_instance = Mock()
        mock_client_instance.upload_dashboard.return_value = {"status": "success"}
        mock_client.return_value = mock_client_instance

        # Create args object
        args = SimpleNamespace(
            dashboard_dir=dashboards_dir,
            grafana_context="test-context"
        )
        upload_dashboards(args)

        # Verify workflow was called
        mock_config_mgr.assert_called_once_with(context="test-context")
        mock_manager.get_context.assert_called_once_with()
        mock_builder_instance.build_all.assert_called_once()
        mock_client_instance.upload_dashboard.assert_called_once()

    def test_main_dashboards_dir_not_found(self, tmp_path):
        """Main should exit if dashboards directory not found."""
        nonexistent_dir = tmp_path / "nonexistent"

        args = SimpleNamespace(
            dashboard_dir=nonexistent_dir,
            grafana_context="test-context"
        )

        with pytest.raises(SystemExit) as exc_info:
            upload_dashboards(args)
        assert exc_info.value.code == 1

    @patch("grafana_weaver.main.GrafanaClient")
    @patch("grafana_weaver.main.JsonnetBuilder")
    @patch("grafana_weaver.main.GrafanaConfigManager")
    def test_main_uses_dashboard_dir_env(
        self,
        mock_config_mgr,
        mock_builder,
        mock_client,
        tmp_path,
    ):
        """Main should use dashboard_dir from args."""
        # Mock config manager
        mock_manager = Mock()
        mock_manager.get_context.return_value = {
            "server": "https://grafana.example.com",
            "user": "admin",
            "password": "secret",
            "org-id": 1,
        }
        mock_config_mgr.return_value = mock_manager

        # Mock builder
        mock_builder_instance = Mock()
        mock_builder_instance.build_all.return_value = []
        mock_builder.return_value = mock_builder_instance

        dashboard_dir = tmp_path / "custom-dashboards"
        dashboard_dir.mkdir()

        args = SimpleNamespace(
            dashboard_dir=dashboard_dir,
            grafana_context="test-context"
        )
        upload_dashboards(args)

        # Builder should be called with the custom directory
        mock_builder.assert_called_once()
        assert mock_builder.call_args[0][0] == dashboard_dir

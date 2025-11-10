"""Tests for upload_dashboards.py module."""

from unittest.mock import Mock, patch

import pytest

from grafana_weaver.upload_dashboards import (
    build_jsonnet_dashboards,
    main,
    upload_dashboards_to_grafana,
)


class TestBuildJsonnetDashboards:
    """Tests for build_jsonnet_dashboards function."""

    @patch("grafana_weaver.upload_dashboards._jsonnet.evaluate_file")
    def test_build_single_dashboard(self, mock_evaluate, tmp_path):
        """Single dashboard should be built correctly."""
        # Create dashboards structure
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        build_dir = tmp_path / "build"

        jsonnet_file = src_dir / "test.jsonnet"
        jsonnet_file.write_text('{"uid": "test", "title": "Test Dashboard"}')

        # Mock jsonnet evaluation to return valid JSON
        mock_evaluate.return_value = '{"uid": "test", "title": "Test Dashboard"}'

        build_jsonnet_dashboards(tmp_path)

        # Check that jsonnet evaluate_file was called
        assert mock_evaluate.called
        assert str(jsonnet_file) in str(mock_evaluate.call_args)

        # Check that output file was created
        output_file = build_dir / "test.json"
        assert output_file.exists()

    @patch("grafana_weaver.upload_dashboards._jsonnet.evaluate_file")
    def test_build_nested_dashboard(self, mock_evaluate, tmp_path):
        """Nested dashboard should preserve folder structure."""
        src_dir = tmp_path / "src"
        nested_dir = src_dir / "folder1" / "folder2"
        nested_dir.mkdir(parents=True)

        jsonnet_file = nested_dir / "nested.jsonnet"
        jsonnet_file.write_text('{"uid": "nested"}')

        # Mock jsonnet evaluation
        mock_evaluate.return_value = '{"uid": "nested"}'

        build_jsonnet_dashboards(tmp_path)

        # Check that nested output directory was created
        output_file = tmp_path / "build" / "folder1" / "folder2" / "nested.json"
        assert output_file.exists()

    @patch("grafana_weaver.upload_dashboards._jsonnet.evaluate_file")
    def test_build_jsonnet_error(self, mock_evaluate, tmp_path):
        """Jsonnet build error should exit with error code."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()

        jsonnet_file = src_dir / "bad.jsonnet"
        jsonnet_file.write_text("invalid jsonnet")

        # Mock failed jsonnet execution
        mock_evaluate.side_effect = RuntimeError("Syntax error")

        with pytest.raises(SystemExit) as exc_info:
            build_jsonnet_dashboards(tmp_path)
        assert exc_info.value.code == 1

    def test_no_jsonnet_files(self, tmp_path, capsys):
        """Empty src directory should complete without error."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()

        build_jsonnet_dashboards(tmp_path)

        captured = capsys.readouterr()
        assert "No .jsonnet files found" in captured.out


class TestUploadDashboardsToGrafana:
    """Tests for upload_dashboards_to_grafana function."""

    @patch("grafana_weaver.upload_dashboards.requests.post")
    @patch("grafana_weaver.upload_dashboards.get_grafana_config")
    def test_successful_upload(self, mock_get_config, mock_requests_post, tmp_path):
        """Successful upload should upload all dashboards."""
        # Mock config
        mock_get_config.return_value = {"server": "https://grafana.example.com", "user": "admin", "password": "secret"}

        # Create build directory with dashboards
        build_dir = tmp_path / "build"
        build_dir.mkdir()

        dashboard1 = build_dir / "dashboard1.json"
        dashboard1.write_text('{"uid": "dash1", "title": "Dashboard 1"}')

        dashboard2 = build_dir / "dashboard2.json"
        dashboard2.write_text('{"uid": "dash2", "title": "Dashboard 2"}')

        # Mock successful API responses
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}
        mock_requests_post.return_value = mock_response

        upload_dashboards_to_grafana(tmp_path, "test-context")

        # Verify 2 dashboards were uploaded
        assert mock_requests_post.call_count == 2

    @patch("grafana_weaver.upload_dashboards.requests.post")
    @patch("grafana_weaver.upload_dashboards.get_grafana_config")
    def test_upload_api_error(self, mock_get_config, mock_requests_post, tmp_path):
        """API error should exit with error code."""
        mock_get_config.return_value = {"server": "https://grafana.example.com", "user": "admin", "password": "secret"}

        # Create build directory with one dashboard
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        dashboard = build_dir / "dashboard.json"
        dashboard.write_text('{"uid": "dash", "title": "Dashboard"}')

        # Mock failed API response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_requests_post.return_value = mock_response

        with pytest.raises(SystemExit) as exc_info:
            upload_dashboards_to_grafana(tmp_path, "test-context")
        assert exc_info.value.code == 1

    @patch("grafana_weaver.upload_dashboards.get_grafana_config")
    def test_build_dir_not_found(self, mock_get_config, tmp_path):
        """Missing build directory should exit with error."""
        mock_get_config.return_value = {"server": "https://grafana.example.com", "user": "admin", "password": "secret"}

        with pytest.raises(SystemExit) as exc_info:
            upload_dashboards_to_grafana(tmp_path, "test-context")
        assert exc_info.value.code == 1

    @patch("grafana_weaver.upload_dashboards.requests.post")
    @patch("grafana_weaver.upload_dashboards.get_grafana_config")
    def test_upload_nested_dashboards(self, mock_get_config, mock_requests_post, tmp_path):
        """Nested dashboards should be uploaded."""
        mock_get_config.return_value = {"server": "https://grafana.example.com", "user": "admin", "password": "secret"}

        # Create nested dashboard
        build_dir = tmp_path / "build" / "subfolder"
        build_dir.mkdir(parents=True)
        dashboard = build_dir / "nested.json"
        dashboard.write_text('{"uid": "nested", "title": "Nested Dashboard"}')

        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}
        mock_requests_post.return_value = mock_response

        upload_dashboards_to_grafana(tmp_path, "test-context")

        # Verify upload was called
        assert mock_requests_post.called


class TestMain:
    """Tests for main function."""

    @patch("grafana_weaver.upload_dashboards.upload_dashboards_to_grafana")
    @patch("grafana_weaver.upload_dashboards.build_jsonnet_dashboards")
    @patch("grafana_weaver.upload_dashboards.get_grafana_context")
    def test_main_success(self, mock_get_grafana_context, mock_build, mock_upload, tmp_path, monkeypatch):
        """Main should orchestrate build and upload."""
        mock_get_grafana_context.return_value = "test-context"
        dashboards_dir = tmp_path / "dashboards"
        dashboards_dir.mkdir()
        monkeypatch.chdir(tmp_path)

        main()

        # Verify workflow was called
        mock_get_grafana_context.assert_called_once()
        mock_build.assert_called_once()
        mock_upload.assert_called_once()

    @patch("grafana_weaver.upload_dashboards.get_grafana_context")
    def test_main_dashboards_dir_not_found(self, mock_get_grafana_context, tmp_path, monkeypatch):
        """Main should exit if dashboards directory not found."""
        mock_get_grafana_context.return_value = "test-context"
        monkeypatch.chdir(tmp_path)

        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1

    @patch("grafana_weaver.upload_dashboards.build_jsonnet_dashboards")
    @patch("grafana_weaver.upload_dashboards.get_grafana_context")
    def test_main_uses_dashboard_dir_env(self, mock_get_grafana_context, mock_build, tmp_path, monkeypatch):
        """Main should use DASHBOARD_DIR environment variable."""
        mock_get_grafana_context.return_value = "test-context"
        dashboard_dir = tmp_path / "custom-dashboards"
        dashboard_dir.mkdir()
        monkeypatch.setenv("DASHBOARD_DIR", str(dashboard_dir))

        with patch("grafana_weaver.upload_dashboards.upload_dashboards_to_grafana"):
            main()

        # Build should be called with the custom directory
        mock_build.assert_called_once_with(dashboard_dir)

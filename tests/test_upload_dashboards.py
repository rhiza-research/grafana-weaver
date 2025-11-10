"""Tests for upload_dashboards.py module."""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

from grafana_weaver.upload_dashboards import (
    build_jsonnet_dashboards,
    main,
)


class TestBuildJsonnetDashboards:
    """Tests for build_jsonnet_dashboards function."""

    def test_build_single_dashboard(self, dashboards_structure, monkeypatch):
        """Single dashboard should be built correctly."""
        # Create a simple jsonnet file
        jsonnet_file = dashboards_structure['src'] / "test.jsonnet"
        jsonnet_file.write_text('{"uid": "test", "title": "Test Dashboard"}')

        # Mock subprocess.run to return valid JSON
        mock_run = MagicMock()
        mock_run.return_value.stdout = '{"uid": "test", "title": "Test Dashboard"}'
        mock_run.return_value.returncode = 0
        monkeypatch.setattr(subprocess, 'run', mock_run)

        build_jsonnet_dashboards(dashboards_structure['base'])

        # Check that jsonnet was called
        assert mock_run.called
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "jsonnet"
        assert str(jsonnet_file) in call_args[1]

        # Check that output file was created
        output_file = dashboards_structure['build'] / "test.json"
        assert output_file.exists()

    def test_build_nested_dashboard(self, dashboards_structure, monkeypatch):
        """Nested dashboard should preserve folder structure."""
        # Create a nested folder structure
        nested_dir = dashboards_structure['src'] / "folder1" / "folder2"
        nested_dir.mkdir(parents=True)

        jsonnet_file = nested_dir / "nested.jsonnet"
        jsonnet_file.write_text('{"uid": "nested"}')

        # Mock subprocess.run
        mock_run = MagicMock()
        mock_run.return_value.stdout = '{"uid": "nested"}'
        mock_run.return_value.returncode = 0
        monkeypatch.setattr(subprocess, 'run', mock_run)

        build_jsonnet_dashboards(dashboards_structure['base'])

        # Check that folder structure is preserved in build
        output_file = dashboards_structure['build'] / "folder1" / "folder2" / "nested.json"
        assert output_file.exists()

    def test_jsonnet_error(self, dashboards_structure, monkeypatch):
        """Jsonnet build error should exit with error."""
        jsonnet_file = dashboards_structure['src'] / "bad.jsonnet"
        jsonnet_file.write_text('invalid jsonnet')

        # Mock subprocess.run to raise CalledProcessError
        def raise_error(*args, **kwargs):
            raise subprocess.CalledProcessError(1, 'jsonnet', stderr='syntax error')

        monkeypatch.setattr(subprocess, 'run', raise_error)

        with pytest.raises(SystemExit) as exc_info:
            build_jsonnet_dashboards(dashboards_structure['base'])
        assert exc_info.value.code == 1

    def test_no_jsonnet_files(self, dashboards_structure, capsys):
        """No jsonnet files should print message and continue."""
        build_jsonnet_dashboards(dashboards_structure['base'])

        captured = capsys.readouterr()
        assert "No .jsonnet files found" in captured.out

    def test_json_decode_error(self, dashboards_structure, monkeypatch):
        """Invalid JSON from jsonnet should exit with error."""
        jsonnet_file = dashboards_structure['src'] / "invalid.jsonnet"
        jsonnet_file.write_text('{"uid": "test"}')

        # Mock subprocess.run to return invalid JSON
        mock_run = MagicMock()
        mock_run.return_value.stdout = 'not valid json {'
        mock_run.return_value.returncode = 0
        monkeypatch.setattr(subprocess, 'run', mock_run)

        with pytest.raises(SystemExit) as exc_info:
            build_jsonnet_dashboards(dashboards_structure['base'])
        assert exc_info.value.code == 1


class TestMain:
    """Integration tests for main function."""

    @patch('grafana_weaver.upload_dashboards.Terraform')
    @patch('grafana_weaver.upload_dashboards.get_workspace')
    @patch('grafana_weaver.upload_dashboards.get_terraform_dir')
    @patch('grafana_weaver.upload_dashboards.build_jsonnet_dashboards')
    def test_main_success(
        self,
        mock_build,
        mock_get_terraform_dir,
        mock_get_workspace,
        mock_terraform_class,
        temp_dir
    ):
        """Main should orchestrate the upload process."""
        # Setup workspace
        mock_get_workspace.return_value = "production"

        # Setup terraform directory
        terraform_dir = temp_dir / "terraform"
        terraform_dir.mkdir()
        mock_get_terraform_dir.return_value = terraform_dir

        # Setup dashboards directory
        dashboards_dir = temp_dir / "dashboards"
        dashboards_dir.mkdir()

        # Mock Terraform
        mock_tf = MagicMock()
        mock_terraform_class.return_value = mock_tf
        mock_tf.workspace.return_value = (0, "Success", "")
        mock_tf.output.return_value = (0, str(dashboards_dir), "")
        mock_tf.apply.return_value = (0, "Applied", "")

        main()

        # Verify the workflow
        mock_get_workspace.assert_called_once()
        mock_get_terraform_dir.assert_called_once()
        mock_terraform_class.assert_called_once_with(working_dir=str(terraform_dir))
        mock_tf.workspace.assert_called_once_with("select", "-or-create=true", "production")
        mock_tf.output.assert_called_once_with("dashboards_base_path", raw=True)
        mock_build.assert_called_once_with(dashboards_dir)
        mock_tf.apply.assert_called_once()

    @patch('grafana_weaver.upload_dashboards.Terraform')
    @patch('grafana_weaver.upload_dashboards.get_workspace')
    @patch('grafana_weaver.upload_dashboards.get_terraform_dir')
    def test_main_workspace_error(
        self,
        mock_get_terraform_dir,
        mock_get_workspace,
        mock_terraform_class,
        temp_dir
    ):
        """Workspace selection error should exit with error code."""
        mock_get_workspace.return_value = "production"

        terraform_dir = temp_dir / "terraform"
        terraform_dir.mkdir()
        mock_get_terraform_dir.return_value = terraform_dir

        mock_tf = MagicMock()
        mock_terraform_class.return_value = mock_tf
        mock_tf.workspace.return_value = (1, "", "Workspace error")

        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1

    @patch('grafana_weaver.upload_dashboards.Terraform')
    @patch('grafana_weaver.upload_dashboards.get_workspace')
    @patch('grafana_weaver.upload_dashboards.get_terraform_dir')
    def test_main_output_error(
        self,
        mock_get_terraform_dir,
        mock_get_workspace,
        mock_terraform_class,
        temp_dir
    ):
        """Terraform output error should exit with error code."""
        mock_get_workspace.return_value = "production"

        terraform_dir = temp_dir / "terraform"
        terraform_dir.mkdir()
        mock_get_terraform_dir.return_value = terraform_dir

        mock_tf = MagicMock()
        mock_terraform_class.return_value = mock_tf
        mock_tf.workspace.return_value = (0, "Success", "")
        mock_tf.output.return_value = (1, "", "Output not found")

        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1

    @patch('grafana_weaver.upload_dashboards.Terraform')
    @patch('grafana_weaver.upload_dashboards.get_workspace')
    @patch('grafana_weaver.upload_dashboards.get_terraform_dir')
    @patch('grafana_weaver.upload_dashboards.build_jsonnet_dashboards')
    def test_main_apply_error(
        self,
        mock_build,
        mock_get_terraform_dir,
        mock_get_workspace,
        mock_terraform_class,
        temp_dir
    ):
        """Terraform apply error should exit with error code."""
        mock_get_workspace.return_value = "production"

        terraform_dir = temp_dir / "terraform"
        terraform_dir.mkdir()
        mock_get_terraform_dir.return_value = terraform_dir

        dashboards_dir = temp_dir / "dashboards"
        dashboards_dir.mkdir()

        mock_tf = MagicMock()
        mock_terraform_class.return_value = mock_tf
        mock_tf.workspace.return_value = (0, "Success", "")
        mock_tf.output.return_value = (0, str(dashboards_dir), "")
        mock_tf.apply.return_value = (1, "", "Apply failed")

        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1

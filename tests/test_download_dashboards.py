"""Tests for download_dashboards.py module."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from grafana_weaver.download_dashboards import (
    download_dashboards_from_grafana,
    main,
    process_dashboards,
)


class TestDownloadDashboardsFromGrafana:
    """Tests for download_dashboards_from_grafana function."""

    def test_successful_download(self, temp_dir):
        """Successful download should complete without error."""
        mock_tf = MagicMock()
        mock_tf.apply.return_value = (0, "Success", "")

        download_dashboards_from_grafana(mock_tf, temp_dir)

        # Verify terraform apply was called with correct parameters
        mock_tf.apply.assert_called_once()
        call_kwargs = mock_tf.apply.call_args[1]
        assert call_kwargs['skip_plan'] is True
        assert call_kwargs['auto_approve'] is True
        assert call_kwargs['var']['dashboard_export_enabled'] is True
        assert call_kwargs['var']['dashboard_export_dir'] == str(temp_dir)

    def test_download_error(self, temp_dir):
        """Download error should exit with error code."""
        mock_tf = MagicMock()
        mock_tf.apply.return_value = (1, "", "Terraform error")

        with pytest.raises(SystemExit) as exc_info:
            download_dashboards_from_grafana(mock_tf, temp_dir)
        assert exc_info.value.code == 1


class TestProcessDashboards:
    """Tests for process_dashboards function."""

    def test_process_single_dashboard(self, temp_dir, monkeypatch, test_data):
        """Single dashboard should be processed correctly."""
        # Copy test data to temp directory
        test_data_file = test_data("download_dashboards/sample_dashboard.json")
        dashboard_file = temp_dir / "dashboard.json"
        with open(test_data_file) as f:
            dashboard_data = f.read()
        with open(dashboard_file, 'w') as f:
            f.write(dashboard_data)

        # Create the extract script location
        script_dir = temp_dir / "grafana_weaver"
        script_dir.mkdir()
        extract_script = script_dir / "extract_external_content.py"
        extract_script.touch()

        # Mock subprocess.run
        mock_run = MagicMock()
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "Processing complete"
        monkeypatch.setattr(subprocess, 'run', mock_run)

        process_dashboards(temp_dir)

        # Verify extract script was called
        assert mock_run.called

    def test_process_nested_dashboards(self, temp_dir, monkeypatch, test_data):
        """Nested dashboards should preserve folder structure."""
        # Create nested folder structure
        nested_dir = temp_dir / "folder1" / "folder2"
        nested_dir.mkdir(parents=True)

        # Copy test data to nested directory
        test_data_file = test_data("download_dashboards/sample_dashboard.json")
        dashboard_file = nested_dir / "nested.json"
        with open(test_data_file) as f:
            dashboard_data = f.read()
        with open(dashboard_file, 'w') as f:
            f.write(dashboard_data)

        # Create the extract script
        script_dir = temp_dir / "grafana_weaver"
        script_dir.mkdir()
        extract_script = script_dir / "extract_external_content.py"
        extract_script.touch()

        # Mock subprocess.run
        mock_run = MagicMock()
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ""
        monkeypatch.setattr(subprocess, 'run', mock_run)

        process_dashboards(temp_dir)

        # Verify the script was called with base_dir parameter
        assert mock_run.called
        call_args = mock_run.call_args[0][0]
        assert str(nested_dir / "nested.json") in " ".join(call_args)

    def test_no_dashboards(self, temp_dir, capsys):
        """No dashboards should print message."""
        script_dir = temp_dir / "grafana_weaver"
        script_dir.mkdir()

        process_dashboards(temp_dir)

        captured = capsys.readouterr()
        assert "No JSON files found" in captured.out

    def test_extract_script_missing(self, temp_dir, test_data):
        """Missing extract script should exit with error."""
        # Copy test data to temp directory
        test_data_file = test_data("download_dashboards/sample_dashboard.json")
        dashboard_file = temp_dir / "dashboard.json"
        with open(test_data_file) as f:
            dashboard_data = f.read()
        with open(dashboard_file, 'w') as f:
            f.write(dashboard_data)

        # Mock the __file__ path to point to a location without the script
        fake_module_path = temp_dir / "fake_module" / "download_dashboards.py"
        fake_module_path.parent.mkdir(parents=True, exist_ok=True)
        fake_module_path.touch()

        with patch('grafana_weaver.download_dashboards.__file__', str(fake_module_path)):
            with pytest.raises(SystemExit) as exc_info:
                process_dashboards(temp_dir)
            assert exc_info.value.code == 1

    def test_extraction_error(self, temp_dir, monkeypatch, test_data):
        """Extraction error should exit with error code."""
        # Copy test data to temp directory
        test_data_file = test_data("download_dashboards/sample_dashboard.json")
        dashboard_file = temp_dir / "dashboard.json"
        with open(test_data_file) as f:
            dashboard_data = f.read()
        with open(dashboard_file, 'w') as f:
            f.write(dashboard_data)

        script_dir = temp_dir / "grafana_weaver"
        script_dir.mkdir()
        extract_script = script_dir / "extract_external_content.py"
        extract_script.touch()

        # Mock subprocess.run to return error
        mock_run = MagicMock()
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = "Extraction failed"
        monkeypatch.setattr(subprocess, 'run', mock_run)

        with pytest.raises(SystemExit) as exc_info:
            process_dashboards(temp_dir)
        assert exc_info.value.code == 1


class TestMain:
    """Integration tests for main function."""

    @patch('grafana_weaver.download_dashboards.tempfile.mkdtemp')
    @patch('grafana_weaver.download_dashboards.Terraform')
    @patch('grafana_weaver.download_dashboards.get_workspace')
    @patch('grafana_weaver.download_dashboards.get_terraform_dir')
    @patch('grafana_weaver.download_dashboards.process_dashboards')
    def test_main_success(
        self,
        mock_process,
        mock_get_terraform_dir,
        mock_get_workspace,
        mock_terraform_class,
        mock_mkdtemp,
        temp_dir
    ):
        """Main should orchestrate the download process."""
        # Setup workspace
        mock_get_workspace.return_value = "production"

        # Setup terraform directory
        terraform_dir = temp_dir / "terraform"
        terraform_dir.mkdir()
        mock_get_terraform_dir.return_value = terraform_dir

        # Setup downloads directory
        downloads_dir = temp_dir / "downloads"
        downloads_dir.mkdir()
        mock_mkdtemp.return_value = str(downloads_dir)

        # Setup dashboards directory
        dashboards_dir = temp_dir / "dashboards"
        dashboards_dir.mkdir()

        # Mock Terraform
        mock_tf = MagicMock()
        mock_terraform_class.return_value = mock_tf
        mock_tf.workspace.return_value = (0, "Success", "")
        mock_tf.output.return_value = (0, str(dashboards_dir), "")
        mock_tf.apply.return_value = (0, "Success", "")

        main()

        # Verify the workflow
        mock_get_workspace.assert_called_once()
        mock_get_terraform_dir.assert_called_once()
        mock_terraform_class.assert_called_once_with(working_dir=str(terraform_dir))
        mock_tf.workspace.assert_called_once_with("select", "-or-create=true", "production")
        mock_tf.output.assert_called_once_with("dashboards_base_path", raw=True)
        mock_tf.apply.assert_called_once()
        mock_process.assert_called_once_with(downloads_dir)

    @patch('grafana_weaver.download_dashboards.tempfile.mkdtemp')
    @patch('grafana_weaver.download_dashboards.Terraform')
    @patch('grafana_weaver.download_dashboards.get_workspace')
    @patch('grafana_weaver.download_dashboards.get_terraform_dir')
    def test_main_workspace_error(
        self,
        mock_get_terraform_dir,
        mock_get_workspace,
        mock_terraform_class,
        mock_mkdtemp,
        temp_dir
    ):
        """Workspace selection error should exit with error code."""
        mock_get_workspace.return_value = "production"

        terraform_dir = temp_dir / "terraform"
        terraform_dir.mkdir()
        mock_get_terraform_dir.return_value = terraform_dir

        downloads_dir = temp_dir / "downloads"
        downloads_dir.mkdir()
        mock_mkdtemp.return_value = str(downloads_dir)

        mock_tf = MagicMock()
        mock_terraform_class.return_value = mock_tf
        mock_tf.workspace.return_value = (1, "", "Workspace not found")

        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1

    @patch('grafana_weaver.download_dashboards.tempfile.mkdtemp')
    @patch('grafana_weaver.download_dashboards.Terraform')
    @patch('grafana_weaver.download_dashboards.get_workspace')
    @patch('grafana_weaver.download_dashboards.get_terraform_dir')
    def test_main_output_error(
        self,
        mock_get_terraform_dir,
        mock_get_workspace,
        mock_terraform_class,
        mock_mkdtemp,
        temp_dir
    ):
        """Terraform output error should exit with error code."""
        mock_get_workspace.return_value = "production"

        terraform_dir = temp_dir / "terraform"
        terraform_dir.mkdir()
        mock_get_terraform_dir.return_value = terraform_dir

        downloads_dir = temp_dir / "downloads"
        downloads_dir.mkdir()
        mock_mkdtemp.return_value = str(downloads_dir)

        mock_tf = MagicMock()
        mock_terraform_class.return_value = mock_tf
        mock_tf.workspace.return_value = (0, "Success", "")
        mock_tf.output.return_value = (1, "", "Output not found")

        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1

    @patch('grafana_weaver.download_dashboards.tempfile.mkdtemp')
    @patch('grafana_weaver.download_dashboards.Terraform')
    @patch('grafana_weaver.download_dashboards.get_workspace')
    @patch('grafana_weaver.download_dashboards.get_terraform_dir')
    def test_main_cleanup_temp_dir(
        self,
        mock_get_terraform_dir,
        mock_get_workspace,
        mock_terraform_class,
        mock_mkdtemp,
        temp_dir
    ):
        """Temporary directory should be cleaned up even on error."""
        # Setup workspace and terraform
        mock_get_workspace.return_value = "production"

        terraform_dir = temp_dir / "terraform"
        terraform_dir.mkdir()
        mock_get_terraform_dir.return_value = terraform_dir

        # Setup a temp directory that we can verify gets cleaned up
        downloads_dir = temp_dir / "downloads"
        downloads_dir.mkdir()
        mock_mkdtemp.return_value = str(downloads_dir)

        # Make terraform workspace fail to trigger cleanup in finally block
        mock_tf = MagicMock()
        mock_terraform_class.return_value = mock_tf
        mock_tf.workspace.return_value = (1, "", "Workspace error")

        with pytest.raises(SystemExit):
            main()

        # Verify cleanup happened
        assert not downloads_dir.exists()

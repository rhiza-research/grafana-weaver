"""Tests for main CLI entrypoint."""

import pytest
from unittest.mock import Mock, patch

from grafana_weaver.main import main


class TestMainCLI:
    """Tests for main CLI entrypoint."""

    def test_no_command_prints_help(self, capsys):
        """Should print help when no command is specified."""
        with patch("sys.argv", ["grafana-weaver"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 2  # argparse exits with 2 for missing required args

        captured = capsys.readouterr()
        assert "grafana-weaver" in captured.err  # argparse prints errors to stderr
        assert "required: command" in captured.err

    @patch("grafana_weaver.main.upload_dashboards")
    def test_upload_command(self, mock_run, tmp_path):
        """Should call upload_dashboards.run() with parsed args."""
        dashboards_dir = tmp_path / "dashboards"
        dashboards_dir.mkdir()

        with patch("sys.argv", ["grafana-weaver", "upload", "--dashboard-dir", str(dashboards_dir)]):
            main()

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args.command == "upload"
        assert args.dashboard_dir == dashboards_dir

    @patch("grafana_weaver.main.download_dashboards")
    def test_download_command(self, mock_run, tmp_path):
        """Should call download_dashboards.run() with parsed args."""
        dashboards_dir = tmp_path / "dashboards"
        dashboards_dir.mkdir()

        with patch("sys.argv", ["grafana-weaver", "download", "--dashboard-dir", str(dashboards_dir)]):
            main()

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args.command == "download"
        assert args.dashboard_dir == dashboards_dir

    @patch("grafana_weaver.main.extract_external_content")
    def test_extract_command(self, mock_run, tmp_path):
        """Should call extract_external_content.run() with parsed args."""
        test_file = tmp_path / "dashboard.json"
        test_file.write_text('{"uid": "test"}')

        # Mock run to raise SystemExit like the real function does
        mock_run.side_effect = SystemExit(0)

        with patch("sys.argv", ["grafana-weaver", "extract", str(test_file)]):
            with pytest.raises(SystemExit):
                main()

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args.command == "extract"
        assert args.json_file == test_file

    @patch("grafana_weaver.main.config_add")
    def test_config_add_command(self, mock_handle):
        """Should call config.handle_command() for config subcommands."""
        with patch("sys.argv", [
            "grafana-weaver", "config", "add", "test-ctx",
            "--server", "https://grafana.test",
            "--user", "admin",
            "--password", "secret"
        ]):
            main()

        mock_handle.assert_called_once()
        args = mock_handle.call_args[0][0]
        assert args.command == "config"
        assert args.config_command == "add"
        assert args.name == "test-ctx"
        assert args.server == "https://grafana.test"

    @patch("grafana_weaver.main.config_list")
    def test_config_list_command(self, mock_config_list):
        """Should call config_list() for config list."""
        with patch("sys.argv", ["grafana-weaver", "config", "list"]):
            main()

        mock_config_list.assert_called_once()
        args = mock_config_list.call_args[0][0]
        assert args.command == "config"
        assert args.config_command == "list"

    def test_env_var_defaults(self, monkeypatch, tmp_path):
        """Should use environment variables as defaults."""
        dashboards_dir = tmp_path / "custom-dashboards"
        dashboards_dir.mkdir()
        monkeypatch.setenv("DASHBOARD_DIR", str(dashboards_dir))
        monkeypatch.setenv("GRAFANA_CONTEXT", "test-context")

        with patch("sys.argv", ["grafana-weaver", "upload"]):
            with patch("grafana_weaver.main.upload_dashboards") as mock_run:
                main()

        args = mock_run.call_args[0][0]
        assert args.dashboard_dir == dashboards_dir
        assert args.grafana_context == "test-context"

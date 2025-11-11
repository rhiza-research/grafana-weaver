"""Tests for config commands in main.py."""

from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
import yaml

from grafana_weaver.main import (
    config_add,
    config_check,
    config_delete,
    config_list,
    config_set,
    config_show,
    config_use,
)


class TestAddContext:
    """Tests for add_context function."""

    @patch("grafana_weaver.main.GrafanaConfigManager")
    def test_add_context_with_use_flag(self, mock_manager_class, capsys):
        """Should add context and set as current when --use-context flag is set."""
        mock_manager = Mock()
        mock_manager.config_path = "/fake/path/config.yaml"
        mock_manager.get_current_context.return_value = None
        mock_manager_class.return_value = mock_manager

        args = SimpleNamespace(
            name="test-ctx",
            server="https://grafana.test",
            user="admin",
            password="secret",
            org_id=1,
            use_context=True,
        )

        config_add(args)

        mock_manager.add_context.assert_called_once_with("test-ctx", "https://grafana.test", "admin", "secret", 1)
        mock_manager.use_context.assert_called_once_with("test-ctx")
        captured = capsys.readouterr()
        assert "Context 'test-ctx' added" in captured.out

    @patch("grafana_weaver.main.GrafanaConfigManager")
    def test_add_context_sets_as_current_if_none_exists(self, mock_manager_class, capsys):
        """Should set as current context if no current context exists."""
        mock_manager = Mock()
        mock_manager.config_path = "/fake/path/config.yaml"
        mock_manager.get_current_context.return_value = None
        mock_manager_class.return_value = mock_manager

        args = SimpleNamespace(
            name="test-ctx",
            server="https://grafana.test",
            user="admin",
            password="secret",
            org_id=1,
            use_context=False,
        )

        config_add(args)

        mock_manager.use_context.assert_called_once_with("test-ctx")


class TestListContexts:
    """Tests for list_contexts function."""

    @patch("grafana_weaver.main.GrafanaConfigManager")
    def test_list_contexts_with_contexts(self, mock_manager_class, capsys):
        """Should list all contexts with current marked."""
        mock_manager = Mock()
        mock_manager.list_contexts.return_value = ["ctx1", "ctx2"]
        mock_manager.get_current_context.return_value = "ctx1"
        mock_manager.load.return_value = {
            "contexts": {
                "ctx1": {"grafana": {"server": "https://server1.com"}},
                "ctx2": {"grafana": {"server": "https://server2.com"}},
            },
        }
        mock_manager_class.return_value = mock_manager

        args = SimpleNamespace()
        config_list(args)

        captured = capsys.readouterr()
        assert "Available contexts:" in captured.out
        assert "ctx1" in captured.out
        assert "ctx2" in captured.out
        assert "*" in captured.out  # Current context marker

    @patch("grafana_weaver.main.GrafanaConfigManager")
    def test_list_contexts_empty(self, mock_manager_class, capsys):
        """Should display message when no contexts exist."""
        mock_manager = Mock()
        mock_manager.list_contexts.return_value = []
        mock_manager_class.return_value = mock_manager

        args = SimpleNamespace()
        config_list(args)

        captured = capsys.readouterr()
        assert "No contexts configured" in captured.out


class TestUseContext:
    """Tests for use_context function."""

    @patch("grafana_weaver.main.GrafanaConfigManager")
    def test_use_context(self, mock_manager_class, capsys):
        """Should switch to specified context."""
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager

        args = SimpleNamespace(name="test-ctx")
        config_use(args)

        mock_manager.use_context.assert_called_once_with("test-ctx")
        captured = capsys.readouterr()
        assert "Switched to context 'test-ctx'" in captured.out


class TestDeleteContext:
    """Tests for delete_context function."""

    @patch("grafana_weaver.main.GrafanaConfigManager")
    def test_delete_context(self, mock_manager_class, capsys):
        """Should delete specified context."""
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager

        args = SimpleNamespace(name="test-ctx")
        config_delete(args)

        mock_manager.delete_context.assert_called_once_with("test-ctx")
        captured = capsys.readouterr()
        assert "Context 'test-ctx' deleted" in captured.out


class TestShowContext:
    """Tests for show_context function."""

    @patch("grafana_weaver.main.GrafanaConfigManager")
    def test_show_context_specified(self, mock_manager_class, capsys):
        """Should show details of specified context."""
        mock_manager = Mock()
        mock_manager.load.return_value = {
            "contexts": {
                "test-ctx": {
                    "grafana": {
                        "server": "https://grafana.test",
                        "user": "admin",
                        "password": "secret123",
                        "org-id": 1,
                    },
                },
            },
        }
        mock_manager_class.return_value = mock_manager

        args = SimpleNamespace(name="test-ctx")
        config_show(args)

        captured = capsys.readouterr()
        assert "Context: test-ctx" in captured.out
        assert "https://grafana.test" in captured.out
        assert "admin" in captured.out
        assert "******" in captured.out  # Masked password

    @patch("grafana_weaver.main.GrafanaConfigManager")
    def test_show_context_current(self, mock_manager_class, capsys):
        """Should show current context when no name specified."""
        mock_manager = Mock()
        mock_manager.get_current_context.return_value = "current-ctx"
        mock_manager.load.return_value = {
            "contexts": {
                "current-ctx": {
                    "grafana": {
                        "server": "https://grafana.test",
                        "user": "admin",
                        "password": "secret",
                        "org-id": 1,
                    },
                },
            },
        }
        mock_manager_class.return_value = mock_manager

        # Use a simple namespace object instead of Mock to avoid "name" attribute issues
        from types import SimpleNamespace

        args = SimpleNamespace(name=None)
        config_show(args)

        captured = capsys.readouterr()
        assert "Context: current-ctx" in captured.out

    @patch("grafana_weaver.main.GrafanaConfigManager")
    def test_show_context_none_specified_no_current(self, mock_manager_class):
        """Should exit with error when no context specified and no current context."""
        mock_manager = Mock()
        mock_manager.get_current_context.return_value = None
        mock_manager.load.return_value = {"contexts": {}}
        mock_manager_class.return_value = mock_manager

        from types import SimpleNamespace

        args = SimpleNamespace(name=None)

        with pytest.raises(SystemExit) as exc_info:
            config_show(args)
        assert exc_info.value.code == 1

    @patch("grafana_weaver.main.GrafanaConfigManager")
    def test_show_context_not_found(self, mock_manager_class):
        """Should exit with error when context not found."""
        mock_manager = Mock()
        mock_manager.load.return_value = {"contexts": {}}
        mock_manager_class.return_value = mock_manager

        args = SimpleNamespace(name="nonexistent")

        with pytest.raises(SystemExit) as exc_info:
            config_show(args)
        assert exc_info.value.code == 1


class TestSetConfig:
    """Tests for set_config function."""

    @patch("grafana_weaver.main.GrafanaConfigManager")
    def test_set_config(self, mock_manager_class, capsys):
        """Should set config value using dot notation."""
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager

        args = SimpleNamespace(key="contexts.test.grafana.server", value="https://grafana.test")
        config_set(args)

        mock_manager.set_value.assert_called_once_with("contexts.test.grafana.server", "https://grafana.test")
        captured = capsys.readouterr()
        assert "Set contexts.test.grafana.server = https://grafana.test" in captured.out


class TestCheckConfig:
    """Tests for check_config function."""

    @patch("grafana_weaver.main.GrafanaConfigManager")
    def test_check_config_exists(self, mock_manager_class, capsys, tmp_path):
        """Should display config status when file exists."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            yaml.dump(
                {
                    "current-context": "test-ctx",
                    "contexts": {
                        "test-ctx": {
                            "grafana": {
                                "server": "https://grafana.test",
                                "user": "admin",
                                "password": "secret",
                            },
                        },
                    },
                },
            ),
        )

        mock_manager = Mock()
        mock_manager.config_path = config_file
        mock_manager.get_current_context.return_value = "test-ctx"
        mock_manager.load.return_value = {
            "current-context": "test-ctx",
            "contexts": {
                "test-ctx": {
                    "grafana": {
                        "server": "https://grafana.test",
                        "user": "admin",
                        "password": "secret",
                    },
                },
            },
        }
        mock_manager_class.return_value = mock_manager

        args = SimpleNamespace()
        config_check(args)

        captured = capsys.readouterr()
        assert "Configuration file:" in captured.out
        assert "Exists: True" in captured.out
        assert "Contexts: 1" in captured.out
        assert "Current context: test-ctx" in captured.out
        assert "Current context 'test-ctx' is valid" in captured.out

    @patch("grafana_weaver.main.GrafanaConfigManager")
    def test_check_config_not_exists(self, mock_manager_class, capsys, tmp_path):
        """Should display message when config file doesn't exist."""
        config_file = tmp_path / "nonexistent.yaml"

        mock_manager = Mock()
        mock_manager.config_path = config_file
        mock_manager_class.return_value = mock_manager

        args = SimpleNamespace()
        config_check(args)

        captured = capsys.readouterr()
        assert "Exists: False" in captured.out
        assert "No configuration file found" in captured.out

    @patch("grafana_weaver.main.GrafanaConfigManager")
    def test_check_config_incomplete(self, mock_manager_class, capsys, tmp_path):
        """Should warn about incomplete configuration."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump({"current-context": "test-ctx", "contexts": {"test-ctx": {"grafana": {}}}}))

        mock_manager = Mock()
        mock_manager.config_path = config_file
        mock_manager.get_current_context.return_value = "test-ctx"
        mock_manager.load.return_value = {"current-context": "test-ctx", "contexts": {"test-ctx": {"grafana": {}}}}
        mock_manager_class.return_value = mock_manager

        args = SimpleNamespace()
        config_check(args)

        captured = capsys.readouterr()
        assert "Warning: Configuration incomplete" in captured.out

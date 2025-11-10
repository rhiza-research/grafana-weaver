"""Tests for utils.py module."""

import pytest
import yaml

from grafana_weaver.utils import get_grafana_config, get_grafana_context


class TestGetGrafanaContext:
    """Tests for get_grafana_context function."""

    def test_context_from_grafana_context_env(self, monkeypatch):
        """Context should be read from GRAFANA_CONTEXT environment variable."""
        monkeypatch.setenv("GRAFANA_CONTEXT", "myproject-1")
        context = get_grafana_context()
        assert context == "myproject-1"

    def test_context_prompt(self, monkeypatch):
        """Context should be prompted if not in environment."""
        monkeypatch.delenv("GRAFANA_CONTEXT", raising=False)
        monkeypatch.setattr("builtins.input", lambda _: "myproject-1")

        context = get_grafana_context()
        assert context == "myproject-1"

    def test_empty_context_exits(self, monkeypatch):
        """Empty context should exit with error."""
        monkeypatch.delenv("GRAFANA_CONTEXT", raising=False)
        monkeypatch.setattr("builtins.input", lambda _: "")

        with pytest.raises(SystemExit) as exc_info:
            get_grafana_context()
        assert exc_info.value.code == 1


class TestGetGrafanaConfig:
    """Tests for get_grafana_config function."""

    def test_config_from_xdg_config_home(self, monkeypatch, tmp_path):
        """Config should be read from XDG_CONFIG_HOME location."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        grafanactl_dir = config_dir / "grafanactl"
        grafanactl_dir.mkdir()
        config_file = grafanactl_dir / "config.yaml"

        config_data = {
            "contexts": {
                "myproject-1": {
                    "grafana": {"server": "https://grafana.example.com", "user": "admin", "password": "secret123"},
                },
            },
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        monkeypatch.setenv("XDG_CONFIG_HOME", str(config_dir))
        monkeypatch.delenv("HOME", raising=False)

        result = get_grafana_config("myproject-1")
        assert result["server"] == "https://grafana.example.com"
        assert result["user"] == "admin"
        assert result["password"] == "secret123"

    def test_config_from_home_config(self, monkeypatch, tmp_path):
        """Config should be read from HOME/.config location."""
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        config_dir = home_dir / ".config" / "grafanactl"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.yaml"

        config_data = {
            "contexts": {
                "test-context": {
                    "grafana": {"server": "https://test.example.com", "user": "testuser", "password": "testpass"},
                },
            },
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.setenv("HOME", str(home_dir))

        result = get_grafana_config("test-context")
        assert result["server"] == "https://test.example.com"
        assert result["user"] == "testuser"

    def test_config_file_not_found_exits(self, monkeypatch, tmp_path):
        """Should exit with error if config file not found."""
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.setenv("HOME", str(tmp_path))

        with pytest.raises(SystemExit) as exc_info:
            get_grafana_config("test-context")
        assert exc_info.value.code == 1

    def test_context_not_found_exits(self, monkeypatch, tmp_path):
        """Should exit with error if context doesn't exist."""
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        config_dir = home_dir / ".config" / "grafanactl"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.yaml"

        config_data = {
            "contexts": {
                "other-context": {
                    "grafana": {"server": "https://other.example.com", "user": "user", "password": "pass"},
                },
            },
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.setenv("HOME", str(home_dir))

        with pytest.raises(SystemExit) as exc_info:
            get_grafana_config("nonexistent-context")
        assert exc_info.value.code == 1

    def test_missing_required_fields_exits(self, monkeypatch, tmp_path):
        """Should exit with error if config is missing required fields."""
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        config_dir = home_dir / ".config" / "grafanactl"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.yaml"

        config_data = {
            "contexts": {
                "incomplete-context": {
                    "grafana": {
                        "server": "https://incomplete.example.com",
                        # Missing user and password
                    },
                },
            },
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.setenv("HOME", str(home_dir))

        with pytest.raises(SystemExit) as exc_info:
            get_grafana_config("incomplete-context")
        assert exc_info.value.code == 1

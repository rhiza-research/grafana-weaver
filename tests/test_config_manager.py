"""Tests for GrafanaConfigManager class."""

import pytest
import yaml

from grafana_weaver.core.config_manager import GrafanaConfigManager


class TestGrafanaConfigManager:
    """Tests for GrafanaConfigManager class."""

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

        manager = GrafanaConfigManager()
        result = manager.get_context("myproject-1")
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

        manager = GrafanaConfigManager()
        result = manager.get_context("test-context")
        assert result["server"] == "https://test.example.com"
        assert result["user"] == "testuser"

    def test_config_file_not_found_exits(self, monkeypatch, tmp_path):
        """Should exit with error if config file not found."""
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.setenv("HOME", str(tmp_path))

        manager = GrafanaConfigManager()
        with pytest.raises(SystemExit) as exc_info:
            manager.get_context("test-context")
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

        manager = GrafanaConfigManager()
        with pytest.raises(SystemExit) as exc_info:
            manager.get_context("nonexistent-context")
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

        manager = GrafanaConfigManager()
        with pytest.raises(SystemExit) as exc_info:
            manager.get_context("incomplete-context")
        assert exc_info.value.code == 1

    def test_context_from_init_param(self, monkeypatch, tmp_path):
        """Context passed to __init__ should be used."""
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        config_dir = home_dir / ".config" / "grafanactl"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.yaml"

        config_data = {
            "contexts": {
                "init-context": {
                    "grafana": {"server": "https://init.example.com", "user": "user", "password": "pass"},
                },
            },
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.setenv("HOME", str(home_dir))

        manager = GrafanaConfigManager(context="init-context")
        result = manager.get_context()
        assert result["server"] == "https://init.example.com"

    def test_context_from_current_context(self, monkeypatch, tmp_path):
        """Should fall back to current-context from config file."""
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        config_dir = home_dir / ".config" / "grafanactl"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.yaml"

        config_data = {
            "current-context": "default-context",
            "contexts": {
                "default-context": {
                    "grafana": {"server": "https://default.example.com", "user": "user", "password": "pass"},
                },
            },
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.setenv("HOME", str(home_dir))

        manager = GrafanaConfigManager()
        result = manager.get_context()
        assert result["server"] == "https://default.example.com"

    def test_init_param_takes_precedence(self, monkeypatch, tmp_path):
        """Context from __init__ should take precedence over current-context."""
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        config_dir = home_dir / ".config" / "grafanactl"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.yaml"

        config_data = {
            "current-context": "default-context",
            "contexts": {
                "default-context": {
                    "grafana": {"server": "https://default.example.com", "user": "user", "password": "pass"},
                },
                "override-context": {
                    "grafana": {"server": "https://override.example.com", "user": "user", "password": "pass"},
                },
            },
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.setenv("HOME", str(home_dir))

        manager = GrafanaConfigManager(context="override-context")
        result = manager.get_context()
        assert result["server"] == "https://override.example.com"

    def test_no_context_exits(self, monkeypatch, tmp_path):
        """Should exit if no context provided and no current-context in file."""
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        config_dir = home_dir / ".config" / "grafanactl"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.yaml"

        config_data = {"contexts": {}}
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.setenv("HOME", str(home_dir))

        manager = GrafanaConfigManager()
        with pytest.raises(SystemExit) as exc_info:
            manager.get_context()
        assert exc_info.value.code == 1

    def test_xdg_config_dirs_fallback(self, monkeypatch, tmp_path):
        """Should check XDG_CONFIG_DIRS as fallback."""
        # Create config in XDG_CONFIG_DIRS location
        config_dir = tmp_path / "etc" / "xdg"
        config_dir.mkdir(parents=True)
        grafanactl_dir = config_dir / "grafanactl"
        grafanactl_dir.mkdir()
        config_file = grafanactl_dir / "config.yaml"

        config_data = {
            "contexts": {
                "xdg-context": {
                    "grafana": {"server": "https://xdg.example.com", "user": "user", "password": "pass"},
                },
            },
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.delenv("HOME", raising=False)
        monkeypatch.setenv("XDG_CONFIG_DIRS", str(config_dir))

        manager = GrafanaConfigManager()
        result = manager.get_context("xdg-context")
        assert result["server"] == "https://xdg.example.com"

    def test_use_context(self, monkeypatch, tmp_path):
        """Should set current context."""
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        config_dir = home_dir / ".config" / "grafanactl"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.yaml"

        config_data = {
            "contexts": {
                "ctx1": {"grafana": {"server": "https://server1.com", "user": "user", "password": "pass"}},
                "ctx2": {"grafana": {"server": "https://server2.com", "user": "user", "password": "pass"}},
            },
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.setenv("HOME", str(home_dir))

        manager = GrafanaConfigManager()
        manager.use_context("ctx2")

        # Reload and check
        config = manager.load()
        assert config["current-context"] == "ctx2"

    def test_use_context_not_found(self, monkeypatch, tmp_path):
        """Should exit if trying to use nonexistent context."""
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        config_dir = home_dir / ".config" / "grafanactl"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.yaml"

        config_data = {"contexts": {}}
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.setenv("HOME", str(home_dir))

        manager = GrafanaConfigManager()
        with pytest.raises(SystemExit) as exc_info:
            manager.use_context("nonexistent")
        assert exc_info.value.code == 1

    def test_delete_context(self, monkeypatch, tmp_path):
        """Should delete context."""
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        config_dir = home_dir / ".config" / "grafanactl"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.yaml"

        config_data = {
            "current-context": "ctx1",
            "contexts": {
                "ctx1": {"grafana": {"server": "https://server1.com", "user": "user", "password": "pass"}},
                "ctx2": {"grafana": {"server": "https://server2.com", "user": "user", "password": "pass"}},
            },
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.setenv("HOME", str(home_dir))

        manager = GrafanaConfigManager()
        manager.delete_context("ctx2")

        # Reload and check
        config = manager.load()
        assert "ctx2" not in config["contexts"]
        assert "ctx1" in config["contexts"]

    def test_delete_current_context_clears_current(self, monkeypatch, tmp_path):
        """Should clear current-context when deleting the current context."""
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        config_dir = home_dir / ".config" / "grafanactl"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.yaml"

        config_data = {
            "current-context": "ctx1",
            "contexts": {
                "ctx1": {"grafana": {"server": "https://server1.com", "user": "user", "password": "pass"}},
                "ctx2": {"grafana": {"server": "https://server2.com", "user": "user", "password": "pass"}},
            },
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.setenv("HOME", str(home_dir))

        manager = GrafanaConfigManager()
        manager.delete_context("ctx1")

        # Should have cleared current-context to None (not switched to ctx2)
        config = manager.load()
        assert config["current-context"] is None

    def test_delete_last_context_clears_current(self, monkeypatch, tmp_path):
        """Should clear current-context when deleting last context."""
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        config_dir = home_dir / ".config" / "grafanactl"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.yaml"

        config_data = {
            "current-context": "ctx1",
            "contexts": {
                "ctx1": {"grafana": {"server": "https://server1.com", "user": "user", "password": "pass"}},
            },
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.setenv("HOME", str(home_dir))

        manager = GrafanaConfigManager()
        manager.delete_context("ctx1")

        # current-context should be None
        config = manager.load()
        assert config["current-context"] is None

    def test_delete_context_not_found(self, monkeypatch, tmp_path):
        """Should exit if trying to delete nonexistent context."""
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        config_dir = home_dir / ".config" / "grafanactl"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.yaml"

        config_data = {"contexts": {}}
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.setenv("HOME", str(home_dir))

        manager = GrafanaConfigManager()
        with pytest.raises(SystemExit) as exc_info:
            manager.delete_context("nonexistent")
        assert exc_info.value.code == 1

    def test_set_value(self, monkeypatch, tmp_path):
        """Should set config value using dot notation."""
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        config_dir = home_dir / ".config" / "grafanactl"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.yaml"

        config_data = {"contexts": {}}
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.setenv("HOME", str(home_dir))

        manager = GrafanaConfigManager()
        manager.set_value("contexts.newctx.grafana.server", "https://new.example.com")

        # Check value was set
        config = manager.load()
        assert config["contexts"]["newctx"]["grafana"]["server"] == "https://new.example.com"

    def test_set_value_org_id_as_int(self, monkeypatch, tmp_path):
        """Should convert org-id to integer."""
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        config_dir = home_dir / ".config" / "grafanactl"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.yaml"

        config_data = {"contexts": {}}
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.setenv("HOME", str(home_dir))

        manager = GrafanaConfigManager()
        manager.set_value("contexts.test.grafana.org-id", "5")

        # Check value was set as int
        config = manager.load()
        assert config["contexts"]["test"]["grafana"]["org-id"] == 5
        assert isinstance(config["contexts"]["test"]["grafana"]["org-id"], int)

    def test_set_value_invalid_org_id(self, monkeypatch, tmp_path):
        """Should exit if org-id is not a valid integer."""
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        config_dir = home_dir / ".config" / "grafanactl"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.yaml"

        config_data = {"contexts": {}}
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.setenv("HOME", str(home_dir))

        manager = GrafanaConfigManager()
        with pytest.raises(SystemExit) as exc_info:
            manager.set_value("contexts.test.grafana.org-id", "notanumber")
        assert exc_info.value.code == 1

    def test_set_value_invalid_path(self, monkeypatch, tmp_path):
        """Should exit if path format is invalid."""
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        config_dir = home_dir / ".config" / "grafanactl"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.yaml"

        config_data = {"contexts": {}}
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.setenv("HOME", str(home_dir))

        manager = GrafanaConfigManager()
        with pytest.raises(SystemExit) as exc_info:
            manager.set_value("invalid.path", "value")
        assert exc_info.value.code == 1

    def test_add_context(self, monkeypatch, tmp_path):
        """Should add a new context."""
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        config_dir = home_dir / ".config" / "grafanactl"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.yaml"

        config_data = {"contexts": {}}
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.setenv("HOME", str(home_dir))

        manager = GrafanaConfigManager()
        manager.add_context("new-ctx", "https://grafana.example.com", "admin", "secret", 2)

        # Check context was added
        config = manager.load()
        assert "new-ctx" in config["contexts"]
        assert config["contexts"]["new-ctx"]["grafana"]["server"] == "https://grafana.example.com"
        assert config["contexts"]["new-ctx"]["grafana"]["user"] == "admin"
        assert config["contexts"]["new-ctx"]["grafana"]["password"] == "secret"
        assert config["contexts"]["new-ctx"]["grafana"]["org-id"] == 2

    def test_add_context_creates_contexts_key(self, monkeypatch, tmp_path):
        """Should create contexts key if missing."""
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        config_dir = home_dir / ".config" / "grafanactl"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.yaml"

        # Config file with no contexts key
        config_data = {}
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.setenv("HOME", str(home_dir))

        manager = GrafanaConfigManager()
        manager.add_context("ctx1", "https://grafana.example.com", "admin", "secret")

        # Check contexts key was created
        config = manager.load()
        assert "contexts" in config
        assert "ctx1" in config["contexts"]

    def test_list_contexts(self, monkeypatch, tmp_path):
        """Should list all context names."""
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        config_dir = home_dir / ".config" / "grafanactl"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.yaml"

        config_data = {
            "contexts": {
                "ctx1": {"grafana": {"server": "https://server1.com", "user": "user", "password": "pass"}},
                "ctx2": {"grafana": {"server": "https://server2.com", "user": "user", "password": "pass"}},
            },
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.setenv("HOME", str(home_dir))

        manager = GrafanaConfigManager()
        contexts = manager.list_contexts()

        assert "ctx1" in contexts
        assert "ctx2" in contexts
        assert len(contexts) == 2

    def test_get_current_context(self, monkeypatch, tmp_path):
        """Should get current context name."""
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        config_dir = home_dir / ".config" / "grafanactl"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.yaml"

        config_data = {
            "current-context": "my-ctx",
            "contexts": {
                "my-ctx": {"grafana": {"server": "https://server.com", "user": "user", "password": "pass"}},
            },
        }
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.setenv("HOME", str(home_dir))

        manager = GrafanaConfigManager()
        current = manager.get_current_context()

        assert current == "my-ctx"

    def test_get_current_context_none(self, monkeypatch, tmp_path):
        """Should return None when no current context."""
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        config_dir = home_dir / ".config" / "grafanactl"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.yaml"

        config_data = {"contexts": {}}
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.setenv("HOME", str(home_dir))

        manager = GrafanaConfigManager()
        current = manager.get_current_context()

        assert current is None

    def test_config_path_property(self, monkeypatch, tmp_path):
        """Should return config path via property."""
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.setenv("HOME", str(home_dir))

        manager = GrafanaConfigManager()
        path = manager.config_path

        assert path == home_dir / ".config" / "grafanactl" / "config.yaml"

    def test_no_home_env_exits(self, monkeypatch):
        """Should exit if HOME not set and no other config path found."""
        monkeypatch.delenv("HOME", raising=False)
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.delenv("XDG_CONFIG_DIRS", raising=False)

        with pytest.raises(SystemExit) as exc_info:
            GrafanaConfigManager()
        assert exc_info.value.code == 1

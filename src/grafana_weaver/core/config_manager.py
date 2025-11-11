#!/usr/bin/env python3
"""Configuration manager for grafana-weaver."""

import os
import sys
from pathlib import Path

import yaml


class GrafanaConfigManager:
    """Manager for grafana-weaver configuration files."""

    def __init__(self, context: str | None = None):
        """
        Initialize config manager and determine config file path.

        Args:
            context: Optional context name. If None, will read from config file's current-context.
                    If not provided and no current-context in file, will error.
        """
        self._config_path = self._find_config_path()
        self._config = None  # Lazy load
        self._context = context

    def _find_config_path(self) -> Path:
        """
        Find the path to the grafana-weaver config file.

        Returns the path even if the file doesn't exist yet (for creating new configs).
        Uses grafanactl-compatible format at:
        1. $XDG_CONFIG_HOME/grafanactl/config.yaml
        2. $HOME/.config/grafanactl/config.yaml
        3. $XDG_CONFIG_DIRS/grafanactl/config.yaml (first existing)

        Returns:
            Path to config file (may not exist yet)

        Raises:
            SystemExit: If config path cannot be determined
        """
        # Check XDG_CONFIG_HOME first
        xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config_home:
            config_path = Path(xdg_config_home) / "grafanactl" / "config.yaml"
            if config_path.exists():
                return config_path

        # Check ~/.config
        home = os.environ.get("HOME")
        if home:
            config_path = Path(home) / ".config" / "grafanactl" / "config.yaml"
            if config_path.exists() or not xdg_config_home:
                return config_path

        # Check XDG_CONFIG_DIRS
        xdg_config_dirs = os.environ.get("XDG_CONFIG_DIRS")
        if xdg_config_dirs:
            for config_dir in xdg_config_dirs.split(":"):
                config_path = Path(config_dir) / "grafanactl" / "config.yaml"
                if config_path.exists():
                    return config_path

        # Default to ~/.config if nothing found
        if home:
            return Path(home) / ".config" / "grafanactl" / "config.yaml"

        print("Error: Could not determine config file location")
        sys.exit(1)

    @property
    def config_path(self) -> Path:
        """Get the path to the config file."""
        return self._config_path

    def load(self) -> dict:
        """
        Load the configuration file.

        Returns cached config if already loaded.

        Returns:
            Configuration dictionary with 'contexts' and optionally 'current-context'
        """
        if self._config is not None:
            return self._config

        if not self._config_path.exists():
            self._config = {"contexts": {}}
            return self._config

        with open(self._config_path) as f:
            self._config = yaml.safe_load(f) or {"contexts": {}}

        return self._config

    def save(self):
        """
        Save the current configuration to disk.

        Creates parent directories if they don't exist.
        Sets file permissions to 0600 for security.
        """
        if self._config is None:
            return

        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._config_path, "w") as f:
            yaml.dump(self._config, f, default_flow_style=False, sort_keys=False)
        self._config_path.chmod(0o600)

    def get_current_context_name(self) -> str | None:
        """
        Get the current context name from the config file.

        Returns:
            The current context name, or None if not set

        Raises:
            SystemExit: If config file cannot be read
        """
        config = self.load()
        return config.get("current-context")

    def reload(self):
        """Force reload configuration from disk."""
        self._config = None
        return self.load()

    def add_context(self, name: str, server: str, user: str, password: str, org_id: int = 1):
        """
        Add or update a context.

        Args:
            name: Context name
            server: Grafana server URL
            user: Grafana username
            password: Grafana password
            org_id: Grafana organization ID
        """
        config = self.load()

        if "contexts" not in config:
            config["contexts"] = {}

        config["contexts"][name] = {
            "grafana": {
                "server": server,
                "user": user,
                "password": password,
                "org-id": org_id,
            },
        }

        self.save()

    def _resolve_context_name(self) -> str:
        """
        Resolve the context name to use.

        Returns:
            The context name (from init param or config file)

        Raises:
            SystemExit: If no context can be resolved
        """
        # Use context provided to __init__ if available
        if self._context:
            return self._context

        # Otherwise, read from config file's current-context
        config = self.load()
        current_context = config.get("current-context")
        if current_context:
            return current_context

        # No context found
        print("Error: No context specified.")
        print("Please either:")
        print("  1. Set GRAFANA_CONTEXT environment variable")
        print("  2. Set current-context in your config file")
        sys.exit(1)

    def get_context(self, name: str | None = None) -> dict:
        """
        Get a specific context configuration.

        Args:
            name: Optional context name. If None, will resolve from init param or config file.

        Returns:
            Dictionary with Grafana configuration (server, user, password, org-id)

        Raises:
            SystemExit: If context doesn't exist or is missing required fields
        """
        # Resolve context name
        if name is None:
            name = self._resolve_context_name()

        config = self.load()
        contexts = config.get("contexts", {})

        if name not in contexts:
            print(f"Error: context '{name}' not found in config")
            available = list(contexts.keys())
            if available:
                print(f"Available contexts: {', '.join(available)}")
            else:
                print("No contexts configured")
            sys.exit(1)

        context = contexts[name]
        grafana_config = context.get("grafana", {})

        # Validate required fields
        required_fields = ["server", "user", "password"]
        missing_fields = [field for field in required_fields if field not in grafana_config]
        if missing_fields:
            print(f"Error: context '{name}' is missing required fields: {', '.join(missing_fields)}")
            sys.exit(1)

        # Ensure org-id has a default
        if "org-id" not in grafana_config:
            grafana_config["org-id"] = 1

        return grafana_config

    def list_contexts(self) -> list[str]:
        """
        List all context names.

        Returns:
            List of context names
        """
        config = self.load()
        return list(config.get("contexts", {}).keys())

    def get_current_context(self) -> str | None:
        """
        Get the current context name.

        Returns:
            Current context name or None if not set
        """
        config = self.load()
        return config.get("current-context")

    def use_context(self, name: str):
        """
        Set the current context.

        Args:
            name: Context name to set as current

        Raises:
            SystemExit: If context doesn't exist
        """
        config = self.load()

        if name not in config.get("contexts", {}):
            print(f"Error: context '{name}' not found")
            sys.exit(1)

        config["current-context"] = name
        self.save()

    def delete_context(self, name: str):
        """
        Delete a context.

        If deleting the current context, clears the current-context setting.
        User must explicitly switch to a new context with 'config use'.

        Args:
            name: Context name to delete

        Raises:
            SystemExit: If context doesn't exist
        """
        config = self.load()

        if name not in config.get("contexts", {}):
            print(f"Error: context '{name}' not found")
            sys.exit(1)

        del config["contexts"][name]

        # Set current-context to None if deleting the current one
        if config.get("current-context") == name:
            config["current-context"] = None

        self.save()

    def set_value(self, path: str, value: str):
        """
        Set a config value using dot notation.

        Args:
            path: Dot-separated path (e.g., "contexts.default.grafana.server")
            value: Value to set

        Raises:
            SystemExit: If path format is invalid
        """
        config = self.load()

        # Parse the path: contexts.{name}.grafana.{key}
        parts = path.split(".")

        if len(parts) < 4 or parts[0] != "contexts" or parts[2] != "grafana":
            print("Error: path must be in format: contexts.<name>.grafana.<key>")
            print("Examples:")
            print("  contexts.default.grafana.server")
            print("  contexts.default.grafana.user")
            print("  contexts.default.grafana.password")
            print("  contexts.default.grafana.token")
            print("  contexts.default.grafana.org-id")
            sys.exit(1)

        context_name = parts[1]
        key = parts[3]

        # Ensure contexts exists
        if "contexts" not in config:
            config["contexts"] = {}

        # Ensure context exists
        if context_name not in config["contexts"]:
            config["contexts"][context_name] = {"grafana": {}}
        elif "grafana" not in config["contexts"][context_name]:
            config["contexts"][context_name]["grafana"] = {}

        # Convert org-id to integer if that's what we're setting
        if key == "org-id":
            try:
                value = int(value)
            except ValueError:
                print(f"Error: org-id must be an integer, got: {value}")
                sys.exit(1)

        # Set the value
        config["contexts"][context_name]["grafana"][key] = value

        self.save()

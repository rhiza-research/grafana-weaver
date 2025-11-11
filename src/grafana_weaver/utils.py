#!/usr/bin/env python3
"""
Shared utility functions for grafana-weaver.
"""

import os
import sys
from pathlib import Path

import yaml


def get_config_path() -> Path:
    """
    Get the path to the grafana-weaver config file.

    Returns the path even if the file doesn't exist yet (for creating new configs).
    Uses grafanactl-compatible format at:
    1. $XDG_CONFIG_HOME/grafanactl/config.yaml
    2. $HOME/.config/grafanactl/config.yaml
    3. $XDG_CONFIG_DIRS/grafanactl/config.yaml (first existing)

    Returns:
        Path to config file (may not exist yet)
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


def get_grafana_context() -> str:
    """
    Get or prompt for the context name.

    Returns:
        str: The context name (e.g., 'myproject-1')
    """
    context = os.environ.get("GRAFANA_CONTEXT")
    if not context:
        context = input("Enter the context name: ").strip()
        if not context:
            print("GRAFANA_CONTEXT is not set, exiting")
            sys.exit(1)
        os.environ["GRAFANA_CONTEXT"] = context
    print(f"Using context: {context}")
    return context

def get_grafana_config(context_name: str) -> dict[str, str]:
    """
    Get Grafana configuration from config file.

    Args:
        context_name: Context name (e.g., 'myproject-1')

    Returns:
        Dict with 'server', 'user', 'password', and 'org-id' keys

    Raises:
        SystemExit: If config file not found or context doesn't exist
    """
    config_path = get_config_path()

    if not config_path.exists():
        print("Error: grafanactl config file not found")
        print(f"Expected location: {config_path}")
        print(f"\nCreate one with: config set contexts.{context_name}.grafana.server <url>")
        sys.exit(1)

    # Read the config file
    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Get the context from config
    contexts = config.get("contexts", {})

    if context_name not in contexts:
        print(f"Error: context '{context_name}' not found in grafanactl config")
        print(f"Available contexts: {', '.join(contexts.keys())}")
        sys.exit(1)

    print(f"Using grafanactl context: {context_name}")

    context = contexts[context_name]
    grafana_config = context.get("grafana", {})

    # Validate required fields
    required_fields = ["server", "user", "password"]
    missing_fields = [field for field in required_fields if field not in grafana_config]
    if missing_fields:
        print(f"Error: context '{context_name}' is missing required fields: {', '.join(missing_fields)}")
        sys.exit(1)

    return grafana_config

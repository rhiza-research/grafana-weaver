#!/usr/bin/env python3
"""Manage grafanactl config file."""

import argparse
import sys
from pathlib import Path

import yaml

from .utils import get_config_path


def load_config(config_path: Path) -> dict:
    """Load the grafanactl config file."""
    if not config_path.exists():
        return {"contexts": {}}

    with open(config_path) as f:
        return yaml.safe_load(f) or {"contexts": {}}


def save_config(config_path: Path, config: dict):
    """Save the grafanactl config file."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    config_path.chmod(0o600)  # Secure the file


def add_context(args):
    """Add or update a context in the config file."""
    config_path = get_config_path()
    config = load_config(config_path)

    if "contexts" not in config:
        config["contexts"] = {}

    config["contexts"][args.name] = {
        "grafana": {
            "server": args.server,
            "user": args.user,
            "password": args.password,
            "org-id": args.org_id,
        }
    }

    # Set as current context if requested
    if args.use_context or "current-context" not in config:
        config["current-context"] = args.name

    save_config(config_path, config)
    print(f"Context '{args.name}' added to {config_path}")


def list_contexts(args):
    """List all contexts in the config file."""
    config_path = get_config_path()
    config = load_config(config_path)

    contexts = config.get("contexts", {})
    current_context = config.get("current-context")

    if not contexts:
        print("No contexts configured")
        return

    print("Available contexts:")
    for name in contexts:
        marker = "*" if name == current_context else " "
        server = contexts[name].get("grafana", {}).get("server", "")
        print(f"{marker} {name:<20} {server}")


def use_context(args):
    """Set the current context."""
    config_path = get_config_path()
    config = load_config(config_path)

    if args.name not in config.get("contexts", {}):
        print(f"Error: context '{args.name}' not found")
        sys.exit(1)

    config["current-context"] = args.name
    save_config(config_path, config)
    print(f"Switched to context '{args.name}'")


def delete_context(args):
    """Delete a context from the config file."""
    config_path = get_config_path()
    config = load_config(config_path)

    if args.name not in config.get("contexts", {}):
        print(f"Error: context '{args.name}' not found")
        sys.exit(1)

    del config["contexts"][args.name]

    # Clear current-context if deleting the current one
    if config.get("current-context") == args.name:
        if config["contexts"]:
            config["current-context"] = next(iter(config["contexts"]))
        else:
            config.pop("current-context", None)

    save_config(config_path, config)
    print(f"Context '{args.name}' deleted")


def show_context(args):
    """Show details of a context."""
    config_path = get_config_path()
    config = load_config(config_path)

    context_name = args.name or config.get("current-context")
    if not context_name:
        print("Error: no context specified and no current context set")
        sys.exit(1)

    if context_name not in config.get("contexts", {}):
        print(f"Error: context '{context_name}' not found")
        sys.exit(1)

    context = config["contexts"][context_name]
    grafana = context.get("grafana", {})

    print(f"Context: {context_name}")
    print(f"  Server:   {grafana.get('server', 'N/A')}")
    print(f"  User:     {grafana.get('user', 'N/A')}")
    print(f"  Password: {'*' * len(grafana.get('password', ''))}")
    print(f"  Org ID:   {grafana.get('org-id', 'N/A')}")


def set_config(args):
    """Set a config value using dot notation (e.g., contexts.default.grafana.server)."""
    config_path = get_config_path()
    config = load_config(config_path)

    # Parse the path: contexts.{name}.grafana.{key}
    parts = args.path.split(".")

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
    value = args.value
    if key == "org-id":
        try:
            value = int(value)
        except ValueError:
            print(f"Error: org-id must be an integer, got: {value}")
            sys.exit(1)

    # Set the value
    config["contexts"][context_name]["grafana"][key] = value

    save_config(config_path, config)
    print(f"Set {args.path} = {value}")


def check_config(args):
    """Check the configuration and display the config file in use."""
    config_path = get_config_path()

    print(f"Configuration file: {config_path}")
    print(f"Exists: {config_path.exists()}")

    if not config_path.exists():
        print("\nNo configuration file found.")
        print(f"Create one with: config set contexts.default.grafana.server <url>")
        return

    config = load_config(config_path)

    # Display summary
    contexts = config.get("contexts", {})
    current_context = config.get("current-context")

    print(f"\nContexts: {len(contexts)}")
    print(f"Current context: {current_context or 'none'}")

    if not contexts:
        print("\nNo contexts configured.")
        return

    # Validate current context
    if current_context:
        if current_context in contexts:
            print(f"\nCurrent context '{current_context}' is valid")
            grafana = contexts[current_context].get("grafana", {})

            # Check required fields
            has_server = bool(grafana.get("server"))
            has_auth = bool(grafana.get("token")) or (
                bool(grafana.get("user")) and bool(grafana.get("password"))
            )

            print(f"  Server configured: {has_server}")
            print(f"  Authentication configured: {has_auth}")

            if not has_server or not has_auth:
                print("\n  Warning: Configuration incomplete")
                if not has_server:
                    print("    - Missing server URL")
                if not has_auth:
                    print("    - Missing authentication (token or user/password)")
        else:
            print(f"\nWarning: Current context '{current_context}' does not exist")

    print(f"\nAll contexts:")
    for name in contexts:
        marker = "*" if name == current_context else " "
        grafana = contexts[name].get("grafana", {})
        server = grafana.get("server", "no server")
        print(f"{marker} {name}: {server}")


def main():
    """Main entry point for config management."""
    parser = argparse.ArgumentParser(
        description="Manage grafanactl config file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Add context (convenience command, not in grafanactl)
    add_parser = subparsers.add_parser("add", help="Add or update a context (convenience command)")
    add_parser.add_argument("name", help="Context name")
    add_parser.add_argument("--server", required=True, help="Grafana server URL")
    add_parser.add_argument("--user", default="admin", help="Grafana username")
    add_parser.add_argument("--password", required=True, help="Grafana password")
    add_parser.add_argument("--org-id", type=int, default=1, help="Grafana org ID")
    add_parser.add_argument(
        "--use-context", action="store_true", help="Set as current context"
    )
    add_parser.set_defaults(func=add_context)

    # List contexts (grafanactl: config list-contexts)
    list_parser = subparsers.add_parser("list-contexts", help="List all contexts")
    list_parser.set_defaults(func=list_contexts)

    # Use context (grafanactl: config use-context)
    use_parser = subparsers.add_parser("use-context", help="Set the current context")
    use_parser.add_argument("name", help="Context name to use")
    use_parser.set_defaults(func=use_context)

    # Delete context (not in grafanactl, but useful)
    delete_parser = subparsers.add_parser("delete", help="Delete a context")
    delete_parser.add_argument("name", help="Context name to delete")
    delete_parser.set_defaults(func=delete_context)

    # View config (grafanactl: config view)
    show_parser = subparsers.add_parser("view", help="Show context details")
    show_parser.add_argument(
        "name", nargs="?", help="Context name (uses current context if not specified)"
    )
    show_parser.set_defaults(func=show_context)

    # Set config value (grafanactl: config set)
    set_parser = subparsers.add_parser("set", help="Set a config value")
    set_parser.add_argument("path", help="Config path (e.g., contexts.default.grafana.server)")
    set_parser.add_argument("value", help="Value to set")
    set_parser.set_defaults(func=set_config)

    # Check config (grafanactl: config check)
    check_parser = subparsers.add_parser("check", help="Check configuration and show status")
    check_parser.set_defaults(func=check_config)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()

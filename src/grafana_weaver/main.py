#!/usr/bin/env python3
"""Main CLI entrypoint for grafana-weaver."""

import argparse
import json
import os
import shutil
import sys
import tempfile
from importlib.metadata import version
from pathlib import Path

from grafana_weaver.core.client import GrafanaClient
from grafana_weaver.core.config_manager import GrafanaConfigManager
from grafana_weaver.core.dashboard_downloader import DashboardDownloader
from grafana_weaver.core.dashboard_extractor import DashboardExtractor
from grafana_weaver.core.jsonnet_builder import JsonnetBuilder

# Read version from package metadata (defined in pyproject.toml)
try:
    __version__ = version("grafana-weaver")
except Exception:
    __version__ = "unknown"


# ============================================================================
# Config Commands
# ============================================================================


def config_add(args):
    """Add or update a context in the config file."""
    manager = GrafanaConfigManager()
    manager.add_context(args.name, args.server, args.user, args.password, args.org_id)

    # Set as current context if requested
    if args.use_context:
        manager.use_context(args.name)
    elif manager.get_current_context() is None:
        manager.use_context(args.name)

    print(f"Context '{args.name}' added to {manager.config_path}")


def config_list(args):
    """List all contexts in the config file."""
    manager = GrafanaConfigManager()
    contexts = manager.list_contexts()
    current_context = manager.get_current_context()

    if not contexts:
        print("No contexts configured")
        return

    config = manager.load()
    print("Available contexts:")
    for name in contexts:
        marker = "*" if name == current_context else " "
        server = config["contexts"][name].get("grafana", {}).get("server", "")
        print(f"{marker} {name:<20} {server}")


def config_use(args):
    """Set the current context."""
    manager = GrafanaConfigManager()
    manager.use_context(args.name)
    print(f"Switched to context '{args.name}'")


def config_delete(args):
    """Delete a context from the config file."""
    manager = GrafanaConfigManager()
    manager.delete_context(args.name)
    print(f"Context '{args.name}' deleted")


def config_show(args):
    """Show details of a context."""
    manager = GrafanaConfigManager()
    config = manager.load()

    context_name = args.name or manager.get_current_context()
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


def config_set(args):
    """Set a config value using dot notation."""
    manager = GrafanaConfigManager()
    manager.set_value(args.key, args.value)
    print(f"Set {args.key} = {args.value}")


def config_check(args):
    """Check the configuration and display the config file in use."""
    manager = GrafanaConfigManager()
    config_path = manager.config_path

    print(f"Configuration file: {config_path}")
    print(f"Exists: {config_path.exists()}")

    if not config_path.exists():
        print("\nNo configuration file found.")
        print("Create one with: config set contexts.default.grafana.server <url>")
        return

    config = manager.load()

    # Display summary
    contexts = config.get("contexts", {})
    current_context = manager.get_current_context()

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
            has_auth = bool(grafana.get("token")) or (bool(grafana.get("user")) and bool(grafana.get("password")))

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

    print("\nAll contexts:")
    for name in contexts:
        marker = "*" if name == current_context else " "
        grafana = contexts[name].get("grafana", {})
        server = grafana.get("server", "no server")
        print(f"{marker} {name}: {server}")


# ============================================================================
# Upload Command
# ============================================================================


def upload_dashboards(args):
    """Upload dashboards to Grafana."""
    if not args.dashboard_dir.exists():
        print(f"Error: dashboards directory not found at {args.dashboard_dir}")
        sys.exit(1)

    print("=" * 42)
    print("Uploading Grafana dashboards...")
    print("=" * 42)
    print(f"Using dashboards directory: {args.dashboard_dir}")

    # Load Grafana config (context resolved from arg/env or config file)
    config_manager = GrafanaConfigManager(context=args.grafana_context)
    grafana_config = config_manager.get_context()

    # Build all jsonnet files
    builder = JsonnetBuilder(args.dashboard_dir)
    json_files = builder.build_all()

    if not json_files:
        print("No dashboards to upload")
        return

    # Create Grafana client
    client = GrafanaClient(
        server=grafana_config["server"],
        user=grafana_config["user"],
        password=grafana_config["password"],
        org_id=grafana_config.get("org-id", 1),
    )

    # Upload dashboards
    print("\nUploading dashboards to Grafana...")
    print(f"Found {len(json_files)} dashboards to upload")

    success_count = 0
    error_count = 0

    # Cache for folder title -> folder UID mapping
    folder_cache = {}

    for json_file in json_files:
        # Read the dashboard JSON
        with open(json_file) as f:
            dashboard_json = json.load(f)

        # Extract folder from file path
        # File structure: dashboard_dir/build/[folder/]dashboard.json
        build_dir = args.dashboard_dir / "build"
        relative_path = json_file.relative_to(build_dir)

        folder_uid = None
        if len(relative_path.parts) > 1:
            # Dashboard is in a subfolder
            folder_name = relative_path.parts[0]

            # Get or create the folder, using cache to avoid repeated API calls
            if folder_name not in folder_cache:
                try:
                    # Convert folder name back to title format (reverse sanitization)
                    folder_title = folder_name.replace("-", " ").title()
                    folder = client.get_or_create_folder(folder_title)
                    folder_cache[folder_name] = folder["uid"]
                    print(f"  Using folder: {folder_title}")
                except Exception as e:
                    print(f"  Warning: Failed to get/create folder '{folder_name}': {e}")
                    folder_cache[folder_name] = None

            folder_uid = folder_cache[folder_name]

        try:
            client.upload_dashboard(dashboard_json, folder_uid=folder_uid)
            print(f"  ✓ Uploaded: {dashboard_json.get('title', json_file.name)}")
            success_count += 1
        except Exception as e:
            print(f"  ✗ Failed to upload {json_file.name}: {e}")
            error_count += 1

    print(f"\nUpload complete: {success_count} succeeded, {error_count} failed")

    if error_count > 0:
        sys.exit(1)

    print("\n" + "=" * 42)
    print("Dashboards uploaded successfully!")
    print("=" * 42)


# ============================================================================
# Download Command
# ============================================================================


def download_dashboards(args):
    """Download dashboards from Grafana."""
    print("=" * 42)
    print("Downloading Grafana dashboards...")
    print("=" * 42)
    print(f"Output directory: {args.dashboard_dir}")

    # Load Grafana config (context resolved from arg/env or config file)
    config_manager = GrafanaConfigManager(context=args.grafana_context)
    grafana_config = config_manager.get_context()

    # Create Grafana client
    client = GrafanaClient(
        server=grafana_config["server"],
        user=grafana_config["user"],
        password=grafana_config["password"],
        org_id=grafana_config.get("org-id", 1),
    )

    # Create temporary directory for downloads
    downloaded_dir = Path(tempfile.mkdtemp())

    try:
        # Step 1: Download dashboards from Grafana
        print("\nStep 1: Downloading dashboards from Grafana...")
        downloader = DashboardDownloader(client)
        downloaded_files = downloader.download_all(downloaded_dir)

        # Step 2: Process dashboards to extract external content
        print("\nStep 2: Processing dashboards to extract external content...")
        extractor = DashboardExtractor(args.dashboard_dir)

        if not downloaded_files:
            print("No dashboards to process")
        else:
            for json_file in downloaded_files:
                print(f"Processing: {json_file}")

                # Process the JSON file using the extractor
                success = extractor.extract_from_file(json_file, base_dir=downloaded_dir)

                if not success:
                    print(f"Error processing {json_file}")
                    sys.exit(1)

        print("\n" + "=" * 42)
        print("Dashboard download complete!")
        print("=" * 42)
        print(f"  - Jsonnet templates: {args.dashboard_dir}/src/")
        print(f"  - Assets: {args.dashboard_dir}/src/assets/")

    finally:
        # Clean up temporary directory
        if downloaded_dir.exists():
            shutil.rmtree(downloaded_dir)


# ============================================================================
# Extract Command
# ============================================================================


def extract_external_content(args):
    """Extract external content from dashboard JSON files."""
    # Create extractor
    extractor = DashboardExtractor(args.dashboard_dir)

    # Extract from file
    success = extractor.extract_from_file(args.json_file, base_dir=args.base_dir)
    sys.exit(0 if success else 1)


# ============================================================================
# CLI Setup and Main Entry Point
# ============================================================================


def add_dashboard_dir_arg(parser):
    """Add common arguments to a parser."""
    parser.add_argument(
        "--dashboard-dir",
        type=Path,
        default=Path(os.environ.get("DASHBOARD_DIR", str(Path.cwd() / "dashboards"))),
        help="Dashboard directory root (defaults to DASHBOARD_DIR env var or './dashboards')",
    )

def add_grafana_context_arg(parser):
    parser.add_argument(
        "--grafana-context",
        default=os.environ.get("GRAFANA_CONTEXT"),
        help="Grafana context name (defaults to GRAFANA_CONTEXT env var or current-context in config)",
    )


def main():
    """Main CLI entrypoint with subcommands."""
    parser = argparse.ArgumentParser(
        prog="grafana-weaver",
        description="Manage Grafana dashboards with Jsonnet templates",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", required=True, help="Available commands")

    # Config subcommand
    config_parser = subparsers.add_parser("config", help="Manage Grafana configuration")
    config_subparsers = config_parser.add_subparsers(dest="config_command", required=True, help="Config commands")

    # config add
    add_parser = config_subparsers.add_parser("add", help="Add a new context")
    add_parser.add_argument("name", help="Context name")
    add_parser.add_argument(
        "--server",
        default=os.environ.get("GRAFANA_SERVER"),
        required=not os.environ.get("GRAFANA_SERVER"),
        help="Grafana server URL (defaults to GRAFANA_SERVER env var)",
    )
    add_parser.add_argument(
        "--user",
        default=os.environ.get("GRAFANA_USER", "admin"),
        help="Grafana username (defaults to GRAFANA_USER env var or 'admin')",
    )
    add_parser.add_argument(
        "--password",
        default=os.environ.get("GRAFANA_PASSWORD"),
        required=not os.environ.get("GRAFANA_PASSWORD"),
        help="Grafana password (defaults to GRAFANA_PASSWORD env var)",
    )
    add_parser.add_argument(
        "--org-id",
        type=int,
        default=int(os.environ.get("GRAFANA_ORG_ID", "1")),
        help="Grafana organization ID (defaults to GRAFANA_ORG_ID env var or 1)",
    )
    add_parser.add_argument("--use-context", action="store_true", help="Set as current context")
    add_parser.set_defaults(func=config_add)

    # config list
    list_parser = config_subparsers.add_parser("list", help="List all contexts")
    list_parser.set_defaults(func=config_list)

    # config use
    use_parser = config_subparsers.add_parser("use", help="Switch to a context")
    use_parser.add_argument("name", help="Context name")
    use_parser.set_defaults(func=config_use)

    # config show
    show_parser = config_subparsers.add_parser("show", help="Show context details")
    show_parser.add_argument("name", nargs="?", help="Context name (defaults to current)")
    show_parser.set_defaults(func=config_show)

    # config delete
    delete_parser = config_subparsers.add_parser("delete", help="Delete a context")
    delete_parser.add_argument("name", help="Context name")
    delete_parser.set_defaults(func=config_delete)

    # config set
    set_parser = config_subparsers.add_parser("set", help="Set a config value")
    set_parser.add_argument("key", help="Config key (e.g., contexts.myproject-1.grafana.server)")
    set_parser.add_argument("value", help="Config value")
    set_parser.set_defaults(func=config_set)

    # config check
    check_parser = config_subparsers.add_parser("check", help="Check config file location")
    check_parser.set_defaults(func=config_check)

    # Upload subcommand
    upload_parser = subparsers.add_parser("upload", help="Upload dashboards to Grafana")
    add_dashboard_dir_arg(upload_parser)
    add_grafana_context_arg(upload_parser)
    upload_parser.set_defaults(func=upload_dashboards)

    # Download subcommand
    download_parser = subparsers.add_parser("download", help="Download dashboards from Grafana")
    add_dashboard_dir_arg(download_parser)
    add_grafana_context_arg(download_parser)
    download_parser.set_defaults(func=download_dashboards)

    # Extract subcommand
    extract_parser = subparsers.add_parser("extract", help="Extract external content from dashboard JSON")
    extract_parser.add_argument("json_file", type=Path, help="Path to the Grafana dashboard JSON file")
    extract_parser.add_argument(
        "--base-dir",
        type=Path,
        help="Base input directory to detect subdirectory structure to preserve in output",
    )
    add_dashboard_dir_arg(extract_parser)
    extract_parser.set_defaults(func=extract_external_content)

    args = parser.parse_args()

    # Call the function associated with the selected command
    args.func(args)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Upload Grafana dashboards from Jsonnet templates to Grafana via Terraform."""

import json
import os
import subprocess
import sys
from pathlib import Path
from python_terraform import Terraform

from .utils import get_workspace, get_terraform_dir


def build_jsonnet_dashboards(dashboards_base_dir: Path) -> None:
    """
    Build all Jsonnet dashboard files to JSON.

    Args:
        dashboards_base_dir: Base directory containing the dashboards
    """
    src_dir = dashboards_base_dir / "src"

    # Find all .jsonnet files
    jsonnet_files = list(src_dir.glob("**/*.jsonnet"))

    if not jsonnet_files:
        print(f"No .jsonnet files found in {src_dir}")
        return

    for dashboard_file in jsonnet_files:
        print(f"Building {dashboard_file}")

        # Get the relative path from src directory
        rel_path = dashboard_file.relative_to(src_dir)

        # Create corresponding build directory
        build_path = dashboards_base_dir / "build" / rel_path.parent
        build_path.mkdir(parents=True, exist_ok=True)

        # Output JSON file path
        output_file = build_path / f"{dashboard_file.stem}.json"

        # Build jsonnet to JSON using jsonnet command
        try:
            # Run jsonnet command
            result = subprocess.run(
                ["jsonnet", str(dashboard_file)],
                capture_output=True,
                text=True,
                check=True
            )

            # Parse and pretty-print the JSON
            json_data = json.loads(result.stdout)
            with open(output_file, 'w') as f:
                json.dump(json_data, f, indent=2)

        except subprocess.CalledProcessError as e:
            print(f"Error building {dashboard_file}: {e.stderr}")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON from {dashboard_file}: {e}")
            sys.exit(1)


def main():
    """Main entry point for uploading dashboards."""
    # Get terraform directory
    terraform_dir = get_terraform_dir()

    # Get or prompt for workspace
    workspace = get_workspace()

    # Initialize Terraform
    tf = Terraform(working_dir=str(terraform_dir))

    # Select or create workspace
    print(f"Selecting workspace: {workspace}")
    return_code, stdout, stderr = tf.workspace("select", "-or-create=true", workspace)
    if return_code != 0:
        print(f"Error selecting workspace: {stderr}")
        sys.exit(1)

    # Get dashboards path from terraform output
    return_code, output, stderr = tf.output("dashboards_base_path")
    if return_code != 0:
        print(f"Error getting dashboards_base_path output: {stderr}")
        sys.exit(1)

    # Parse JSON output to get the value
    dashboards_base_path = json.loads(output)["dashboards_base_path"]["value"]
    dashboards_base_dir = Path(dashboards_base_path)
    print(f"Using dashboards directory: {dashboards_base_dir}")

    # Build all jsonnet files
    build_jsonnet_dashboards(dashboards_base_dir)

    # Apply terraform changes
    print("\nApplying Terraform configuration...")
    return_code, stdout, stderr = tf.apply(skip_plan=True, auto_approve=True)

    if return_code != 0:
        print(f"Error applying Terraform: {stderr}")
        sys.exit(1)

    print("\nDashboards uploaded successfully!")


if __name__ == "__main__":
    main()

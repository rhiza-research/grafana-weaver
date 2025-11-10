#!/usr/bin/env python3
"""Download Grafana dashboards and extract external content."""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from python_terraform import Terraform

from .utils import get_workspace, get_terraform_dir


def download_dashboards_from_grafana(tf: Terraform, downloaded_dir: Path) -> None:
    """
    Download dashboards from Grafana using Terraform.

    Args:
        tf: Terraform instance
        downloaded_dir: Directory to download dashboards to
    """
    print("\nStep 1: Downloading dashboards from Grafana...")
    print("Exporting dashboards to local files...")

    # Export dashboards (this only creates local files, doesn't touch Grafana)
    return_code, stdout, stderr = tf.apply(
        skip_plan=True,
        auto_approve=True,
        var={
            "dashboard_export_enabled": True,
            "dashboard_export_dir": str(downloaded_dir)
        }
    )

    if return_code != 0:
        print(f"Error exporting dashboards: {stderr}")
        sys.exit(1)


def process_dashboards(downloaded_dir: Path) -> None:
    """
    Process downloaded dashboards to extract external content.

    Args:
        downloaded_dir: Directory containing downloaded JSON files
    """
    print("\nStep 2: Processing dashboards to extract external content...")

    # Find all JSON files in the downloaded directory
    json_files = list(downloaded_dir.rglob("*.json"))

    if not json_files:
        print(f"No JSON files found in {downloaded_dir}")
        return

    # Get the extract script from the package
    extract_script = Path(__file__).parent / "extract_external_content.py"
    if not extract_script.exists():
        print(f"Error: extract_external_content.py not found at {extract_script}")
        sys.exit(1)

    for json_file in json_files:
        # Get the relative path from the downloaded directory
        rel_path = json_file.relative_to(downloaded_dir)
        base_dir = rel_path.parent if rel_path.parent != Path('.') else None

        print(f"Processing: {json_file}")

        # Run the extraction script
        cmd = [sys.executable, str(extract_script), str(json_file)]
        if base_dir:
            cmd.append(str(base_dir))

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"Error processing {json_file}:")
            print(result.stderr)
            sys.exit(1)

        # Print the output from the extraction script
        if result.stdout:
            print(result.stdout)


def main():
    """Main entry point for downloading dashboards."""
    # Get terraform directory
    terraform_dir = get_terraform_dir()

    # Create temporary directory for downloads
    downloaded_dir = Path(tempfile.mkdtemp())

    try:
        # Get or prompt for workspace
        workspace = get_workspace()

        print("=" * 42)
        print("Downloading Grafana dashboards...")
        print("=" * 42)

        # Initialize Terraform
        tf = Terraform(working_dir=str(terraform_dir))

        # Select or create workspace
        print(f"Selecting workspace: {workspace}")
        return_code, stdout, stderr = tf.workspace("select", "-or-create=true", workspace)
        if return_code != 0:
            print(f"Error selecting workspace: {stderr}")
            sys.exit(1)

        # Get dashboards path from terraform output
        return_code, dashboards_base_path, stderr = tf.output("dashboards_base_path")
        if return_code != 0:
            print(f"Error getting dashboards_base_path output: {stderr}")
            sys.exit(1)

        dashboards_base_dir = Path(dashboards_base_path)
        print(f"Using dashboards directory: {dashboards_base_dir}")

        # Download dashboards
        download_dashboards_from_grafana(tf, downloaded_dir)

        # Process dashboards to extract external content
        process_dashboards(downloaded_dir)

        print("\n" + "=" * 42)
        print("Dashboard download complete!")
        print("=" * 42)
        print(f"  - Downloaded to: {downloaded_dir}/")
        print(f"  - Jsonnet templates: {dashboards_base_dir}/src/")
        print(f"  - Assets: {dashboards_base_dir}/src/assets/")

    finally:
        # Clean up temporary directory
        if downloaded_dir.exists():
            shutil.rmtree(downloaded_dir)


if __name__ == "__main__":
    main()

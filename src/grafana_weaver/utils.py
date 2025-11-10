#!/usr/bin/env python3
"""
Shared utility functions for grafana-weaver.
"""

import os
import sys
from pathlib import Path


def get_workspace() -> str:
    """
    Get or prompt for the workspace name.

    Returns:
        str: The workspace name
    """
    workspace = os.environ.get("WORKSPACE")
    if not workspace:
        workspace = input("Enter the workspace name: ").strip()
        if not workspace:
            print("WORKSPACE is not set, exiting")
            sys.exit(1)
        os.environ["WORKSPACE"] = workspace
    print(f"WORKSPACE is set to {workspace}")
    return workspace


def get_terraform_dir() -> Path:
    """
    Get terraform directory from environment or default location.

    Returns:
        Path: The terraform directory path

    Raises:
        SystemExit: If terraform directory is not found
    """
    terraform_dir_str = os.environ.get("TERRAFORM_DIR")
    if terraform_dir_str:
        terraform_dir = Path(terraform_dir_str)
    else:
        # Default: look for infrastructure/terraform-config relative to current directory
        terraform_dir = Path.cwd() / "infrastructure" / "terraform-config"

    if not terraform_dir.exists():
        print(f"Error: Terraform directory not found: {terraform_dir}")
        print("Set TERRAFORM_DIR environment variable to specify the terraform directory")
        sys.exit(1)

    return terraform_dir

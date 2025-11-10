"""Tests for utils.py module."""

import pytest
from pathlib import Path

from grafana_weaver.utils import get_workspace, get_terraform_dir


class TestGetWorkspace:
    """Tests for get_workspace function."""

    def test_workspace_from_env(self, monkeypatch):
        """Workspace should be read from environment variable."""
        monkeypatch.setenv("WORKSPACE", "production")
        workspace = get_workspace()
        assert workspace == "production"

    def test_workspace_prompt(self, monkeypatch):
        """Workspace should be prompted if not in environment."""
        monkeypatch.delenv("WORKSPACE", raising=False)
        monkeypatch.setattr('builtins.input', lambda _: "dev")

        workspace = get_workspace()
        assert workspace == "dev"

    def test_empty_workspace_exits(self, monkeypatch):
        """Empty workspace should exit with error."""
        monkeypatch.delenv("WORKSPACE", raising=False)
        monkeypatch.setattr('builtins.input', lambda _: "")

        with pytest.raises(SystemExit) as exc_info:
            get_workspace()
        assert exc_info.value.code == 1


class TestGetTerraformDir:
    """Tests for get_terraform_dir function."""

    def test_terraform_dir_from_env(self, monkeypatch, tmp_path):
        """Terraform directory should be read from environment variable."""
        terraform_dir = tmp_path / "custom-terraform"
        terraform_dir.mkdir()
        monkeypatch.setenv("TERRAFORM_DIR", str(terraform_dir))

        result = get_terraform_dir()
        assert result == terraform_dir

    def test_terraform_dir_default_location(self, monkeypatch, tmp_path):
        """Terraform directory should use default location if env not set."""
        monkeypatch.delenv("TERRAFORM_DIR", raising=False)
        monkeypatch.chdir(tmp_path)

        # Create the default location
        default_dir = tmp_path / "infrastructure" / "terraform-config"
        default_dir.mkdir(parents=True)

        result = get_terraform_dir()
        assert result == default_dir

    def test_terraform_dir_not_found_exits(self, monkeypatch, tmp_path):
        """Should exit with error if terraform directory not found."""
        monkeypatch.delenv("TERRAFORM_DIR", raising=False)
        monkeypatch.chdir(tmp_path)

        with pytest.raises(SystemExit) as exc_info:
            get_terraform_dir()
        assert exc_info.value.code == 1

    def test_terraform_dir_env_not_found_exits(self, monkeypatch, tmp_path):
        """Should exit with error if env var points to nonexistent directory."""
        nonexistent_dir = tmp_path / "does-not-exist"
        monkeypatch.setenv("TERRAFORM_DIR", str(nonexistent_dir))

        with pytest.raises(SystemExit) as exc_info:
            get_terraform_dir()
        assert exc_info.value.code == 1

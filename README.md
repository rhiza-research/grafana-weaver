# Grafana-Weaver

[![Tests](https://github.com/rhiza-research/grafana-weaver/actions/workflows/test.yml/badge.svg)](https://github.com/rhiza-research/grafana-weaver/actions/workflows/test.yml)


A system for managing Grafana dashboards as code using Jsonnet, with support for extracting large content blocks (SQL queries, JavaScript, etc.) into separate asset files.

## Overview

This system allows you to:
1. **Download** dashboards from Grafana and convert them to Jsonnet templates with external assets
2. **Edit** dashboard configuration and assets as code
3. **Upload** changes back to Grafana via the Grafana API

## Installation

Grafana-Weaver is a pure Python project that can be run directly using `uvx` without installation:

```bash
# Download dashboards from Grafana
uvx --from git+https://github.com/rhiza-research/grafana-weaver download-dashboards

# Upload dashboards to Grafana
uvx --from git+https://github.com/rhiza-research/grafana-weaver upload-dashboards
```

Or if you have the repository locally:

```bash
# From the repository root
uvx --from . download-dashboards
uvx --from . upload-dashboards
```

Alternatively, you can install it with uv:

```bash
uv pip install git+https://github.com/rhiza-research/grafana-weaver
# Or from local directory
uv pip install .
```

## Workflow

### Download Dashboards from Grafana

Using uvx (no installation required):
```bash
GRAFANA_CONTEXT=myproject-1 DASHBOARD_DIR=./dashboards uvx --from . download-dashboards
```

Or if installed:
```bash
GRAFANA_CONTEXT=myproject-1 DASHBOARD_DIR=./dashboards download-dashboards
```

This script:
1. Reads credentials from your grafanactl config file
2. Downloads all dashboards from Grafana via the Grafana API (including folder structure)
3. Extracts external content (marked with `EXTERNAL`) into `./dashboards/src/assets/`
4. Generates Jsonnet templates in `./dashboards/src/`

### Upload Dashboards to Grafana

Using uvx (no installation required):
```bash
GRAFANA_CONTEXT=myproject-1 DASHBOARD_DIR=./dashboards uvx --from . upload-dashboards
```

Or if installed:
```bash
GRAFANA_CONTEXT=myproject-1 DASHBOARD_DIR=./dashboards upload-dashboards
```

This script:
1. Reads credentials from your grafanactl config file
2. Builds all `.jsonnet` files from `./dashboards/src/` into JSON
3. Uploads them to Grafana via the Grafana API

## External Content

Any content in a dashboard that starts with `EXTERNAL` on the first line will be extracted to a separate file. This is useful for:
- Long SQL queries
- JavaScript code for custom panels
- Markdown documentation
- Any large text blocks

### Usage Patterns

#### 1. Auto-generated filename
```javascript
// EXTERNAL
function myFunction() {
    return 'Hello World';
}
```
Creates: `assets/[dashboard-uid]-[panel-id]-[field-name].js`

#### 2. Custom filename
```javascript
// EXTERNAL:shared-utils.js
function sharedFunction() {
    return 'Shared across panels';
}
```
Creates: `assets/shared-utils.js`

#### 3. Custom filename with parameters
```javascript
// EXTERNAL({panel_id: "shared", key: "utils"})
function utilities() {
    return 'Organized content';
}
```
Creates: `assets/[dashboard-uid]-shared-utils.js`

### Supported Comment Syntaxes

The `EXTERNAL` tag works with any comment syntax:

- **JavaScript/TypeScript**: `// EXTERNAL`
- **Python**: `# EXTERNAL`
- **SQL**: `-- EXTERNAL`
- **HTML**: `<!-- EXTERNAL -->`
- **Markdown**: `[comment]: # (EXTERNAL)`
- **CSS**: `/* EXTERNAL */`

### Parameters

Override parts of the auto-generated filename:

- `dashboard_id`: Override dashboard UID in filename
- `panel_id`: Override panel ID in filename
- `key`: Override field name in filename
- `ext`: Override file extension (e.g., `"js"`, `"sql"`)

Example:
```sql
-- EXTERNAL({dashboard_id: "metrics", key: "query", ext: "sql"})
SELECT * FROM metrics WHERE date > NOW() - INTERVAL '7 days'
```

## Folder Structure

```
grafana-weaver/
├── pyproject.toml              # Python project configuration
├── src/
│   └── grafana_weaver/
│       ├── __init__.py
│       ├── download_dashboards.py  # Download from Grafana
│       ├── upload_dashboards.py    # Upload to Grafana
│       └── extract_external_content.py  # Extract EXTERNAL content
└── terraform_module/           # Terraform module for Grafana

../dashboards/
├── src/
│   ├── assets/                 # Extracted content files
│   │   ├── dashboard-uid-panel-id-script.js
│   │   ├── shared-query.sql
│   │   └── ...
│   ├── some-folder/            # Example: dashboards in Grafana folders
│   │   └── dashboard.jsonnet
│   └── dashboard.jsonnet       # Main dashboard templates
└── build/
    ├── some-folder/
    │   └── dashboard.json
    └── dashboard.json          # Built JSON files (generated)
```

## Configuration

Grafana-Weaver uses a config file in the [grafanactl](https://github.com/grafana/grafana-cli) format for Grafana credentials. You don't need to have grafanactl installed - just create the config file with your Grafana server details.

### Environment Variables

- `GRAFANA_CONTEXT` - The grafanactl context name (e.g., `myproject-1`)
- `DASHBOARD_DIR` - Path to the dashboards directory (defaults to `./dashboards`)

### Config File

The tool reads Grafana server URL and credentials from a YAML config file (in grafanactl format), which is located at one of:
- `$XDG_CONFIG_HOME/grafanactl/config.yaml`
- `$HOME/.config/grafanactl/config.yaml`
- `$XDG_CONFIG_DIRS/grafanactl/config.yaml`

Example config:
```yaml
contexts:
  myproject-1:
    grafana:
      server: https://grafana.example.com
      user: admin
      password: secret123
      org-id: 1
current-context: myproject-1
```

The `GRAFANA_CONTEXT` environment variable should match a context name in your config file.

### Terraform Integration

Use the Terraform module at `terraform_module/` to integrate grafana-weaver with Terraform:

```hcl
module "grafana_weaver" {
  source = "git::https://github.com/rhiza-research/grafana-weaver.git//terraform_module"

  repo_name            = "myproject"
  pr_number            = "1"
  grafana_url          = "https://grafana.example.com"
  grafana_user = "admin"
  grafana_password = "password"
  grafana_org_id = 1
  dashboards_base_path = "./dashboards"
  dashboard_download_enabled = true
  dashboard_upload_enabled = true
}
```

The module handles:
- Writing the grafanactl config file
- Merging contexts for multiple PRs/repos
- Running upload operations

See [terraform_module/README.md](terraform_module/README.md) for full documentation.

## Conflict Detection

When multiple panels reference the same external file with different content:

1. **First write wins** - The first panel's content is saved to the main file
2. **Conflicts are saved** - Subsequent different content is saved as `.conflict1`, `.conflict2`, etc.
3. **Same content is skipped** - If content matches, no conflict is created

Example output:
```
Processing panel 1: Creating shared-content.txt
Processing panel 2: WARNING: Conflict detected for shared-content.txt
                    Saving to shared-content.txt.conflict1
Processing panel 3: Skipping shared-content.txt (same content as first panel)
```

This allows you to see that there was a conflict and saves the conflicting content for review. You can then decide to delete or replace the original file with the conflicting content.

## Round-trip Editing

The system supports full round-trip editing:

1. Create/edit dashboard in Grafana UI
2. Add `EXTERNAL` tags to content you want as separate files
3. Download to get Jsonnet + assets
4. Edit assets locally and view diffs in git
5. Upload changes back to Grafana
6. Repeat

This makes dashboard development natural while keeping large content blocks maintainable in version control.

## Implementation Details

- **Grafana API** manages dashboard deployment via direct API calls
- **Jsonnet** provides templating and imports for dashboards
- **Python** handles EXTERNAL content extraction with hash-based change detection and orchestrates the download/upload workflow

## Requirements

- Python 3.9 or higher
- [uv](https://docs.astral.sh/uv/) (for running with uvx)
- A config file (in grafanactl format) with your Grafana credentials

All Python dependencies (including jsonnet) are automatically managed by uv when using uvx.

## Development

### Running Tests

This project uses pytest for testing. With uv, you can run tests without manual dependency installation:

```bash
# Run all tests with uv (installs deps automatically)
uv run pytest

# Run tests with coverage report
uv run pytest --cov=grafana_weaver --cov-report=html

# Run specific test file
uv run pytest tests/test_extract_external_content.py

# Run specific test
uv run pytest tests/test_extract_external_content.py::TestComputeContentHash::test_same_content_same_hash

# Run with verbose output
uv run pytest -v
```

Or install in development mode:

```bash
# Install with development dependencies
uv pip install -e ".[dev]"

# Then run tests directly
pytest
```

The test suite includes:
- Unit tests for all core functions
- Integration tests for main workflows
- Test fixtures for sample Grafana dashboards
- Mock objects for Grafana API and external dependencies

Coverage reports are generated in `htmlcov/` directory.

### Project Structure

```
tests/
├── conftest.py                          # Shared fixtures
├── fixtures/                            # Sample data files
│   ├── sample_dashboard.json
│   ├── sample_dashboard_with_params.json
│   └── sample_dashboard_concat.json
├── test_extract_external_content.py     # Tests for extraction logic
├── test_upload_dashboards.py            # Tests for upload workflow
├── test_download_dashboards.py          # Tests for download workflow
└── test_utils.py                        # Tests for utility functions
```

### Code Quality

This project uses [Ruff](https://github.com/astral-sh/ruff) for both linting and formatting.

**Linting:**
```bash
# Check for linting issues
uv run ruff check src/ tests/

# Auto-fix linting issues
uv run ruff check --fix src/ tests/
```

**Formatting:**
```bash
# Format code
uv run ruff format src/ tests/

# Check formatting without making changes
uv run ruff format --check src/ tests/
```

**Run both:**
```bash
# Lint and format in one go
uv run ruff check --fix src/ tests/ && uv run ruff format src/ tests/
```

**Configuration:**
- Line length: 120 characters
- Enabled rules: pycodestyle, pyflakes, isort, pep8-naming, pyupgrade, flake8-commas
- Trailing commas: Automatically added to multi-line collections

See `[tool.ruff]` section in `pyproject.toml` for full configuration.

### Dependencies

The project has minimal dependencies:
- `requests` - For Grafana API calls
- `pyyaml` - For reading grafanactl config files
- `jsonnet` - For compiling jsonnet templates to JSON

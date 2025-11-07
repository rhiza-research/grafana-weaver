# Grafana-Weaver

A system for managing Grafana dashboards as code using Jsonnet, with support for extracting large content blocks (SQL queries, JavaScript, etc.) into separate asset files.

## Overview

This system allows you to:
1. **Download** dashboards from Grafana and convert them to Jsonnet templates with external assets
2. **Edit** dashboard configuration and assets as code
3. **Upload** changes back to Grafana via Terraform

## Workflow

### Download Dashboards from Grafana

```bash
./download-dashboards.sh
```

This script:
1. Exports all dashboards from Grafana (including folder structure)
2. Extracts external content (marked with `EXTERNAL`) into `../dashboards/src/assets/`
3. Generates Jsonnet templates in `../dashboards/src/`

### Upload Dashboards to Grafana

```bash
./upload-dashboards.sh
```

This script:
1. Builds all `.jsonnet` files from `../dashboards/src/` into JSON
2. Applies them to Grafana via Terraform

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
├── download-dashboards.sh      # Download from Grafana
├── upload-dashboards.sh        # Upload to Grafana
├── extract_external_content.py # Python script for extracting EXTERNAL content
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

In your terraform configuration that uses this module, define the dashboard location in your `terraform.tfvars`:

```hcl
dashboards_base_path = "../../dashboards"  # Path relative to your terraform config
```

This tells the module where to find your dashboard source files. The scripts will read this value to determine where to write downloaded dashboards and read dashboards for upload.

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

- **Terraform** manages dashboard deployment and folder structure
- **Jsonnet** provides templating and imports for dashboards
- **Python** handles EXTERNAL content extraction with hash-based change detection
- **Bash scripts** orchestrate the download/upload workflow

## Requirements

- Python 3
- Terraform
- Jsonnet
- jq

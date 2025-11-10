# Grafana-Weaver Terraform Module

This Terraform module manages grafanactl configuration and runs grafana-weaver Python scripts for downloading and uploading Grafana dashboards.

## Features

- Creates/updates `~/.config/grafanactl/config.yaml` with Grafana credentials
- Merges contexts without clobbering configurations from other PRs/repos
- Runs grafana-weaver upload operations using Python scripts
- Suitable for ephemeral Grafana instances in CI/CD
- Dynamic context names based on `repo-pr#` pattern

## Usage


### Upload Dashboards

```hcl
module "grafana_upload" {
  source = "git::https://github.com/rhiza-research/grafana-weaver.git//terraform_module"

  repo_name            = "myproject"
  pr_number            = "1"
  grafana_url          = "https://grafana.example.com"
  grafana_user         = "admin"
  grafana_password     = "password"
  dashboard_upload_enabled = true
  grafana_org_id = 1
  dashboards_base_path = "./dashboards"
}
```

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| repo_name | Repository name (e.g., 'myproject') | `string` | n/a | yes |
| pr_number | PR number for this ephemeral instance | `string` | n/a | yes |
| grafana_url | Grafana server URL | `string` | n/a | yes |
| grafana_password | Grafana password | `string` | n/a | yes |
| grafana_user | Grafana username | `string` | `"admin"` | no |
| grafana_org_id | Grafana organization ID | `number` | `1` | no |
| dashboards_base_path | Base path for dashboards directory | `string` | `"./dashboards"` | no |
| dashboard_download_enabled | Enable dashboard download from Grafana | `bool` | `false` | no |
## Outputs

| Name | Description |
|------|-------------|
| context_name | The grafanactl context name (e.g., 'myproject-1') |
| config_path | Path to the grafanactl config file |

## Multi-Tenant Support

This module works with multiple PRs/repos running in parallel. Each adds its own context (e.g., `myproject-24`) without removing others.

## Requirements

- Terraform >= 1.0
- `uv` installed where Terraform runs
- Network access to Grafana and GitHub

## Example for Arcus

```hcl
module "grafana_weaver" {
  source = "git::https://github.com/rhiza-research/grafana-weaver.git//terraform_module"

  repo_name            = "myproject"
  pr_number            = var.pr_number
  grafana_url          = "https://grafana.pr-${var.pr_number}.myproject.example.com"
  grafana_password     = var.grafana_password
  dashboard_download_enabled = true
}
```

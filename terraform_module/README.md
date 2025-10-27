# Dynamic Grafana Dashboard and Folder Configuration

This terraform module is used to configure the Grafana dashboards and folders for the dynamic-dash project.

It is used to upload and download dashboards from Grafana.

## Usage

### Upload Dashboards to Grafana
Set the variable when applying:

```bash
terraform apply -var="dashboard_export_enabled=true"
```

### Download Dashboards from Grafana
Set the variable when applying:

```bash
terraform apply -var="dashboard_import_enabled=true"
```

# this is a module so it must be imported into a terraform configuration file.
# here is a minimal example of how to import the module:
```hcl

provider "grafana" {
  url = "https://grafana.example.com"
  auth = "admin:password"
}

resource "grafana_organization" "org" {
  name = "My Organization"
  admin_user = "admin"
  create_users = true
}

resource "grafana_data_source" "postgres" {
  name = "grafana-postgresql-datasource"
  type = "postgres"
  url = "postgres:5432"
  user = "postgres"
  password = "postgres"
  database = "postgres"
  port = 5432
  ssl_mode = "disable"
  secure_json_data = {
    password = "postgres"
  }
}

module "dynamic-dash" {
  source = "./terraform_module"
  dashboard_export_enabled = var.dashboard_export_enabled
  dashboard_import_enabled = var.dashboard_import_enabled
  org_id = grafana_organization.org.id
  dashboards_base_path = "./dashboards"
  datasource_config = {
    "grafana-postgresql-datasource" = grafana_data_source.postgres.uid
  }
  repo_name = "sheerwater-benchmarking"
  pr_number = "87"
}
```

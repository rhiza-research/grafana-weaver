# Export Grafana dashboards to JSON files

# Fetch all dashboards (only when export is enabled)
data "grafana_dashboards" "export" {
  count = var.dashboard_export_enabled ? 1 : 0

  org_id = var.org_id
  depends_on = [grafana_dashboard.dashboards]
}

# Fetch full JSON for each dashboard
data "grafana_dashboard" "export" {
  for_each = var.dashboard_export_enabled ? toset([for d in data.grafana_dashboards.export[0].dashboards : d.uid]) : toset([])

  uid = each.key
  org_id = var.org_id

  depends_on = [data.grafana_dashboards.export]
}

# Helper function to sanitize folder/dashboard names for file paths
locals {
  # Sanitize a name: lowercase, replace non-alphanumeric with dash, trim dashes
  sanitize_name = {
    for name in distinct(concat(
      # Dashboard titles
      [for d in try(data.grafana_dashboard.export, {}) : jsondecode(d.config_json).title],
      # Folder titles (get from grafana_dashboards data source)
      var.dashboard_export_enabled ? [for d in data.grafana_dashboards.export[0].dashboards : d.folder_title if d.folder_title != null && d.folder_title != ""] : []
    )) : name => replace(replace(replace(lower(name), " ", "-"), "/[^a-z0-9-]+/", "-"), "/^-+|-+$/", "")
  }

  # Map dashboard UIDs to folder titles from the dashboards data source
  dashboard_folders = var.dashboard_export_enabled ? {
    for d in data.grafana_dashboards.export[0].dashboards : d.uid => d.folder_title
  } : {}

  # Build the export structure
  exported_dashboards = var.dashboard_export_enabled ? {
    for uid, dashboard in data.grafana_dashboard.export : uid => {
      config_json = dashboard.config_json
      title = jsondecode(dashboard.config_json).title
      folder_title = local.dashboard_folders[uid]
      # Build file path with optional folder prefix
      file_path = local.dashboard_folders[uid] != null && local.dashboard_folders[uid] != "" ? (
        "${local.sanitize_name[local.dashboard_folders[uid]]}/${local.sanitize_name[jsondecode(dashboard.config_json).title]}.json"
        ) : (
        "${local.sanitize_name[jsondecode(dashboard.config_json).title]}.json"
      )
    }
  } : {}
}

# Write dashboard JSON files (with folder structure)
resource "local_file" "exported_dashboard_json" {
  for_each = var.dashboard_export_enabled ? local.exported_dashboards : {}

  filename = "${var.dashboard_export_dir}/${each.value.file_path}"
  content = each.value.config_json
  file_permission = "0644"
}

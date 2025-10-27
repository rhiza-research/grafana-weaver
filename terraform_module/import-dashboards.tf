########################################################
# Dynamic Grafana Dashboard and Folder Configuration
#
# This file dynamically creates folders and dashboards based on
# the directory structure in var.dashboards_base_path
#
# Folder naming convention: {slug}
# Dashboards in folders will be placed in those folders
# Dashboards at root level stay at root
########################################################

# Get directories using external data source
data "external" "folder_detection" {
  count = var.dashboard_import_enabled ? 1 : 0
  program = ["sh", "-c", "echo '{\"dirs\":\"'$(find ${var.dashboards_base_path} -maxdepth 1 -mindepth 1 -type d -exec basename {} \\; | tr '\n' ',' | sed 's/,$//')'\"}' "]
}

locals {

  # Parse folder directories from external data
  folder_dirs_raw = data.external.folder_detection.result.dirs != "" ? split(",", data.external.folder_detection.result.dirs) : []
  folder_dirs = toset([for dir in local.folder_dirs_raw : dir if dir != ""])

  # Parse folder information from directory names
  folders = {
    for dir in local.folder_dirs : dir => {
      uid = substr(sha256(dir), 0, 14)
      slug = dir
      title = title(dir)
      path = "${var.dashboards_base_path}/${dir}"
    }
  }

  # Get all dashboard JSON files from root level
  root_dashboard_files = toset([
    for file in fileset(var.dashboards_base_path, "*.json") :
    file
  ])

  # Get all dashboard JSON files from folders
  folder_dashboard_files = merge([
    for folder_dir, folder_info in local.folders : {
      for file in fileset(folder_info.path, "*.json") :
      "${folder_dir}/${file}" => {
        file = file
        folder_uid = folder_info.uid
        folder_dir = folder_dir
        full_path = "${folder_info.path}/${file}"
      }
    }
  ]...)

  # Parse all dashboards and key by UID
  all_dashboard_files = merge(
    # Root level dashboards
    {
      for file in local.root_dashboard_files :
      jsondecode(file("${var.dashboards_base_path}/${file}")).uid => {
        path = "${var.dashboards_base_path}/${file}"
        folder_uid = null
        json = jsondecode(file("${var.dashboards_base_path}/${file}"))
      }
      if can(jsondecode(file("${var.dashboards_base_path}/${file}")).uid)
    },
    # Folder dashboards
    {
      for key, info in local.folder_dashboard_files :
      jsondecode(file(info.full_path)).uid => {
        path = info.full_path
        folder_uid = info.folder_uid
        json = jsondecode(file(info.full_path))
      }
      if can(jsondecode(file(info.full_path)).uid)
    }
  )
}

# Create folders dynamically based on directory structure
resource "grafana_folder" "folders" {
  count = var.dashboard_import_enabled ? 1 : 0
  for_each = local.folders
  uid = each.value.uid
  title = each.value.title
  org_id = var.org_id
}

# Create dashboards dynamically, placing them in folders as needed
resource "grafana_dashboard" "dashboards" {
  count = var.dashboard_import_enabled ? 1 : 0
  for_each = local.all_dashboard_files

  config_json = jsonencode(merge(
    each.value.json
  ))

  folder = each.value.folder_uid

  message = "Modified by terraform from https://github.com/rhiza-research/${var.repo_name}/pull/${var.pr_number}"

  overwrite = true
  org_id = var.org_id

  depends_on = [
    grafana_folder.folders,
  ]
}

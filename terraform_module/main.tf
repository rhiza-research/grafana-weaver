terraform {
  required_version = ">= 1.5.7"
}

# Variables for the grafanactl context
locals {
  context_name = "${var.repo_name}-${var.pr_number}"
}

# Read existing grafanactl config if it exists
data "local_file" "existing_grafanactl_config" {
  filename = pathexpand("~/.config/grafanactl/config.yaml")
  count    = fileexists(pathexpand("~/.config/grafanactl/config.yaml")) ? 1 : 0
}

locals {
  # Parse existing config or start with empty
  existing_config = length(data.local_file.existing_grafanactl_config) > 0 ? yamldecode(data.local_file.existing_grafanactl_config[0].content) : { contexts = {} }

  # Merge in the new context for this PR/repo
  merged_contexts = merge(
    lookup(local.existing_config, "contexts", {}),
    {
      "${local.context_name}" = {
        grafana = {
          server   = var.grafana_url
          user     = var.grafana_user
          password = var.grafana_password
          org-id   = var.grafana_org_id
        }
      }
    }
  )
}

# Create config directory if it doesn't exist
resource "null_resource" "create_config_dir" {
  provisioner "local-exec" {
    command = "mkdir -p ~/.config/grafanactl"
  }
}

# Write merged config back
resource "local_file" "grafanactl_config" {
  depends_on = [null_resource.create_config_dir]

  content = yamlencode({
    contexts        = local.merged_contexts
    current-context = local.context_name
  })
  filename        = pathexpand("~/.config/grafanactl/config.yaml")
  file_permission = "0600"
}

# I don't think we need to download dashboards via terraform now.
# # Download dashboards from Grafana
# resource "null_resource" "download_dashboards" {
#   count = var.dashboard_download_enabled ? 1 : 0

#   depends_on = [local_file.grafanactl_config]

#   provisioner "local-exec" {
#     command = "uvx --from git+https://github.com/rhiza-research/grafana-weaver download-dashboards"
#     environment = {
#       GRAFANA_CONTEXT = local.context_name
#       DASHBOARD_DIR   = var.dashboards_base_path
#     }
#   }

#   triggers = {
#     config_hash = sha256(local_file.grafanactl_config.content)
#     always_run  = timestamp()
#   }
# }

# Upload dashboards to Grafana
resource "null_resource" "upload_dashboards" {
  count = var.dashboard_upload_enabled ? 1 : 0

  depends_on = [local_file.grafanactl_config]

  provisioner "local-exec" {
    command = "uvx --from git+https://github.com/rhiza-research/grafana-weaver upload-dashboards"
    environment = {
      GRAFANA_CONTEXT = local.context_name
      DASHBOARD_DIR   = var.dashboards_base_path
    }
  }

  triggers = {
    config_hash = sha256(local_file.grafanactl_config.content)
    always_run  = timestamp()
  }
}

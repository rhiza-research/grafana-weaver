variable "repo_name" {
  description = "Repository name"
  type        = string
}

variable "pr_number" {
  description = "PR number for this ephemeral instance"
  type        = string
}

variable "grafana_url" {
  description = "Grafana server URL"
  type        = string
}

variable "grafana_user" {
  description = "Grafana username"
  type        = string
  default     = "admin"
}

variable "grafana_password" {
  description = "Grafana password"
  type        = string
  sensitive   = true
}

variable "grafana_org_id" {
  description = "Grafana organization ID"
  type        = number
  default     = 1
}

variable "dashboards_base_path" {
  description = "Base path for dashboards directory"
  type        = string
  default     = "./dashboards"
}

# variable "dashboard_download_enabled" {
#   description = "Enable dashboard download from Grafana"
#   type        = bool
#   default     = false
# }

variable "dashboard_upload_enabled" {
  description = "Enable dashboard upload to Grafana"
  type        = bool
  default     = false
}

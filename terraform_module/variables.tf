variable "dashboard_export_enabled" {
  description = "Enable dashboard export to local files"
  type = bool
  default = false
}

variable "dashboard_export_dir" {
  description = "Directory to export dashboards to (absolute path)"
  type = string
  default = "/tmp/exported-dashboards"
}


# variable "grafana_url" {
#   description = "The url of the Grafana instance"
#   type = string
# }

# variable "grafana_auth" {
#   description = "The auth token for the Grafana instance"
#   type = string
# }

variable "org_id" {
  description = "The id of the Grafana organization"
  type = number
  default = 1
}

variable "dashboards_base_path" {
  description = "The base path of the dashboards to upload to Grafana"
  type = string
  default = "../../dashboards/"
}

# these are only used for the dashboard message, nothing critical.
variable "repo_name" {
  description = "The name of the git repository (only used for the dashboard message)"
  type = string
  default = ""
}

variable "pr_number" {
  description = "The number of the pull request (only used for the dashboard message)"
  type = string
  default = ""
}
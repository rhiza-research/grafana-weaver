output "context_name" {
  description = "The grafanactl context name that was configured"
  value       = local.context_name
}

output "config_path" {
  description = "Path to the grafanactl config file"
  value       = local_file.grafanactl_config.filename
}

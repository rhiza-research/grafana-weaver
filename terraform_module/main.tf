terraform {
  required_version = ">= 1.5.7"
  required_providers {
    google = {
      source = "hashicorp/google"
      version = "6.45.0"
    }

    grafana = {
      source = "grafana/grafana"
      version = "4.5.1"
    }

    external = {
      source = "hashicorp/external"
      version = "~> 2.0"
    }

    local = {
      source = "hashicorp/local"
      version = "~> 2.0"
    }
  }
}

resource "local_file" "datasource_config" {
  content = jsonencode(var.datasource_config)
  filename = "${var.dashboards_base_path}/datasource_config.json"
}

#!/bin/bash
# Sync dashboards from Grafana and extract external content
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TERRAFORM_DIR="$SCRIPT_DIR/../infrastructure/terraform-config"

DOWNLOADED_DASHBOARDS_DIR=$(mktemp -d)

# TODO: make this dynamic
WORKSPACE="grafana-pr-87"

echo "=========================================="
echo "Downloading Grafana dashboards..."
echo "=========================================="

# Download dashboards using Terraform
echo ""
echo "Step 1: Downloading dashboards from Grafana..."
cd "$TERRAFORM_DIR"
terraform workspace select $WORKSPACE
terraform apply -var="dashboard_export_enabled=true" -var="dashboard_export_dir=$DOWNLOADED_DASHBOARDS_DIR" -auto-approve

# Extract external content from each dashboard
echo ""
echo "Step 2: Processing dashboards to extract external content..."
cd "$SCRIPT_DIR"
for json_file in $DOWNLOADED_DASHBOARDS_DIR/*.json; do
    if [ -f "$json_file" ]; then
        echo "Processing: $(basename "$json_file")"
        python3 extract_external_content.py "$json_file"
    fi
done

rm -rf $DOWNLOADED_DASHBOARDS_DIR

echo ""
echo "=========================================="
echo "Dashboard download complete!"
echo "=========================================="
echo "  - Downloaded to: $DOWNLOADED_DASHBOARDS_DIR/"
echo "  - Jsonnet templates: src/"
echo "  - Assets: src/assets/"

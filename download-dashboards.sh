#!/bin/bash
# Sync dashboards from Grafana and extract external content
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TERRAFORM_DIR="$SCRIPT_DIR/../infrastructure/terraform-config"

# note, this makes the script print the content of all dashboards every time it runs because the directory is empty
DOWNLOADED_DASHBOARDS_DIR=$(mktemp -d)

# check if WORKSPACE is set, if not ask the user to enter it
if [ -z "$WORKSPACE" ]; then
    read -p "Enter the workspace name: " WORKSPACE
    export WORKSPACE
    if [ -z "$WORKSPACE" ]; then
        echo "WORKSPACE is not set, exiting"
        exit 1
    fi
fi
echo "WORKSPACE is set to $WORKSPACE"

echo "=========================================="
echo "Downloading Grafana dashboards..."
echo "=========================================="

cd "$TERRAFORM_DIR"
terraform workspace select -or-create=true $WORKSPACE

# Get dashboards path from terraform config
DASHBOARDS_BASE_DIR=$(terraform output -raw dashboards_base_path)
echo "Using dashboards directory: $DASHBOARDS_BASE_DIR"

# Download dashboards using Terraform
echo ""
echo "Step 1: Downloading dashboards from Grafana..."

# First refresh state without applying changes
#echo "Refreshing Terraform state..."
#terraform apply -refresh-only -var="dashboard_export_enabled=false" -var="dashboard_export_dir=$DOWNLOADED_DASHBOARDS_DIR" -auto-approve

# Then export dashboards (this only creates local files, doesn't touch Grafana)
echo "Exporting dashboards to local files..."
terraform apply -var="dashboard_export_enabled=true" -var="dashboard_export_dir=$DOWNLOADED_DASHBOARDS_DIR" -auto-approve


# Extract external content from each dashboard
echo ""
echo "Step 2: Processing dashboards to extract external content..."
cd "$SCRIPT_DIR"
cd "$DOWNLOADED_DASHBOARDS_DIR"
find . -type f -name "*.json" | while read json_file; do
    # Remove leading ./ from find output
    json_file="${json_file#./}"
    echo "Processing: $json_file"
    python3 "$SCRIPT_DIR/extract_external_content.py" "$DOWNLOADED_DASHBOARDS_DIR/$json_file" "$(dirname "$json_file")"
done

rm -rf $DOWNLOADED_DASHBOARDS_DIR

echo ""
echo "=========================================="
echo "Dashboard download complete!"
echo "=========================================="
echo "  - Downloaded to: $DOWNLOADED_DASHBOARDS_DIR/"
echo "  - Jsonnet templates: $DASHBOARDS_BASE_DIR/src/"
echo "  - Assets: $DASHBOARDS_BASE_DIR/src/assets/"

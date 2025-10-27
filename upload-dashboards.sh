#!/usr/bin/env bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

TERRAFORM_DIR="$SCRIPT_DIR/../infrastructure/terraform-config"
# TODO: make this dynamic
WORKSPACE="grafana-pr-24"

cd $TERRAFORM_DIR
terraform workspace select -or-create=true $WORKSPACE

# Get dashboards path from terraform config
DASHBOARDS_BASE_DIR=$(terraform output -raw dashboards_base_path)
echo "Using dashboards directory: $DASHBOARDS_BASE_DIR"

for dashboard in $(find $DASHBOARDS_BASE_DIR/src -type f -name '*.jsonnet'); do
    echo "Building $dashboard"
    
    # remove jsonnet from the extension without losing the folder structure
    dashboard_folder=$(dirname $dashboard)

    # replace src with build
    dashboard_folder=$(echo $dashboard_folder | sed 's|src|build|')

    mkdir -p $dashboard_folder
    jsonnet $dashboard | jq > $dashboard_folder/$(basename $dashboard .jsonnet).json
done

cd $TERRAFORM_DIR
terraform apply -auto-approve
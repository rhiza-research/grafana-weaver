#!/usr/bin/env bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

TERRAFORM_DIR="$SCRIPT_DIR/../infrastructure/terraform-config"

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
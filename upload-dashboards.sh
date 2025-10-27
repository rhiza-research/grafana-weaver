#!/usr/bin/env bash

TERRAFORM_DIR="../infrastructure/terraform-config"
# TODO: make this dynamic
WORKSPACE="grafana-pr-87"


for dashboard in $(find src -type f -name '*.jsonnet'); do
    echo "Building $dashboard"
    
    # remove jsonnet from the extension without losing the folder structure
    dashboard_folder=$(dirname $dashboard)

    # replace src with build
    dashboard_folder=$(echo $dashboard_folder | sed 's|src|build|')

    mkdir -p $dashboard_folder
    jsonnet $dashboard | jq > $dashboard_folder/$(basename $dashboard .jsonnet).json
done

cd $TERRAFORM_DIR
terraform workspace select $WORKSPACE
terraform apply -auto-approve
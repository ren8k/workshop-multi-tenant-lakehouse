#!/bin/bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# EMR Steps Script for Spark Jobs
# This script submits multiple Spark jobs as steps to an EMR cluster

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/emr-config.conf"

# Load configuration
if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "Error: Configuration file not found at $CONFIG_FILE"
    exit 1
fi

source "$CONFIG_FILE"

# Configuration
CLUSTER_ID=""
S3_SCRIPT_LOCATION=""
REGION="$DEFAULT_REGION"
STEPS_TO_EXECUTE="ALL"

# Function to display usage
usage() {
    echo "Usage: $0 -c CLUSTER_ID -s S3_SCRIPT_LOCATION [-r REGION] [-f CONFIG_FILE] [-e STEPS]"
    echo "  -c CLUSTER_ID         EMR cluster ID"
    echo "  -s S3_SCRIPT_LOCATION S3 location where Spark scripts are stored (e.g., s3://bucket/scripts/)"
    echo "  -r REGION            AWS region (default: $DEFAULT_REGION)"
    echo "  -f CONFIG_FILE       Path to configuration file (default: ./emr-config.conf)"
    echo "  -e STEPS             Steps to execute (default: ALL)"
    echo ""
    echo "Available step options:"
    echo "  ALL                  Execute all steps"
    echo "  STANDARD_NETWORK     Execute standard tenant network step"
    echo "  STANDARD_AUTH        Execute standard tenant auth step"
    echo "  STANDARD_ENDPOINT    Execute standard tenant endpoint step"
    echo "  STANDARD_SOFTWARE    Execute standard tenant software step"
    echo "  PREMIUM_NETWORK      Execute premium tenant network step"
    echo "  PREMIUM_AUTH         Execute premium tenant auth step"
    echo "  PREMIUM_ENDPOINT     Execute premium tenant endpoint step"
    echo "  PREMIUM_SOFTWARE     Execute premium tenant software step"
    echo "  CVE                  Execute CVE step"
    echo "  THREAT               Execute threat intelligence step"
    echo ""
    echo "Multiple steps can be specified separated by commas (e.g., STANDARD_NETWORK,PREMIUM_NETWORK)"
    exit 1
}

# Parse command line arguments
while getopts "c:s:r:f:e:h" opt; do
    case $opt in
        c) CLUSTER_ID="$OPTARG" ;;
        s) S3_SCRIPT_LOCATION="$OPTARG" ;;
        r) REGION="$OPTARG" ;;
        f) CONFIG_FILE="$OPTARG"; source "$CONFIG_FILE" ;;
        e) STEPS_TO_EXECUTE="$OPTARG" ;;
        h) usage ;;
        *) usage ;;
    esac
done

# Validate required parameters
if [[ -z "$CLUSTER_ID" || -z "$S3_SCRIPT_LOCATION" ]]; then
    echo "Error: Missing required parameters"
    usage
fi

# Remove trailing slash from S3 location if present
S3_SCRIPT_LOCATION=${S3_SCRIPT_LOCATION%/}

echo "Starting EMR steps submission..."
echo "Cluster ID: $CLUSTER_ID"
echo "S3 Script Location: $S3_SCRIPT_LOCATION"
echo "Region: $REGION"
echo "Config File: $CONFIG_FILE"
echo "Steps to Execute: $STEPS_TO_EXECUTE"

# Function to check if a step should be executed
should_execute_step() {
    local step_name="$1"
    if [[ "$STEPS_TO_EXECUTE" == "ALL" ]]; then
        return 0
    fi
    
    # Convert comma-separated list to array and check if step is included
    IFS=',' read -ra STEPS_ARRAY <<< "$STEPS_TO_EXECUTE"
    for step in "${STEPS_ARRAY[@]}"; do
        if [[ "$step" == "$step_name" ]]; then
            return 0
        fi
    done
    return 1
}

# Function to submit a Spark job step
submit_spark_step() {
    local step_name="$1"
    local script_name="$2"
    local table_name="$3"
    local topic_name="$4"
    local database_name="$5"
    local checkpoint_location="$6"
    local display_name="$7"
    local tenant_required="$8"
    
    echo "Submitting Step: $display_name..."
    
    # Build arguments array
    local args=(
        "spark-submit"
        "--deploy-mode" "$SPARK_DEPLOY_MODE"
        "--packages" "$SPARK_PACKAGES"
        "--jars" "$SPARK_JARS"
        "$S3_SCRIPT_LOCATION/$script_name"
        "--catalog" "$CATALOG_NAME"
        "--database" "$database_name"
        "--table" "$table_name"
        "--bootstrap-servers" "$BOOTSTRAP_SERVERS"
        "--topic" "$topic_name"
        "--checkpoint-location" "$checkpoint_location"
        "--warehouse-location" "$WAREHOUSE_LOCATION"
    )
    
    # Add tenant-ids if required
    if [[ "$tenant_required" == "true" ]]; then
        args+=("--tenant-ids" "$TENANT_IDS")
    fi
    
    # Convert args array to JSON format
    local json_args=""
    for arg in "${args[@]}"; do
        if [[ -z "$json_args" ]]; then
            json_args="\"$arg\""
        else
            json_args="$json_args, \"$arg\""
        fi
    done
    
    # Submit the step
    aws emr add-steps \
        --cluster-id "$CLUSTER_ID" \
        --region "$REGION" \
        --steps "[
            {
                \"Name\": \"$display_name\",
                \"ActionOnFailure\": \"$ACTION_ON_FAILURE\",
                \"Jar\": \"$HADOOP_JAR\",
                \"Args\": [$json_args]
            }
        ]"
    sleep 20
}

# Submit standard tenant steps
TENANT_IDS="$STANDARD_TENANT_IDS"

if should_execute_step "STANDARD_NETWORK"; then
    submit_spark_step "network" "$NETWORK_SCRIPT" "$NETWORK_TABLE" "$NETWORK_TOPIC" "$S_DATABASE" "$NETWORK_CHECKPOINT" "$NETWORK_DISPLAY_NAME" "$NETWORK_TENANT_REQUIRED"
fi

if should_execute_step "STANDARD_AUTH"; then
    submit_spark_step "auth" "$AUTH_SCRIPT" "$AUTH_TABLE" "$AUTH_TOPIC" "$S_DATABASE" "$AUTH_CHECKPOINT" "$AUTH_DISPLAY_NAME" "$AUTH_TENANT_REQUIRED"
fi

if should_execute_step "STANDARD_ENDPOINT"; then
    submit_spark_step "endpoint" "$ENDPOINT_SCRIPT" "$ENDPOINT_TABLE" "$ENDPOINT_TOPIC" "$S_DATABASE" "$ENDPOINT_CHECKPOINT" "$ENDPOINT_DISPLAY_NAME" "$ENDPOINT_TENANT_REQUIRED"
fi

if should_execute_step "STANDARD_SOFTWARE"; then
    submit_spark_step "software" "$SOFTWARE_SCRIPT" "$SOFTWARE_TABLE" "$SOFTWARE_TOPIC" "$S_DATABASE" "$SOFTWARE_CHECKPOINT" "$SOFTWARE_DISPLAY_NAME" "$SOFTWARE_TENANT_REQUIRED"
fi

# Check if any standard tenant steps were executed
if should_execute_step "STANDARD_NETWORK" || should_execute_step "STANDARD_AUTH" || should_execute_step "STANDARD_ENDPOINT" || should_execute_step "STANDARD_SOFTWARE"; then
    echo "Standard Tenant EMR steps have been submitted successfully!"
fi

TENANT_IDS="$PREMIUM_TENANT_IDS"

if should_execute_step "PREMIUM_NETWORK"; then
    submit_spark_step "network" "$NETWORK_SCRIPT" "$NETWORK_TABLE" "$P_NETWORK_TOPIC" "$P_DATABASE" "$P_NETWORK_CHECKPOINT" "$P_NETWORK_DISPLAY_NAME" "$NETWORK_TENANT_REQUIRED"
fi

if should_execute_step "PREMIUM_AUTH"; then
    submit_spark_step "auth" "$AUTH_SCRIPT" "$AUTH_TABLE" "$P_AUTH_TOPIC" "$P_DATABASE" "$P_AUTH_CHECKPOINT" "$P_AUTH_DISPLAY_NAME" "$AUTH_TENANT_REQUIRED"
fi

if should_execute_step "PREMIUM_ENDPOINT"; then
    submit_spark_step "endpoint" "$ENDPOINT_SCRIPT" "$ENDPOINT_TABLE" "$P_ENDPOINT_TOPIC" "$P_DATABASE" "$P_ENDPOINT_CHECKPOINT" "$P_ENDPOINT_DISPLAY_NAME" "$ENDPOINT_TENANT_REQUIRED"
fi

if should_execute_step "PREMIUM_SOFTWARE"; then
    submit_spark_step "software" "$SOFTWARE_SCRIPT" "$SOFTWARE_TABLE" "$P_SOFTWARE_TOPIC" "$P_DATABASE" "$P_SOFTWARE_CHECKPOINT" "$P_SOFTWARE_DISPLAY_NAME" "$SOFTWARE_TENANT_REQUIRED"
fi

# Check if any premium tenant steps were executed
if should_execute_step "PREMIUM_NETWORK" || should_execute_step "PREMIUM_AUTH" || should_execute_step "PREMIUM_ENDPOINT" || should_execute_step "PREMIUM_SOFTWARE"; then
    echo "Premium Tenant EMR steps have been submitted successfully!"
fi

if should_execute_step "CVE"; then
    submit_spark_step "cve" "$CVE_SCRIPT" "$CVE_TABLE" "$CVE_TOPIC" "$CVE_DATABASE" "$CVE_CHECKPOINT" "$CVE_DISPLAY_NAME" "$CVE_TENANT_REQUIRED"
fi

if should_execute_step "THREAT"; then
    submit_spark_step "threat" "$THREAT_SCRIPT" "$THREAT_TABLE" "$THREAT_TOPIC" "$THREAT_DATABASE" "$THREAT_CHECKPOINT" "$THREAT_DISPLAY_NAME" "$THREAT_TENANT_REQUIRED"
fi
sleep 20
echo "Requested EMR steps have been submitted successfully!"
echo "You can monitor the progress using:"
echo "aws emr describe-cluster --cluster-id $CLUSTER_ID --region $REGION"
echo "aws emr list-steps --cluster-id $CLUSTER_ID --region $REGION"
echo "aws emr describe-cluster --cluster-id $CLUSTER_ID --region $REGION"
echo "aws emr list-steps --cluster-id $CLUSTER_ID --region $REGION"
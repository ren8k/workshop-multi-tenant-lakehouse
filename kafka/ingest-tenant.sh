#!/bin/bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
set -e

# Check required environment variables
check_env_vars() {
    local vars=("TOPIC_AUTHENTICATION_LOGS" "TOPIC_ENDPOINT" "TOPIC_NETWORK_EVENTS" "TOPIC_INSTALLED_SOFTWARE" "TENANT_IDS" "COUNT" "BOOTSTRAP_SERVERS" "AWS_REGION")
    for var in "${vars[@]}"; do
        if [ -z "${!var}" ]; then
            echo "Error: Environment variable $var is not set"
            exit 1
        fi
        echo "$var=${!var}"
    done
}

# Function to run producer script with error handling
run_producer() {
    local script=$1
    local topic=$2
    local extra_args=$3
    
    echo "Starting $script for topic $topic..."
    if python3 $script --topic-name "$topic" --tenant-ids "$TENANT_IDS" --count "$COUNT" --broker "$BOOTSTRAP_SERVERS" --region "$AWS_REGION" $extra_args; then
        echo "✓ $script completed successfully"
    else
        echo "✗ $script failed with exit code $?"
        exit 1
    fi
}

# Check environment variables first
check_env_vars

# Run all producer scripts
run_producer "kafka-auth.py" "$TOPIC_AUTHENTICATION_LOGS" ""
run_producer "kafka-endpoint.py" "$TOPIC_ENDPOINT" "--first-run True"
run_producer "kafka-network.py" "$TOPIC_NETWORK_EVENTS" ""
run_producer "kafka-software.py" "$TOPIC_INSTALLED_SOFTWARE" ""

echo "All producer scripts completed successfully!"

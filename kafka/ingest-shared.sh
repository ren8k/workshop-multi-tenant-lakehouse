#!/bin/bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
set -e

# Check required environment variables
check_env_vars() {
    local vars=("TOPIC_CVE_INFO" "TOPIC_THREAT_INTELLIGENCE" "COUNT" "BOOTSTRAP_SERVERS" "AWS_REGION")
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
    if python3 $script --topic-name "$topic"  --count "$COUNT" --broker "$BOOTSTRAP_SERVERS" --region "$AWS_REGION" $extra_args; then
        echo "✓ $script completed successfully"
    else
        echo "✗ $script failed with exit code $?"
        exit 1
    fi
}

# Check environment variables first
check_env_vars

# Run all producer scripts
run_producer "kafka-cve-info.py" "$TOPIC_CVE_INFO" ""
run_producer "kafka-threat-intelligence.py" "$TOPIC_THREAT_INTELLIGENCE" ""

echo "All producer scripts completed successfully!"

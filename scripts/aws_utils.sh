#!/bin/bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# AWS Utilities - Shared functions for AWS operations

# Function to get AWS region with fallback logic
get_aws_region() {
    local region=""
    
    # Try AWS_REGION environment variable first
    if [ -n "${AWS_REGION:-}" ]; then
        region="$AWS_REGION"
    # Try AWS_DEFAULT_REGION environment variable
    elif [ -n "${AWS_DEFAULT_REGION:-}" ]; then
        region="$AWS_DEFAULT_REGION"
    # Try AWS CLI configuration
    else
        region=$(aws configure get region 2>/dev/null || echo "")
        if [ -z "$region" ]; then
            echo "Error: Could not determine AWS region. Please set AWS_REGION environment variable or configure AWS CLI default region." >&2
            return 1
        fi
    fi
    
    echo "$region"
}

# Function to get AWS account ID
get_aws_account_id() {
    aws sts get-caller-identity --query Account --output text 2>/dev/null || {
        echo "Error: Could not get AWS account ID. Please check your AWS credentials." >&2
        return 1
    }
}

# Function to validate AWS CLI is available and configured
validate_aws_cli() {
    command -v aws >/dev/null 2>&1 || {
        echo "Error: AWS CLI is required but not installed." >&2
        return 1
    }
    
    # Test AWS credentials by trying to get caller identity
    aws sts get-caller-identity >/dev/null 2>&1 || {
        echo "Error: AWS CLI is not configured or credentials are invalid." >&2
        return 1
    }
}

# Function to set up AWS environment variables
setup_aws_environment() {
    validate_aws_cli || return 1
    
    export AWS_ACCOUNT_ID
    AWS_ACCOUNT_ID=$(get_aws_account_id) || return 1
    
    export AWS_REGION
    AWS_REGION=$(get_aws_region) || return 1
    
    echo "AWS Account ID: ${AWS_ACCOUNT_ID}"
    echo "AWS Region: ${AWS_REGION}"
}
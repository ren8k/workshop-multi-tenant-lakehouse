#!/bin/bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# Build script for Multi-Tenant Security Analytics Backend

set -e

# Export AWS credentials from ~/.aws/credentials
# export AWS_ACCESS_KEY_ID=$(grep aws_access_key_id ~/.aws/credentials | cut -d'=' -f2 | xargs)
# export AWS_SECRET_ACCESS_KEY=$(grep aws_secret_access_key ~/.aws/credentials | cut -d'=' -f2 | xargs)
# export AWS_SESSION_TOKEN=$(grep aws_session_token ~/.aws/credentials | cut -d'=' -f2 | xargs)
export AWS_REGION=$(aws ec2 describe-availability-zones --output text --query 'AvailabilityZones[0].[RegionName]')
export AWS_DEFAULT_REGION=$AWS_REGION

echo "Installing and starting Docker..."
sudo dnf install -y docker
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -a -G docker $USER

echo "Cleaning previous build..."
sudo rm -rf .aws-sam/

echo "Building Lambda functions with SAM..."

# Build with SAM for ARM64 architecture (Graviton)
sudo sam build --use-container --build-image public.ecr.aws/sam/build-python3.11:latest-arm64

echo "✅ Build completed successfully!"
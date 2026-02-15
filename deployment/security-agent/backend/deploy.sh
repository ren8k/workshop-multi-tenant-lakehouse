#!/bin/bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# Deploy script for Multi-Tenant Security Analytics Backend

set -e

# Configuration Variables
REGION=$(aws ec2 describe-availability-zones --output text --query 'AvailabilityZones[0].[RegionName]')
STACK_NAME="security-analytics-backend"
TENANT_MGMT_STACK="LakehouseTenantUserManagementStack"

# Export AWS credentials from ~/.aws/credentials
# export AWS_ACCESS_KEY_ID=$(grep aws_access_key_id ~/.aws/credentials | cut -d'=' -f2 | xargs)
# export AWS_SECRET_ACCESS_KEY=$(grep aws_secret_access_key ~/.aws/credentials | cut -d'=' -f2 | xargs)
# export AWS_SESSION_TOKEN=$(grep aws_session_token ~/.aws/credentials | cut -d'=' -f2 | xargs)
export AWS_REGION=$REGION
export AWS_DEFAULT_REGION=$REGION

echo "Deploying Multi-Tenant Security Analytics Backend..."

# Check if build exists
if [ ! -d ".aws-sam" ]; then
    echo "❌ No build found. Run './build.sh' first."
    exit 1
fi

USER_POOL_ID=$(aws cloudformation describe-stacks \
    --stack-name $TENANT_MGMT_STACK \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`LakehouseTenantUserpoolId`].OutputValue' \
    --output text)

CLIENT_ID=$(aws cloudformation describe-stacks \
    --stack-name $TENANT_MGMT_STACK \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`LakehouseUserPoolClientId`].OutputValue' \
    --output text)

IDENTITY_POOL_ID=$(aws cloudformation describe-stacks \
    --stack-name $TENANT_MGMT_STACK \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`LakehouseIdentityPoolId`].OutputValue' \
    --output text)

# Deploy with SAM using existing Cognito resources
echo "Deploying with SAM..."
sam deploy --stack-name $STACK_NAME --capabilities CAPABILITY_IAM --region $REGION --resolve-s3 \
    --parameter-overrides UserPoolId=$USER_POOL_ID IdentityPoolId=$IDENTITY_POOL_ID ClientId=$CLIENT_ID AWSRegion=$REGION


# Configure Cognito User Pool with trigger
echo "Configuring Cognito User Pool trigger..."
TRIGGER_FUNCTION_ARN=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`CognitoTriggerFunctionArn`].OutputValue' \
    --output text)

aws cognito-idp update-user-pool \
    --user-pool-id $USER_POOL_ID \
    --region $REGION \
    --lambda-config PreTokenGeneration=$TRIGGER_FUNCTION_ARN

# Get outputs
WEBSOCKET_URL=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`WebSocketUrl`].OutputValue' \
    --output text)

QUERY_HANDLER_ARN=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`QueryHandlerFunctionArn`].OutputValue' \
    --output text)

# Create deployment info file for frontend configuration
cat > deployment_info.txt << EOF
# Multi-Tenant Security Analytics Backend - Deployment Information
# Generated on: $(date)
# Region: $REGION
# Stack: $STACK_NAME

# ========================================
# API Configuration
# ========================================
WebSocketUrl=$WEBSOCKET_URL

# ========================================
# Cognito Configuration
# ========================================
COGNITO_USER_POOL_ID=$USER_POOL_ID
COGNITO_CLIENT_ID=$CLIENT_ID
COGNITO_IDENTITY_POOL_ID=$IDENTITY_POOL_ID
COGNITO_REGION=$REGION

# ========================================
# Lambda Functions
# ========================================
COGNITO_TRIGGER_FUNCTION_ARN=$TRIGGER_FUNCTION_ARN
QUERY_HANDLER_FUNCTION_ARN=$QUERY_HANDLER_ARN

# ========================================
# AWS Infrastructure
# ========================================
AWS_REGION=$REGION
CLOUDFORMATION_STACK_NAME=$STACK_NAME
S3_RESULTS_BUCKET=security-analytics-results
ATHENA_WORKGROUP=security-analytics

# ========================================
# Multi-Tenant Configuration
# ========================================
TENANT_TIERS=premium,standard
PREMIUM_TENANTS=premium_tenant1
STANDARD_TENANTS=standard_tenant1,standard_tenant2

# ========================================
# Frontend Environment Variables
# Copy these to your frontend .env file:
# ========================================
REACT_APP_API_URL=$WEBSOCKET_URL
REACT_APP_USER_POOL_ID=$USER_POOL_ID
REACT_APP_CLIENT_ID=$CLIENT_ID
REACT_APP_IDENTITY_POOL_ID=$IDENTITY_POOL_ID
REACT_APP_REGION=$REGION

# ========================================
# Data Infrastructure (Manual Setup)
# ========================================
S3_DATA_BUCKET=multi-tenant-lakehouse-tables
GLUE_DATABASE=security_analytics
LAKE_FORMATION_ENABLED=true

# Data Namespaces:
# - premium/: Premium tenant data with advanced features
# - standard/: Standard tenant data with basic features  
# - shared/: Shared data accessible by all tenants

# ========================================
# Deployment URLs
# ========================================
API_ENDPOINT=$WEBSOCKET_URL
CORS_ENABLED=true
AUTH_METHOD=Cognito_User_Pools

EOF

echo ""
echo "=== Deployment Completed Successfully! 🚀 ==="
echo "Region: $REGION"
echo "Stack: $STACK_NAME"
echo "WebSocket URL: $WEBSOCKET_URL"
echo "Cognito User Pool: $USER_POOL_ID"
echo "Cognito Client ID: $CLIENT_ID"
echo "Identity Pool: $IDENTITY_POOL_ID"
echo "Trigger Function: $TRIGGER_FUNCTION_ARN"
echo "Query Handler: $QUERY_HANDLER_ARN"
echo ""
echo "📄 Deployment info saved to: deployment_info.txt"
echo "📋 Use this file to configure your frontend application"
echo "🔧 All configuration variables are organized by section"

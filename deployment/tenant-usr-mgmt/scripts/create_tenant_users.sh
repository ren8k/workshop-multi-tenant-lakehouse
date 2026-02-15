#!/bin/bash -e
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

STACK_NAME=LakehouseTenantUserManagementStack
SECRET_NAME="${TENANT_PASSWORD_SECRET_NAME:-lakehouse-tenant-user-password}"

# Function to display usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "Options:"
    echo "  -s SECRET_NAME    Name of the secret in AWS Secrets Manager (default: lakehouse-tenant-user-password)"
    echo "  -h                Display this help message"
    echo ""
    echo "Environment Variables:"
    echo "  TENANT_PASSWORD_SECRET_NAME    Override default secret name"
    exit 1
}

# Parse command line arguments
while getopts "s:h" opt; do
    case $opt in
        s) SECRET_NAME="$OPTARG" ;;
        h) usage ;;
        *) usage ;;
    esac
done

# Function to create secret in Secrets Manager
create_secret_if_not_exists() {
    local secret_name="$1"
    local secret_value="$2"
    
    echo "Checking if secret exists in AWS Secrets Manager..."
    
    # Check if secret already exists
    if aws secretsmanager describe-secret --secret-id "$secret_name" >/dev/null 2>&1; then
        echo "Secret '$secret_name' already exists in Secrets Manager"
        return 0
    else
        echo "Secret '$secret_name' does not exist. Creating it..."
        
        # Create the secret
        local result=$(aws secretsmanager create-secret \
            --name "$secret_name" \
            --secret-string "$secret_value" \
            --description "Password for lakehouse tenant users" 2>&1)
        
        if [[ $? -eq 0 ]]; then
            echo "Secret '$secret_name' created successfully in Secrets Manager"
            return 0
        else
            echo "Error: Failed to create secret '$secret_name' in Secrets Manager"
            echo "$result"
            exit 1
        fi
    fi
}

echo "Starting tenant user creation process..."
echo "Stack Name: $STACK_NAME"
echo "Secret Name: $SECRET_NAME"
echo ""

echo "Get user pool id from the cloudformation stack"
USER_POOL_ID=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --query "Stacks[0].Outputs[?OutputKey=='LakehouseTenantUserpoolId'].OutputValue" --output text)
if [[ -z "$USER_POOL_ID" ]]; then
    echo "Error: Could not retrieve User Pool ID from CloudFormation stack: $STACK_NAME"
    exit 1
fi
echo "User pool id: $USER_POOL_ID"

echo "Get user pool client id from the cloudformation stack"
USERPOOL_CLIENT_ID=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --query "Stacks[0].Outputs[?OutputKey=='LakehouseUserPoolClientId'].OutputValue" --output text)
if [[ -z "$USERPOOL_CLIENT_ID" ]]; then
    echo "Error: Could not retrieve User Pool Client ID from CloudFormation stack: $STACK_NAME"
    exit 1
fi
echo "User pool client id: $USERPOOL_CLIENT_ID"

# Create secret if it doesn't exist and get password from Secrets Manager
echo ""
DEFAULT_PASSWORD="#LakehouseTenantUser1234"
create_secret_if_not_exists "$SECRET_NAME" "$DEFAULT_PASSWORD"
TENANT_USER_PASSWORD=$(aws secretsmanager get-secret-value \
        --secret-id "$SECRET_NAME" \
        --query 'SecretString' \
        --output text 2>/dev/null)

# Validate the retrieved password
if [[ -z "$TENANT_USER_PASSWORD" ]]; then
    echo "Error: Retrieved password is empty"
    exit 1
fi

# Define tenant users to create
declare -a TENANT_USERS=(
  "standard_tenant1_user:standard_tenant1:standard"
  "standard_tenant2_user:standard_tenant2:standard"
  "premium_tenant1_user:premium_tenant1:premium"
  "premium_tenant2_user:premium_tenant2:premium"
)

# Update user pool client to allow password auth (only needs to be done once)
echo "Updating user pool client to allow password authentication"
RESULT=$(aws cognito-idp update-user-pool-client \
          --user-pool-id "$USER_POOL_ID" \
          --client-id "$USERPOOL_CLIENT_ID" \
          --explicit-auth-flows USER_PASSWORD_AUTH)

# Loop through each tenant user and create them
for user_config in "${TENANT_USERS[@]}"; do
  IFS=':' read -r username tenant_id tier <<< "$user_config"
  
  echo "Creating user: $username for tenant: $tenant_id with tier: $tier"
  
  email="${tenant_id}@simulator.amazonses.com"
  
  # Create the user
  RESULT=$(aws cognito-idp admin-create-user \
    --user-pool-id "$USER_POOL_ID" \
    --username "$username" \
    --user-attributes Name=email,Value="$email" Name=email_verified,Value="True" Name=phone_number,Value="+11234567890" Name="custom:userRole",Value="TenantAdmin" Name="custom:tenantId",Value="$tenant_id" Name="custom:tenantTier",Value="$tier" \
    --desired-delivery-mediums EMAIL)
  
  echo "Setting password for user: $username"  
  RESULT=$(aws cognito-idp admin-set-user-password \
    --user-pool-id $USER_POOL_ID \
    --username $username \
    --password "$TENANT_USER_PASSWORD" \
    --permanent)
  
  echo "Successfully created user: $username with email: $email"
  echo "---"
done

echo "All tenant users created successfully!"

# Note: This script automatically creates the secret in AWS Secrets Manager if it doesn't exist
# Default password: "#LakehouseTenantUser1234"
# 
# To update the password in the secret, run:
# aws secretsmanager update-secret --secret-id "lakehouse-tenant-user-password" --secret-string "YourNewSecurePassword123!"
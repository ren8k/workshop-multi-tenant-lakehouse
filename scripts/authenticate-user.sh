#!/bin/bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# Function to authenticate user and get credentials
authenticate_user() {
    local username=$1
    local password=$2
    

    AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    REGION=$AWS_REGION

    #ATHENA_RESULTS_BUCKET="aws-athena-query-results-${AWS_ACCOUNT_ID}-${REGION}-lakehouse"

    TENANT_USER_STACK_NAME=LakehouseTenantUserManagementStack

    echo "Get user pool id from the cloudformation stack"
    USER_POOL_ID=$(aws cloudformation describe-stacks --stack-name $TENANT_USER_STACK_NAME --query "Stacks[0].Outputs[?OutputKey=='LakehouseTenantUserpoolId'].OutputValue" --output text)
    echo "User pool id: $USER_POOL_ID"

    echo "Get user pool client id from the cloudformation stack"
    USERPOOL_CLIENT_ID=$(aws cloudformation describe-stacks --stack-name $TENANT_USER_STACK_NAME --query "Stacks[0].Outputs[?OutputKey=='LakehouseUserPoolClientId'].OutputValue" --output text)
    echo "User pool client id: $USERPOOL_CLIENT_ID"

    echo "Get ideneity pool id from the cloudformation stack"
    IDENTITY_POOL_ID=$(aws cloudformation describe-stacks --stack-name $TENANT_USER_STACK_NAME --query "Stacks[0].Outputs[?OutputKey=='LakehouseIdentityPoolId'].OutputValue" --output text)
    echo "User pool client id: $IDENTITY_POOL_ID"

    echo "🔐 Authenticating user: $username"
    
    # Authenticate with Cognito User Pool

    local auth_response=$(aws cognito-idp initiate-auth \
        --auth-flow USER_PASSWORD_AUTH \
        --client-id "${USERPOOL_CLIENT_ID}" \
        --auth-parameters "USERNAME=${username},PASSWORD='${password}'" )

    if [ $? -ne 0 ]; then
        echo "❌ Authentication failed for user: $username"
        return 1
    fi
    
    local id_token=$(echo "$auth_response" | jq -r '.AuthenticationResult.IdToken')
    
    # Get Identity Pool credentials
    local identity_response=$(aws cognito-identity get-id \
        --identity-pool-id "$IDENTITY_POOL_ID" \
        --logins "cognito-idp.${REGION}.amazonaws.com/${USER_POOL_ID}=${id_token}" \
        --output json)
    
    local identity_id=$(echo "$identity_response" | jq -r '.IdentityId')

    local credentials_response=$(aws cognito-identity get-credentials-for-identity \
        --identity-id "$identity_id" \
        --logins "cognito-idp.${REGION}.amazonaws.com/${USER_POOL_ID}=${id_token}" \
        --output json 2>/dev/null)
    
    # Export credentials for use in tests
    export TEST_ACCESS_KEY=$(echo "$credentials_response" | jq -r '.Credentials.AccessKeyId')
    export TEST_SECRET_KEY=$(echo "$credentials_response" | jq -r '.Credentials.SecretKey')
    export TEST_SESSION_TOKEN=$(echo "$credentials_response" | jq -r '.Credentials.SessionToken')
    
    echo "token"
    echo $TEST_SESSION_TOKEN
    
    echo "✅ Successfully authenticated: $username"
    return 0
}
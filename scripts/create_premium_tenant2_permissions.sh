#!/bin/bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

source ~/.my_custom_env
cd ~/multi-tenant-lakehouse/scripts
export TABLE_BUCKET_NAME="multi-tenant-lakehouse-tables"

# Premium tier database
PREMIUM_DATABASE="premium_tenant2_data"
PREMIUM_TABLES=("network_events" "authentication_logs" "endpoints" "installed_software")

# Set up environment variables
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export CATALOG_ID="s3tablescatalog/multi-tenant-lakehouse-tables"

# Authenticated tenant user role
TENANT_USER_ROLE_ARN="arn:aws:iam::$AWS_ACCOUNT_ID:role/lakehouse-tenant-authenticated-user-role"

TENANT_ID="premium_tenant2"
TENANT_TIER="premium"

CEDAR_CONDITION="context.iam.principalTags.hasTag(\\\"tenantTier\\\") && context.iam.principalTags.getTag(\\\"tenantTier\\\") == \\\"$TENANT_TIER\\\" && context.iam.principalTags.hasTag(\\\"tenantId\\\") && context.iam.principalTags.getTag(\\\"tenantId\\\") == \\\"$TENANT_ID\\\""

aws lakeformation grant-permissions \
    --region $AWS_REGION \
    --principal '{
        "DataLakePrincipalIdentifier": "'"$AWS_ACCOUNT_ID"':IAMPrincipals"
    }' \
    --resource '{
        "Database": {
            "CatalogId": "'"$CATALOG_ID"'",
            "Name": "'"$PREMIUM_DATABASE"'"
        }
    }' \
    --permissions "DESCRIBE" \
    --condition '{
        "Expression": "'"$CEDAR_CONDITION"'"
    }'


for table in "${SHARED_TABLES[@]}"; do
    aws lakeformation grant-permissions \
        --region $AWS_REGION \
        --principal '{
            "DataLakePrincipalIdentifier": "'"$AWS_ACCOUNT_ID"':IAMPrincipals"
        }' \
        --resource '{
            "Table": {
                "CatalogId": "'"$CATALOG_ID"'",
                "DatabaseName": "'"$PREMIUM_DATABASE"'",
                "Name": "'"$table"'"
            }
        }' \
        --permissions "SELECT" "DESCRIBE" \
        --condition '{
            "Expression": "'"$CEDAR_CONDITION"'"
        }'
done
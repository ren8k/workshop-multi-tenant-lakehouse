#!/bin/bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# Shared data configuration
SHARED_DATABASE="shared_data"
SHARED_TABLES=("threat_intelligence" "cve_info")

# Set up environment variables
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
#export AWS_REGION=$(aws configure get region)
#export REGION=$AWS_REGION
export CATALOG_ID="s3tablescatalog/multi-tenant-lakehouse-tables"

# Premium tier database
PREMIUM_DATABASE="premium_tenant1_data"

# Authenticated tenant user role
TENANT_USER_ROLE_ARN="arn:aws:iam::$AWS_ACCOUNT_ID:role/lakehouse-tenant-authenticated-user-role"

SHARED_CEDAR_CONDITION="context.iam.principalTags.hasTag(\\\"tenantTier\\\") && (context.iam.principalTags.getTag(\\\"tenantTier\\\") == \\\"standard\\\" || context.iam.principalTags.getTag(\\\"tenantTier\\\") == \\\"premium\\\")"

aws lakeformation grant-permissions \
    --region $AWS_REGION \
    --principal '{
        "DataLakePrincipalIdentifier": "'"$AWS_ACCOUNT_ID"':IAMPrincipals"
    }' \
    --resource '{
        "Database": {
            "CatalogId": "'"$CATALOG_ID"'",
            "Name": "'"$SHARED_DATABASE"'"
        }
    }' \
    --permissions "DESCRIBE" \
    --condition '{
        "Expression": "'"$SHARED_CEDAR_CONDITION"'"
    }'


#SHARED_CEDAR_CONDITION="context.iam.principalTags.hasTag(\\\"tenantTier\\\") && (context.iam.principalTags.getTag(\\\"tenantTier\\\") == \\\"standard\\\" || context.iam.principalTags.getTag(\\\"tenantTier\\\") == \\\"premium\\\")"


for table in "${SHARED_TABLES[@]}"; do
    aws lakeformation grant-permissions \
        --region $AWS_REGION \
        --principal '{
            "DataLakePrincipalIdentifier": "'"$AWS_ACCOUNT_ID"':IAMPrincipals"
        }' \
        --resource '{
            "Table": {
                "CatalogId": "'"$CATALOG_ID"'",
                "DatabaseName": "'"$SHARED_DATABASE"'",
                "Name": "'"$table"'"
            }
        }' \
        --permissions "SELECT" "DESCRIBE" \
        --condition '{
            "Expression": "'"$SHARED_CEDAR_CONDITION"'"
        }'
done

# Grant explicit describe permissions for all tables
for table in "${PREMIUM_TABLES[@]}"; do
    aws lakeformation grant-permissions \
        --region $AWS_REGION \
        --principal '{"DataLakePrincipalIdentifier":"'"$TENANT_USER_ROLE_ARN"'"}' \
        --resource Table="{DatabaseName=$PREMIUM_DATABASE,TableWildcard={},CatalogId=$CATALOG_ID}" \
        --permissions "DESCRIBE"
done

# Grant explicit describe permissions for all tables
aws lakeformation grant-permissions \
    --region $AWS_REGION \
    --principal '{"DataLakePrincipalIdentifier":"'"$TENANT_USER_ROLE_ARN"'"}' \
    --resource Table="{DatabaseName=$SHARED_DATABASE,TableWildcard={},CatalogId=$CATALOG_ID}" \
    --permissions "DESCRIBE"
#!/bin/bash -e
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0


# Set up environment variables
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export CATALOG_ID="s3tablescatalog/multi-tenant-lakehouse-tables"

TOKEN=$(curl --request PUT "http://169.254.169.254/latest/api/token" --header "X-aws-ec2-metadata-token-ttl-seconds: 3600")

AWS_REGION=$(curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone --header "X-aws-ec2-metadata-token: $TOKEN" | sed 's/\(.*\)[a-z]/\1/')


# User role
USER_ROLE_ARN="arn:aws:iam::$AWS_ACCOUNT_ID:role/awsmtlkh-test-SaaSApp-ec2MskClusterRole"

# Database and table configuration for standard tier
STANDARD_DATABASE="standard_tier_data"
STANDARD_TABLES=("network_events" "authentication_logs" "endpoints" "installed_software")
# Standard tier tenants
STANDARD_TENANTS=("standard_tenant1" "standard_tenant2")

# Premium tier configuration
PREMIUM_TENANT="premium_tenant1"
PREMIUM_DATABASE="premium_tenant1_data"
PREMIUM_TABLES=("network_events" "authentication_logs" "endpoints" "installed_software")

# Set premium tier variables for Cedar condition
PREMIUM_TENANT_ID="premium_tenant1"
PREMIUM_TENANT_TIER="premium"

# Shared data configuration
SHARED_DATABASE="shared_data"
SHARED_TABLES=("threat_intelligence" "cve_info")


# Grant permissions for Shared DB
aws lakeformation grant-permissions \
    --region $AWS_REGION \
    --principal '{
        "DataLakePrincipalIdentifier": "'"$USER_ROLE_ARN"'"
    }' \
    --resource '{
        "Database": {
            "CatalogId": "'"$CATALOG_ID"'",
            "Name": "'"$SHARED_DATABASE"'"
        }
    }' \
    --permissions "DESCRIBE"

# Grant permissions for Premium DB
aws lakeformation grant-permissions \
    --region $AWS_REGION \
    --principal '{
        "DataLakePrincipalIdentifier": "'"$USER_ROLE_ARN"'"
    }' \
    --resource '{
        "Database": {
            "CatalogId": "'"$CATALOG_ID"'",
            "Name": "'"$PREMIUM_DATABASE"'"
        }
    }' \
    --permissions "DESCRIBE"

# Grant permissions for Standard DB
aws lakeformation grant-permissions \
    --region $AWS_REGION \
    --principal '{
        "DataLakePrincipalIdentifier": "'"$USER_ROLE_ARN"'"
    }' \
    --resource '{
        "Database": {
            "CatalogId": "'"$CATALOG_ID"'",
            "Name": "'"$STANDARD_DATABASE"'"
        }
    }' \
    --permissions "DESCRIBE"


# Grant permissions for all tables
aws lakeformation grant-permissions \
    --region $AWS_REGION \
    --principal '{"DataLakePrincipalIdentifier":"'"$USER_ROLE_ARN"'"}' \
    --resource Table="{DatabaseName=$SHARED_DATABASE,TableWildcard={},CatalogId=$CATALOG_ID}" \
    --permissions "DESCRIBE" "SELECT" "INSERT"

# Grant permissions for all tables
aws lakeformation grant-permissions \
    --region $AWS_REGION \
    --principal '{"DataLakePrincipalIdentifier":"'"$USER_ROLE_ARN"'"}' \
    --resource Table="{DatabaseName=$STANDARD_DATABASE,TableWildcard={},CatalogId=$CATALOG_ID}" \
    --permissions "DESCRIBE" "SELECT" "INSERT"

# Grant permissions for all tables
aws lakeformation grant-permissions \
    --region $AWS_REGION \
    --principal '{"DataLakePrincipalIdentifier":"'"$USER_ROLE_ARN"'"}' \
    --resource Table="{DatabaseName=$PREMIUM_DATABASE,TableWildcard={},CatalogId=$CATALOG_ID}" \
    --permissions "DESCRIBE" "SELECT" "INSERT"

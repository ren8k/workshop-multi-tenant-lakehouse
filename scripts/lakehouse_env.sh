#!/bin/bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
# Auto-generated environment file for Multi-Tenant Lakehouse
# Source this file to load all environment variables

export AWS_ACCOUNT_ID="536036142624"
export AWS_REGION="us-west-2"
export REGION="us-west-2"
export CATALOG_ID="s3tablescatalog/multi-tenant-lakehouse-tables"
export TENANT_USER_ROLE_ARN="arn:aws:iam::536036142624:role/lakehouse-tenant-authenticated-user-role"
export STANDARD_DATABASE="standard_tier_data"
export STANDARD_TABLES=(network_events authentication_logs endpoints installed_software)
export STANDARD_TENANTS=(standard_tenant1 standard_tenant2)
export PREMIUM_TENANT="premium_tenant1"
export PREMIUM_DATABASE="premium_tenant1_data"
export PREMIUM_TABLES=(network_events authentication_logs endpoints installed_software)
export PREMIUM_TENANT_ID="premium_tenant1"
export PREMIUM_TENANT_TIER="premium"

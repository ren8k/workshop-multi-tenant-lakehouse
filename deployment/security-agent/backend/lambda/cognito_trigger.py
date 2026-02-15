# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    Cognito Pre Token Generation Lambda Trigger
    Maps User Pool custom attributes to Identity Pool attributes
    """
    
    logger.info(f"[lambda_handler] Cognito trigger invocation started - Request ID: {context.aws_request_id}")
    logger.info(f"[lambda_handler] Trigger event: {json.dumps(event, default=str)}")
    
    try:
        # Extract user attributes from the event
        logger.info("[lambda_handler] Extracting user attributes from Cognito event")
        user_attributes = event.get('request', {}).get('userAttributes', {})
        username = event.get('userName', 'unknown')
        
        logger.info(f"[lambda_handler] Processing user: {username}")
        logger.info(f"[lambda_handler] User attributes: {json.dumps(user_attributes, default=str)}")
        
        # Get custom attributes
        tenant_id = user_attributes.get('custom:tenantId')
        user_role = user_attributes.get('custom:userRole', 'analyst')
        tenant_tier = user_attributes.get('custom:tenantTier', 'standard')
        
        logger.info(f"[lambda_handler] === USER CONTEXT ===")
        logger.info(f"[lambda_handler] Username: {username}")
        logger.info(f"[lambda_handler] Tenant ID: {tenant_id}")
        logger.info(f"[lambda_handler] User Role: {user_role}")
        logger.info(f"[lambda_handler] Tenant Tier: {tenant_tier}")
        
        # Validate required attributes
        if not tenant_id:
            logger.error(f"[lambda_handler] Missing required custom:tenantId attribute for user {username}")
            raise Exception("User missing required tenant information")
        
        logger.info("[lambda_handler] Validation passed - all required attributes present")
        
        # Add claims to the ID token for Identity Pool mapping
        logger.info("[lambda_handler] Setting up claims override structure")
        if 'response' not in event:
            event['response'] = {}
        
        if 'claimsOverrideDetails' not in event['response']:
            event['response']['claimsOverrideDetails'] = {}
        
        if 'claimsToAddOrOverride' not in event['response']['claimsOverrideDetails']:
            event['response']['claimsOverrideDetails']['claimsToAddOrOverride'] = {}
        
        # Map custom attributes to standard claims for Identity Pool
        logger.info("[lambda_handler] Mapping custom attributes to Identity Pool claims")
        claims_to_add = {
            'tenant_id': tenant_id,
            'user_role': user_role,
            'tenant_tier': tenant_tier,
            'custom:tenantId': tenant_id,  # Keep original for backward compatibility
            'custom:userRole': user_role,
            'custom:tenantTier': tenant_tier
        }
        
        event['response']['claimsOverrideDetails']['claimsToAddOrOverride'].update(claims_to_add)
        logger.info(f"[lambda_handler] Added claims: {json.dumps(claims_to_add, default=str)}")
        
        # Add tenant context to group claims for IAM role mapping
        logger.info("[lambda_handler] Setting up group claims for IAM role mapping")
        if 'groupsToOverride' not in event['response']['claimsOverrideDetails']:
            event['response']['claimsOverrideDetails']['groupsToOverride'] = []
        
        # Add tenant-based group for IAM role selection
        tenant_group = f"tenant-{tenant_id}-{user_role}"
        event['response']['claimsOverrideDetails']['groupsToOverride'].append(tenant_group)
        logger.info(f"[lambda_handler] Added tenant group: {tenant_group}")
        
        logger.info(f"[lambda_handler] === CLAIMS PROCESSING COMPLETE ===")
        logger.info(f"[lambda_handler] Successfully processed claims for user {username} in tenant {tenant_id}")
        logger.info(f"[lambda_handler] Final response structure: {json.dumps(event['response'], default=str)}")
        
        return event
        
    except Exception as e:
        logger.error(f"[lambda_handler] Error in Cognito trigger for user {username}: {str(e)}", exc_info=True)
        logger.error(f"[lambda_handler] Request ID: {context.aws_request_id}")
        # Don't block authentication, but log the error
        return event
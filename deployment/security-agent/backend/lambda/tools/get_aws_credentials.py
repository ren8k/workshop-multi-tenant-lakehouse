# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json
import boto3
import logging
import os
from strands import Agent, tool
import jwt
from datetime import datetime
import time
import asyncio
from botocore.exceptions import ClientError
from . import aws_utils

# Configure logging  
logger = aws_utils.logger

@tool
def get_aws_credentials(jwt_token: str) -> dict:
    """Get AWS credentials from Cognito Identity Pool for authenticated user"""
    logger.info("[get_aws_credentials] Exchanging JWT for AWS credentials")
    
    try:
        cognito_identity = boto3.client('cognito-identity')
        identity_pool_id = os.environ.get('IDENTITY_POOL_ID')
        user_pool_provider = os.environ.get('USER_POOL_PROVIDER')
        
        if not identity_pool_id or not user_pool_provider:
            raise Exception("Missing required environment variables")
        
        identity_response = cognito_identity.get_id(
            IdentityPoolId=identity_pool_id,
            Logins={user_pool_provider: jwt_token}
        )
        
        credentials_response = cognito_identity.get_credentials_for_identity(
            IdentityId=identity_response['IdentityId'],
            Logins={user_pool_provider: jwt_token}
        )
        
        credentials = credentials_response['Credentials']
        logger.info("[get_aws_credentials] Successfully obtained AWS credentials")
        
        # Initialize global clients
        aws_utils.initialize_aws_clients(credentials)

        result_credentials = {
            'AccessKeyId': credentials['AccessKeyId'],
            'SecretKey': credentials['SecretKey'],
            'SessionToken': credentials['SessionToken'],
            'status_message': 'AWS credentials obtained successfully'
        }
        
        logger.info(f"[get_aws_credentials] Returning credentials with AccessKeyId: {result_credentials['AccessKeyId'][:10]}...")
        return result_credentials
        
    except Exception as e:
        logger.error(f"[get_aws_credentials] Error: {str(e)}")
        raise Exception(f"Failed to get AWS credentials: {str(e)}")
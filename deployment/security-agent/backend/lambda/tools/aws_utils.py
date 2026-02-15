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

# Global AWS clients - will be initialized when credentials are available
# USE ONLY IN WORKSHOP ENVIRONMENT. THIS is NOT safe for multiple users.
sts_client = None
athena_client = None

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def initialize_aws_clients(credentials):
    """Initialize global AWS clients with provided credentials"""
    global sts_client, athena_client
    
    sts_client = boto3.client(
        'sts',
        aws_access_key_id=credentials['AccessKeyId'],
        aws_secret_access_key=credentials['SecretKey'],
        aws_session_token=credentials['SessionToken']
    )
    
    athena_client = boto3.client(
        'athena',
        aws_access_key_id=credentials['AccessKeyId'],
        aws_secret_access_key=credentials['SecretKey'],
        aws_session_token=credentials['SessionToken']
    )
    
    return sts_client, athena_client

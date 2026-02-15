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
def query_security_data(sql_query: str, credentials: dict, database: str) -> dict:
    """Execute SQL query against security database using AWS Athena"""
    logger.info(f"[query_security_data] Executing query in database: {database}")
    logger.info(f"[query_security_data] SQL: {sql_query}")
    logger.info(f"[query_security_data] Credentials type: {type(credentials)}")
    logger.info(f"[query_security_data] Credentials keys: {list(credentials.keys()) if isinstance(credentials, dict) else 'Not a dict'}")
    
    try:
        # Handle different credential formats that might be passed by the agent
        if isinstance(credentials, str):
            try:
                credentials = json.loads(credentials)
            except json.JSONDecodeError:
                raise Exception("Invalid credentials format - expected JSON string or dict")
        
        if not isinstance(credentials, dict):
            raise Exception(f"Invalid credentials type: {type(credentials)}. Expected dict.")
        
        # Check for required credential keys
        required_keys = ['AccessKeyId', 'SecretKey', 'SessionToken']
        missing_keys = [key for key in required_keys if key not in credentials]
        if missing_keys:
            raise Exception(f"Missing required credential keys: {missing_keys}")
        
        logger.info(f"[query_security_data] Using credentials with AccessKeyId: {credentials['AccessKeyId'][:10]}...")
        
        # Initialize global clients if not already done
        if aws_utils.athena_client is None or aws_utils.sts_client is None:
            aws_utils.initialize_aws_clients(credentials)

        # Import the initialized clients from aws_utils
        from .aws_utils import sts_client, athena_client
        
        account_id = aws_utils.sts_client.get_caller_identity()['Account']
        region = os.environ.get('AWS_REGION', 'us-west-2')
        
        response = aws_utils.athena_client.start_query_execution(
            QueryString=sql_query,
            WorkGroup='primary',
            QueryExecutionContext={
                'Catalog': 's3tablescatalog/multi-tenant-lakehouse-tables',
                'Database': database
            },
            ResultConfiguration={
                'OutputLocation': f's3://aws-athena-query-results-{account_id}-{region}-lakehouse/'
            }
        )
        
        query_execution_id = response['QueryExecutionId']
        logger.info(f"[query_security_data] Query started: {query_execution_id}")
        
        for attempt in range(3):
            status_response = aws_utils.athena_client.get_query_execution(QueryExecutionId=query_execution_id)
            status = status_response['QueryExecution']['Status']['State']
            
            if status == 'SUCCEEDED':
                break
            elif status in ['FAILED', 'CANCELLED']:
                error_reason = status_response['QueryExecution']['Status'].get('StateChangeReason', 'Unknown error')
                raise Exception(f"Query failed: {error_reason}")
            
            time.sleep(2)
        
        if status != 'SUCCEEDED':
            raise Exception("Query timed out")
        
        results = aws_utils.athena_client.get_query_results(QueryExecutionId=query_execution_id)
        result_rows = results.get('ResultSet', {}).get('Rows', [])
        
        if not result_rows:
            return {
                'data': [], 
                'row_count': 0,
                'sql_executed': sql_query,
                'status_message': 'Query executed successfully - no results found'
            }
        
        headers = [col.get('VarCharValue', '') for col in result_rows[0].get('Data', [])]
        
        data = []
        for row in result_rows[1:]:
            row_data = [col.get('VarCharValue', '') for col in row.get('Data', [])]
            data.append(dict(zip(headers, row_data)))
        
        logger.info(f"[query_security_data] Query successful: {len(data)} rows returned")
        
        return {
            'data': data,
            'row_count': len(data),
            'headers': headers,
            'query_id': query_execution_id,
            'sql_executed': sql_query,
            'status_message': f'Query executed successfully - {len(data)} rows returned'
        }
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        logger.error(f"[query_security_data] AWS Error {error_code}: {error_message}")
        raise Exception(f"Database query failed: {error_code} - {error_message}")
    except Exception as e:
        logger.error(f"[query_security_data] Unexpected error: {str(e)}")
        raise  # Re-raise original exception
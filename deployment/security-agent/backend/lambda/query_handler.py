# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json
import logging
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """Simple HTTP handler - redirects to WebSocket"""
    logger.info(f"[query_handler] HTTP request received - Request ID: {context.aws_request_id}")
    
    # Handle CORS preflight
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization'
            },
            'body': ''
        }
    
    # Handle health checks
    if event.get('path') == '/health':
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()})
        }
    
    # All other requests redirect to WebSocket
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({
            'message': 'Please use WebSocket endpoint for queries',
            'websocket_url': 'wss://6ybdo6acc8.execute-api.us-west-2.amazonaws.com/prod',
            'timestamp': datetime.utcnow().isoformat()
        })
    }
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json
import logging
import os
from strands import Agent

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """Test Lambda handler for Strands Agent debugging (ALB)"""
    logger.info(f"[simple_agent] Lambda invocation started - Request ID: {context.aws_request_id}")
    logger.info(f"[simple_agent] Event: {json.dumps(event, default=str)}")
    logger.info("This is just for testing strands")
    
    try:
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
        
        # Handle ALB health checks
        if event.get('path') == '/health':
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'status': 'healthy'})
            }
        
        # Initialize Strands Agent
        logger.info("[simple_agent] Initializing Strands Agent")
        agent = Agent(
            model="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
            system_prompt="You are a helpful assistant. Respond with 'Hello from Strands Agent!' to any input."
        )
        logger.info("[simple_agent] Strands Agent initialized successfully")
        
        # Test simple prompt
        logger.info("[simple_agent] Testing simple prompt")
        response = agent("Say hello")
        logger.info(f"[simple_agent] Agent response type: {type(response)}")
        logger.info(f"[simple_agent] Agent response: {response}")
        
        # Handle different response types
        if hasattr(response, 'message') and hasattr(response.message, 'content'):
            content = response.message.content
        elif hasattr(response, 'content'):
            content = response.content
        elif isinstance(response, dict) and 'content' in response:
            content = response['content']
        else:
            content = str(response)
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'message': 'Strands Agent test successful',
                'agent_response': content,
                'request_id': context.aws_request_id
            })
        }
        
    except Exception as e:
        logger.error(f"[simple_agent] Error testing Strands Agent: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': f'Strands Agent test failed: {str(e)}',
                'request_id': context.aws_request_id
            })
        }
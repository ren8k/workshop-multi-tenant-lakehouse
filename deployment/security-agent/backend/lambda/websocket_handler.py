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
from tools.get_aws_credentials import get_aws_credentials
from tools.query_tenant_data import query_security_data

# Global AWS clients - will be initialized when credentials are available
# USE ONLY IN WORKSHOP ENVIRONMENT. THIS is NOT safe for multiple users.
sts_client = None
athena_client = None

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


# Schema information for SQL generation
SECURITY_SCHEMA = {
    'authentication_logs': {
        'columns': {
            'auth_id': 'bigint',
            'tenant_id': 'string',
            'timestamp': 'timestamp',
            'user_id': 'string',
            'source_ip': 'string',
            'authentication_type': 'string',
            'status': 'string',
            'failure_reason': 'string',
            'location': 'string',
            'country_code': 'string',
            'device_type': 'string'
        },
        'description': 'User authentication events and outcomes'
    },
    'network_events': {
        'columns': {
            'event_id': 'bigint',
            'tenant_id': 'string',
            'timestamp': 'timestamp',
            'source_ip': 'string',
            'destination_ip': 'string',
            'source_port': 'int',
            'destination_port': 'int',
            'protocol': 'string',
            'bytes_sent': 'bigint',
            'bytes_received': 'bigint',
            'action': 'string',
            'threat_level': 'string',
            'region': 'string'
        },
        'description': 'Network traffic events and security actions'
    },
    'endpoints': {
        'columns': {
            'endpoint_id': 'bigint',
            'tenant_id': 'string',
            'hostname': 'string',
            'ip_address': 'string',
            'operating_system': 'string',
            'os_version': 'string',
            'last_patch_date': 'timestamp',
            'antivirus_status': 'string',
            'risk_score': 'decimal(3,2)',
            'department': 'string',
            'region': 'string',
            'country_code': 'string'
        },
        'description': 'Endpoint information and risk assessment'
    },
    'installed_software': {
        'columns': {
            'software_instance_id': 'bigint',
            'endpoint_id': 'bigint',
            'tenant_id': 'string',
            'software_name': 'string',
            'version': 'string',
            'install_date': 'timestamp',
            'is_critical': 'boolean'
        },
        'description': 'Software installed on endpoints'
    }
}

SHARED_TABLES = {
    'threat_intelligence': {
        'columns': ['ip_address', 'threat_type', 'confidence_score', 'last_updated'],
        'description': 'External threat intelligence data'
    },
    'cve_info': {
        'columns': ['cve_id', 'severity', 'cvss_score', 'affected_software_name', 'description'],
        'description': 'Common Vulnerabilities and Exposures information'
    }
}

def get_system_prompt(tenant_id, tenant_tier, database, jwt_token):
    """Generate system prompt for the security analytics agent"""
    return f"""
You are a security analytics expert in a multi-tenant application. You will be querying Data Lakehouse securely maintaining strict tenant isolation

USE THESE TOOLS:

1. get_aws_credentials(jwt_token) - Get AWS credentials for data access  
2. query_security_data(sql, credentials, database) - Execute SQL queries against security data

CURRENT USER CONTEXT:
- User Tenant ID: {tenant_id}
- User Tenant Tier: {tenant_tier}
- Accessible Database: {database}
- Authorized Tenant Data Access: {tenant_id} ONLY

AUTHORIZATION VALIDATION:
CRITICAL: Before executing any queries, validate tenant access authorization:
- The user can ONLY access data for tenant_id = "{tenant_id}"
- If the user query requests data for ANY other tenant (e.g., standard_tenant2, premium_tenant1, etc.), immediately respond with:
  "❌ AUTHORIZATION ERROR: You do not have access to data for the requested tenant. Your access is restricted to tenant_id = '{tenant_id}' only. Please modify your query to only include data for your authorized tenant."
- Do NOT waste time executing credentials or database queries for unauthorized tenant requests
- Only proceed with database queries if the requested tenant data is within the user's authorization scope
- For queries without specific tenant mentions, use the user's default accessible tenant data

EXECUTION STEPS:
1. Validate authorization for tenant_id = "{tenant_id}"
2. Get credentials: credentials = get_aws_credentials("{jwt_token}")
3. Generate Athena-compatible SQL query
4. Execute: query_security_data(sql_query, credentials, "{database}")
5. Provide concise results
6. Ask 2-3 specific follow-up questions to help the user dive deeper

CRITICAL: Always use the credentials object returned from get_aws_credentials() directly in query_security_data(). Do not modify, stringify, or reformat the credentials.

DATABASE TYPE: ATHENA
SUPPORTED FUNCTIONS:
- Date operations: date_add(), date_diff(), current_timestamp
- String operations: array_join(), array_agg(), CAST()
UNSUPPORTED FUNCTIONS (DO NOT USE):
- DATEDIFF(), now(), date_format() with incompatible types

SECURITY DATABASE SCHEMA:
{json.dumps(SECURITY_SCHEMA, indent=2)}

SHARED TABLES (accessible to all tenants):
{json.dumps(SHARED_TABLES, indent=2)}

COLUMN VALUE SPECIFICATIONS:
- status: Possible values are "SUCCESS" and "FAILED"
- tenant_id: 
  * For "standard_tier_data" database: "standard_tenant1", "standard_tenant2", "standard_tenant3", etc.
  * For "premium_tenant1_data" database: "premium_tenant1"
- timestamp: Format is "YYYY-MM-DD HH:MM:SS.ssssss" (e.g., "2025-10-12 22:02:17.904000")

SQL GENERATION GUIDELINES (ATHENA-OPTIMIZED):
- Use proper table prefixes (schema_name.table_name or shared_data.table_name)
- Include meaningful WHERE clauses based on query intent
- DO NOT filter by tenant ID. The connection itself is tenant scoped
- Use JOINs when correlating data across tables
- Always include LIMIT clauses (typically 100-500 rows)
- Order results meaningfully (usually by timestamp DESC)

ATHENA-SPECIFIC REQUIREMENTS:
- Date arithmetic: date_add('day', -90, current_timestamp) NOT date_add('day', -90, now())
- Date differences: date_diff('day', date1, date2) NOT DATEDIFF('day', date1, date2)
- Type conversions: CAST(column AS date) for date comparisons
- String aggregation: array_join(array_agg(column), ', ')
- Boolean comparisons: Use direct boolean evaluation (s.is_critical) NOT (s.is_critical = 'true')
- When filtering by status, use "SUCCESS" or "FAILED" values
- When working with timestamps, use the format "YYYY-MM-DD HH:MM:SS.ssssss"

DATE RANGE FILTERING REQUIREMENTS:
- Use realistic date thresholds based on actual data:
  * For "outdated" software: > 90 days (not 730+ days)
  * For "very old" software: > 180 days  
  * For "ancient" software: > 365 days
- Never use thresholds > 365 days as data may not exist

SAMPLE QUERY TEMPLATES:
For queries about "authentication anomalies in Europe region" or similar regional authentication analysis:

```sql
WITH european_offices AS (
    SELECT DISTINCT location
    FROM "{database}"."authentication_logs"
    WHERE tenant_id = '{tenant_id}'
    AND country_code IN ('DE', 'FR', 'GB', 'IT', 'ES', 'NL', 'PL', 'BE', 'SE', 'CH', 'AT', 'CZ', 'GR', 'PT')
),
auth_attempts AS (
    SELECT 
        al.source_ip,
        al.location,
        al.country_code,
        COUNT(*) as total_attempts,
        COUNT(DISTINCT al.user_id) as unique_users,
        MAX(al.timestamp) as last_attempt,
        MIN(al.timestamp) as first_attempt,
        array_join(array_agg(DISTINCT al.authentication_type), ', ') as auth_types,
        COUNT(CASE WHEN al.status = 'FAILED' THEN 1 END) as failed_attempts
    FROM "{database}"."authentication_logs" al
    JOIN european_offices eo ON al.location = eo.location
    WHERE al.tenant_id = '{tenant_id}'
    WHERE al.timestamp >= date_add('hour', -72, current_timestamp)
    GROUP BY al.source_ip, al.location, al.country_code
)
SELECT 
    aa.*,
    e.hostname,
    e.department,
    ROUND(CAST(aa.failed_attempts AS DOUBLE) / CAST(aa.total_attempts AS DOUBLE) * 100, 2) as failure_rate
FROM auth_attempts aa
LEFT JOIN "{database}"."endpoints" e ON aa.source_ip = e.ip_address AND e.tenant_id = '{tenant_id}'
WHERE aa.failed_attempts > 10 
   OR (CAST(aa.failed_attempts AS DOUBLE) / CAST(aa.total_attempts AS DOUBLE) > 0.3)
ORDER BY aa.failed_attempts DESC, failure_rate DESC 
LIMIT 100;
```
Sample query about outdated software

```
SELECT 
    e.hostname,
    e.ip_address,
    e.operating_system,
    e.department,
    e.risk_score,
    s.software_name,
    s.version,
    s.install_date
FROM endpoints e
INNER JOIN installed_software s ON e.endpoint_id = s.endpoint_id
WHERE date_diff('day', CAST(s.install_date AS date), CAST(current_timestamp AS date)) > 90
LIMIT 100
```

This template shows how to:
- Use parameterized database.
- Filter by European countries for regional analysis
- Calculate failure rates and identify anomalies
- Join with endpoints table for additional context
- Set reasonable thresholds for anomaly detection

Be intelligent about SQL generation - analyze the user's intent and create queries that provide the most relevant security insights while respecting authorization boundaries."""

def lambda_handler(event, context):
    """WebSocket handler for real-time query processing with streaming"""
    try:
        route_key = event.get('requestContext', {}).get('routeKey')
        connection_id = event.get('requestContext', {}).get('connectionId')
        
        logger.info(f"[websocket_handler] Route: {route_key}, Connection: {connection_id}")
        
        if route_key == '$connect':
            return {'statusCode': 200}
        elif route_key == '$disconnect':
            return {'statusCode': 200}
        elif route_key == 'query':
            return asyncio.run(handle_query_with_streaming(event, context))
        
        return {'statusCode': 400, 'body': 'Unknown route'}
        
    except Exception as e:
        logger.error(f"[websocket_handler] Error: {str(e)}")
        return {'statusCode': 500}

async def handle_query_with_streaming(event, context):
    """Handle query with real Strands Agent streaming"""
    connection_id = None
    apigateway = None
    
    try:
        connection_id = event.get('requestContext', {}).get('connectionId')
        domain_name = event.get('requestContext', {}).get('domainName')
        stage = event.get('requestContext', {}).get('stage')
        
        logger.info(f"[handle_query_with_streaming] Starting streaming query processing for connection: {connection_id}")
        
        apigateway = boto3.client(
            'apigatewaymanagementapi',
            endpoint_url=f'https://{domain_name}/{stage}'
        )
        
        body = json.loads(event.get('body', '{}'))
        query = body.get('query', '')
        jwt_token = body.get('jwt_token', '')
        
        if not query or not jwt_token:
            await send_message_async(apigateway, connection_id, {
                'type': 'error',
                'message': 'Query and JWT token required'
            })
            return {'statusCode': 400}
        
        # Get tenant context
        decoded = jwt.decode(jwt_token, options={"verify_signature": False})
        tenant_tier = decoded.get('custom:tenantTier', 'standard')
        tenant_id = decoded.get('custom:tenantId')
        database = 'premium_tenant1_data' if tenant_tier == 'premium' else 'standard_tier_data'
        
        logger.info(f"[handle_query_with_streaming] Tenant: {tenant_id}, Database: {database}")
        
        # Send initial status
        if not await send_message_async(apigateway, connection_id, {
            'type': 'status',
            'message': 'Initializing streaming security analysis...'
        }):
            return {'statusCode': 410}
        
        # Create streaming callback handler
        accumulated_content = ""
        current_tool_use = None
        
        def streaming_callback_handler(**kwargs):
            nonlocal accumulated_content, current_tool_use
            
            try:
                if "data" in kwargs:
                    chunk = kwargs["data"]
                    accumulated_content += chunk
                    
                    # Add newline for better readability
                    formatted_chunk = chunk + "\n" if not chunk.endswith("\n") else chunk
                    
                    # Check if chunk contains SQL
                    sql_detected = any(keyword in chunk.upper() for keyword in ['SELECT', 'FROM', 'WHERE', 'INSERT', 'UPDATE', 'DELETE'])
                    
                    logger.info(f"[streaming_callback_handler] Streaming chunk (length: {len(chunk)}): {chunk[:100]}{'...' if len(chunk) > 100 else ''}")
                    
                    send_message_sync(apigateway, connection_id, {
                        'type': 'stream',
                        'content': formatted_chunk,
                        'accumulated': accumulated_content,
                        'sql_detected': sql_detected
                    })
                    
                elif "current_tool_use" in kwargs:
                    tool_info = kwargs["current_tool_use"]
                    tool_name = tool_info.get('name', 'unknown')
                    tool_use_id = tool_info.get('toolUseId', '')
                    tool_input = tool_info.get('input', {})
                    
                    if current_tool_use != tool_use_id:
                        current_tool_use = tool_use_id
                        
                        if tool_name == 'get_aws_credentials':
                            message = '🔐 Getting AWS credentials...'
                        elif tool_name == 'query_security_data':
                            message = '🔍 Executing security database query...'
                            # Extract SQL from tool input if available
                            if 'sql_query' in tool_input:
                                sql_query = tool_input['sql_query']
                                logger.info(f"[streaming_callback_handler] SQL Query detected: {sql_query}")
                                # Send SQL as separate message
                                send_message_sync(apigateway, connection_id, {
                                    'type': 'sql_query',
                                    'sql': sql_query,
                                    'message': f'📊 Executing SQL:\n{sql_query}\n'
                                })
                        else:
                            message = f'🛠️ Using tool: {tool_name}...'
                        
                        logger.info(f"[streaming_callback_handler] Tool use: {tool_name} with input: {str(tool_input)[:200]}")
                        
                        send_message_sync(apigateway, connection_id, {
                            'type': 'tool_use',
                            'tool_name': tool_name,
                            'message': message + '\n'
                        })
                        
                elif "tool_result" in kwargs:
                    tool_result = kwargs["tool_result"]
                    tool_name = tool_result.get('name', 'unknown')
                    result_content = tool_result.get('content', '')
                    
                    if tool_name == 'get_aws_credentials':
                        message = '✅ AWS credentials obtained'
                    elif tool_name == 'query_security_data':
                        message = '✅ Database query completed'
                        # Log query results
                        if isinstance(result_content, str):
                            try:
                                result_data = json.loads(result_content)
                                if 'row_count' in result_data:
                                    message += f' - {result_data["row_count"]} rows returned'
                            except:
                                pass
                    else:
                        message = f'✅ Tool {tool_name} completed'
                    
                    logger.info(f"[streaming_callback_handler] Tool result: {tool_name} - {str(result_content)[:200]}")
                    
                    send_message_sync(apigateway, connection_id, {
                        'type': 'tool_complete',
                        'tool_name': tool_name,
                        'message': message + '\n'
                    })
                    
            except Exception as e:
                logger.error(f"[streaming_callback_handler] Error: {str(e)}")
        
        # Create agent with streaming callback
        agent = Agent(
            model="global.anthropic.claude-haiku-4-5-20251001-v1:0",
            callback_handler=streaming_callback_handler,
            system_prompt=get_system_prompt(tenant_id, tenant_tier, database, jwt_token),
            
            tools=[get_aws_credentials, query_security_data]
        )

    
        # Send processing status
        await send_message_async(apigateway, connection_id, {
            'type': 'status',
            'message': '🧠 Agent initialized - starting analysis...'
        })
        
        # Create agent prompt
        agent_prompt = f"""
User Query: "{query}"

CRITICAL SQL REQUIREMENTS:
- Use date_add('day', -N, current_timestamp) for date operations
- Use CAST() for type conversions
- Maximum 2 retry attempts on errors
- Always filter by tenant_id = "{tenant_id}"

RESPONSE FORMAT:
📊 **Query Results:** [Brief summary of findings]

🔍 **Key Insights:** [1-2 most important security insights]

❓ **Follow-up Questions:**
- [Specific question 1 to explore further]
- [Specific question 2 for deeper analysis]
- [Specific question 3 for related security concerns]

GUIDELINES:
- Be FAST and DIRECT - no lengthy analysis
- Focus on answering the user's specific question first
- Keep initial response under 100 words
- Ask actionable follow-up questions that lead to deeper security insights
- Avoid over-analyzing - let the user guide the conversation

Execute now with speed and precision.
"""

        agent.tool.get_aws_credentials(jwt_token=jwt_token)

        await send_message_async(apigateway, connection_id, {
            'type': 'tool_complete',
            'tool_name': 'get_aws_credentials',
            'message': str(f"🔐 Tenant credentials obtained\n✅ Authorized Scope : {tenant_id}\n")
        })        

        logger.info(f"[handle_query_with_streaming] Starting agent execution with streaming...")
        
        # Execute agent with streaming
        result = agent(agent_prompt)

        summary = result.metrics.get_summary()
        
        logger.info(f"[handle_query_with_streaming] Agent execution completed")
        
        # Send final result
        await send_message_async(apigateway, connection_id, {
            'type': 'result',
            'message': str(f"{result}"),
            'query': query,
            'status': 'SUCCESS'
        })
        
        # Send completion
        await send_message_async(apigateway, connection_id, {
            'type': 'complete',
            'message': 'Security analysis complete',
            'tenant_context': {
                'tenant_id': tenant_id,
                'tenant_tier': tenant_tier
            },
            'timestamp': datetime.utcnow().isoformat(),
            'request_id': context.aws_request_id
        })
        
        return {'statusCode': 200}
        
    except Exception as e:
        logger.error(f"[handle_query_with_streaming] Error: {str(e)}")
        if connection_id and apigateway:
            try:
                await send_message_async(apigateway, connection_id, {
                    'type': 'error',
                    'message': f'Analysis failed: {str(e)}'
                })
            except:
                pass
        return {'statusCode': 500}

def send_message_sync(apigateway, connection_id, message):
    """Send message to WebSocket connection synchronously"""
    try:
        msg_type = message.get('type', 'unknown')
        
        # Log message content for debugging
        if msg_type == 'stream':
            content = message.get('content', '')
            logger.info(f"[send_message_sync] Sending stream to {connection_id}: {content[:50]}{'...' if len(content) > 50 else ''}")
        elif msg_type == 'sql_query':
            sql = message.get('sql', '')
            logger.info(f"[send_message_sync] Sending SQL to {connection_id}: {sql[:100]}{'...' if len(sql) > 100 else ''}")
        else:
            logger.info(f"[send_message_sync] Sending {msg_type} to {connection_id}: {message.get('message', '')[:50]}")
        
        apigateway.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps(message)
        )
        return True
    except apigateway.exceptions.GoneException:
        logger.warning(f"[send_message_sync] Connection {connection_id} is gone")
        return False
    except Exception as e:
        logger.error(f"[send_message_sync] Failed to send message: {str(e)}")
        return False

async def send_message_async(apigateway, connection_id, message):
    """Send message to WebSocket connection asynchronously"""
    try:
        logger.debug(f"[send_message_async] Sending {message.get('type', 'unknown')} to {connection_id}")
        apigateway.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps(message)
        )
        return True
    except apigateway.exceptions.GoneException:
        logger.warning(f"[send_message_async] Connection {connection_id} is gone")
        return False
    except Exception as e:
        logger.error(f"[send_message_async] Failed to send message: {str(e)}")
        return False
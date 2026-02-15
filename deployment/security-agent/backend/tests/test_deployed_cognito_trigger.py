#!/usr/bin/env python3
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json
import boto3
import os

def test_deployed_cognito_trigger():
    """Test the deployed Cognito trigger Lambda function directly"""
    
    # Set up AWS credentials
    os.environ['AWS_ACCESS_KEY_ID'] = os.popen("grep aws_access_key_id ~/.aws/credentials | cut -d'=' -f2 | tr -d ' '").read().strip()
    os.environ['AWS_SECRET_ACCESS_KEY'] = os.popen("grep aws_secret_access_key ~/.aws/credentials | cut -d'=' -f2 | tr -d ' '").read().strip()
    os.environ['AWS_DEFAULT_REGION'] = 'us-west-2'
    
    # Lambda function ARN from deployment
    function_arn = "arn:aws:lambda:us-west-2:536036142624:function:security-analytics-backend-CognitoTriggerFunction-QO4LtRqRSbek"
    
    # Create Lambda client
    lambda_client = boto3.client('lambda', region_name='us-west-2')
    
    # Mock Cognito Pre Token Generation event
    test_event = {
        "version": "1",
        "region": "us-west-2",
        "userPoolId": "us-west-2_9ds2h5gYh",
        "userName": "standard_tenant1_user",
        "callerContext": {
            "awsSdkVersion": "aws-sdk-unknown-version",
            "clientId": "14omhqmpv72dftnnmhumsl24ef"
        },
        "triggerSource": "TokenGeneration_HostedAuth",
        "request": {
            "userAttributes": {
                "sub": "48f1c320-2051-70ab-c621-1e3b4d15ffaa",
                "email_verified": "true",
                "custom:tenantId": "standard_tenant1",
                "custom:userRole": "TenantAdmin", 
                "custom:tenantTier": "standard",
                "email": "test@example.com"
            },
            "groupConfiguration": {},
            "clientMetadata": {}
        },
        "response": {}
    }
    
    print("=== Testing Deployed Cognito Trigger ===")
    print(f"Function ARN: {function_arn}")
    print(f"Test event: {json.dumps(test_event, indent=2)}")
    
    try:
        # Invoke the Lambda function
        response = lambda_client.invoke(
            FunctionName=function_arn,
            InvocationType='RequestResponse',
            Payload=json.dumps(test_event)
        )
        
        # Parse the response
        payload = json.loads(response['Payload'].read())
        
        print(f"\n=== Lambda Response ===")
        print(f"Status Code: {response['StatusCode']}")
        print(f"Response: {json.dumps(payload, indent=2)}")
        
        # Validate the response
        if 'response' in payload and 'claimsOverrideDetails' in payload['response']:
            claims = payload['response']['claimsOverrideDetails']['claimsToAddOrOverride']
            groups = payload['response']['claimsOverrideDetails']['groupsToOverride']
            
            print(f"\n✅ Cognito trigger executed successfully!")
            print(f"✅ Tenant ID: {claims.get('tenant_id')}")
            print(f"✅ User Role: {claims.get('user_role')}")
            print(f"✅ Tenant Tier: {claims.get('tenant_tier')}")
            print(f"✅ Tenant Group: {groups[0] if groups else 'None'}")
        else:
            print("❌ Unexpected response format")
            
    except Exception as e:
        print(f"❌ Error invoking Lambda: {str(e)}")

def test_real_cognito_authentication():
    """Test by performing real Cognito authentication to trigger the Lambda"""
    
    # Set up AWS credentials
    os.environ['AWS_ACCESS_KEY_ID'] = os.popen("grep aws_access_key_id ~/.aws/credentials | cut -d'=' -f2 | tr -d ' '").read().strip()
    os.environ['AWS_SECRET_ACCESS_KEY'] = os.popen("grep aws_secret_access_key ~/.aws/credentials | cut -d'=' -f2 | tr -d ' '").read().strip()
    os.environ['AWS_DEFAULT_REGION'] = 'us-west-2'
    
    # Cognito configuration
    user_pool_id = "us-west-2_9ds2h5gYh"
    client_id = "14omhqmpv72dftnnmhumsl24ef"
    username = "standard_tenant1_user"
    password = "TempPassword123!"
    
    # Create Cognito client
    cognito_client = boto3.client('cognito-idp', region_name='us-west-2')
    
    print("\n=== Testing Real Cognito Authentication ===")
    print(f"User Pool: {user_pool_id}")
    print(f"Username: {username}")
    
    try:
        # Authenticate user (this will trigger the Pre Token Generation Lambda)
        response = cognito_client.admin_initiate_auth(
            UserPoolId=user_pool_id,
            ClientId=client_id,
            AuthFlow='ADMIN_NO_SRP_AUTH',
            AuthParameters={
                'USERNAME': username,
                'PASSWORD': password
            }
        )
        
        # Get the ID token
        id_token = response['AuthenticationResult']['IdToken']
        
        # Decode the token to see the claims (without verification for testing)
        import jwt
        decoded_token = jwt.decode(id_token, options={"verify_signature": False})
        
        print(f"\n✅ Authentication successful!")
        print(f"✅ ID Token received (length: {len(id_token)})")
        print(f"\n=== Token Claims (Enhanced by Trigger) ===")
        print(f"Tenant ID: {decoded_token.get('tenant_id', 'Not found')}")
        print(f"User Role: {decoded_token.get('user_role', 'Not found')}")
        print(f"Tenant Tier: {decoded_token.get('tenant_tier', 'Not found')}")
        print(f"Custom Tenant ID: {decoded_token.get('custom:tenantId', 'Not found')}")
        
        return id_token
        
    except Exception as e:
        print(f"❌ Authentication failed: {str(e)}")
        return None

if __name__ == "__main__":
    # Test 1: Direct Lambda invocation
    test_deployed_cognito_trigger()
    
    # Test 2: Real Cognito authentication
    test_real_cognito_authentication()
#!/usr/bin/env python3
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import boto3
import json
import sys
import os

# Add parent directory to path for AWS credentials
sys.path.insert(0, '..')

def get_jwt_token():
    """Get a real JWT token from Cognito User Pool"""
    
    # Source AWS credentials
    os.system('source ../.aws/credentials')
    
    # Configuration
    USER_POOL_ID = "us-west-2_9ds2h5gYh"
    CLIENT_ID = "14omhqmpv72dftnnmhumsl24ef"
    USERNAME = "standard_tenant1_user"
    PASSWORD = "TempPassword123!"
    
    # Create Cognito client
    client = boto3.client('cognito-idp', region_name='us-west-2')
    
    try:
        print("Authenticating with Cognito User Pool...")
        
        # Initiate authentication
        response = client.initiate_auth(
            ClientId=CLIENT_ID,
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': USERNAME,
                'PASSWORD': PASSWORD
            }
        )
        
        # Extract tokens
        auth_result = response['AuthenticationResult']
        id_token = auth_result['IdToken']
        access_token = auth_result['AccessToken']
        refresh_token = auth_result['RefreshToken']
        
        print("✓ Authentication successful!")
        print(f"\nID Token (use this for testing):")
        print(f"{id_token}")
        
        print(f"\nAccess Token:")
        print(f"{access_token}")
        
        # Decode and display token claims (without verification for testing)
        import jwt
        decoded = jwt.decode(id_token, options={"verify_signature": False})
        
        print(f"\nDecoded Token Claims:")
        print(json.dumps(decoded, indent=2))
        
        # Save token to file for easy use
        with open('jwt_token.txt', 'w') as f:
            f.write(id_token)
        
        print(f"\n✓ Token saved to jwt_token.txt")
        
        return id_token
        
    except Exception as e:
        print(f"✗ Authentication failed: {e}")
        return None

if __name__ == "__main__":
    get_jwt_token()
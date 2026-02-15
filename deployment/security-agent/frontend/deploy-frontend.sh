#!/bin/bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

echo "🚀 Deploying Multi-Tenant Security Analytics Frontend..."
echo "======================================================"

# Export AWS credentials from ~/.aws/credentials
# export AWS_ACCESS_KEY_ID=$(grep aws_access_key_id ~/.aws/credentials | cut -d'=' -f2 | xargs)
# export AWS_SECRET_ACCESS_KEY=$(grep aws_secret_access_key ~/.aws/credentials | cut -d'=' -f2 | xargs)
# export AWS_SESSION_TOKEN=$(grep aws_session_token ~/.aws/credentials | cut -d'=' -f2 | xargs)
# export AWS_DEFAULT_REGION=$(grep region ~/.aws/credentials | cut -d'=' -f2 | xargs)
export AWS_DEFAULT_REGION=$AWS_REGION

# Check AWS credentials
# if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
    # echo "❌ AWS credentials not found in ~/.aws/credentials"
    # exit 1
# fi

# if [ -z "$AWS_DEFAULT_REGION" ]; then
    # echo "❌ AWS region not found in ~/.aws/credentials"
    # exit 1
# fi

# echo "✅ AWS credentials configured"
echo "🌍 Using AWS region: $AWS_DEFAULT_REGION"
echo ""

# Update .env file from backend deployment info
# Install npm dependencies
echo "📦 Installing npm dependencies..."
npm install

if [ $? -ne 0 ]; then
    echo "❌ npm install failed!"
    exit 1
fi

echo "✅ npm dependencies installed"
echo ""

echo "📋 Updating .env file from backend deployment..."
BACKEND_DEPLOYMENT_INFO="../backend/deployment_info.txt"

if [ ! -f "$BACKEND_DEPLOYMENT_INFO" ]; then
    echo "❌ Backend deployment info not found at $BACKEND_DEPLOYMENT_INFO"
    echo "Please deploy the backend first to generate deployment_info.txt"
    exit 1
fi

# Extract values from backend deployment_info.txt
COGNITO_USER_POOL_ID=$(grep "^COGNITO_USER_POOL_ID=" $BACKEND_DEPLOYMENT_INFO | cut -d'=' -f2)
COGNITO_CLIENT_ID=$(grep "^COGNITO_CLIENT_ID=" $BACKEND_DEPLOYMENT_INFO | cut -d'=' -f2)
COGNITO_IDENTITY_POOL_ID=$(grep "^COGNITO_IDENTITY_POOL_ID=" $BACKEND_DEPLOYMENT_INFO | cut -d'=' -f2)
COGNITO_REGION=$(grep "^COGNITO_REGION=" $BACKEND_DEPLOYMENT_INFO | cut -d'=' -f2)

# Extract WebSocket URL from backend deployment
WEBSOCKET_URL=$(grep "^WebSocketUrl=" $BACKEND_DEPLOYMENT_INFO | cut -d'=' -f2)

# Update .env file - use CloudFront URL for API calls
cat > .env << EOF
# AWS Configuration
REACT_APP_AWS_REGION=$COGNITO_REGION
REACT_APP_COGNITO_USER_POOL_ID=$COGNITO_USER_POOL_ID
REACT_APP_COGNITO_CLIENT_ID=$COGNITO_CLIENT_ID
REACT_APP_COGNITO_IDENTITY_POOL_ID=$COGNITO_IDENTITY_POOL_ID

# WebSocket URL for queries
REACT_APP_WEBSOCKET_URL=$WEBSOCKET_URL

# OAuth Redirects
REACT_APP_REDIRECT_SIGN_IN=http://localhost:3000/
REACT_APP_REDIRECT_SIGN_OUT=http://localhost:3000/
EOF

echo "✅ .env file updated with backend deployment values"
echo ""

# Build React app
echo "📦 Building React application..."
npm run build

if [ $? -ne 0 ]; then
    echo "❌ React build failed!"
    exit 1
fi

echo "✅ React build completed"
echo ""

# Use fixed stack name for updates
STACK_NAME="security-analytics-frontend"

echo "📦 Deploying CloudFormation stack: $STACK_NAME"
echo "⏱️  This will take 15-20 minutes (CloudFront global deployment)..."

aws cloudformation deploy \
    --template-file cloudfront-deployment.yaml \
    --stack-name $STACK_NAME \
    --capabilities CAPABILITY_IAM \
    --region $AWS_DEFAULT_REGION

if [ $? -ne 0 ]; then
    echo "❌ Infrastructure deployment failed!"
    exit 1
fi

echo ""
echo "📋 Getting deployment outputs..."

# Get bucket name
BUCKET_NAME=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $AWS_DEFAULT_REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`S3BucketName`].OutputValue' \
    --output text)

# Get CloudFront URL
CLOUDFRONT_URL=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $AWS_DEFAULT_REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontURL`].OutputValue' \
    --output text)

# Get Distribution ID
DISTRIBUTION_ID=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $AWS_DEFAULT_REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`DistributionId`].OutputValue' \
    --output text)

echo "📁 S3 Bucket: $BUCKET_NAME"
echo "🌐 CloudFront URL: $CLOUDFRONT_URL"
echo ""

# Update .env with CloudFront URL and rebuild
cat > .env << EOF
# AWS Configuration
REACT_APP_AWS_REGION=$COGNITO_REGION
REACT_APP_COGNITO_USER_POOL_ID=$COGNITO_USER_POOL_ID
REACT_APP_COGNITO_CLIENT_ID=$COGNITO_CLIENT_ID
REACT_APP_COGNITO_IDENTITY_POOL_ID=$COGNITO_IDENTITY_POOL_ID

# WebSocket URL for queries
REACT_APP_WEBSOCKET_URL=$WEBSOCKET_URL

# OAuth Redirects
REACT_APP_REDIRECT_SIGN_IN=$CLOUDRONT_URL/
REACT_APP_REDIRECT_SIGN_OUT=$CLOUDFRONT_URL/
EOF

echo "📦 Rebuilding with CloudFront URL..."
npm run build

echo "📤 Uploading React build files to S3..."
aws s3 sync build/ s3://$BUCKET_NAME/ --region $AWS_DEFAULT_REGION --delete

echo "🔄 Invalidating CloudFront cache..."
aws cloudfront create-invalidation \
    --distribution-id $DISTRIBUTION_ID \
    --paths "/*" \
    --region $AWS_DEFAULT_REGION > /dev/null

# Save deployment info
cat > deployment-info.txt << EOF
# Multi-Tenant Security Analytics Frontend Deployment
# Generated on: $(date)

STACK_NAME=$STACK_NAME
S3_BUCKET=$BUCKET_NAME
CLOUDFRONT_URL=$CLOUDFRONT_URL
DISTRIBUTION_ID=$DISTRIBUTION_ID
AWS_REGION=$AWS_DEFAULT_REGION

# Frontend URL
FRONTEND_URL=$CLOUDFRONT_URL

# Backend Integration
ALB_URL=$ALB_URL
API_GATEWAY_URL=$ALB_URL
COGNITO_USER_POOL_ID=$COGNITO_USER_POOL_ID
COGNITO_CLIENT_ID=$COGNITO_CLIENT_ID
COGNITO_IDENTITY_POOL_ID=$COGNITO_IDENTITY_POOL_ID

# To update the frontend:
# 1. Update backend deployment if needed
# 2. ./deploy-frontend.sh (will auto-update .env from backend deployment_info.txt)
EOF

echo ""
echo "✅ Deployment Complete!"
echo "🌐 Access your frontend at: $CLOUDFRONT_URL"
echo "🔒 S3 bucket is private, accessed only through CloudFront"
echo "🛡️  Multi-Tenant Security Analytics Dashboard is ready!"
echo ""
echo "📄 Deployment info saved to: deployment-info.txt"
echo ""
echo "Note: CloudFront may take 5-10 more minutes to fully propagate globally."

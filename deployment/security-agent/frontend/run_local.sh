#!/bin/bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# Frontend Development Server Script

set -e

echo "🚀 Starting Multi-Tenant Security Analytics Frontend..."

# Kill any existing React development servers
echo "🔄 Checking for existing React servers..."
if lsof -ti:3000 >/dev/null 2>&1; then
    echo "⚠️  Killing existing server on port 3000..."
    kill -9 $(lsof -ti:3000) 2>/dev/null || true
    sleep 2
fi

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
else
    echo "✅ Dependencies already installed"
fi

# Display configuration
echo ""
echo "🔧 Frontend Configuration:"
echo "API Gateway URL: $(grep REACT_APP_API_GATEWAY_URL .env | cut -d'=' -f2)"
echo "Cognito User Pool: $(grep REACT_APP_COGNITO_USER_POOL_ID .env | cut -d'=' -f2)"
echo "Cognito Client ID: $(grep REACT_APP_COGNITO_CLIENT_ID .env | cut -d'=' -f2)"
echo ""

# Start development server
echo "🌐 Starting development server on http://localhost:3000"
echo ""

npm start
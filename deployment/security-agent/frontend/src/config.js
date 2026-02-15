// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

// AWS Configuration for Amplify v6
export const awsConfig = {
  Auth: {
    Cognito: {
      userPoolId: process.env.REACT_APP_COGNITO_USER_POOL_ID,
      userPoolClientId: process.env.REACT_APP_COGNITO_CLIENT_ID
    }
  }
};

export const wsConfig = {
  url: process.env.REACT_APP_WEBSOCKET_URL // WebSocket API Gateway for all queries
};
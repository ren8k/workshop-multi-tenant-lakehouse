// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

import { fetchAuthSession } from 'aws-amplify/auth';
import { wsConfig } from '../config';

class ApiService {

  async submitQuery(query, onProgress) {
    return this.submitWebSocketQuery(query, onProgress);
  }

  async submitWebSocketQuery(query, onProgress) {
    return new Promise(async (resolve, reject) => {
      try {
        // Get auth token
        const session = await fetchAuthSession();
        const token = session.tokens.idToken.toString();
        
        // WebSocket URL from config - backend handles routing internally
        const wsUrl = wsConfig.url;
        
        console.log('Connecting to WebSocket:', wsUrl);
        const ws = new WebSocket(wsUrl);
        
        ws.onopen = () => {
          console.log('WebSocket connected');
          // Send query with action field for route selection
          ws.send(JSON.stringify({
            action: 'query',
            query: query,
            jwt_token: token
          }));
        };
        
        ws.onmessage = (event) => {
          const message = JSON.parse(event.data);
          console.log('WebSocket message:', message);
          
          if (message.type === 'progress' || message.type === 'status' || message.type === 'test' || message.type === 'sql_info' || message.type === 'stream' || message.type === 'sql_detected' || message.type === 'processing' || message.type === 'tool_use' || message.type === 'tool_complete' || message.type === 'sql_query') {
            onProgress && onProgress(message);
          } else if (message.type === 'result') {
            // Don't close yet, wait for complete message
            resolve(message);
          } else if (message.type === 'success') {
            // Alternative result format
            resolve(message.data);
          } else if (message.type === 'complete') {
            // Now we can close
            ws.close();
          } else if (message.type === 'error') {
            ws.close();
            reject(new Error(message.message));
          }
        };
        
        ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          reject(new Error('WebSocket connection failed'));
        };
        
        ws.onclose = () => {
          console.log('WebSocket closed');
        };
        
        // Timeout after 10 minutes for long queries
        setTimeout(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.close();
            reject(new Error('Query timeout'));
          }
        }, 600000);
        
      } catch (error) {
        console.error('WebSocket query failed:', error);
        reject(error);
      }
    });
  }
}

export default new ApiService();
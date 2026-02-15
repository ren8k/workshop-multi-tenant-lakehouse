// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

import React, { useState, useEffect } from 'react';
import { signOut, fetchAuthSession } from 'aws-amplify/auth';
import apiService from '../services/apiService';

const QueryInterface = ({ user }) => {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [isSimpleAgent, setIsSimpleAgent] = useState(false);
  const [tenantInfo, setTenantInfo] = useState({ tenantId: 'Unknown', userRole: 'Unknown', tenantTier: 'Unknown' });
  const [progress, setProgress] = useState(null);
  const [streamingContent, setStreamingContent] = useState('');
  const [showStreaming, setShowStreaming] = useState(false);

  // Debug and extract tenant info from JWT token
  useEffect(() => {
    const extractTenantInfo = async () => {
      try {
        console.log('User object:', user);
        console.log('User attributes:', user?.attributes);
        
        const session = await fetchAuthSession();
        const idToken = session.tokens?.idToken?.toString();
        if (idToken) {
          const payload = JSON.parse(atob(idToken.split('.')[1]));
          console.log('JWT Token Payload:', payload);
          
          setTenantInfo({
            tenantId: payload.tenant_id || payload['custom:tenantId'] || 'Unknown',
            userRole: payload.user_role || payload['custom:userRole'] || 'Unknown',
            tenantTier: payload.tenant_tier || payload['custom:tenantTier'] || 'Unknown'
          });
        }
      } catch (error) {
        console.error('Error extracting tenant info:', error);
      }
    };
    extractTenantInfo();
  }, [user]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError(null);
    setResult(null);
    setProgress(null);
    setStreamingContent('');
    setShowStreaming(true);
    setIsSimpleAgent(false);

    try {
      const response = await apiService.submitQuery(query, (progressMsg) => {
        console.log('Progress update:', progressMsg);
        setProgress(progressMsg);
        
        // Handle streaming content
        if (progressMsg.type === 'stream') {
          setStreamingContent(progressMsg.accumulated || '');
        } else if (progressMsg.type === 'sql_query') {
          // Add SQL query to streaming content
          setStreamingContent(prev => prev + '\n🔍 SQL Query Detected:\n' + progressMsg.sql + '\n\n');
        } else if (progressMsg.type === 'tool_use') {
          // Add tool usage to streaming content
          setStreamingContent(prev => prev + '\n' + progressMsg.message);
        } else if (progressMsg.type === 'tool_complete') {
          // Add tool completion to streaming content
          setStreamingContent(prev => prev + progressMsg.message + '\n');
        }
      });
      console.log('Final response:', response);
      setResult(response);
      setProgress(null);
      setShowStreaming(false);
    } catch (err) {
      console.error('Query error:', err);
      setError(err.message);
      setProgress(null);
      setShowStreaming(false);
    } finally {
      setLoading(false);
    }
  };

  const handleTestAgent = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    setIsSimpleAgent(true);

    try {
      const response = await apiService.testSimpleAgent();
      setResult(response);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleNetworkTest = async () => {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await apiService.testNetworkConnectivity();
      setResult({ message: 'Network connectivity test successful', data: response });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleWebSocketQuery = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError(null);
    setResult(null);
    setProgress(null);
    setIsSimpleAgent(false);

    try {
      const response = await apiService.submitWebSocketQuery(query, (progressMsg) => {
        console.log('WebSocket progress:', progressMsg);
        setProgress(progressMsg);
      });
      setResult(response);
      setProgress(null);
    } catch (err) {
      setError(err.message);
      setProgress(null);
    } finally {
      setLoading(false);
    }
  };

  const handleSignOut = async () => {
    try {
      await signOut();
    } catch (error) {
      console.error('Error signing out:', error);
    }
  };

  return (
    <div style={{ maxWidth: '800px', margin: '0 auto', padding: '20px' }}>
      {/* Header */}
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        marginBottom: '30px',
        padding: '20px',
        backgroundColor: '#f5f5f5',
        borderRadius: '8px'
      }}>
        <div>
          <h1 style={{ margin: 0, color: '#333' }}>Security Analytics Agent</h1>
          <p style={{ margin: '5px 0 0 0', color: '#666' }}>
            Tenant: {tenantInfo.tenantId} | Role: {tenantInfo.userRole} | Tier: {tenantInfo.tenantTier} | 
            User: {user?.username}
          </p>
        </div>
        <button 
          onClick={handleSignOut}
          style={{
            padding: '8px 16px',
            backgroundColor: '#dc3545',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer'
          }}
        >
          Sign Out
        </button>
      </div>

      {/* Query Form */}
      <form onSubmit={handleSubmit} style={{ marginBottom: '30px' }}>
        <div style={{ marginBottom: '15px' }}>
          <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>
            Ask a security question:
          </label>
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g., Show me all failed login attempts in the last 24 hours"
            style={{
              width: '100%',
              minHeight: '100px',
              padding: '10px',
              border: '1px solid #ddd',
              borderRadius: '4px',
              fontSize: '14px',
              resize: 'vertical'
            }}
            disabled={loading}
          />
        </div>
        <button
          type="submit"
          disabled={loading || !query.trim()}
          style={{
            padding: '12px 24px',
            backgroundColor: loading ? '#ccc' : '#007bff',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: loading ? 'not-allowed' : 'pointer',
            fontSize: '16px',
            marginRight: '10px'
          }}
        >
          {loading ? 'Processing...' : 'Submit Query'}
        </button>

      </form>

      {/* Progress Display */}
      {progress && (
        <div style={{
          padding: '15px',
          backgroundColor: progress.type === 'sql_detected' ? '#fff3cd' : '#d1ecf1',
          color: progress.type === 'sql_detected' ? '#856404' : '#0c5460',
          border: `1px solid ${progress.type === 'sql_detected' ? '#ffeaa7' : '#bee5eb'}`,
          borderRadius: '4px',
          marginBottom: '20px'
        }}>
          <strong>{progress.type === 'sql_detected' ? '🔍 SQL:' : progress.type === 'processing' ? '✨ Processing:' : 'Status:'}</strong> {progress.message}
        </div>
      )}

      {/* Streaming Content Display */}
      {showStreaming && streamingContent && (
        <div style={{
          border: '1px solid #ddd',
          borderRadius: '8px',
          marginBottom: '20px',
          overflow: 'hidden'
        }}>
          <div style={{
            padding: '15px',
            backgroundColor: '#e8f5e8',
            color: '#2d5a2d',
            borderBottom: '1px solid #ddd',
            fontWeight: 'bold'
          }}>
            🤖 Agent Thinking (Live Stream)
          </div>
          <div style={{
            padding: '20px',
            backgroundColor: '#f8f9fa',
            maxHeight: '400px',
            overflowY: 'auto',
            fontFamily: 'monospace',
            fontSize: '14px',
            lineHeight: '1.5',
            whiteSpace: 'pre-wrap'
          }}>
            {streamingContent}
            <span style={{
              display: 'inline-block',
              width: '8px',
              height: '16px',
              backgroundColor: '#007bff',
              animation: 'blink 1s infinite'
            }}>|</span>
          </div>
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div style={{
          padding: '15px',
          backgroundColor: '#f8d7da',
          color: '#721c24',
          border: '1px solid #f5c6cb',
          borderRadius: '4px',
          marginBottom: '20px'
        }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Results Display */}
      {result && (
        <div style={{
          border: '1px solid #ddd',
          borderRadius: '8px',
          overflow: 'hidden'
        }}>
          {/* Handle different response formats based on endpoint */}
          {!isSimpleAgent ? (
            // WebSocket query response format
            <>
              {/* Status */}
              <div style={{
                padding: '15px',
                backgroundColor: result.status === 'SUCCESS' ? '#d4edda' : '#f8d7da',
                color: result.status === 'SUCCESS' ? '#155724' : '#721c24',
                borderBottom: '1px solid #ddd'
              }}>
                <strong>Status:</strong> {result.status || 'SUCCESS'}
              </div>

              {/* Results */}
              <div style={{ padding: '20px', backgroundColor: '#f8f9fa' }}>
                <h3 style={{ margin: '0 0 10px 0' }}>Security Analysis Results</h3>
                <div style={{ 
                  lineHeight: '1.6',
                  whiteSpace: 'pre-wrap',
                  fontFamily: 'inherit'
                }}>
                  {result.message || result.result || 'Analysis completed'}
                </div>
              </div>

              {/* Query Info */}
              {result.query && (
                <div style={{
                  padding: '15px',
                  backgroundColor: '#f8f9fa',
                  borderTop: '1px solid #ddd',
                  fontSize: '12px',
                  color: '#666'
                }}>
                  <strong>Original Query:</strong> {result.query}
                </div>
              )}
            </>
          ) : (
            // Simple agent response format
            <>
              {/* Status */}
              <div style={{
                padding: '15px',
                backgroundColor: result.error ? '#f8d7da' : '#d4edda',
                color: result.error ? '#721c24' : '#155724',
                borderBottom: '1px solid #ddd'
              }}>
                <strong>Status:</strong> {result.error ? 'ERROR' : 'SUCCESS'}
              </div>

              {!result.error && (
                <>
                  {/* Simple Agent Response */}
                  <div style={{ padding: '20px', backgroundColor: '#f8f9fa' }}>
                    <h3 style={{ margin: '0 0 10px 0' }}>Simple Agent Response</h3>
                    <p style={{ margin: 0, lineHeight: '1.6' }}>
                      {result.message || 'Simple agent test completed'}
                    </p>
                    {result.agent_response && (
                      <div style={{ marginTop: '10px', padding: '10px', backgroundColor: '#e9ecef', borderRadius: '4px' }}>
                        <strong>Agent Output:</strong> {result.agent_response}
                      </div>
                    )}
                  </div>

                  {/* Metadata */}
                  <div style={{
                    padding: '15px',
                    backgroundColor: '#f8f9fa',
                    borderTop: '1px solid #ddd',
                    fontSize: '12px',
                    color: '#666'
                  }}>
                    <strong>Request ID:</strong> {result.request_id}
                  </div>
                </>
              )}

              {result.error && (
                <div style={{ padding: '20px' }}>
                  <h4 style={{ margin: '0 0 10px 0', color: '#721c24' }}>Error Details</h4>
                  <p style={{ margin: 0, color: '#721c24' }}>
                    {result.error}
                  </p>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Example Queries */}
      <div style={{ marginTop: '40px', padding: '20px', backgroundColor: '#f8f9fa', borderRadius: '8px' }}>
        <h3 style={{ margin: '0 0 15px 0' }}>Example Queries</h3>
        <ul style={{ margin: 0, paddingLeft: '20px' }}>
          <li>Show me all failed login attempts in the last 24 hours</li>
          <li>Find network events from suspicious IP addresses</li>
          <li>List all endpoints running outdated software</li>
          <li>Show high severity CVEs affecting our environment</li>
          <li>Find authentication events for user john.doe</li>
        </ul>
      </div>

      {/* CSS for blinking cursor */}
      <style>{`
        @keyframes blink {
          0%, 50% { opacity: 1; }
          51%, 100% { opacity: 0; }
        }
      `}</style>
    </div>
  );
};

export default QueryInterface;
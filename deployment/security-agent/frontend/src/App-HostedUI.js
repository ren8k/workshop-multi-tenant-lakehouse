// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

import React, { useEffect, useState } from 'react';
import { Amplify, Auth, Hub } from 'aws-amplify';
import { awsConfig } from './config';
import QueryInterface from './components/QueryInterface';

// Configure Amplify
Amplify.configure(awsConfig);

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkAuthState();
    
    // Listen for auth events
    const hubListener = (data) => {
      const { payload } = data;
      if (payload.event === 'signIn') {
        setUser(payload.data);
      } else if (payload.event === 'signOut') {
        setUser(null);
      }
    };

    Hub.listen('auth', hubListener);
    return () => Hub.remove('auth', hubListener);
  }, []);

  const checkAuthState = async () => {
    try {
      const currentUser = await Auth.currentAuthenticatedUser();
      setUser(currentUser);
    } catch (error) {
      console.log('User not authenticated');
    } finally {
      setLoading(false);
    }
  };

  const signIn = async () => {
    try {
      await Auth.federatedSignIn();
    } catch (error) {
      console.error('Error signing in:', error);
    }
  };

  const signOut = async () => {
    try {
      await Auth.signOut();
      setUser(null);
    } catch (error) {
      console.error('Error signing out:', error);
    }
  };

  if (loading) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh' 
      }}>
        <div>Loading...</div>
      </div>
    );
  }

  if (!user) {
    return (
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100vh',
        backgroundColor: '#f8f9fa'
      }}>
        <div style={{
          textAlign: 'center',
          padding: '40px',
          backgroundColor: 'white',
          borderRadius: '8px',
          boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
          maxWidth: '400px'
        }}>
          <h1 style={{ margin: '0 0 20px 0', color: '#333' }}>
            Multi-Tenant Security Analytics
          </h1>
          <p style={{ margin: '0 0 30px 0', color: '#666' }}>
            Sign in to access your security data and analytics
          </p>
          <button
            onClick={signIn}
            style={{
              padding: '12px 24px',
              backgroundColor: '#007bff',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '16px',
              width: '100%'
            }}
          >
            Sign In with Cognito
          </button>
        </div>
      </div>
    );
  }

  return <QueryInterface user={user} signOut={signOut} />;
}

export default App;
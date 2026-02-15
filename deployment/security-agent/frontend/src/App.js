// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

import React, { useEffect, useState } from 'react';
import { Amplify } from 'aws-amplify';
import { getCurrentUser } from 'aws-amplify/auth';
import { Authenticator } from '@aws-amplify/ui-react';
import '@aws-amplify/ui-react/styles.css';
import { awsConfig } from './config';
import QueryInterface from './components/QueryInterface';

// Configure Amplify
Amplify.configure(awsConfig);

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    console.log('App component mounted');
    checkAuthState();
  }, []);

  const checkAuthState = async () => {
    try {
      console.log('Checking auth state...');
      const currentUser = await getCurrentUser();
      console.log('Current user:', currentUser);
      setUser(currentUser);
    } catch (error) {
      console.log('User not authenticated:', error);
    } finally {
      console.log('Setting loading to false');
      setLoading(false);
    }
  };

  console.log('App render - loading:', loading, 'user:', user);

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

  return (
    <div className="App">
      <Authenticator
        hideSignUp={true}
        components={{
          Header() {
            return (
              <div style={{ 
                textAlign: 'center', 
                padding: '20px',
                backgroundColor: '#f8f9fa',
                borderBottom: '1px solid #dee2e6'
              }}>
                <h2 style={{ margin: 0, color: '#333' }}>
                  Multi-Tenant Security Analytics
                </h2>
                <p style={{ margin: '5px 0 0 0', color: '#666' }}>
                  Sign in to access your security data
                </p>
              </div>
            );
          }
        }}
      >
        {({ signOut, user }) => (
          <QueryInterface user={user} signOut={signOut} />
        )}
      </Authenticator>
    </div>
  );
}

export default App;
# Security Analytics Frontend

React application for the Multi-Tenant Security Analytics Agent.

## Features

- **Authentication**: AWS Cognito integration (embedded or hosted UI)
- **Natural Language Queries**: Submit security questions in plain English
- **Real-time Results**: View insights, SQL queries, and execution metadata
- **Tenant Context**: Automatic tenant isolation and user context display
- **Responsive Design**: Clean, intuitive interface

## Setup

1. **Install Dependencies**:
   ```bash
   npm install
   ```

2. **Configure Environment**:
   ```bash
   cp .env.example .env
   ```
   
   Update `.env` with your AWS configuration:
   - `REACT_APP_COGNITO_USER_POOL_ID`
   - `REACT_APP_COGNITO_CLIENT_ID`
   - `REACT_APP_API_GATEWAY_URL`

3. **Start Development Server**:
   ```bash
   npm start
   ```

## Authentication Options

### Option 1: Embedded Authenticator (Default)
Uses `@aws-amplify/ui-react` Authenticator component with custom styling.

**File**: `src/App.js`

### Option 2: Hosted UI
Redirects to Cognito Hosted UI for authentication.

**To use Hosted UI**:
1. Rename `src/App.js` to `src/App-Embedded.js`
2. Rename `src/App-HostedUI.js` to `src/App.js`
3. Configure OAuth settings in Cognito User Pool

## Cognito User Pool Setup

Your Cognito User Pool must have these **custom attributes**:
- `custom:tenant_id` (String, Mutable)
- `custom:role` (String, Mutable)

### App Client Settings
- **Enabled Identity Providers**: Cognito User Pool
- **Callback URLs**: `http://localhost:3000/` (development)
- **Sign out URLs**: `http://localhost:3000/` (development)
- **OAuth Flow**: Authorization code grant
- **OAuth Scopes**: email, openid, profile

## API Integration

The app automatically:
1. Extracts JWT token from Cognito session
2. Includes `Authorization: Bearer <token>` header in API requests
3. Handles authentication errors and redirects

## Example Queries

- "Show me all failed login attempts in the last 24 hours"
- "Find network events from suspicious IP addresses"
- "List all endpoints running outdated software"
- "Show high severity CVEs affecting our environment"

## Project Structure

```
src/
├── components/
│   └── QueryInterface.js    # Main query interface
├── services/
│   └── apiService.js        # API client with auth
├── config.js                # AWS configuration
├── App.js                   # Main app (embedded auth)
├── App-HostedUI.js         # Alternative (hosted UI)
└── index.js                # Entry point
```

## Build for Production

```bash
npm run build
```

The build artifacts will be in the `build/` directory, ready for deployment to S3, CloudFront, or any static hosting service.
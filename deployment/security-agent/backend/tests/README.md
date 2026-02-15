# Backend Testing

This directory contains test scripts for the Multi-Tenant Security Analytics Backend.

## Test Scripts

### 1. `test_backend.py`
**Full end-to-end API testing with real Cognito authentication**

```bash
python3 test_backend.py
```

**Features:**
- Authenticates with Cognito User Pool
- Gets real JWT token
- Tests API Gateway endpoints
- Validates responses

**Requirements:**
- Valid Cognito user credentials
- Deployed API Gateway
- `boto3` and `requests` libraries

### 2. `test_requests.sh`
**cURL-based API testing**

```bash
# Update JWT_TOKEN and API_GATEWAY_URL in the script first
./test_requests.sh
```

**Features:**
- Direct HTTP requests to API Gateway
- Multiple test queries
- JSON response formatting with `jq`

**Requirements:**
- Valid JWT token (get from Cognito)
- Deployed API Gateway URL
- `curl` and `jq` installed

### 3. `test_lambda_local.py`
**Local Lambda function testing (without deployment)**

```bash
python3 test_lambda_local.py
```

**Features:**
- Tests Lambda function locally
- Mock JWT token
- No AWS deployment needed
- Quick development testing

**Requirements:**
- Lambda dependencies installed locally
- Mock data setup

## Testing Strategy

### **Phase 1: Local Development**
```bash
cd tests
python3 test_lambda_local.py
```

### **Phase 2: Deployed Backend**
```bash
# Deploy backend first
cd ..
./deploy-cognito-trigger.sh
./deploy.sh

# Then test
cd tests
python3 test_backend.py
```

### **Phase 3: Manual API Testing**
```bash
# Get JWT token from Cognito console or test_backend.py
# Update test_requests.sh with token and URL
./test_requests.sh
```

## Test Queries

All scripts test these security analytics queries:
- "Show me all failed login attempts in the last 24 hours"
- "Find network events from suspicious IP addresses"
- "List all endpoints running outdated software"
- "Show high severity CVEs affecting our environment"

## Expected Response Format

```json
{
  "result": {
    "status": "SUCCESS",
    "sql_query": "SELECT * FROM AuthenticationLogs WHERE success = false",
    "insights": "Found 15 failed login attempts...",
    "query_execution_id": "12345-abcde"
  },
  "tenant_context": {
    "tenant_id": "tenant-123",
    "user_id": "user-456",
    "role": "analyst",
    "tenant_tier": "standard"
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Troubleshooting

### Authentication Issues
- Verify Cognito User Pool configuration
- Check custom attributes are set on user
- Ensure Cognito trigger is deployed

### API Gateway Issues
- Verify API Gateway URL
- Check CORS configuration
- Validate JWT token format

### Lambda Issues
- Check CloudWatch logs
- Verify IAM permissions
- Test Identity Pool integration
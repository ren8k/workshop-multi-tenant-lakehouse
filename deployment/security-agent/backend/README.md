# Multi-Tenant Security Analytics Backend

This backend implements the core functionality for the Multi-Tenant Security Analytics Agent using:
- **API Gateway** → **Lambda** → **Strands Agent** → **Athena** → **Lake Formation**
- **Cognito Lambda Trigger** for Identity Pool attribute mapping

## Architecture

```
User Login → User Pool → Cognito Trigger → Enhanced JWT → API Gateway → Lambda
                              ↓                           ↓              ↓
                    Maps tenant attributes        Cognito Auth    Identity Pool Exchange
                              ↓                           ↓              ↓
                    Enhanced JWT claims              Validates JWT   User AWS Credentials
                                                                     ↓
                                                            Strands Agent → Athena → Lake Formation
                                                                     ↓              ↓
                                                                NL to SQL    Automatic Tenant Isolation
```

## Key Features

- **Automatic Tenant Isolation**: Lake Formation enforces tenant data isolation without manual SQL filtering
- **Enhanced JWT Claims**: Cognito Lambda Trigger maps custom attributes to Identity Pool-compatible claims
- **Identity Pool Integration**: Lambda exchanges JWT for user AWS credentials with tenant context
- **Natural Language Processing**: Strands Agent converts NL to SQL without tenant_id injection
- **Security Validation**: Only SELECT operations allowed, Lake Formation handles data access control
- **Audit Logging**: Complete request/response logging plus Lake Formation access logs
- **Scalable Architecture**: No manual tenant filtering, automatic isolation at infrastructure level

## Components

### Lambda Functions
- **`lambda/query_handler.py`**: 
  - Handles natural language queries via Strands Agent
  - Exchanges JWT for Identity Pool credentials within Lambda
  - Uses user credentials (not Lambda role) for Athena queries
  - Eliminates manual tenant_id filtering
- **`lambda/cognito_trigger.py`**: 
  - **CRITICAL**: Pre Token Generation trigger for User Pool
  - Maps `custom:tenantId` → `tenant_id` for Identity Pool compatibility
  - Maps `custom:userRole` → `user_role` and `custom:tenantTier` → `tenant_tier`
  - Enables Lake Formation to access tenant attributes from AWS credentials
  - **Required for tenant isolation** - without this, no tenant context reaches Lake Formation

### Infrastructure
- `infrastructure/lambda.yaml`: Main Lambda function and IAM roles
- `infrastructure/api_gateway.yaml`: API Gateway with Cognito auth
- `infrastructure/cognito_trigger.yaml`: Cognito Lambda Trigger setup

### Database Schema (Lake Formation Managed)
**Tenant-Specific Tables** (automatic tenant isolation via Lake Formation):
- `NetworkEvents`: Network traffic events (tenant_id, event_time, source_ip, dest_ip, protocol, action)
- `AuthenticationLogs`: Login/logout events (tenant_id, timestamp, user_id, success, source_ip)
- `Endpoints`: Managed endpoints (tenant_id, endpoint_id, hostname, os_type, last_seen)
- `InstalledSoftware`: Software inventory (tenant_id, endpoint_id, software_name, version)

**Global Tables** (read-only access, no tenant filtering):
- `CVEInfo`: Vulnerability information (cve_id, severity, description)
- `ThreatIntelligence`: Threat indicators (indicator, type, severity, source)

**Lake Formation Benefits**:
- **Automatic Row-Level Security**: Filters data based on `tenant_id` from user credentials
- **Column-Level Permissions**: Different access by `tenant_tier` (standard/premium/enterprise)
- **No Manual SQL Filtering**: Strands Agent generates clean SQL, Lake Formation adds tenant filters
- **Complete Audit Trail**: All data access logged with user and tenant context
- **Scalable**: No Lambda code changes needed for new tenants or tables

## Deployment

1. **Install Dependencies**:
   ```bash
   cd lambda
   pip install -r requirements.txt -t .
   ```

2. **Deploy Cognito Lambda Trigger**:
   ```bash
   source ../.aws/credentials
   ./deploy-cognito-trigger.sh
   ```

3. **Deploy Main Backend**:
   ```bash
   ./deploy.sh
   ```

4. **Configure Lake Formation** (REQUIRED for tenant isolation):
   
   **a. Register S3 locations as tables in Glue Catalog:**
   ```bash
   # Register S3 locations with Lake Formation
   aws lakeformation register-resource \
       --resource-arn arn:aws:s3:::security-analytics-data/ \
       --use-service-linked-role
   
   # Create Glue tables for each data source
   aws glue create-table --database-input Name=security_analytics \
       --table-input Name=NetworkEvents,StorageDescriptor=...
   ```
   
   **b. Configure permissions based on Identity Pool attributes:**
   ```bash
   # Grant permissions using tenant attributes
   aws lakeformation grant-permissions \
       --principal DataLakePrincipalIdentifier=arn:aws:iam::ACCOUNT:role/IdentityPoolRole \
       --permissions SELECT \
       --resource Table=NetworkEvents \
       --permissions-with-grant-option \
           --resource-policy '{"tenant_id": "${saml:tenant_id}"}'
   ```
   
   **c. Set up row-level security using tenant attributes:**
   ```bash
   # Create row-level security filter
   aws lakeformation create-data-cells-filter \
       --table-data TableCatalogId=ACCOUNT,DatabaseName=security_analytics,TableName=NetworkEvents \
       --column-names "*" \
       --row-filter "tenant_id = '${saml:tenant_id}'"
   ```
   
   ****This eliminates manual tenant_id injection while maintaining strict isolation through Lake Formation!**

## Critical Flow Explanation

### Why Each Component is Essential:

1. **Cognito Trigger (MANDATORY)**:
   - Maps `custom:tenantId` to `tenant_id` in JWT claims
   - Without this, Identity Pool receives JWT with unmappable custom attributes
   - Lake Formation would have NO tenant context for isolation

2. **Identity Pool Exchange in Lambda**:
   - Lambda exchanges enhanced JWT for AWS credentials with tenant attributes
   - These credentials carry tenant context to all AWS service calls
   - Athena queries execute with user credentials (not Lambda role)

3. **Lake Formation Integration**:
   - Receives AWS credentials with tenant attributes from Identity Pool
   - Automatically applies row-level security based on `tenant_id`
   - No manual SQL filtering needed in application code

### Complete Request Flow:
```
1. User logs in → Cognito Trigger enhances JWT with tenant_id
2. Frontend calls API → API Gateway validates enhanced JWT
3. Lambda receives JWT → Exchanges for Identity Pool credentials
4. Lambda calls Athena → Uses user credentials with tenant context
5. Lake Formation sees tenant_id → Automatically filters data
6. Results returned → Only tenant's data included
```

**Result**: Zero cross-tenant data access with no manual filtering code!**

5. **Deploy API Gateway**:
   ```bash
   aws cloudformation deploy \
       --template-file infrastructure/api_gateway.yaml \
       --stack-name security-analytics-api \
       --parameter-overrides \
           LambdaFunctionArn=<LAMBDA_ARN> \
           CognitoUserPoolArn=<COGNITO_ARN>
   ```

## API Usage

### Endpoint
```
POST /query
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json
```

### Request Body
```json
{
  "query": "Show me all failed login attempts in the last 24 hours"
}
```

### Response
```json
{
  "result": {
    "status": "SUCCESS",
    "sql_query": "SELECT * FROM AuthenticationLogs WHERE tenant_id = 'tenant123' AND success = false AND timestamp > NOW() - INTERVAL '24' HOUR",
    "insights": "Found 15 failed login attempts in the last 24 hours...",
    "query_execution_id": "12345-abcde"
  },
  "tenant_context": {
    "tenant_id": "tenant123",
    "user_id": "user456"
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Security Features

1. **Authentication**: JWT tokens from Cognito
2. **Authorization**: Tenant context extraction
3. **Query Validation**: Only SELECT operations
4. **Tenant Isolation**: Automatic tenant_id filtering
5. **Audit Logging**: All requests logged with context

## Configuration

### Cognito Pools (Pre-configured)
- **User Pool**: `LakehouseTenantsUserPool` (us-west-2_9ds2h5gYh)
- **Identity Pool**: `LakehouseTenantsIdentityPool` (us-west-2:863a0928-0253-4eb6-9814-2115b9861662)
- **App Client**: 14omhqmpv72dftnnmhumsl24ef

### Custom Attributes
- `custom:tenantId`: Tenant identifier for data isolation
- `custom:userRole`: User role (analyst, admin, etc.)
- `custom:tenantTier`: Tenant tier (standard, premium, enterprise)

### Environment Variables
- `ATHENA_WORKGROUP`: Athena workgroup name
- `S3_RESULTS_BUCKET`: S3 bucket for query results  
- `LOG_LEVEL`: Logging level (INFO, DEBUG)
- `IDENTITY_POOL_ID`: LakehouseTenantsIdentityPool ID (configurable via CloudFormation)
- `USER_POOL_PROVIDER`: Cognito User Pool provider URL (auto-generated from parameters)

## Testing

Example natural language queries:
- "Show me all network events from the last hour"
- "Find failed authentication attempts for user john.doe"
- "List all endpoints running Windows"
- "Show high severity CVEs affecting our software"
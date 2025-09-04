# Security Policies Guide

This document explains the security policies, row-level security, field-level RBAC, and data residency features implemented in SBH.

## Overview

The security system provides:

- **Policy Engine**: Central, testable access control
- **Row-Level Security (RLS)**: Tenant isolation at database level
- **Field-Level RBAC**: Sensitive field redaction by role
- **Data Residency**: Per-tenant region routing
- **GDPR Compliance**: Export and deletion operations
- **Backup & Restore**: Secure data backup and recovery

## Policy Engine

### Core Concepts

#### User Context
```python
@dataclass
class UserContext:
    user_id: str
    tenant_id: str
    role: Role
    region: Optional[str] = None
```

#### Resource
```python
@dataclass
class Resource:
    type: str
    id: Optional[str] = None
    tenant_id: Optional[str] = None
    owner_id: Optional[str] = None
```

#### Actions
- `CREATE`: Create new resources
- `READ`: Read existing resources
- `UPDATE`: Modify existing resources
- `DELETE`: Delete resources
- `EXPORT`: Export data
- `BACKUP`: Create backups
- `RESTORE`: Restore backups

#### Roles
- `VIEWER`: Read-only access
- `MEMBER`: Read/write access to own resources
- `ADMIN`: Full access within tenant
- `OWNER`: Complete system access

### Policy Evaluation

#### Basic Usage
```python
from src.security.policy import policy_engine, UserContext, Action, Resource, Role

# Create user context
user_ctx = UserContext(
    user_id='user-1',
    tenant_id='tenant-1',
    role=Role.ADMIN
)

# Create resource
resource = Resource(
    type='users',
    id='user-2',
    tenant_id='tenant-1'
)

# Check permissions
can_read = policy_engine.can(user_ctx, Action.READ, resource)
can_create = policy_engine.can(user_ctx, Action.CREATE, resource)
```

#### Field-Level Redaction
```python
# Original data
user_data = {
    'id': 'user-1',
    'email': 'user@example.com',
    'password_hash': 'hashed_password',
    'first_name': 'John',
    'last_name': 'Doe'
}

# Redact for viewer role
redacted_data = policy_engine.redact(user_data, Role.VIEWER, 'users')
# Result: password_hash and email are redacted
```

## Row-Level Security (RLS)

### Database-Level Filters

RLS automatically applies tenant filters to all database queries:

```python
from src.security.rls import rls_manager

# Apply tenant filter to query
query = session.query(User)
filtered_query = rls_manager.with_tenant(query, tenant_id)

# Get by ID with tenant check
user = rls_manager.get_by_id_and_tenant(user_id, tenant_id)

# Create with tenant context
user = rls_manager.create_with_tenant(tenant_id, email='user@example.com')
```

### Session Events

RLS automatically sets tenant_id on new records:

```python
# Before flush event
def _before_flush(self, session: Session, context, instances):
    tenant_id = session.info.get('tenant_id')
    for instance in session.new:
        if hasattr(instance, 'tenant_id') and not instance.tenant_id:
            instance.tenant_id = tenant_id
```

### Decorator Usage

```python
from src.security.rls import enforce_rls_decorator

@enforce_rls_decorator
def create_user(session, user_data):
    # Tenant context is automatically enforced
    user = User(**user_data)
    session.add(user)
    return user
```

## Field-Level RBAC

### Resource Definitions

```python
RESOURCES = {
    'users': ResourceDefinition(
        name='users',
        actions=[Action.READ, Action.CREATE, Action.UPDATE, Action.DELETE],
        fields=['id', 'email', 'first_name', 'last_name', 'role', 'is_active'],
        sensitive_fields=['password_hash', 'api_key_hash'],
        owner_field='id',
        tenant_field='tenant_id'
    ),
    'payments': ResourceDefinition(
        name='payments',
        actions=[Action.READ, Action.CREATE, Action.UPDATE],
        fields=['id', 'amount', 'currency', 'status', 'provider_customer_id'],
        sensitive_fields=['provider_customer_id', 'payment_method_token'],
        owner_field='user_id',
        tenant_field='tenant_id'
    )
}
```

### Field Visibility by Role

#### Users Resource
- **VIEWER**: `id`, `first_name`, `last_name`, `role`, `is_active`
- **MEMBER**: `id`, `email`, `first_name`, `last_name`, `role`, `is_active`, `created_at`
- **ADMIN**: `id`, `email`, `first_name`, `last_name`, `role`, `is_active`, `created_at`, `updated_at`
- **OWNER**: All fields (except sensitive)

#### Payments Resource
- **VIEWER**: `id`, `amount`, `currency`, `status`, `created_at`
- **MEMBER**: `id`, `amount`, `currency`, `status`, `created_at`
- **ADMIN**: `id`, `amount`, `currency`, `status`, `provider_customer_id`, `created_at`, `updated_at`
- **OWNER**: All fields (except sensitive)

#### Analytics Resource
- **VIEWER**: `aggregates`, `summary`
- **MEMBER**: `aggregates`, `summary`, `basic_events`
- **ADMIN**: `aggregates`, `summary`, `raw_events`, `user_data`
- **OWNER**: All fields (except sensitive)

### Sensitive Field Redaction

Sensitive fields are automatically redacted:

```python
# Original data
payment_data = {
    'id': 'payment-1',
    'amount': 100,
    'currency': 'USD',
    'provider_customer_id': 'cus_123456',
    'payment_method_token': 'tok_123456'
}

# Redacted for viewer
redacted = policy_engine.redact(payment_data, Role.VIEWER, 'payments')
# Result: provider_customer_id and payment_method_token are "•••"
```

## Data Residency

### Region Configuration

```python
REGIONS = {
    'us-east-1': RegionConfig(
        region='us-east-1',
        s3_bucket='sbh-files-us-east-1',
        s3_prefix='files/',
        enabled=True
    ),
    'eu-west-1': RegionConfig(
        region='eu-west-1',
        s3_bucket='sbh-files-eu-west-1',
        s3_prefix='files/',
        enabled=True
    )
}
```

### Tenant Region Mapping

```python
# Get tenant region
region = residency_manager.get_tenant_region(tenant_id)

# Get storage configuration
storage_config = residency_manager.get_storage_config(tenant_id)

# Validate region access
can_access = residency_manager.validate_region_access(tenant_id, region)
```

### Storage Routing

```python
# Get presigned URL configuration
url_config = residency_manager.get_presigned_url_config(tenant_id, file_path)

# Get backup storage configuration
backup_config = residency_manager.get_backup_storage_config(tenant_id)
```

## Flask Route Protection

### Decorators

#### Enforce Policy
```python
from src.security.decorators import enforce, Action

@app.route('/api/users/<id>', methods=['GET'])
@enforce(Action.READ, 'users')
def get_user(id):
    # Policy is automatically enforced
    return user_service.get_user(id)
```

#### Require Role
```python
from src.security.decorators import require_role, Role

@app.route('/api/admin/backup', methods=['POST'])
@require_role(Role.ADMIN)
def create_backup():
    # Only admins can access
    return backup_service.create_backup()
```

#### Require Tenant Context
```python
from src.security.decorators import require_tenant_context

@app.route('/api/data', methods=['GET'])
@require_tenant_context
def get_data():
    # Tenant context is required
    return data_service.get_data()
```

#### Rate Limit GDPR
```python
from src.security.decorators import rate_limit_gdpr

@app.route('/api/gdpr/export', methods=['POST'])
@rate_limit_gdpr(max_requests=5, window_seconds=3600)
def export_data():
    # Rate limited to 5 requests per hour
    return gdpr_service.export_data()
```

## GDPR Operations

### Data Export

```python
# Export user data
export_result = gdpr_service.export_user_data(
    user_id='user-1',
    tenant_id='tenant-1',
    user_ctx=user_context
)

# Result includes:
# - User profile data
# - User files list
# - User analytics data
# - Download URL (expires in 1 hour)
```

### Data Deletion

```python
# Delete user data
delete_result = gdpr_service.delete_user_data(
    user_id='user-1',
    tenant_id='tenant-1',
    user_ctx=user_context
)

# Result includes:
# - User soft deleted
# - Files deleted
# - Analytics anonymized
# - Audit trail maintained
```

## Backup & Restore

### Creating Backups

```python
# Create full backup
backup_result = backup_service.create_backup(
    tenant_id='tenant-1',
    user_ctx=user_context,
    backup_type='full'
)

# Result includes:
# - Database backup
# - File backup
# - Manifest with checksums
# - S3 storage location
```

### Restoring Backups

```python
# Restore backup
restore_result = backup_service.restore_backup(
    backup_id='backup_20240115_1200',
    tenant_id='tenant-1',
    user_ctx=user_context
)

# Result includes:
# - Database restored
# - Files restored
# - Validation results
```

## Monitoring & Analytics

### Policy Metrics

Track policy denials and redactions:

```python
# Policy denial event
analytics.track(
    tenant_id=tenant_id,
    event='policy.deny',
    user_id=user_id,
    source='security',
    props={
        'action': 'read',
        'resource_type': 'users',
        'reason': 'tenant_mismatch'
    }
)

# Field redaction event
analytics.track(
    tenant_id=tenant_id,
    event='policy.redact',
    user_id=user_id,
    source='security',
    props={
        'role': 'viewer',
        'resource_type': 'users',
        'redacted_fields': ['password_hash', 'email']
    }
)
```

### Security Events

- `policy.deny`: Policy denial
- `policy.redact`: Field redaction
- `backup.created`: Backup creation
- `backup.restored`: Backup restoration
- `gdpr.export`: Data export
- `gdpr.delete`: Data deletion
- `residency.region_access`: Region access

## Best Practices

### Policy Design
1. **Principle of Least Privilege**: Grant minimum necessary permissions
2. **Role Hierarchy**: Use clear role progression
3. **Resource Isolation**: Ensure tenant isolation
4. **Field Sensitivity**: Identify and protect sensitive fields

### Implementation
1. **Consistent Enforcement**: Apply policies consistently
2. **Audit Logging**: Log all security events
3. **Testing**: Test policies thoroughly
4. **Documentation**: Document policy decisions

### Security
1. **Input Validation**: Validate all inputs
2. **Output Sanitization**: Sanitize all outputs
3. **Error Handling**: Handle errors securely
4. **Monitoring**: Monitor for security events

## Troubleshooting

### Common Issues

#### Policy Denials
```python
# Check user context
print(f"User: {user_ctx.user_id}")
print(f"Tenant: {user_ctx.tenant_id}")
print(f"Role: {user_ctx.role}")

# Check resource
print(f"Resource: {resource.type}")
print(f"Resource Tenant: {resource.tenant_id}")

# Test policy
can_access = policy_engine.can(user_ctx, action, resource)
print(f"Can access: {can_access}")
```

#### RLS Issues
```python
# Check tenant context
tenant_id = get_current_tenant_id()
print(f"Current tenant: {tenant_id}")

# Check session tenant
session_tenant = session.info.get('tenant_id')
print(f"Session tenant: {session_tenant}")
```

#### Field Redaction
```python
# Check field visibility
visible_fields = policy_engine.visible_fields(role, resource_type)
print(f"Visible fields: {visible_fields}")

# Check sensitive fields
sensitive_fields = policy_engine.sensitive_fields.get(resource_type, [])
print(f"Sensitive fields: {sensitive_fields}")
```

### Debug Commands

#### Test Policy
```bash
curl -X POST https://api.example.com/api/security/policy/test \
  -H "Authorization: Bearer <token>" \
  -H "X-Tenant-Slug: <tenant>" \
  -d '{
    "action": "read",
    "resource_type": "users",
    "resource_id": "user-1"
  }'
```

#### Test RLS
```bash
curl -X POST https://api.example.com/api/security/rls/test \
  -H "Authorization: Bearer <token>" \
  -H "X-Tenant-Slug: <tenant>" \
  -d '{
    "test_tenant_id": "other-tenant"
  }'
```

#### Test Redaction
```bash
curl -X POST https://api.example.com/api/security/redaction/test \
  -H "Authorization: Bearer <token>" \
  -H "X-Tenant-Slug: <tenant>" \
  -d '{
    "resource_type": "users",
    "resource_data": {
      "id": "user-1",
      "email": "user@example.com",
      "password_hash": "hashed_password"
    }
  }'
```

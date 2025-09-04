# Multi-Tenancy Guide

This document explains how multi-tenancy works in SBH and how to configure it for different environments.

## Overview

SBH supports multi-tenancy with complete data isolation between tenants. Every request runs in a tenant context, and all data (projects, files, builder states, etc.) is scoped to the current tenant.

## Tenant Resolution

### Development Environment

In development, tenants are resolved in the following order:

1. **Header**: `X-Tenant-Slug: tenant-name`
2. **Query Parameter**: `?tenant=tenant-name`
3. **Cookie**: `tenant=tenant-name`

Example:
```bash
# Using header
curl -H "X-Tenant-Slug: primary" http://localhost:5001/api/tenants/me

# Using query parameter
curl "http://localhost:5001/api/tenants/me?tenant=primary"

# Using cookie
curl -b "tenant=primary" http://localhost:5001/api/tenants/me
```

### Production Environment

In production, tenants are resolved via subdomains:

- `primary.your-domain.com` → tenant slug: `primary`
- `acme.your-domain.com` → tenant slug: `acme`
- `demo.your-domain.com` → tenant slug: `demo`

The system also supports header fallback if enabled via `ALLOW_HEADER_TENANT=true`.

## Tenant Management

### Creating Tenants

```bash
# Create a new tenant
curl -X POST http://localhost:5001/api/tenants \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Acme Corp",
    "slug": "acme"
  }'
```

### Listing User's Tenants

```bash
# Get all tenants for current user
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:5001/api/tenants/me
```

### Inviting Users to Tenants

```bash
# Invite user to tenant
curl -X POST http://localhost:5001/api/tenants/invite \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "X-Tenant-Slug: acme" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "role": "member"
  }'
```

## Role-Based Access Control (RBAC)

### Tenant Roles

- **Owner**: Full control over tenant, can manage members and settings
- **Admin**: Can manage projects and invite users
- **Member**: Can create and manage projects
- **Viewer**: Read-only access to tenant resources

### Role Hierarchy

```
Owner > Admin > Member > Viewer
```

### Using Role Decorators

```python
from src.tenancy.decorators import tenant_owner, tenant_admin, tenant_member

@app.route('/admin-only')
@tenant_admin
def admin_only_endpoint():
    return "Admin only"

@app.route('/owner-only')
@tenant_owner
def owner_only_endpoint():
    return "Owner only"
```

## Data Isolation

### File Storage

Files are automatically prefixed with tenant ID:

- **Local Storage**: `instance/uploads/tenants/{tenant_id}/stores/{store_name}/`
- **S3 Storage**: `s3://bucket/tenants/{tenant_id}/stores/{store_name}/`

### Database Tables

All relevant tables include a `tenant_id` column:

- `projects`
- `builder_states`
- `audit_events`
- `file_store_configs`

### API Endpoints

All builder and file endpoints are tenant-scoped:

- `/api/builder/save` - Requires tenant context
- `/api/builder/generate-build` - Requires tenant context
- `/api/files/{store}/upload` - Files stored in tenant prefix
- `/api/files/{store}/{filename}` - Files served from tenant prefix

## JWT Token Integration

JWT tokens include tenant context when available:

```json
{
  "user_id": "user-123",
  "email": "user@example.com",
  "role": "user",
  "ten": "tenant-456",  // Tenant ID when in tenant context
  "exp": 1640995200
}
```

## Environment Configuration

### Development

```bash
# Enable auto-tenant creation in development
export FEATURE_AUTO_TENANT_DEV=true

# Allow header-based tenant resolution
export ALLOW_HEADER_TENANT=true
```

### Production

```bash
# Disable auto-tenant creation
export FEATURE_AUTO_TENANT_DEV=false

# Disable header-based tenant resolution (use subdomains)
export ALLOW_HEADER_TENANT=false
```

## Custom Domains

### Setting Up Custom Domains

1. **DNS Configuration**:
   ```
   tenant1.your-domain.com → CNAME → your-app.elasticbeanstalk.com
   tenant2.your-domain.com → CNAME → your-app.elasticbeanstalk.com
   ```

2. **SSL Certificates**:
   - Use wildcard certificate: `*.your-domain.com`
   - Or individual certificates per tenant

3. **Load Balancer Configuration**:
   - Configure ALB to route subdomains to your application
   - Set up SSL termination

### Example DNS Setup

```bash
# Add DNS records
aws route53 create-record-set \
  --hosted-zone-id Z1234567890 \
  --name "tenant1.your-domain.com" \
  --type CNAME \
  --ttl 300 \
  --resource-records "your-app.elasticbeanstalk.com"
```

## Stripe Integration

### Per-Tenant Billing

Each tenant can have its own Stripe customer:

```python
# Get tenant's Stripe customer
tenant = get_current_tenant()
stripe_customer_id = tenant.stripe_customer_id

# Create subscription for tenant
subscription = stripe.Subscription.create(
    customer=stripe_customer_id,
    items=[{'price': 'price_123'}]
)
```

### Subscription Management

```python
# Check tenant subscription status
def current_tenant_subscription():
    tenant = get_current_tenant()
    if tenant.stripe_customer_id:
        # Get subscription from Stripe
        customer = stripe.Customer.retrieve(tenant.stripe_customer_id)
        subscriptions = stripe.Subscription.list(customer=customer.id)
        return subscriptions.data[0] if subscriptions.data else None
    return None
```

## S3 Prefixing & Data Export

### S3 Structure

```
s3://your-bucket/
├── tenants/
│   ├── tenant-1/
│   │   ├── stores/
│   │   │   ├── uploads/
│   │   │   └── documents/
│   │   └── exports/
│   └── tenant-2/
│       ├── stores/
│       └── exports/
└── shared/
    └── templates/
```

### Data Export

```python
# Export tenant data
def export_tenant_data(tenant_id):
    # Export files
    s3_client.list_objects_v2(
        Bucket='your-bucket',
        Prefix=f'tenants/{tenant_id}/'
    )
    
    # Export database records
    projects = session.query(Project).filter(
        Project.tenant_id == tenant_id
    ).all()
    
    return {
        'files': files,
        'projects': projects
    }
```

## Monitoring & Observability

### Tenant-Scoped Metrics

```python
# Track metrics per tenant
from src.obs.metrics import tenant_requests_total

def track_tenant_request(tenant_id):
    tenant_requests_total.labels(tenant_id=tenant_id).inc()
```

### Audit Logging

All audit events include tenant context:

```python
# Audit tenant actions
audit_event('tenant_created', {
    'tenant_id': tenant.id,
    'tenant_slug': tenant.slug,
    'created_by': user_id
})
```

### Health Checks

Health checks include tenant information:

```json
{
  "status": "healthy",
  "tenant": {
    "id": "tenant-123",
    "slug": "acme",
    "status": "active"
  }
}
```

## Migration Guide

### From Single-Tenant to Multi-Tenant

1. **Run Migration**:
   ```bash
   alembic upgrade head
   ```

2. **Create Default Tenant**:
   ```python
   # Create primary tenant
   tenant = Tenant(
       slug='primary',
       name='Primary Tenant',
       plan='free',
       status='active'
   )
   ```

3. **Migrate Existing Data**:
   ```python
   # Link existing projects to primary tenant
   session.execute("""
       UPDATE projects 
       SET tenant_id = (SELECT id FROM tenants WHERE slug = 'primary')
       WHERE tenant_id IS NULL
   """)
   ```

### Testing Multi-Tenancy

```python
# Test tenant isolation
def test_tenant_isolation():
    # Create two tenants
    tenant1 = create_tenant('tenant1')
    tenant2 = create_tenant('tenant2')
    
    # Upload file to tenant1
    upload_file(tenant1, 'test.txt')
    
    # Verify file not accessible in tenant2
    assert not file_exists(tenant2, 'test.txt')
```

## Troubleshooting

### Common Issues

1. **Tenant Not Found**:
   - Check tenant slug format (lowercase, hyphens only)
   - Verify tenant exists in database
   - Check subdomain configuration

2. **Permission Denied**:
   - Verify user is member of tenant
   - Check user role permissions
   - Ensure JWT token is valid

3. **Data Isolation Issues**:
   - Verify tenant_id is set on all operations
   - Check storage provider tenant prefixing
   - Review database queries for tenant filtering

### Debug Commands

```bash
# Check tenant resolution
curl -H "X-Tenant-Slug: test" http://localhost:5001/readiness

# Verify tenant context in logs
grep "Request for tenant" logs/app.log

# Check database tenant isolation
sqlite3 instance/sbh.db "SELECT * FROM tenants;"
```

## Best Practices

1. **Always Use Tenant Context**: Never bypass tenant scoping
2. **Validate Tenant Access**: Check user membership before operations
3. **Use Role-Based Permissions**: Implement proper RBAC
4. **Monitor Tenant Usage**: Track resource usage per tenant
5. **Backup Per Tenant**: Implement tenant-specific backups
6. **Test Isolation**: Regularly test cross-tenant data isolation

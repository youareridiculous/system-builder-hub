# Data Residency Guide

This document explains the data residency features, region configuration, and storage routing implemented in SBH.

## Overview

Data residency ensures that tenant data is stored and processed in specific geographic regions to comply with data protection regulations and business requirements.

### Key Features

- **Region Configuration**: Per-tenant region assignment
- **Storage Routing**: S3 bucket/prefix routing by region
- **Database Residency**: Region tagging for audit and compliance
- **Presigned URL Routing**: Region-aware file access
- **Backup Residency**: Region-specific backup storage

## Region Configuration

### Supported Regions

```python
REGIONS = {
    'us-east-1': RegionConfig(
        region='us-east-1',
        s3_bucket='sbh-files-us-east-1',
        s3_prefix='files/',
        enabled=True
    ),
    'us-west-2': RegionConfig(
        region='us-west-2',
        s3_bucket='sbh-files-us-west-2',
        s3_prefix='files/',
        enabled=True
    ),
    'eu-west-1': RegionConfig(
        region='eu-west-1',
        s3_bucket='sbh-files-eu-west-1',
        s3_prefix='files/',
        enabled=True
    ),
    'ap-southeast-1': RegionConfig(
        region='ap-southeast-1',
        s3_bucket='sbh-files-ap-southeast-1',
        s3_prefix='files/',
        enabled=True
    )
}
```

### Region Mapping

| Region | Location | S3 Bucket | Status |
|--------|----------|-----------|---------|
| us-east-1 | US East (N. Virginia) | sbh-files-us-east-1 | Active |
| us-west-2 | US West (Oregon) | sbh-files-us-west-2 | Active |
| eu-west-1 | Europe (Ireland) | sbh-files-eu-west-1 | Active |
| ap-southeast-1 | Asia Pacific (Singapore) | sbh-files-ap-southeast-1 | Active |

## Tenant Region Assignment

### Automatic Assignment

Tenants are automatically assigned regions based on their tenant ID:

```python
def get_tenant_region(tenant_id: str) -> str:
    """Get region for tenant"""
    if 'eu' in tenant_id.lower():
        return 'eu-west-1'
    elif 'ap' in tenant_id.lower():
        return 'ap-southeast-1'
    elif 'west' in tenant_id.lower():
        return 'us-west-2'
    else:
        return 'us-east-1'  # Default
```

### Manual Assignment

For production deployments, regions can be manually assigned:

```python
# Set tenant region
tenant.region = 'eu-west-1'
tenant.save()

# Validate region access
can_access = residency_manager.validate_region_access(tenant_id, 'eu-west-1')
```

## Storage Configuration

### File Storage

```python
# Get storage configuration for tenant
storage_config = residency_manager.get_storage_config(tenant_id)

# Result:
{
    'region': 'eu-west-1',
    'bucket': 'sbh-files-eu-west-1',
    'prefix': 'files/tenant-1/',
    'enabled': True
}
```

### Backup Storage

```python
# Get backup storage configuration
backup_config = residency_manager.get_backup_storage_config(tenant_id)

# Result:
{
    'bucket': 'sbh-files-eu-west-1',
    'prefix': 'files/tenant-1/backups/',
    'region': 'eu-west-1'
}
```

## Presigned URL Routing

### File Upload

```python
# Get presigned URL configuration for upload
url_config = residency_manager.get_presigned_url_config(tenant_id, file_path)

# Result:
{
    'bucket': 'sbh-files-eu-west-1',
    'key': 'files/tenant-1/documents/file.pdf',
    'region': 'eu-west-1',
    'expires_in': 3600
}
```

### File Download

```python
# Generate presigned download URL
presigned_url = s3_client.generate_presigned_url(
    'get_object',
    Params={
        'Bucket': url_config['bucket'],
        'Key': url_config['key']
    },
    ExpiresIn=url_config['expires_in']
)
```

## Database Residency

### Region Tagging

All database records include region information for audit and compliance:

```python
# User record with region
{
    'id': 'user-1',
    'tenant_id': 'tenant-1',
    'region': 'eu-west-1',
    'email': 'user@example.com',
    'created_at': '2024-01-01T00:00:00Z'
}
```

### Audit Trail

Region information is included in all audit events:

```python
# Audit event with region
{
    'event_type': 'user.created',
    'tenant_id': 'tenant-1',
    'region': 'eu-west-1',
    'user_id': 'user-1',
    'timestamp': '2024-01-01T00:00:00Z'
}
```

## Backup Residency

### Backup Storage

Backups are stored in the same region as the tenant's data:

```python
# Backup manifest with region
{
    'id': 'backup_20240115_1200',
    'tenant_id': 'tenant-1',
    'region': 'eu-west-1',
    'storage': {
        'bucket': 'sbh-files-eu-west-1',
        'prefix': 'files/tenant-1/backups/',
        'region': 'eu-west-1'
    }
}
```

### Cross-Region Backup

For disaster recovery, backups can be replicated to secondary regions:

```python
# Cross-region backup configuration
{
    'primary_region': 'eu-west-1',
    'secondary_regions': ['us-east-1'],
    'replication_enabled': True,
    'replication_schedule': 'daily'
}
```

## GDPR Compliance

### Data Export

Exported data includes region information:

```python
# GDPR export with region
{
    'export_info': {
        'user_id': 'user-1',
        'tenant_id': 'tenant-1',
        'region': 'eu-west-1',
        'exported_at': '2024-01-01T00:00:00Z'
    },
    'user_data': {...},
    'files': [...],
    'analytics': [...]
}
```

### Data Deletion

Deletion operations respect regional data residency:

```python
# Deletion with region tracking
{
    'deletion_id': 'delete_user_1_20240101_120000',
    'user_id': 'user-1',
    'tenant_id': 'tenant-1',
    'region': 'eu-west-1',
    'deleted_at': '2024-01-01T12:00:00Z'
}
```

## Monitoring & Analytics

### Region Access Tracking

```python
# Track region access
residency_manager.track_region_access(
    tenant_id='tenant-1',
    region='eu-west-1',
    operation='file_upload',
    success=True
)
```

### Analytics Events

- `residency.region_access`: Region access tracking
- `residency.cross_region_access`: Cross-region access attempts
- `residency.storage_routing`: Storage routing events

## Configuration

### Environment Variables

```bash
# Default region
DEFAULT_REGION=us-east-1

# Enabled regions
ENABLED_REGIONS=us-east-1,us-west-2,eu-west-1,ap-southeast-1

# S3 bucket mapping
S3_BUCKET_US_EAST_1=sbh-files-us-east-1
S3_BUCKET_US_WEST_2=sbh-files-us-west-2
S3_BUCKET_EU_WEST_1=sbh-files-eu-west-1
S3_BUCKET_AP_SOUTHEAST_1=sbh-files-ap-southeast-1
```

### Tenant Configuration

```python
# Tenant region configuration
tenant_config = {
    'tenant_id': 'tenant-1',
    'region': 'eu-west-1',
    'storage_enabled': True,
    'backup_enabled': True,
    'cross_region_backup': False
}
```

## Best Practices

### Region Selection
1. **Proximity**: Choose regions close to users
2. **Compliance**: Ensure regions meet regulatory requirements
3. **Performance**: Consider latency and bandwidth
4. **Cost**: Factor in regional pricing differences

### Data Management
1. **Consistency**: Keep data in single region when possible
2. **Backup**: Implement cross-region backup for critical data
3. **Monitoring**: Monitor regional performance and costs
4. **Documentation**: Document regional data flows

### Security
1. **Encryption**: Encrypt data in transit and at rest
2. **Access Control**: Implement region-aware access controls
3. **Audit**: Log all cross-region data movements
4. **Compliance**: Ensure regional compliance requirements

## Troubleshooting

### Common Issues

#### Region Mismatch
```python
# Check tenant region
tenant_region = residency_manager.get_tenant_region(tenant_id)
print(f"Tenant region: {tenant_region}")

# Check storage config
storage_config = residency_manager.get_storage_config(tenant_id)
print(f"Storage region: {storage_config['region']}")

# Validate access
can_access = residency_manager.validate_region_access(tenant_id, region)
print(f"Can access region: {can_access}")
```

#### Storage Routing Issues
```python
# Check S3 configuration
s3_config = residency_manager.get_storage_config(tenant_id)
print(f"S3 bucket: {s3_config['bucket']}")
print(f"S3 prefix: {s3_config['prefix']}")

# Test S3 access
try:
    s3_client.head_bucket(Bucket=s3_config['bucket'])
    print("S3 bucket accessible")
except Exception as e:
    print(f"S3 access error: {e}")
```

### Debug Commands

#### Check Region Configuration
```bash
curl -H "Authorization: Bearer <token>" \
  -H "X-Tenant-Slug: <tenant>" \
  https://api.example.com/api/security/residency/config
```

#### Test Storage Routing
```bash
curl -X POST https://api.example.com/api/security/residency/test \
  -H "Authorization: Bearer <token>" \
  -H "X-Tenant-Slug: <tenant>" \
  -d '{
    "operation": "file_upload",
    "file_path": "test.txt"
  }'
```

## Compliance Considerations

### GDPR
- **Data Localization**: Store EU data in EU regions
- **Cross-Border Transfers**: Minimize cross-region data transfers
- **Right to Erasure**: Ensure complete data deletion in all regions
- **Data Portability**: Support data export from specific regions

### CCPA
- **California Residents**: Store data in US regions
- **Data Access**: Provide access to data in specific regions
- **Deletion Rights**: Support regional data deletion

### Industry Standards
- **SOC 2**: Regional compliance with SOC 2 requirements
- **ISO 27001**: Regional security controls
- **HIPAA**: Regional healthcare data compliance

## Migration Guide

### Changing Tenant Region

```python
# 1. Create backup in current region
backup = backup_service.create_backup(tenant_id, user_ctx)

# 2. Update tenant region
tenant.region = 'new-region'
tenant.save()

# 3. Restore backup in new region
restore = backup_service.restore_backup(backup['id'], tenant_id, user_ctx)

# 4. Verify data integrity
verification = verify_data_integrity(tenant_id)
```

### Cross-Region Replication

```python
# Enable cross-region replication
replication_config = {
    'source_region': 'us-east-1',
    'destination_regions': ['eu-west-1'],
    'replication_rules': [
        {
            'prefix': 'files/',
            'status': 'enabled'
        }
    ]
}
```

# Backup & Restore Guide

This document explains the backup and restore system, including scheduling, procedures, and safety considerations.

## Overview

The backup and restore system provides:

- **Database Backups**: Complete database snapshots
- **File Backups**: S3 file storage backups
- **Point-in-Time Recovery**: Restore to specific points in time
- **Regional Storage**: Region-aware backup storage
- **Security**: Encrypted backups with access controls

## Backup Types

### Full Backup
Complete backup of all tenant data:
- Database tables and data
- File storage contents
- Configuration and metadata
- Audit logs and analytics

### Incremental Backup
Backup of changes since last backup:
- Database changes only
- New/modified files
- Configuration changes
- Reduced storage and time

### Differential Backup
Backup of changes since last full backup:
- All changes since full backup
- Faster than full backup
- More storage than incremental

## Backup Components

### Database Backup
```python
# Database backup structure
{
    'type': 'json',
    'key': 'files/tenant-1/backups/database/backup_20240115_1200.json',
    'size': 1048576,
    'checksum': 'sha256:abc123...',
    'tables': ['users', 'projects', 'tasks', 'files', 'payments', 'analytics']
}
```

### File Backup
```python
# File backup structure
{
    'type': 'file_list',
    'key': 'files/tenant-1/backups/files/backup_20240115_1200.json',
    'size': 51200,
    'checksum': 'sha256:def456...',
    'file_count': 150,
    'total_size': 104857600
}
```

### Backup Manifest
```python
# Complete backup manifest
{
    'id': 'backup_20240115_1200',
    'tenant_id': 'tenant-1',
    'type': 'full',
    'region': 'eu-west-1',
    'created_by': 'admin-user',
    'created_at': '2024-01-15T12:00:00Z',
    'components': {
        'database': {...},
        'files': {...}
    },
    'checksum': 'sha256:ghi789...',
    'size': 1100000
}
```

## Creating Backups

### API Endpoint
```http
POST /api/backup
Content-Type: application/json
Authorization: Bearer <token>
X-Tenant-Slug: <tenant>

{
  "type": "full",
  "description": "Weekly backup"
}
```

### CLI Command
```bash
# Create backup
python -c "
from src.backup.service import backup_service
from src.security.policy import UserContext, Role

user_ctx = UserContext(
    user_id='admin',
    tenant_id='tenant-1',
    role=Role.ADMIN
)

result = backup_service.create_backup('tenant-1', user_ctx, 'full')
print(f'Backup created: {result[\"id\"]}')
"
```

### Scheduled Backups
```python
# Cron job for daily backups
0 2 * * * /usr/bin/python /app/scripts/create_backup.py --tenant=tenant-1 --type=full

# Cron job for hourly incremental backups
0 * * * * /usr/bin/python /app/scripts/create_backup.py --tenant=tenant-1 --type=incremental
```

## Restoring Backups

### API Endpoint
```http
POST /api/backup/{backup_id}/restore
Content-Type: application/json
Authorization: Bearer <token>
X-Tenant-Slug: <tenant>

{
  "confirm": true,
  "validate_only": false
}
```

### CLI Command
```bash
# Restore backup
python -c "
from src.backup.service import backup_service
from src.security.policy import UserContext, Role

user_ctx = UserContext(
    user_id='admin',
    tenant_id='tenant-1',
    role=Role.ADMIN
)

result = backup_service.restore_backup('backup_20240115_1200', 'tenant-1', user_ctx)
print(f'Backup restored: {result[\"backup_id\"]}')
"
```

### Validation Mode
```python
# Validate backup without restoring
result = backup_service.validate_backup(backup_id, tenant_id, user_ctx)
print(f'Backup valid: {result[\"valid\"]}')
print(f'Issues: {result[\"issues\"]}')
```

## Backup Storage

### Regional Storage
```python
# Get backup storage configuration
storage_config = residency_manager.get_backup_storage_config(tenant_id)

# Result:
{
    'bucket': 'sbh-files-eu-west-1',
    'prefix': 'files/tenant-1/backups/',
    'region': 'eu-west-1'
}
```

### Storage Structure
```
s3://sbh-files-eu-west-1/
├── files/
│   └── tenant-1/
│       └── backups/
│           ├── manifests/
│           │   ├── backup_20240115_1200.json
│           │   └── backup_20240116_1200.json
│           ├── database/
│           │   ├── backup_20240115_1200.json
│           │   └── backup_20240116_1200.json
│           └── files/
│               ├── backup_20240115_1200.json
│               └── backup_20240116_1200.json
```

### Retention Policy
```python
# Backup retention configuration
retention_config = {
    'full_backups': {
        'keep_daily': 7,      # Keep daily backups for 7 days
        'keep_weekly': 4,     # Keep weekly backups for 4 weeks
        'keep_monthly': 12    # Keep monthly backups for 12 months
    },
    'incremental_backups': {
        'keep_hourly': 24,    # Keep hourly backups for 24 hours
        'keep_daily': 7       # Keep daily backups for 7 days
    }
}
```

## Security

### Access Control
```python
# Backup access requires admin role
@require_role(Role.ADMIN)
def create_backup():
    # Only admins can create backups
    pass

@require_role(Role.ADMIN)
def restore_backup():
    # Only admins can restore backups
    pass
```

### Encryption
```python
# Backup encryption configuration
encryption_config = {
    'algorithm': 'AES-256',
    'key_management': 'AWS KMS',
    'encrypt_at_rest': True,
    'encrypt_in_transit': True
}
```

### Audit Logging
```python
# Backup audit events
analytics.track(
    tenant_id=tenant_id,
    event='backup.created',
    user_id=user_id,
    source='backup',
    props={
        'backup_id': backup_id,
        'type': backup_type,
        'size': backup_size,
        'region': region
    }
)
```

## Monitoring

### Backup Metrics
```python
# Backup metrics
backup_metrics = {
    'backups_total': 150,
    'backups_successful': 148,
    'backups_failed': 2,
    'backup_size_total': 1073741824,  # 1GB
    'backup_duration_avg': 300,       # 5 minutes
    'last_backup_at': '2024-01-15T12:00:00Z'
}
```

### Health Checks
```python
# Backup health check
def check_backup_health():
    return {
        'backup_service': 'healthy',
        'storage_accessible': True,
        'last_backup_successful': True,
        'backup_size_reasonable': True,
        'retention_policy_enforced': True
    }
```

## Best Practices

### Backup Strategy
1. **Regular Schedule**: Create backups on a regular schedule
2. **Multiple Types**: Use full, incremental, and differential backups
3. **Off-site Storage**: Store backups in multiple regions
4. **Testing**: Regularly test backup restoration

### Performance
1. **Off-peak Hours**: Schedule backups during off-peak hours
2. **Parallel Processing**: Use parallel processing for large backups
3. **Compression**: Compress backup data to reduce storage
4. **Deduplication**: Use deduplication to reduce storage

### Security
1. **Access Control**: Restrict backup access to authorized users
2. **Encryption**: Encrypt all backup data
3. **Audit Logging**: Log all backup operations
4. **Validation**: Validate backup integrity

## Troubleshooting

### Common Issues

#### Backup Failures
```python
# Check backup status
backup_status = backup_service.get_backup_status(backup_id)
print(f"Status: {backup_status['status']}")
print(f"Error: {backup_status.get('error')}")

# Common causes:
# - Insufficient storage space
# - Network connectivity issues
# - Permission problems
# - Database connection issues
```

#### Restore Failures
```python
# Check restore status
restore_status = backup_service.get_restore_status(restore_id)
print(f"Status: {restore_status['status']}")
print(f"Progress: {restore_status['progress']}%")

# Common causes:
# - Corrupted backup files
# - Insufficient disk space
# - Database schema changes
# - Permission problems
```

#### Storage Issues
```python
# Check storage configuration
storage_config = residency_manager.get_backup_storage_config(tenant_id)
print(f"Bucket: {storage_config['bucket']}")
print(f"Region: {storage_config['region']}")

# Test S3 access
try:
    s3_client.head_bucket(Bucket=storage_config['bucket'])
    print("S3 bucket accessible")
except Exception as e:
    print(f"S3 access error: {e}")
```

### Debug Commands

#### List Backups
```bash
curl -H "Authorization: Bearer <token>" \
  -H "X-Tenant-Slug: <tenant>" \
  https://api.example.com/api/backup/
```

#### Get Backup Details
```bash
curl -H "Authorization: Bearer <token>" \
  -H "X-Tenant-Slug: <tenant>" \
  https://api.example.com/api/backup/backup_20240115_1200
```

#### Validate Backup
```bash
curl -X POST https://api.example.com/api/backup/backup_20240115_1200/validate \
  -H "Authorization: Bearer <token>" \
  -H "X-Tenant-Slug: <tenant>"
```

## Disaster Recovery

### Recovery Procedures

#### Complete System Failure
1. **Assess Damage**: Determine extent of failure
2. **Choose Recovery Point**: Select appropriate backup
3. **Restore Infrastructure**: Restore system infrastructure
4. **Restore Data**: Restore from backup
5. **Validate System**: Verify system functionality
6. **Update DNS**: Point traffic to restored system

#### Partial Data Loss
1. **Identify Affected Data**: Determine what data was lost
2. **Select Backup**: Choose backup with required data
3. **Restore Data**: Restore only affected data
4. **Validate Integrity**: Verify data consistency
5. **Update Applications**: Restart affected applications

### Recovery Time Objectives (RTO)

| Scenario | RTO | Backup Type |
|----------|-----|-------------|
| Complete failure | 4 hours | Full backup |
| Database corruption | 1 hour | Database backup |
| File system loss | 2 hours | File backup |
| Configuration error | 30 minutes | Configuration backup |

### Recovery Point Objectives (RPO)

| Data Type | RPO | Backup Frequency |
|-----------|-----|------------------|
| Critical data | 1 hour | Hourly incremental |
| Important data | 24 hours | Daily full |
| Archive data | 7 days | Weekly full |

## Compliance

### Regulatory Requirements
- **GDPR**: Data backup and recovery procedures
- **SOC 2**: Backup security and availability
- **HIPAA**: Healthcare data backup requirements
- **PCI DSS**: Payment data backup security

### Audit Requirements
- **Backup Logs**: Complete audit trail of backup operations
- **Access Logs**: Log all backup access and modifications
- **Retention Logs**: Log backup retention and deletion
- **Recovery Logs**: Log all recovery operations

### Documentation
- **Backup Procedures**: Documented backup procedures
- **Recovery Procedures**: Documented recovery procedures
- **Testing Procedures**: Documented testing procedures
- **Incident Response**: Documented incident response procedures

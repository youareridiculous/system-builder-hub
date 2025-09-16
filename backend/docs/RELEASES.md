# Release Management Guide

This document explains the release management system for staged deployments with safe migrations and rollbacks.

## Overview

The release management system provides:

- **Staged Deployments**: Dev → Staging → Production workflow
- **Safe Migrations**: Database migration planning and execution
- **Rollback Support**: Automatic rollback on failures
- **Release Manifests**: Complete release documentation
- **Tool Integration**: Integration with agent tools for automation

## Release Workflow

### 1. Development Environment
- **Purpose**: Active development and testing
- **Database**: Development database with test data
- **Features**: All features enabled for testing
- **Deployment**: Continuous deployment from development

### 2. Staging Environment
- **Purpose**: Pre-production testing and validation
- **Database**: Staging database with production-like data
- **Features**: Production feature flags and configuration
- **Deployment**: Manual promotion from development

### 3. Production Environment
- **Purpose**: Live production environment
- **Database**: Production database with live data
- **Features**: Production configuration and limits
- **Deployment**: Manual promotion from staging

## Release Process

### Prepare Release

#### API Endpoint
```http
POST /api/releases/prepare
Content-Type: application/json
Authorization: Bearer <token>
X-Tenant-Slug: <tenant>

{
  "from_env": "dev",
  "to_env": "staging",
  "bundle_data": {
    "database": {
      "changes": [
        {
          "type": "create_table",
          "table": "new_feature",
          "columns": [...]
        }
      ]
    }
  }
}
```

#### CLI Command
```bash
make release-prepare TENANT=primary
```

#### Response
```json
{
  "success": true,
  "data": {
    "release_id": "rel_20240115_1200",
    "status": "prepared",
    "from_env": "dev",
    "to_env": "staging",
    "bundle_sha256": "abc123...",
    "migrations": [
      {
        "operation": "create_table",
        "table": "new_feature",
        "sql": "CREATE TABLE new_feature (...);",
        "dry_run_result": {...}
      }
    ],
    "feature_flags": {...},
    "created_at": "2024-01-15T12:00:00Z"
  }
}
```

### Promote Release

#### API Endpoint
```http
POST /api/releases/promote
Content-Type: application/json
Authorization: Bearer <token>
X-Tenant-Slug: <tenant>

{
  "release_id": "rel_20240115_1200"
}
```

#### CLI Command
```bash
make release-promote TENANT=primary
```

#### Response
```json
{
  "success": true,
  "data": {
    "release_id": "rel_20240115_1200",
    "status": "promoted",
    "from_env": "staging",
    "to_env": "prod",
    "promoted_at": "2024-01-15T14:00:00Z"
  }
}
```

### Rollback Release

#### API Endpoint
```http
POST /api/releases/rollback
Content-Type: application/json
Authorization: Bearer <token>
X-Tenant-Slug: <tenant>

{
  "release_id": "rel_20240115_1200"
}
```

#### Response
```json
{
  "success": true,
  "data": {
    "release_id": "rel_20240115_1200",
    "rolled_back": true
  }
}
```

## Release Manifest

### Structure
```json
{
  "id": "rel_YYYYMMDD_hhmm",
  "from_env": "dev",
  "to_env": "staging|prod",
  "bundle_sha256": "...",
  "migrations": [
    {
      "operation": "create_table|add_column|drop_column|modify_column",
      "table": "table_name",
      "sql": "SQL statement",
      "dry_run_result": {...}
    }
  ],
  "feature_flags": {
    "feature_name": "true|false|plan_name"
  },
  "tools_transcript_ids": ["transcript_1", "transcript_2"],
  "status": "prepared|promoted|failed|rolled_back",
  "created_by": "user_id",
  "created_at": "2024-01-15T12:00:00Z",
  "promoted_at": "2024-01-15T14:00:00Z",
  "failed_at": "2024-01-15T14:00:00Z",
  "error_message": "Error description"
}
```

### Fields

#### Basic Information
- **id**: Unique release identifier (format: rel_YYYYMMDD_hhmm)
- **from_env**: Source environment (dev, staging, prod)
- **to_env**: Target environment (staging, prod)
- **bundle_sha256**: SHA256 hash of the deployment bundle
- **status**: Current release status

#### Migrations
- **operation**: Migration operation type
- **table**: Affected table name
- **sql**: SQL statement to execute
- **dry_run_result**: Result from dry-run execution

#### Feature Flags
- **feature_name**: Name of the feature flag
- **value**: Flag value (true, false, or plan name)

#### Metadata
- **created_by**: User who created the release
- **created_at**: Release creation timestamp
- **promoted_at**: Promotion timestamp
- **failed_at**: Failure timestamp
- **error_message**: Error description if failed

## Safe Migrations

### Migration Planning
1. **Dry Run**: All migrations are executed in dry-run mode first
2. **Validation**: SQL statements are validated for syntax and safety
3. **Dependencies**: Migration dependencies are checked
4. **Rollback Plan**: Rollback SQL is generated for each migration

### Migration Execution
1. **Pre-checks**: Database connectivity and backup verification
2. **Transaction**: Migrations are executed within a transaction
3. **Validation**: Post-migration validation and testing
4. **Commit/Rollback**: Transaction is committed or rolled back

### Rollback Strategy
1. **Automatic Rollback**: Failed migrations trigger automatic rollback
2. **Manual Rollback**: Manual rollback to previous release
3. **Data Preservation**: Data is preserved during rollback
4. **Audit Trail**: Complete audit trail of rollback operations

## Tool Integration

### Database Migration Tool
```python
# Migration planning
call = ToolCall(
    id='mig_1',
    tool='db.migrate',
    args={
        'op': 'create_table',
        'table': 'new_feature',
        'columns': [...],
        'dry_run': True
    }
)

result = tool_kernel.execute(call, tool_context)
```

### Queue Integration
```python
# Background job execution
call = ToolCall(
    id='job_1',
    tool='queue.enqueue',
    args={
        'queue': 'default',
        'job': 'post_deployment_task',
        'payload': {...}
    }
)

result = tool_kernel.execute(call, tool_context)
```

### Email Notifications
```python
# Release notifications
call = ToolCall(
    id='email_1',
    tool='email.send',
    args={
        'template': 'release_notification',
        'to': 'admin@company.com',
        'payload': {
            'release_id': 'rel_20240115_1200',
            'status': 'promoted'
        },
        'dry_run': False
    }
)

result = tool_kernel.execute(call, tool_context)
```

## Environment Configuration

### Development
```bash
# Development environment
FLASK_ENV=development
DATABASE_URL=postgresql://localhost/dev_db
FEATURE_FLAGS={"custom_domains": true, "advanced_analytics": true}
```

### Staging
```bash
# Staging environment
FLASK_ENV=staging
DATABASE_URL=postgresql://staging-host/staging_db
FEATURE_FLAGS={"custom_domains": true, "advanced_analytics": false}
```

### Production
```bash
# Production environment
FLASK_ENV=production
DATABASE_URL=postgresql://prod-host/prod_db
FEATURE_FLAGS={"custom_domains": false, "advanced_analytics": false}
```

## Monitoring & Analytics

### Release Metrics
- **releases_prepared_total**: Total releases prepared
- **releases_promoted_total**: Total releases promoted
- **releases_failed_total**: Total releases failed
- **release_prepare_seconds**: Time to prepare release
- **release_promote_seconds**: Time to promote release

### Audit Events
- **release.prepared**: Release preparation completed
- **release.promoted**: Release promotion completed
- **release.failed**: Release promotion failed
- **release.rollback**: Release rollback executed

### Health Checks
```http
GET /health
```

Response includes release status:
```json
{
  "releases": {
    "configured": true,
    "ok": true,
    "latest_release": "rel_20240115_1200",
    "environment": "production"
  }
}
```

## Best Practices

### Release Planning
1. **Small Increments**: Keep releases small and focused
2. **Testing**: Thorough testing in development and staging
3. **Documentation**: Document all changes and migrations
4. **Communication**: Notify stakeholders of release plans

### Migration Safety
1. **Backup First**: Always backup before migrations
2. **Test Migrations**: Test migrations in staging environment
3. **Rollback Plan**: Have a clear rollback plan
4. **Monitoring**: Monitor migration execution

### Production Deployment
1. **Low Traffic**: Deploy during low traffic periods
2. **Gradual Rollout**: Use feature flags for gradual rollout
3. **Monitoring**: Monitor application health during deployment
4. **Rollback Ready**: Be ready to rollback if issues arise

## Troubleshooting

### Common Issues

#### Migration Failures
```bash
# Check migration status
curl -H "Authorization: Bearer <token>" \
  -H "X-Tenant-Slug: <tenant>" \
  https://api.example.com/api/releases/rel_20240115_1200

# Rollback failed migration
curl -X POST https://api.example.com/api/releases/rollback \
  -H "Authorization: Bearer <token>" \
  -H "X-Tenant-Slug: <tenant>" \
  -d '{"release_id": "rel_20240115_1200"}'
```

#### Database Connection Issues
```bash
# Check database connectivity
python -c "from src.database import get_session; print('DB OK')"

# Check migration tool
python -c "from src.agent_tools.tools import db_migrate_handler; print('Tool OK')"
```

#### Environment Configuration
```bash
# Check environment variables
echo $FLASK_ENV
echo $DATABASE_URL
echo $FEATURE_FLAGS

# Validate configuration
python -c "from src.releases.service import ReleaseService; print('Config OK')"
```

### Debug Commands

#### List Releases
```bash
curl -H "Authorization: Bearer <token>" \
  -H "X-Tenant-Slug: <tenant>" \
  https://api.example.com/api/releases/
```

#### Get Release Details
```bash
curl -H "Authorization: Bearer <token>" \
  -H "X-Tenant-Slug: <tenant>" \
  https://api.example.com/api/releases/rel_20240115_1200
```

#### Check Release Status
```bash
python -c "
from src.releases.service import ReleaseService
service = ReleaseService()
releases = service.get_releases('tenant-id')
for release in releases:
    print(f'{release.release_id}: {release.status}')
"
```

## CI/CD Integration

### GitHub Actions
```yaml
name: Release Pipeline

on:
  push:
    tags:
      - 'v*'

jobs:
  prepare-release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Prepare Release
        run: |
          curl -X POST ${{ secrets.API_URL }}/api/releases/prepare \
            -H "Authorization: Bearer ${{ secrets.API_TOKEN }}" \
            -H "X-Tenant-Slug: ${{ secrets.TENANT_ID }}" \
            -d '{"from_env": "dev", "to_env": "staging"}'

  promote-release:
    runs-on: ubuntu-latest
    needs: prepare-release
    steps:
      - name: Promote Release
        run: |
          curl -X POST ${{ secrets.API_URL }}/api/releases/promote \
            -H "Authorization: Bearer ${{ secrets.API_TOKEN }}" \
            -H "X-Tenant-Slug: ${{ secrets.TENANT_ID }}" \
            -d '{"release_id": "${{ needs.prepare-release.outputs.release_id }}"}'
```

### Environment Variables
```bash
# Required for CI/CD
API_URL=https://api.example.com
API_TOKEN=your_api_token
TENANT_ID=your_tenant_id
```

## Security Considerations

### Access Control
- **Admin Only**: Release operations require admin privileges
- **Audit Logging**: All release operations are logged
- **Environment Isolation**: Strict environment separation

### Data Protection
- **Encryption**: Database connections use encryption
- **Backup**: Regular database backups before releases
- **Validation**: Input validation for all release operations

### Network Security
- **HTTPS**: All API calls use HTTPS
- **Authentication**: Token-based authentication required
- **Rate Limiting**: API rate limiting for release endpoints

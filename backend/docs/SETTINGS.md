# Settings and Configuration

This document describes all configurable settings in System Builder Hub, including feature flags, environment variables, and their precedence rules.

## Feature Flags

### Meta-Builder v3 Auto-Fix

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `FEATURE_META_V3_AUTOFIX` | bool | `true` (staging)<br>`false` (prod) | Enable v3 auto-fix functionality |
| `META_V3_MAX_TOTAL_ATTEMPTS` | int | `6` | Maximum total auto-fix attempts per run |
| `META_V3_MAX_PER_STEP_ATTEMPTS` | int | `3` | Maximum attempts per individual step |
| `META_V3_BACKOFF_CAP_SECONDS` | int | `60` | Maximum backoff delay in seconds |

### Environment-Specific Defaults

#### Staging Environment
```bash
FEATURE_META_V3_AUTOFIX=true
META_V3_MAX_TOTAL_ATTEMPTS=6
META_V3_MAX_PER_STEP_ATTEMPTS=3
META_V3_BACKOFF_CAP_SECONDS=60
```

#### Production Environment
```bash
FEATURE_META_V3_AUTOFIX=false
META_V3_MAX_TOTAL_ATTEMPTS=6
META_V3_MAX_PER_STEP_ATTEMPTS=3
META_V3_BACKOFF_CAP_SECONDS=60
```

## Settings Precedence

Settings are applied in the following order (highest to lowest priority):

1. **Run Override**: Settings specific to a build run
2. **Tenant Override**: Settings specific to a tenant
3. **Platform Default**: Environment-wide default settings

### Example Precedence

```python
# Platform default
FEATURE_META_V3_AUTOFIX=false

# Tenant override
tenant_settings.autofix_enabled = true

# Run override
run_settings.max_total_attempts = 8

# Final result:
# autofix_enabled = true (from tenant)
# max_total_attempts = 8 (from run)
# max_per_step_attempts = 3 (from platform)
```

## Admin UI Configuration

### Accessing Settings

1. Navigate to **Settings → Builder → Auto-Fix (v3)**
2. Requires **Tenant Admin** or **Platform Admin** role

### Available Actions

- **Enable/Disable**: Toggle v3 auto-fix for the tenant
- **Retry Budgets**: Adjust maximum attempts and delays
- **View Current Settings**: See active configuration
- **Reset to Defaults**: Restore platform defaults

### RBAC Requirements

- **Tenant Admin**: Can modify tenant-level settings
- **Platform Admin**: Can modify platform defaults
- **Regular User**: Can view settings (read-only)

## API Configuration

### Get Current Settings

```bash
GET /api/meta/v2/tenants/{tenant_id}/settings
```

Response:
```json
{
  "autofix_enabled": true,
  "max_total_attempts": 6,
  "max_per_step_attempts": 3,
  "backoff_cap_seconds": 60
}
```

### Update Tenant Settings

```bash
PUT /api/meta/v2/tenants/{tenant_id}/settings
Content-Type: application/json

{
  "autofix_enabled": true,
  "max_total_attempts": 8,
  "max_per_step_attempts": 4
}
```

### Update Run Settings

```bash
PUT /api/meta/v2/runs/{run_id}/settings
Content-Type: application/json

{
  "autofix_enabled": true,
  "max_total_attempts": 10
}
```

## Environment Variables

### Required Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost/db

# Redis
REDIS_URL=redis://localhost:6379

# Authentication
JWT_SECRET=your-secret-key
```

### Optional Variables

```bash
# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Monitoring
PROMETHEUS_ENABLED=true
GRAFANA_URL=http://localhost:3000

# Feature Flags
FEATURE_META_V3_AUTOFIX=true
META_V3_MAX_TOTAL_ATTEMPTS=6
META_V3_MAX_PER_STEP_ATTEMPTS=3
META_V3_BACKOFF_CAP_SECONDS=60

# Testing
RUN_SMOKE=false
SMOKE_BASE_URL=http://localhost:5001
```

## Configuration Management

### Development

Use `.env` file for local development:

```bash
# .env
FEATURE_META_V3_AUTOFIX=true
META_V3_MAX_TOTAL_ATTEMPTS=10
META_V3_MAX_PER_STEP_ATTEMPTS=5
```

### Staging

Use environment variables or SSM Parameter Store:

```bash
# Environment variables
export FEATURE_META_V3_AUTOFIX=true
export META_V3_MAX_TOTAL_ATTEMPTS=6

# Or SSM
aws ssm put-parameter \
  --name "/sbh/staging/FEATURE_META_V3_AUTOFIX" \
  --value "true" \
  --type "String"
```

### Production

Use SSM Parameter Store for secure configuration:

```bash
# Platform defaults
aws ssm put-parameter \
  --name "/sbh/prod/FEATURE_META_V3_AUTOFIX" \
  --value "false" \
  --type "String"

aws ssm put-parameter \
  --name "/sbh/prod/META_V3_MAX_TOTAL_ATTEMPTS" \
  --value "6" \
  --type "String"
```

## Validation Rules

### Retry Budgets

- `max_total_attempts`: 1-20 (default: 6)
- `max_per_step_attempts`: 1-10 (default: 3)
- `backoff_cap_seconds`: 10-300 (default: 60)

### Feature Flags

- `autofix_enabled`: boolean (default: false in prod, true in staging)

## Monitoring Settings

### Metrics to Watch

- Auto-fix success ratio
- Retry attempt distribution
- Backoff delay patterns
- Approval request rates

### Alerts

Set up alerts for:
- Success ratio < 70%
- Excessive retries (> 80% of runs)
- High backoff delays (> 60s average)

## Troubleshooting

### Common Issues

1. **Settings not applying**
   - Check precedence order
   - Verify RBAC permissions
   - Check environment variables

2. **Feature flag not working**
   - Restart application after changes
   - Check cache invalidation
   - Verify tenant ID

3. **Invalid settings**
   - Check validation rules
   - Review error logs
   - Use admin UI for validation

### Debug Commands

```bash
# Check current settings
curl /api/meta/v2/tenants/{tenant_id}/settings

# Validate settings
curl -X POST /api/meta/v2/settings/validate \
  -d '{"max_total_attempts": 15}'

# Clear settings cache
curl -X POST /api/meta/v2/settings/cache/clear
```

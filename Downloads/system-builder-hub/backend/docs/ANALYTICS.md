# Analytics & Usage Tracking Guide

This document explains SBH's analytics and usage tracking system, including event ingestion, dashboards, quotas, and data export capabilities.

## Overview

SBH provides comprehensive analytics and usage tracking for tenants, including:

1. **Event Tracking**: Automatic tracking of user actions and system events
2. **Usage Metrics**: Daily aggregation of usage counters
3. **Dashboards**: Real-time analytics visualization
4. **Quotas**: Soft quota enforcement with alerts
5. **Data Export**: CSV export with row limits

## Data Model

### Analytics Events
```sql
CREATE TABLE analytics_events (
    id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id),
    user_id VARCHAR(255),
    source VARCHAR(50), -- app, api, webhook, job, payments, files, builder, agent
    event TEXT NOT NULL,
    ts TIMESTAMPTZ DEFAULT NOW(),
    props JSONB,
    ip TEXT,
    request_id TEXT
);
```

### Daily Usage
```sql
CREATE TABLE analytics_daily_usage (
    tenant_id UUID REFERENCES tenants(id),
    date DATE,
    metric TEXT,
    count BIGINT DEFAULT 0,
    meta JSONB,
    PRIMARY KEY (tenant_id, date, metric)
);
```

## Event Tracking

### Automatic Events
SBH automatically tracks the following events:

#### Authentication Events
- `auth.user.registered` - User registration
- `auth.user.login` - User login

#### Builder Events
- `builder.generate.started` - Build process started
- `builder.generate.completed` - Build process completed

#### File Events
- `files.uploaded` - File upload

#### API Events
- `apikey.request` - API key usage
- `apikey.rate_limited` - Rate limit exceeded

#### Webhook Events
- `webhook.delivered` - Webhook delivery successful
- `webhook.failed` - Webhook delivery failed

#### Email Events
- `email.sent` - Email sent
- `email.failed` - Email failed

#### Payment Events
- `payments.checkout.created` - Checkout created
- `payments.subscription.active` - Subscription activated
- `payments.subscription.canceled` - Subscription canceled

### Manual Event Tracking
```python
from src.analytics.service import AnalyticsService

analytics = AnalyticsService()
analytics.track(
    tenant_id='tenant-123',
    event='custom.event',
    user_id='user-456',
    source='app',
    props={'key': 'value'},
    ip='192.168.1.1',
    request_id='req-789'
)
```

## Usage Metrics

### Incrementing Usage
```python
from src.analytics.service import AnalyticsService

analytics = AnalyticsService()
analytics.increment_usage(
    tenant_id='tenant-123',
    metric='api_requests_daily',
    n=1
)
```

### Daily Aggregation
Usage metrics are automatically aggregated daily via background jobs:

```python
from src.jobs.analytics_agg import rollup_daily_usage_job

# Trigger rollup for specific date
rollup_daily_usage_job('2024-01-15')
```

## API Endpoints

### Get Events
```http
GET /api/analytics/events?from=2024-01-01&to=2024-01-31&event=auth.user.login&source=app&limit=100&cursor=2024-01-15T10:30:00Z
Authorization: Bearer <token>
X-Tenant-Slug: <tenant>
```

**Response:**
```json
{
  "success": true,
  "data": {
    "events": [
      {
        "id": "event-123",
        "user_id": "user-456",
        "source": "app",
        "event": "auth.user.login",
        "ts": "2024-01-15T10:30:00Z",
        "props": {"email": "user@example.com"},
        "ip": "192.168.1.1",
        "request_id": "req-789"
      }
    ],
    "has_more": true,
    "next_cursor": "2024-01-15T09:30:00Z"
  }
}
```

### Get Usage Data
```http
GET /api/analytics/usage?from=2024-01-01&to=2024-01-31&metric[]=auth.user.login&metric[]=builder.generate.completed
Authorization: Bearer <token>
X-Tenant-Slug: <tenant>
```

**Response:**
```json
{
  "success": true,
  "data": {
    "auth.user.login": [
      {
        "date": "2024-01-15",
        "count": 25,
        "meta": {}
      }
    ],
    "builder.generate.completed": [
      {
        "date": "2024-01-15",
        "count": 5,
        "meta": {}
      }
    ]
  }
}
```

### Get KPIs
```http
GET /api/analytics/metrics
Authorization: Bearer <token>
X-Tenant-Slug: <tenant>
```

**Response:**
```json
{
  "success": true,
  "data": {
    "auth.user.registered": {
      "today": 3,
      "week": 15,
      "month": 45
    },
    "auth.user.login": {
      "today": 25,
      "week": 150,
      "month": 450
    },
    "builder.generate.completed": {
      "today": 5,
      "week": 30,
      "month": 120
    }
  }
}
```

### Export CSV
```http
GET /api/analytics/export.csv?from=2024-01-01&to=2024-01-31&event=auth.user.login
Authorization: Bearer <token>
X-Tenant-Slug: <tenant>
```

**Response:** CSV file download

### Get Quotas
```http
GET /api/analytics/quotas
Authorization: Bearer <token>
X-Tenant-Slug: <tenant>
```

**Response:**
```json
{
  "success": true,
  "data": {
    "api_requests_daily": {
      "exceeded": false,
      "current": 5000,
      "limit": 100000
    },
    "builds_daily": {
      "exceeded": false,
      "current": 10,
      "limit": 200
    }
  }
}
```

### Trigger Rollup
```http
POST /api/analytics/rollup?date=2024-01-15
Authorization: Bearer <token>
X-Tenant-Slug: <tenant>
```

## Dashboard Features

### KPI Cards
- **Signups**: New user registrations (30d)
- **Active Users**: User logins (30d)
- **Builds**: Completed builds (30d)
- **API Requests**: API key usage (30d)

### Charts
- Time series charts for selected metrics
- Date range filtering (7d, 30d, 90d, custom)
- Metric selection dropdown

### Events Table
- Recent events with pagination
- Filtering by event type and source
- Export to CSV functionality

### Filters
- **Date Range**: Last 7/30/90 days or custom
- **Event Type**: Filter by specific events
- **Source**: Filter by event source (app, api, webhook, etc.)

## Quotas & Limits

### Default Quotas
```json
{
  "api_requests_daily": 100000,
  "builds_daily": 200,
  "emails_daily": 5000,
  "webhooks_daily": 50000,
  "storage_gb": 50
}
```

### Quota Checking
```python
from src.analytics.service import AnalyticsService

analytics = AnalyticsService()
quota_result = analytics.check_quota('tenant-123', 'api_requests_daily')

if quota_result['exceeded']:
    print(f"Quota exceeded: {quota_result['current']}/{quota_result['limit']}")
```

### Configuration
```bash
# Enable quotas
export QUOTAS_ENABLED=true

# Set custom quotas
export QUOTA_DEFAULTS='{"api_requests_daily":50000,"builds_daily":100}'
```

## Prometheus Metrics

### Analytics Metrics
- `sbh_analytics_events_total{tenant,event,source}` - Total events tracked
- `sbh_usage_count_total{tenant,metric}` - Usage counters
- `sbh_quota_exceeded_total{tenant,metric}` - Quota exceeded events
- `sbh_analytics_export_requests_total{tenant}` - Export requests
- `sbh_analytics_rollup_runs_total` - Rollup job runs
- `sbh_analytics_rollup_duration_seconds` - Rollup job duration
- `sbh_analytics_query_duration_seconds` - Query duration

### Example Queries
```promql
# Events per tenant
rate(sbh_analytics_events_total[5m])

# Quota exceeded alerts
sbh_quota_exceeded_total > 0

# Rollup job duration
histogram_quantile(0.95, sbh_analytics_rollup_duration_seconds_bucket)
```

## Background Jobs

### Daily Rollup Job
The analytics rollup job runs daily at 00:10 UTC to aggregate usage data:

```python
# Job configuration
@rq.job
def rollup_daily_usage_job(date_str):
    """Rollup daily usage from Redis to database"""
    # Implementation in src/jobs/analytics_agg.py
```

### Manual Rollup
```bash
# Trigger rollup for specific date
curl -X POST "https://myapp.com/api/analytics/rollup?date=2024-01-15" \
  -H "Authorization: Bearer <token>" \
  -H "X-Tenant-Slug: <tenant>"
```

## Security & RBAC

### Access Control
- **Admin/Owner**: Full access to analytics
- **Member/Viewer**: No access to analytics
- **API Keys**: Require `analytics:read` scope

### Data Isolation
- All analytics data is tenant-scoped
- No cross-tenant data access
- Tenant context required for all operations

### Audit Logging
- Export downloads are logged
- Rollup jobs are audited
- Quota exceeded events are tracked

## Configuration

### Environment Variables
```bash
# Enable analytics
ANALYTICS_ENABLED=true

# Export limits
ANALYTICS_MAX_EXPORT_ROWS=50000

# Quota settings
QUOTAS_ENABLED=true
QUOTA_DEFAULTS='{"api_requests_daily":100000,"builds_daily":200}'
```

### Database Indexes
```sql
-- Performance indexes
CREATE INDEX idx_analytics_events_tenant_ts ON analytics_events(tenant_id, ts);
CREATE INDEX idx_analytics_events_tenant_event_ts ON analytics_events(tenant_id, event, ts);
CREATE INDEX idx_analytics_daily_usage_tenant_date ON analytics_daily_usage(tenant_id, date);
```

## Performance Considerations

### Event Ingestion
- Events are written asynchronously
- Failures don't break user flows
- Redis counters for hot paths

### Query Optimization
- Pagination with cursors
- Date range filtering
- Tenant-scoped queries

### Storage
- Events are retained for 90 days by default
- Daily usage aggregates are kept indefinitely
- CSV exports are limited to 50,000 rows

## Troubleshooting

### Common Issues

#### Events Not Appearing
1. Check `ANALYTICS_ENABLED` environment variable
2. Verify tenant context is set
3. Check application logs for errors

#### Slow Queries
1. Ensure database indexes are created
2. Use date range filters
3. Limit result sets with pagination

#### Quota Issues
1. Verify `QUOTAS_ENABLED` is set
2. Check Redis connectivity for counters
3. Review quota configuration

### Debug Commands
```bash
# Check analytics status
curl https://myapp.com/readiness

# Test event tracking
curl -X POST https://myapp.com/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'

# Check metrics
curl https://myapp.com/metrics | grep analytics
```

## Best Practices

### Event Design
1. **Use consistent naming**: `domain.action` format
2. **Keep props small**: Include only essential data
3. **Avoid PII**: Don't log sensitive information
4. **Use appropriate sources**: Distinguish between app, api, webhook

### Performance
1. **Batch operations**: Use bulk inserts when possible
2. **Cache frequently accessed data**: Redis for hot metrics
3. **Monitor query performance**: Use database indexes
4. **Limit export sizes**: Respect row limits

### Monitoring
1. **Set up alerts**: Monitor quota exceeded events
2. **Track rollup jobs**: Ensure daily aggregation runs
3. **Monitor storage**: Clean up old events periodically
4. **Watch error rates**: Analytics failures shouldn't break apps

## Integration Examples

### Custom Event Tracking
```python
# In your application code
from src.analytics.service import AnalyticsService

analytics = AnalyticsService()

# Track custom business event
analytics.track(
    tenant_id=g.tenant_id,
    event='business.order.completed',
    user_id=g.user_id,
    source='app',
    props={
        'order_id': order.id,
        'amount': order.total,
        'items_count': len(order.items)
    }
)
```

### Usage Monitoring
```python
# Monitor API usage
def api_endpoint():
    # Check quota before processing
    quota = analytics.check_quota(g.tenant_id, 'api_requests_daily')
    if quota['exceeded']:
        return jsonify({'error': 'Daily API limit exceeded'}), 429
    
    # Process request
    result = process_request()
    
    # Increment usage
    analytics.increment_usage(g.tenant_id, 'api_requests_daily')
    
    return jsonify(result)
```

### Dashboard Integration
```javascript
// Load analytics data in frontend
async function loadAnalytics() {
    const response = await fetch('/api/analytics/metrics', {
        headers: {
            'Authorization': `Bearer ${token}`,
            'X-Tenant-Slug': tenant
        }
    });
    
    const data = await response.json();
    updateDashboard(data.data);
}
```

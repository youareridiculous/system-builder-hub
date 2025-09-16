# Dogfooding Guide for Meta-Builder v3

This guide explains how to enable, test, and manage Meta-Builder v3 auto-fix functionality in your environment.

## Enabling Meta-Builder v3

### Platform Level

Set environment variables:

```bash
# Enable v3 auto-fix (default: true in staging, false in production)
FEATURE_META_V3_AUTOFIX=true

# Configure retry limits
META_V3_MAX_TOTAL_ATTEMPTS=6
META_V3_MAX_PER_STEP_ATTEMPTS=3
META_V3_BACKOFF_CAP_SECONDS=60
```

### Tenant Level

Use the Admin UI or API to configure tenant-specific settings:

1. Navigate to **Settings → Builder → Auto-Fix (v3)**
2. Toggle "Enable Auto-Fix v3"
3. Adjust retry budgets:
   - Max Total Attempts: 6
   - Max Per-Step Attempts: 3
   - Backoff Cap (seconds): 60

### Run Level

Override settings for specific runs via API:

```bash
curl -X POST /api/meta/v2/runs/{run_id}/settings \
  -H "Content-Type: application/json" \
  -d '{
    "autofix_enabled": true,
    "max_total_attempts": 8,
    "max_per_step_attempts": 4
  }'
```

## Testing Auto-Fix Functionality

### 1. Create a Test Run

Use the staging seed script to create a test environment:

```bash
./scripts/seed_staging_v3.sh
```

This will:
- Create a staging tenant
- Enable v3 auto-fix
- Seed demo data
- Start a run with known issues

### 2. Monitor Auto-Fix Timeline

1. Navigate to the run details page
2. Look for the "Auto-Fix Timeline" panel
3. Monitor attempts, signals, and outcomes

### 3. Test Different Failure Types

#### Lint Errors
```python
# This will trigger a lint failure
def bad_function():
    x=1  # Missing space around operator
    return x
```

#### Test Failures
```python
# This will trigger a test failure
def test_example():
    assert 1 == 2  # This will fail
```

#### Transient Errors
```python
# Simulate network timeout
import time
time.sleep(30)  # Simulate slow response
```

## Approving Auto-Fix Escalations

### 1. When Escalations Occur

Auto-fix will escalate to manual approval for:
- Security issues
- Policy violations
- Unknown failures after retries

### 2. Approval Process

1. Check the run status - it will be "paused_awaiting_approval"
2. Review the failure signal and proposed fix
3. Use the Admin UI or API to approve/reject

#### Via Admin UI
1. Navigate to **Runs → {run_id} → Approvals**
2. Review the escalation details
3. Click "Approve" or "Reject"

#### Via API
```bash
# Approve
curl -X POST /api/meta/v2/approvals/{gate_id}/approve

# Reject
curl -X POST /api/meta/v2/approvals/{gate_id}/reject
```

### 3. After Approval

- **Approved**: Run continues with the fix applied
- **Rejected**: Run fails and stops

## Inspecting Auto-Fix History

### 1. View Timeline

```bash
curl /api/meta/v2/runs/{run_id}/autofix
```

Response includes:
- Attempt history
- Signal types
- Strategies used
- Outcomes
- Backoff delays

### 2. View Plan Deltas

```bash
curl /api/meta/v2/runs/{run_id}/plan-delta
```

Shows changes made during re-planning.

### 3. View Escalations

```bash
curl /api/meta/v2/runs/{run_id}/escalation
```

Shows pending approval gates.

## Monitoring and Metrics

### 1. Grafana Dashboard

Import the dashboard from `ops/grafana/meta_builder_v3_dashboard.json`:

1. Open Grafana
2. Go to **Dashboards → Import**
3. Upload the JSON file
4. Configure Prometheus data source
5. Save the dashboard

### 2. Key Metrics

- **Auto-Fix Success Ratio**: Should be > 80%
- **Backoff Delays**: Monitor for excessive delays
- **Re-Plans**: Track frequency of re-planning
- **Approvals**: Monitor approval/rejection rates

### 3. Alerts

Set up alerts for:
- Success ratio < 70%
- Excessive re-plans (> 10/hour)
- High approval rejection rate (> 50%)

## Rollback Procedures

### 1. Disable for Tenant

```bash
# Via API
curl -X POST /api/meta/v2/tenants/{tenant_id}/settings \
  -d '{"autofix_enabled": false}'

# Via Admin UI
Settings → Builder → Auto-Fix (v3) → Disable
```

### 2. Disable Platform-Wide

```bash
# Set environment variable
FEATURE_META_V3_AUTOFIX=false

# Restart application
```

### 3. Emergency Rollback

If critical issues occur:

1. Disable feature flag immediately
2. Stop new runs from using v3
3. Monitor existing runs
4. Investigate and fix issues
5. Re-enable with fixes

## Troubleshooting

### Common Issues

1. **Auto-fix not running**
   - Check feature flag is enabled
   - Verify tenant settings
   - Check logs for errors

2. **Excessive retries**
   - Review retry budgets
   - Check for persistent failures
   - Monitor backoff delays

3. **Approval gates not appearing**
   - Check escalation rules
   - Verify notification settings
   - Review RBAC permissions

### Debug Commands

```bash
# Check feature flag status
curl /api/meta/v2/tenants/{tenant_id}/settings

# View run logs
curl /api/meta/v2/runs/{run_id}/logs

# Classify a failure manually
curl -X POST /api/meta/v2/classify-failure \
  -d '{"step_name": "test", "logs": "error message"}'
```

## Best Practices

1. **Start Small**: Enable for a few tenants first
2. **Monitor Closely**: Watch metrics during initial rollout
3. **Set Conservative Limits**: Start with lower retry budgets
4. **Train Team**: Ensure team knows how to approve/reject
5. **Document Issues**: Keep track of problems and solutions

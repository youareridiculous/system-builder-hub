# Meta-Builder v4 Operations Runbook

## Overview

This runbook provides operational procedures for managing Meta-Builder v4 in production, including monitoring, troubleshooting, and emergency procedures.

## Monitoring & Alerting

### Key Metrics to Monitor

#### Fleet Health
- **Worker Utilization**: Target 70-80%
- **Queue Depth**: Alert if > 100 items per queue
- **Worker Heartbeats**: Alert if > 5 minutes stale
- **Active Workers**: Alert if < 50% of expected

#### Repair Performance
- **Repair Success Rate**: Target > 90%
- **Average Repair Duration**: Target < 5 minutes
- **Circuit Breaker States**: Alert if any open
- **Budget Exceedances**: Alert if > 5% of runs

#### Cost Management
- **Average Cost per Run**: Target < $5.00
- **Budget Exceedance Rate**: Alert if > 10%
- **Cost Efficiency**: Target > 0.8 (80% of budget)

#### Canary Performance
- **Success Rate Delta**: Alert if v4 < control by > 5%
- **Cost Ratio**: Alert if v4 > control by > 20%
- **Duration Ratio**: Alert if v4 > control by > 10%

### Grafana Dashboards

1. **Meta-Builder v4 Overview**
   - URL: `/grafana/d/meta-builder-v4/overview`
   - Refresh: 30 seconds
   - Key panels: Fleet health, repair metrics, cost trends

2. **Canary Performance**
   - URL: `/grafana/d/meta-builder-v4/canary`
   - Refresh: 1 minute
   - Key panels: A/B comparison, statistical significance

3. **Chaos Engineering**
   - URL: `/grafana/d/meta-builder-v4/chaos`
   - Refresh: 30 seconds
   - Key panels: Recovery rates, failure patterns

### Alert Rules

```yaml
# High queue depth
- alert: HighQueueDepth
  expr: meta_builder_v4_queue_depth > 100
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "High queue depth detected"
    description: "Queue {{ $labels.queue_name }} has {{ $value }} items"

# Circuit breaker open
- alert: CircuitBreakerOpen
  expr: meta_builder_v4_circuit_breaker_state > 0
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "Circuit breaker open"
    description: "Circuit breaker for {{ $labels.failure_class }} is open"

# Budget exceeded
- alert: BudgetExceeded
  expr: meta_builder_v4_budget_exceeded_total > 0
  for: 1m
  labels:
    severity: warning
  annotations:
    summary: "Budget exceeded"
    description: "Budget {{ $labels.budget_type }} exceeded for tenant {{ $labels.tenant_id }}"

# Canary performance degradation
- alert: CanaryPerformanceDegradation
  expr: meta_builder_v4_canary_comparison{metric_name="success_rate"} < 0.95
  for: 10m
  labels:
    severity: critical
  annotations:
    summary: "Canary performance degradation"
    description: "v4 success rate below 95% threshold"
```

## Emergency Procedures

### Circuit Breaker Management

#### Check Circuit Breaker Status
```bash
# Check all circuit breakers
curl -X GET "http://localhost:8000/api/meta/v4/stats" \
  -H "Authorization: Bearer $API_TOKEN"

# Check specific failure class
curl -X GET "http://localhost:8000/api/meta/v4/circuit-breakers/lint" \
  -H "Authorization: Bearer $API_TOKEN"
```

#### Reset Circuit Breaker
```bash
# Reset circuit breaker for specific failure class
curl -X POST "http://localhost:8000/api/meta/v4/circuit-breakers/lint/reset" \
  -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tenant_id": "tenant_123"}'
```

#### Emergency Disable v4
```bash
# Disable v4 for specific tenant
curl -X POST "http://localhost:8000/api/settings/tenant/tenant_123/feature-flags" \
  -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"meta_v4_enabled": false}'

# Disable v4 globally
export FEATURE_META_V4_ENABLED=false
systemctl restart meta-builder
```

### Queue Management

#### Drain Queues
```bash
# Stop accepting new tasks
curl -X POST "http://localhost:8000/api/meta/v4/queues/drain" \
  -H "Authorization: Bearer $API_TOKEN"

# Check queue status
curl -X GET "http://localhost:8000/api/meta/v4/queues/status" \
  -H "Authorization: Bearer $API_TOKEN"
```

#### Restart Workers
```bash
# Graceful worker shutdown
curl -X POST "http://localhost:8000/api/meta/v4/workers/shutdown" \
  -H "Authorization: Bearer $API_TOKEN"

# Force restart
systemctl restart meta-builder-workers
```

### Budget Management

#### Adjust Budgets
```bash
# Increase budget for specific tenant
curl -X PUT "http://localhost:8000/api/meta/v4/budgets/tenant_123" \
  -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"cost_budget_usd": 20.0, "time_budget_seconds": 3600}'
```

#### Emergency Budget Override
```bash
# Override budget for specific run
curl -X POST "http://localhost:8000/api/meta/v4/runs/run_123/budget-override" \
  -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"cost_budget_usd": 50.0, "reason": "emergency_override"}'
```

## Troubleshooting

### Common Issues

#### High Queue Depth

**Symptoms:**
- Queue depth > 100 items
- Long processing times
- Worker utilization < 50%

**Diagnosis:**
```bash
# Check queue depths
curl -X GET "http://localhost:8000/api/meta/v4/stats" | jq '.queues'

# Check worker status
curl -X GET "http://localhost:8000/api/meta/v4/workers/status" | jq '.'

# Check recent failures
curl -X GET "http://localhost:8000/api/meta/v4/repair-attempts" | jq '.'
```

**Resolution:**
1. Scale up workers for affected queues
2. Check for stuck tasks and restart workers
3. Investigate root cause of failures
4. Consider disabling v4 temporarily

#### Circuit Breaker Open

**Symptoms:**
- All repair attempts failing
- High failure rate for specific class
- Circuit breaker state = "open"

**Diagnosis:**
```bash
# Check circuit breaker status
curl -X GET "http://localhost:8000/api/meta/v4/circuit-breakers" | jq '.'

# Check recent failures
curl -X GET "http://localhost:8000/api/meta/v4/failures?class=lint" | jq '.'
```

**Resolution:**
1. Investigate root cause of failures
2. Check external service dependencies
3. Consider resetting circuit breaker
4. Implement temporary workarounds

#### Budget Exceedances

**Symptoms:**
- High cost per run
- Frequent budget exceedances
- Cost alerts firing

**Diagnosis:**
```bash
# Check cost trends
curl -X GET "http://localhost:8000/api/meta/v4/costs" | jq '.'

# Check model usage
curl -X GET "http://localhost:8000/api/meta/v4/models/usage" | jq '.'
```

**Resolution:**
1. Review model selection logic
2. Adjust budget limits if appropriate
3. Optimize scheduling algorithms
4. Consider cost optimization features

#### Canary Performance Issues

**Symptoms:**
- v4 performance worse than control
- Statistical significance alerts
- High rollback rate

**Diagnosis:**
```bash
# Check canary metrics
curl -X GET "http://localhost:8000/api/meta/v4/canary/stats" | jq '.'

# Compare performance
curl -X GET "http://localhost:8000/api/meta/v4/canary/comparison" | jq '.'
```

**Resolution:**
1. Reduce canary percentage
2. Investigate performance regression
3. Check for configuration issues
4. Consider rolling back v4 features

### Debugging Tools

#### Replay Bundles
```bash
# List replay bundles
curl -X GET "http://localhost:8000/api/meta/v4/replay-bundles" | jq '.'

# Replay specific bundle
curl -X POST "http://localhost:8000/api/meta/v4/replay-bundles/bundle_123/replay" \
  -H "Authorization: Bearer $API_TOKEN"
```

#### Timeline Analysis
```bash
# Get run timeline
curl -X GET "http://localhost:8000/api/meta/v4/runs/run_123/timeline" | jq '.'

# Get repair status
curl -X GET "http://localhost:8000/api/meta/v4/runs/run_123/repair-status" | jq '.'
```

#### Chaos Testing
```bash
# Check chaos stats
curl -X GET "http://localhost:8000/api/meta/v4/chaos/stats" | jq '.'

# Disable chaos
curl -X POST "http://localhost:8000/api/meta/v4/chaos/disable" \
  -H "Authorization: Bearer $API_TOKEN"
```

## Maintenance Procedures

### Daily Checks

1. **Review Dashboard Alerts**
   - Check Grafana dashboards for any alerts
   - Review queue depths and worker utilization
   - Monitor repair success rates

2. **Check Circuit Breakers**
   - Verify all circuit breakers are closed
   - Review any recent failures
   - Check cooldown periods

3. **Monitor Costs**
   - Review daily cost trends
   - Check for budget exceedances
   - Analyze model usage patterns

4. **Canary Performance**
   - Review canary metrics
   - Check statistical significance
   - Monitor promotion/demotion recommendations

### Weekly Tasks

1. **Performance Analysis**
   - Review weekly performance trends
   - Analyze repair phase distribution
   - Check cost efficiency metrics

2. **Capacity Planning**
   - Review worker utilization trends
   - Plan for capacity increases
   - Optimize queue configurations

3. **Security Review**
   - Review circuit breaker patterns
   - Check for security-related failures
   - Audit budget override usage

### Monthly Tasks

1. **Feature Flag Review**
   - Review feature flag usage
   - Plan for feature rollouts
   - Clean up unused overrides

2. **Chaos Testing**
   - Review chaos testing results
   - Update chaos scenarios
   - Plan resilience improvements

3. **Documentation Updates**
   - Update runbook procedures
   - Review alert thresholds
   - Update troubleshooting guides

## Recovery Procedures

### Complete System Failure

1. **Emergency Shutdown**
   ```bash
   # Stop all workers
   systemctl stop meta-builder-workers
   
   # Stop main service
   systemctl stop meta-builder
   ```

2. **Database Recovery**
   ```bash
   # Check database status
   sudo -u postgres pg_isready
   
   # Restore from backup if needed
   pg_restore -d meta_builder_v4 backup.sql
   ```

3. **Service Restart**
   ```bash
   # Start main service
   systemctl start meta-builder
   
   # Start workers
   systemctl start meta-builder-workers
   
   # Verify health
   curl -X GET "http://localhost:8000/health"
   ```

### Partial Failure Recovery

1. **Worker Recovery**
   ```bash
   # Restart specific workers
   systemctl restart meta-builder-worker@cpu
   systemctl restart meta-builder-worker@llm
   
   # Check worker health
   curl -X GET "http://localhost:8000/api/meta/v4/workers/health"
   ```

2. **Queue Recovery**
   ```bash
   # Clear stuck tasks
   curl -X POST "http://localhost:8000/api/meta/v4/queues/clear-stuck" \
     -H "Authorization: Bearer $API_TOKEN"
   
   # Restart queue processing
   curl -X POST "http://localhost:8000/api/meta/v4/queues/restart" \
     -H "Authorization: Bearer $API_TOKEN"
   ```

3. **Circuit Breaker Recovery**
   ```bash
   # Reset all circuit breakers
   curl -X POST "http://localhost:8000/api/meta/v4/circuit-breakers/reset-all" \
     -H "Authorization: Bearer $API_TOKEN"
   ```

## Performance Tuning

### Worker Configuration

```bash
# CPU workers
META_V4_CPU_WORKERS=10
META_V4_CPU_QUEUE_SIZE=100

# IO workers
META_V4_IO_WORKERS=20
META_V4_IO_QUEUE_SIZE=200

# LLM workers
META_V4_LLM_WORKERS=5
META_V4_LLM_QUEUE_SIZE=50
```

### Queue Optimization

```bash
# Queue priorities
META_V4_HIGH_PRIORITY_QUEUE_SIZE=50
META_V4_NORMAL_PRIORITY_QUEUE_SIZE=200
META_V4_LOW_PRIORITY_QUEUE_SIZE=500

# Processing limits
META_V4_MAX_CONCURRENT_TASKS=100
META_V4_MAX_TASKS_PER_WORKER=10
```

### Budget Optimization

```bash
# Default budgets
META_V4_DEFAULT_TIME_BUDGET_SECONDS=1800
META_V4_DEFAULT_COST_BUDGET_USD=10.0
META_V4_DEFAULT_ATTEMPT_BUDGET=10

# Circuit breaker thresholds
META_V4_CIRCUIT_BREAKER_THRESHOLD=5
META_V4_CIRCUIT_BREAKER_COOLDOWN_MINUTES=5
```

## Security Considerations

### Access Control

- All API endpoints require authentication
- Admin operations require elevated privileges
- Audit logging for all configuration changes
- Rate limiting on all endpoints

### Data Protection

- Sensitive data redaction in logs
- Encryption at rest for all data
- Secure communication channels
- Regular security audits

### Compliance

- GDPR compliance for data retention
- SOC 2 compliance for security controls
- Regular penetration testing
- Security incident response procedures

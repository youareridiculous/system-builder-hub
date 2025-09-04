# Meta-Builder v3: Advanced Auto-Fix System

## Overview

Meta-Builder v3 enhances the existing v2 system with advanced auto-fix capabilities, intelligent failure classification, and robust retry/re-planning logic. This system provides production-grade error handling and recovery mechanisms.

## Key Features

### 1. Failure Taxonomy & Classification

The v3 system introduces a comprehensive failure classification system with 11 failure types:

- **TRANSIENT**: Network timeouts, temporary service unavailability
- **INFRA**: Infrastructure issues, deployment failures
- **TEST_ASSERT**: Test failures, assertion errors
- **LINT**: Code style and formatting issues
- **TYPECHECK**: Type checking errors
- **SECURITY**: Security violations, vulnerabilities
- **POLICY**: Policy violations, permissions
- **RUNTIME**: Runtime errors, exceptions
- **SCHEMA_MIGRATION**: Database schema issues
- **RATE_LIMIT**: Rate limiting, throttling
- **UNKNOWN**: Unclassified failures

### 2. Advanced Auto-Fix Agent

The AutoFixerAgentV3 provides intelligent failure resolution with:

- **Retry Logic**: Exponential backoff with configurable limits
- **Patch Generation**: Automatic code fixes for common issues
- **Re-planning**: Intelligent system redesign when needed
- **Escalation**: Human-in-the-loop approval for security/policy issues
- **Rollback**: Safe rollback to previous successful states

### 3. Orchestrator Integration

Enhanced orchestrator with:

- **Retry State Tracking**: Per-step and total attempt counters
- **Failure Signal Processing**: Real-time failure classification
- **Auto-Fix Loop**: Seamless integration with build process
- **Approval Gates**: Human oversight for critical decisions

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Build Step    │───▶│  Failure Signal  │───▶│  Auto-Fixer v3  │
│   Execution     │    │   Classification │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │   Retry State    │    │   Fix Strategy  │
                       │   Management     │    │   Selection     │
                       └──────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │   Approval      │◀───│   Apply Fixes   │
                       │   Gates         │    │                 │
                       └─────────────────┘    └─────────────────┘
```

## API Endpoints

### Auto-Fix History
```
GET /api/meta/v3/runs/{run_id}/autofix
```
Returns auto-fix history for a build run including retry state and attempt details.

### Approval Management
```
POST /api/meta/v3/approvals/{gate_id}/approve
POST /api/meta/v3/approvals/{gate_id}/reject
```
Approve or reject auto-fix escalations (requires owner/admin role).

### Run Retry
```
POST /api/meta/v3/runs/{run_id}/retry
```
Manually retry a failed run with incremented iteration.

### Escalation History
```
GET /api/meta/v3/runs/{run_id}/escalations
```
Get escalation history for a run.

### Plan Deltas
```
GET /api/meta/v3/runs/{run_id}/plan-deltas
```
Get plan delta history showing re-planning events.

### Failure Classification
```
POST /api/meta/v3/classify-failure
```
Classify a failure using the v3 classifier.

## Configuration

### Retry Policy

Default retry configuration:

```python
RetryPolicy:
  max_retries:
    TRANSIENT: 3
    INFRA: 2
    TEST_ASSERT: 0
    LINT: 0
    TYPECHECK: 0
    SECURITY: 0
    POLICY: 0
    RUNTIME: 1
    SCHEMA_MIGRATION: 0
    RATE_LIMIT: 3
    UNKNOWN: 2
  
  backoff_multiplier:
    TRANSIENT: 2.0
    INFRA: 1.5
    RATE_LIMIT: 2.0
    RUNTIME: 1.0
    UNKNOWN: 1.5
  
  base_delay: 1.0 seconds
  max_delay: 60.0 seconds
  max_total_attempts: 6
  max_per_step_attempts: 3
```

## Usage Examples

### Basic Auto-Fix Flow

```python
from src.meta_builder_v3.orchestrator_v3 import MetaBuilderOrchestratorV3
from src.meta_builder_v3.failures import classify_failure

# Execute step with auto-fix
orchestrator = MetaBuilderOrchestratorV3()
result = await orchestrator.execute_step_with_auto_fix(step, context, db_session)

if result["success"]:
    print("Step completed successfully")
else:
    print(f"Auto-fix outcome: {result['auto_fix_outcome']}")
```

### Failure Classification

```python
from src.meta_builder_v3.failures import classify_failure

# Classify a failure
signal = classify_failure(
    step_name="test_step",
    logs="AssertionError: expected 1 but got 2",
    artifacts=[]
)

print(f"Failure type: {signal.type}")
print(f"Can retry: {signal.can_retry}")
print(f"Requires re-plan: {signal.requires_replan}")
```

### Custom Retry Policy

```python
from src.meta_builder_v3.auto_fixer_v3 import RetryPolicy

# Custom retry policy
policy = RetryPolicy()
policy.max_retries[FailureType.TRANSIENT] = 5
policy.base_delay = 2.0
policy.max_delay = 120.0
```

## Database Schema

### AutoFixRun Table
```sql
CREATE TABLE auto_fix_runs (
    id UUID PRIMARY KEY,
    run_id UUID REFERENCES build_runs(id),
    step_id UUID REFERENCES build_steps(id),
    signal_type VARCHAR(50) NOT NULL,
    strategy VARCHAR(50),
    outcome VARCHAR(50) NOT NULL,
    attempt INTEGER NOT NULL DEFAULT 1,
    backoff FLOAT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

### RetryState Table
```sql
CREATE TABLE retry_states (
    id UUID PRIMARY KEY,
    run_id UUID REFERENCES build_runs(id) UNIQUE,
    attempt_counter INTEGER NOT NULL DEFAULT 0,
    per_step_attempts JSON NOT NULL DEFAULT '{}',
    total_attempts INTEGER NOT NULL DEFAULT 0,
    last_backoff_seconds FLOAT,
    max_total_attempts INTEGER NOT NULL DEFAULT 6,
    max_per_step_attempts INTEGER NOT NULL DEFAULT 3,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

### PlanDelta Table
```sql
CREATE TABLE plan_deltas (
    id UUID PRIMARY KEY,
    original_plan_id UUID REFERENCES scaffold_plans(id),
    new_plan_id UUID REFERENCES scaffold_plans(id),
    run_id UUID REFERENCES build_runs(id),
    delta_data JSON NOT NULL,
    triggered_by VARCHAR(100) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

## Testing

### Running Tests

```bash
# Run all v3 tests
pytest tests/meta_builder_v3/ -v

# Run specific test categories
pytest tests/meta_builder_v3/test_failures.py -v
pytest tests/meta_builder_v3/test_auto_fixer_v3.py -v
pytest tests/meta_builder_v3/test_orchestrator_integration.py -v
pytest tests/meta_builder_v3/test_api_v3.py -v
```

### Test Coverage

The v3 system includes comprehensive tests for:

- **Failure Classification**: Pattern matching, confidence scoring, rule application
- **Auto-Fixer Logic**: Strategy selection, retry logic, fix generation
- **Orchestrator Integration**: Step execution, failure handling, state management
- **API Endpoints**: CRUD operations, permissions, error handling

## Monitoring & Observability

### Metrics

Key metrics to monitor:

- `autofix_attempts_total{signal, outcome}`
- `autofix_backoff_seconds`
- `autofix_replans_total`
- `autofix_success_ratio`

### Logs

Structured logging includes:

- `run_id`: Build run identifier
- `step_id`: Step identifier
- `signal_type`: Failure classification
- `strategy`: Fix strategy used
- `outcome`: Auto-fix outcome
- `attempt`: Attempt number

### Audit Events

Audit events for compliance:

- `autofix.classified`: Failure classification
- `autofix.retry`: Retry attempt
- `autofix.patch_applied`: Fix applied
- `autofix.replanned`: System re-planned
- `autofix.escalated`: Escalated to human
- `approval.granted`: Approval granted
- `approval.rejected`: Approval rejected

## Migration Guide

### From v2 to v3

1. **Database Migration**: Run the v3 migration to create new tables
2. **API Updates**: Update API calls to use v3 endpoints
3. **Configuration**: Update retry policies and failure patterns
4. **Monitoring**: Add v3 metrics and logging

### Backward Compatibility

The v3 system maintains backward compatibility with v2:

- All v2 APIs continue to work
- Existing data is preserved
- Gradual migration path available

## Troubleshooting

### Common Issues

1. **High Retry Counts**: Check failure classification patterns
2. **Excessive Re-planning**: Review architecture failure detection
3. **Approval Bottlenecks**: Monitor escalation frequency
4. **Performance Issues**: Check retry backoff configuration

### Debug Mode

Enable debug logging:

```python
import logging
logging.getLogger('src.meta_builder_v3').setLevel(logging.DEBUG)
```

### Manual Intervention

When auto-fix gives up:

1. Review failure signals and classification
2. Check retry state and limits
3. Consider manual re-planning
4. Escalate to development team

## Future Enhancements

### Planned Features

1. **Machine Learning**: ML-based failure prediction
2. **Advanced Patterns**: Custom failure pattern definitions
3. **Distributed Tracing**: End-to-end request tracing
4. **Performance Optimization**: Caching and optimization
5. **Integration APIs**: Third-party system integration

### Roadmap

- **Q1 2024**: ML failure prediction
- **Q2 2024**: Advanced pattern engine
- **Q3 2024**: Performance optimization
- **Q4 2024**: Enterprise features

## Feature Flag Behavior

### Configuration

Meta-Builder v3 behavior is controlled by feature flags at multiple levels:

1. **Platform Level**: Environment variables set defaults
2. **Tenant Level**: Admin UI allows tenant-specific overrides
3. **Run Level**: API allows run-specific overrides

### Default Settings

| Environment | Auto-Fix Enabled | Max Total Attempts | Max Per-Step Attempts | Backoff Cap |
|-------------|------------------|-------------------|----------------------|-------------|
| Development | true | 10 | 5 | 60s |
| Staging | true | 6 | 3 | 60s |
| Production | false | 6 | 3 | 60s |

### Admin UI

Navigate to **Settings → Builder → Auto-Fix (v3)** to:

- Enable/disable v3 auto-fix for the tenant
- Adjust retry budgets and backoff limits
- View current settings and precedence
- Reset to platform defaults

### API Endpoints

```bash
# Get tenant settings
GET /api/meta/v2/tenants/{tenant_id}/settings

# Update tenant settings
PUT /api/meta/v2/tenants/{tenant_id}/settings

# Get run settings
GET /api/meta/v2/runs/{run_id}/settings

# Update run settings
PUT /api/meta/v2/runs/{run_id}/settings
```

## Observability Dashboards

### Grafana Dashboard

Import the Meta-Builder v3 dashboard from `ops/grafana/meta_builder_v3_dashboard.json`:

1. Open Grafana
2. Go to **Dashboards → Import**
3. Upload the JSON file
4. Configure Prometheus data source
5. Save the dashboard

### Dashboard Panels

The dashboard includes panels for:

- **Auto-Fix Attempts by Signal Type**: Shows distribution of failure types
- **Auto-Fix Success Ratio**: Gauge showing overall success rate
- **Backoff Delay Distribution**: Histogram of retry delays
- **Re-Plans Triggered**: Counter of re-planning events
- **Approval Requests**: Time series of approval workflow
- **Auto-Fix Outcomes**: Pie chart of final outcomes
- **Processing Time by Operation**: Bar chart of operation performance

### Key Metrics

Monitor these metrics for system health:

- `autofix_attempts_total{signal_type, outcome}`
- `autofix_success_ratio`
- `autofix_backoff_seconds_bucket`
- `autofix_replans_total`
- `approval_requests_total{status}`

### Alerts

Set up alerts for:

- Success ratio < 70%
- Excessive re-plans (> 10/hour)
- High approval rejection rate (> 50%)
- Backoff delays > 60 seconds average

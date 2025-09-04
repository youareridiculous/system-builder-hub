# Meta-Builder v4: Self-Healing Orchestrator & Distributed Agents

## Overview

Meta-Builder v4 introduces a comprehensive self-healing orchestration system with distributed agent execution, cost-aware scheduling, and advanced failure recovery mechanisms. This version builds upon v3's auto-fix capabilities with multi-phase repair, circuit breakers, and intelligent resource management.

## Architecture

### Core Components

1. **Distributed Agent Execution** (`dist_exec.py`)
   - Worker pool abstraction with queue management
   - Per-agent queue classes (CPU, IO, LLM, High, Low priority)
   - Concurrency controls and idempotent execution
   - Heartbeats and lease renewal

2. **Self-Healing Orchestrator** (`orchestrator_v4.py`)
   - Multi-phase repair: Retry → Patch → Re-plan → Rollback
   - Circuit breakers per failure class
   - Safety sandbox with write allowlists
   - SLO enforcement and budget management

3. **Cost-Aware Scheduling** (`scheduling.py`)
   - Dynamic model selection based on SLA and budget
   - Queue routing optimization
   - Token metering and cost tracking
   - SLA-aware task prioritization

4. **Enhanced Evaluation** (`eval_v4.py`)
   - 30+ golden test cases
   - Deterministic replay bundles
   - Confidence scoring and risk assessment
   - Multi-agent coordination testing

5. **Canary Testing** (`canary.py`)
   - A/B testing with gradual rollout
   - Performance comparison and metrics
   - Automatic promotion/demotion logic
   - Statistical significance validation

6. **Chaos Testing** (`chaos.py`)
   - Fault injection for resilience validation
   - Multiple chaos types (network, memory, CPU, etc.)
   - Recovery time measurement
   - Failure pattern analysis

## Database Schema

### New Tables

```sql
-- Canary testing samples
mb_v4_canary_sample (
    id, run_id, tenant_id, canary_group, assigned_at, completed_at,
    success, metrics, cost_usd, duration_seconds, retry_count,
    replan_count, rollback_count
)

-- Deterministic replay bundles
mb_v4_replay_bundle (
    id, run_id, tenant_id, bundle_hash, prompts, tool_inputs,
    tool_outputs, diffs, failure_reason, created_at, replayed_at,
    replay_success
)

-- Queue leases for distributed workers
mb_v4_queue_lease (
    id, worker_id, queue_name, tenant_id, lease_key, acquired_at,
    expires_at, last_heartbeat, status
)

-- Budget tracking
mb_v4_run_budget (
    id, run_id, tenant_id, budget_type, budget_limit, budget_used,
    budget_unit, created_at, updated_at, exceeded_at
)

-- Circuit breakers
mb_v4_circuit_breaker (
    id, tenant_id, failure_class, failure_count, threshold, state,
    opened_at, cooldown_until, last_failure_at, created_at, updated_at
)

-- Agent metrics
mb_v4_agent_metrics (
    id, tenant_id, agent_name, queue_name, metric_type, metric_value,
    metric_unit, timestamp, metadata
)
```

## Feature Flags

### Environment Variables

```bash
# Meta-Builder v4 Core
FEATURE_META_V4_ENABLED=false
FEATURE_META_V4_CANARY_PERCENT=0.0

# Repair Configuration
META_V4_MAX_REPAIR_ATTEMPTS=5
META_V4_CIRCUIT_BREAKER_THRESHOLD=5
META_V4_CIRCUIT_BREAKER_COOLDOWN_MINUTES=5

# Budget Defaults
META_V4_DEFAULT_TIME_BUDGET_SECONDS=1800
META_V4_DEFAULT_COST_BUDGET_USD=10.0
META_V4_DEFAULT_ATTEMPT_BUDGET=10

# Chaos Testing
META_V4_CHAOS_ENABLED=false
META_V4_CHAOS_INJECTION_PROBABILITY=0.1
```

### Precedence Order

1. **Platform Defaults** (environment variables)
2. **Tenant Overrides** (Settings Hub)
3. **Run Overrides** (per-run configuration)

## API Endpoints

### Core v4 Endpoints

```http
# Promote run to v4
POST /api/meta/v4/runs/{id}/promote

# Get run timeline
GET /api/meta/v4/runs/{id}/timeline

# Get v4 statistics
GET /api/meta/v4/stats

# Get repair status
GET /api/meta/v4/runs/{id}/repair-status

# Approve rollback
POST /api/meta/v4/runs/{id}/approve-rollback
```

### Replay Bundle Endpoints

```http
# Get replay bundles
GET /api/meta/v4/replay-bundles

# Replay specific bundle
POST /api/meta/v4/replay-bundles/{id}/replay
```

### Golden Test Endpoints

```http
# Get golden test stats
GET /api/meta/v4/golden-tests

# Run specific test
POST /api/meta/v4/golden-tests/{id}/run
```

### Canary & Chaos Endpoints

```http
# Get canary stats
GET /api/meta/v4/canary/stats

# Get chaos stats
GET /api/meta/v4/chaos/stats
```

## Self-Healing Flow

### Repair Phases

1. **Retry Phase**
   - Simple retry with exponential backoff
   - Uses v3 auto-fix logic
   - Quick resolution for transient issues

2. **Patch Phase**
   - Targeted code patches
   - Safety checks and validation
   - File allowlist enforcement

3. **Re-plan Phase**
   - Partial re-planning for impacted modules
   - Scope-limited changes
   - Dependency analysis

4. **Rollback Phase**
   - Human approval required
   - Rollback to last known good state
   - Escalation path

### Circuit Breakers

- **Failure Classes**: Lint, Test, Infra, Security, Runtime
- **States**: Closed, Open, Half-Open
- **Thresholds**: Configurable per tenant
- **Cooldown**: Automatic recovery periods

## Cost-Aware Scheduling

### Model Selection

- **Small Models**: Fast, cheap (GPT-3.5-turbo, Claude-3-haiku)
- **Medium Models**: Balanced (GPT-4, Claude-3-sonnet)
- **Large Models**: High quality, expensive (GPT-4-turbo, Claude-3-opus)

### SLA Classes

- **Fast**: < 5 minutes, higher cost acceptable
- **Normal**: < 15 minutes, balanced cost/quality
- **Thorough**: < 30 minutes, prioritize quality

### Queue Routing

- **CPU**: CPU-intensive agents (codegen, analysis)
- **IO**: I/O-bound agents (file operations, git)
- **LLM**: LLM-dependent agents (planning, generation)
- **High**: High priority tasks
- **Low**: Low priority tasks

## Canary Testing

### Configuration

```python
canary_config = CanaryConfig(
    enabled=True,
    canary_percent=0.15,  # 15% of runs use v4
    min_sample_size=100,
    evaluation_window_hours=24,
    success_threshold=0.95,
    cost_threshold=1.2,
    duration_threshold=1.1
)
```

### Evaluation Metrics

- **Success Rate**: Must maintain 95%+ success rate
- **Cost Efficiency**: Must not exceed 120% of control cost
- **Duration**: Must not exceed 110% of control duration

### Recommendations

- `promote_v4_aggressively`: Excellent performance
- `promote_v4_cautiously`: Good performance
- `maintain_canary`: Stable performance
- `reduce_canary_percentage`: Performance concerns
- `rollback_v4_immediately`: Critical issues

## Chaos Testing

### Chaos Types

- **Transient Errors**: Connection timeouts, rate limits
- **Network Issues**: Latency, failures, timeouts
- **Resource Pressure**: Memory, CPU, disk pressure
- **Service Failures**: Unavailable services

### Configuration

```python
chaos_config = ChaosConfig(
    enabled=True,
    chaos_types=[ChaosType.TRANSIENT_ERROR, ChaosType.NETWORK_LATENCY],
    injection_probability=0.1,  # 10% chance
    max_duration_seconds=30,
    recovery_timeout_seconds=60
)
```

## Monitoring & Metrics

### Prometheus Metrics

```python
# Agent metrics
meta_builder_v4_agent_latency_seconds
meta_builder_v4_agent_throughput_total
meta_builder_v4_queue_depth

# Repair metrics
meta_builder_v4_repair_attempts_total
meta_builder_v4_repair_duration_seconds

# Budget metrics
meta_builder_v4_budget_usage
meta_builder_v4_budget_exceeded_total

# Cost metrics
meta_builder_v4_run_cost_usd
meta_builder_v4_total_cost_usd

# Canary metrics
meta_builder_v4_canary_runs_total
meta_builder_v4_canary_comparison

# Chaos metrics
meta_builder_v4_chaos_events_total
meta_builder_v4_chaos_recovery_seconds
```

### Grafana Dashboards

- **Fleet Overview**: Worker utilization, queue depths
- **Repair Analytics**: Success rates, phase distribution
- **Cost Analysis**: Budget usage, cost trends
- **Canary Performance**: A/B comparison metrics
- **Chaos Resilience**: Recovery rates, failure patterns

## Integration with v2/v3

### Backward Compatibility

- All v2/v3 APIs remain unchanged
- v4 features are opt-in via feature flags
- Gradual migration path through canary testing
- Fallback to v3 auto-fix when v4 is disabled

### Adapter Pattern

```python
# v4 orchestrator integrates with v3 adapter
self.v3_adapter = V3AutoFixAdapter(db_session, orchestrator_v2)

# v3 auto-fix logic is reused in v4 retry phase
result = await self.v3_adapter.auto_fix(run_id, step_id, failure_reason)
```

## Security & Privacy

### Safety Sandbox

- **Write Allowlist**: Only allowed paths can be modified
- **Secret Denylist**: Sensitive files are protected
- **Patch Size Limits**: Maximum patch size enforcement
- **Binary Diff Guards**: Protection against binary changes

### Privacy Integration

- Respects all privacy modes (Local-Only, BYO Keys, Private Cloud)
- No violation of domain allowlists
- Automatic redaction of sensitive data
- Tenant isolation maintained

## Deployment

### Staging Configuration

```bash
FEATURE_META_V4_ENABLED=true
FEATURE_META_V4_CANARY_PERCENT=50
META_V4_CHAOS_ENABLED=true
META_V4_CHAOS_INJECTION_PROBABILITY=0.05
```

### Production Configuration

```bash
FEATURE_META_V4_ENABLED=false
FEATURE_META_V4_CANARY_PERCENT=0
META_V4_CHAOS_ENABLED=false
```

### Migration Strategy

1. **Phase 1**: Deploy to staging with canary testing
2. **Phase 2**: Enable for internal dogfooding
3. **Phase 3**: Gradual rollout to select tenants
4. **Phase 4**: Full production deployment

## Troubleshooting

### Common Issues

1. **Circuit Breaker Open**
   - Check failure patterns for specific classes
   - Review cooldown periods
   - Consider adjusting thresholds

2. **Budget Exceeded**
   - Analyze cost patterns
   - Review model selection logic
   - Adjust budget limits if appropriate

3. **Canary Performance Issues**
   - Compare metrics between control and v4 groups
   - Check for statistical significance
   - Review evaluation criteria

4. **Chaos Recovery Failures**
   - Analyze recovery time patterns
   - Check circuit breaker states
   - Review failure injection patterns

### Debugging Tools

- **Replay Bundles**: Reproduce failures deterministically
- **Timeline View**: Step-by-step execution history
- **Repair Status**: Detailed repair phase information
- **Metrics Dashboard**: Real-time performance monitoring

## Future Enhancements

### Planned Features

1. **Advanced Scheduling**
   - Machine learning-based queue optimization
   - Predictive resource allocation
   - Dynamic scaling based on demand

2. **Enhanced Repair**
   - AI-powered patch generation
   - Semantic code analysis
   - Cross-module impact assessment

3. **Advanced Canary**
   - Multi-variant testing
   - Statistical significance testing
   - Automatic rollback triggers

4. **Extended Chaos**
   - Custom chaos scenarios
   - Chaos engineering workflows
   - Failure injection APIs

### Integration Roadmap

1. **Kubernetes Integration**
   - Native K8s deployment
   - Horizontal pod autoscaling
   - Service mesh integration

2. **Observability Stack**
   - Distributed tracing
   - Advanced alerting
   - Performance profiling

3. **Security Enhancements**
   - Code signing verification
   - Vulnerability scanning
   - Compliance automation

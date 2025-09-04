# Canary Testing & Chaos Engineering for Meta-Builder v4

## Overview

Meta-Builder v4 includes comprehensive canary testing and chaos engineering capabilities to ensure safe deployment and validate system resilience. This document covers the implementation, configuration, and operational procedures for both systems.

## Canary Testing

### Architecture

Canary testing in Meta-Builder v4 uses an A/B testing approach to compare v4 performance against the v2/v3 baseline. The system automatically assigns runs to either the control group (v2/v3) or the v4 experimental group based on configurable percentages.

#### Components

1. **CanaryManager**: Manages canary configuration and run assignment
2. **CanarySample**: Database model for tracking canary runs
3. **CanaryConfig**: Configuration for canary testing parameters
4. **Evaluation Engine**: Statistical analysis and recommendation generation

#### Database Schema

```sql
mb_v4_canary_sample (
    id, run_id, tenant_id, canary_group, assigned_at, completed_at,
    success, metrics, cost_usd, duration_seconds, retry_count,
    replan_count, rollback_count
)
```

### Configuration

#### Environment Variables

```bash
# Enable canary testing
FEATURE_META_V4_ENABLED=true
FEATURE_META_V4_CANARY_PERCENT=0.15

# Canary evaluation parameters
META_V4_CANARY_MIN_SAMPLE_SIZE=100
META_V4_CANARY_EVALUATION_WINDOW_HOURS=24
META_V4_CANARY_SUCCESS_THRESHOLD=0.95
META_V4_CANARY_COST_THRESHOLD=1.2
META_V4_CANARY_DURATION_THRESHOLD=1.1
```

#### CanaryConfig Class

```python
@dataclass
class CanaryConfig:
    enabled: bool = False
    canary_percent: float = 0.0  # 0.0 to 1.0
    min_sample_size: int = 100
    max_sample_size: int = 1000
    evaluation_window_hours: int = 24
    success_threshold: float = 0.95  # 95% success rate
    cost_threshold: float = 1.2      # 20% cost increase max
    duration_threshold: float = 1.1  # 10% duration increase max
```

### Run Assignment Logic

```python
async def should_use_v4(self, run_id: str, tenant_id: str) -> bool:
    """Determine if a run should use v4 based on canary configuration."""
    if not self.config.enabled:
        return False
    
    if self.config.canary_percent <= 0.0:
        return False
    
    # Check if run is already assigned to a group
    existing_sample = await self._get_canary_sample(run_id)
    if existing_sample:
        return existing_sample.canary_group == CanaryGroup.V4.value
    
    # Determine group based on canary percentage
    use_v4 = random.random() < self.config.canary_percent
    
    # Create canary sample
    await self._create_canary_sample(run_id, tenant_id, use_v4)
    
    return use_v4
```

### Metrics Collection

The canary system collects comprehensive metrics for each run:

- **Success Rate**: Whether the run completed successfully
- **Cost**: Total cost in USD
- **Duration**: Total execution time in seconds
- **Retry Count**: Number of retry attempts
- **Replan Count**: Number of re-plan attempts
- **Rollback Count**: Number of rollback attempts

### Statistical Analysis

#### Performance Comparison

```python
def _calculate_group_metrics(self, samples: List) -> CanaryMetrics:
    """Calculate metrics for a group of samples."""
    if not samples:
        return CanaryMetrics(
            success_rate=0.0,
            avg_cost_usd=0.0,
            avg_duration_seconds=0.0,
            retry_rate=0.0,
            replan_rate=0.0,
            rollback_rate=0.0,
            confidence_score=0.0,
            sample_size=0
        )
    
    successful_runs = [s for s in samples if s.success]
    success_rate = len(successful_runs) / len(samples)
    
    avg_cost = sum(s.cost_usd or 0 for s in samples) / len(samples)
    avg_duration = sum(s.duration_seconds or 0 for s in samples) / len(samples)
    
    avg_retries = sum(s.retry_count or 0 for s in samples) / len(samples)
    avg_replans = sum(s.replan_count or 0 for s in samples) / len(samples)
    avg_rollbacks = sum(s.rollback_count or 0 for s in samples) / len(samples)
    
    return CanaryMetrics(
        success_rate=success_rate,
        avg_cost_usd=avg_cost,
        avg_duration_seconds=avg_duration,
        retry_rate=avg_retries,
        replan_rate=avg_replans,
        rollback_rate=avg_rollbacks,
        confidence_score=0.0,  # Calculated separately
        sample_size=len(samples)
    )
```

#### Evaluation Logic

```python
async def evaluate_canary_performance(self) -> Dict[str, Any]:
    """Evaluate canary performance against thresholds."""
    metrics = await self.get_canary_metrics(self.config.evaluation_window_hours)
    
    control = metrics["control"]
    v4 = metrics["v4"]
    
    # Check if we have enough samples
    if control.sample_size < self.config.min_sample_size or v4.sample_size < self.config.min_sample_size:
        return {
            "evaluation_ready": False,
            "reason": "Insufficient sample size",
            "control_samples": control.sample_size,
            "v4_samples": v4.sample_size,
            "min_required": self.config.min_sample_size
        }
    
    # Calculate relative performance
    success_ratio = v4.success_rate / control.success_rate if control.success_rate > 0 else 0.0
    cost_ratio = v4.avg_cost_usd / control.avg_cost_usd if control.avg_cost_usd > 0 else 1.0
    duration_ratio = v4.avg_duration_seconds / control.avg_duration_seconds if control.avg_duration_seconds > 0 else 1.0
    
    # Evaluate against thresholds
    success_ok = success_ratio >= self.config.success_threshold
    cost_ok = cost_ratio <= self.config.cost_threshold
    duration_ok = duration_ratio <= self.config.duration_threshold
    
    overall_success = success_ok and cost_ok and duration_ok
    
    return {
        "evaluation_ready": True,
        "overall_success": overall_success,
        "metrics": {
            "success_rate": {
                "control": control.success_rate,
                "v4": v4.success_rate,
                "ratio": success_ratio,
                "threshold": self.config.success_threshold,
                "pass": success_ok
            },
            "cost": {
                "control": control.avg_cost_usd,
                "v4": v4.avg_cost_usd,
                "ratio": cost_ratio,
                "threshold": self.config.cost_threshold,
                "pass": cost_ok
            },
            "duration": {
                "control": control.avg_duration_seconds,
                "v4": v4.avg_duration_seconds,
                "ratio": duration_ratio,
                "threshold": self.config.duration_threshold,
                "pass": duration_ok
            }
        },
        "recommendation": self._get_recommendation(overall_success, success_ratio, cost_ratio, duration_ratio)
    }
```

### Recommendations

The canary system provides automated recommendations based on performance analysis:

```python
def _get_recommendation(self, overall_success: bool, success_ratio: float, 
                       cost_ratio: float, duration_ratio: float) -> str:
    """Get recommendation based on evaluation results."""
    if overall_success:
        if success_ratio > 1.1 and cost_ratio < 0.9:
            return "promote_v4_aggressively"
        elif success_ratio > 1.05:
            return "promote_v4_cautiously"
        else:
            return "maintain_canary"
    else:
        if success_ratio < 0.8:
            return "rollback_v4_immediately"
        elif cost_ratio > 1.5:
            return "reduce_canary_percentage"
        else:
            return "investigate_and_adjust"
```

### API Endpoints

#### Get Canary Statistics

```http
GET /api/meta/v4/canary/stats
```

Response:
```json
{
  "config": {
    "enabled": true,
    "canary_percent": 0.15,
    "evaluation_window_hours": 24
  },
  "samples": {
    "total": 1000,
    "control": 850,
    "v4": 150,
    "completed": 950
  },
  "actual_percent": 0.15,
  "evaluation": {
    "evaluation_ready": true,
    "overall_success": true,
    "metrics": {
      "success_rate": {
        "control": 0.94,
        "v4": 0.96,
        "ratio": 1.02,
        "threshold": 0.95,
        "pass": true
      },
      "cost": {
        "control": 2.5,
        "v4": 2.4,
        "ratio": 0.96,
        "threshold": 1.2,
        "pass": true
      },
      "duration": {
        "control": 300.0,
        "v4": 295.0,
        "ratio": 0.98,
        "threshold": 1.1,
        "pass": true
      }
    },
    "recommendation": "promote_v4_cautiously"
  }
}
```

### Operational Procedures

#### Starting Canary Testing

1. **Enable Feature Flag**
   ```bash
   export FEATURE_META_V4_ENABLED=true
   export FEATURE_META_V4_CANARY_PERCENT=0.05  # Start with 5%
   ```

2. **Monitor Initial Results**
   ```bash
   # Check canary stats every hour
   curl -X GET "http://localhost:8000/api/meta/v4/canary/stats" | jq '.'
   ```

3. **Gradual Increase**
   ```bash
   # Increase to 10% after 24 hours of good performance
   export FEATURE_META_V4_CANARY_PERCENT=0.10
   ```

#### Responding to Issues

1. **Performance Degradation**
   ```bash
   # Reduce canary percentage
   export FEATURE_META_V4_CANARY_PERCENT=0.01
   
   # Investigate root cause
   curl -X GET "http://localhost:8000/api/meta/v4/canary/stats" | jq '.evaluation'
   ```

2. **Critical Issues**
   ```bash
   # Disable v4 immediately
   export FEATURE_META_V4_ENABLED=false
   systemctl restart meta-builder
   ```

## Chaos Engineering

### Architecture

Chaos engineering in Meta-Builder v4 uses controlled fault injection to validate system resilience and identify failure modes before they occur in production.

#### Components

1. **ChaosEngine**: Manages chaos testing configuration and execution
2. **ChaosEvent**: Database model for tracking chaos events
3. **ChaosConfig**: Configuration for chaos testing parameters
4. **ChaosType**: Enumeration of different chaos types

#### Chaos Types

```python
class ChaosType(Enum):
    """Types of chaos to inject."""
    TRANSIENT_ERROR = "transient_error"
    RATE_LIMIT = "rate_limit"
    NETWORK_LATENCY = "network_latency"
    NETWORK_FAILURE = "network_failure"
    TIMEOUT = "timeout"
    MEMORY_PRESSURE = "memory_pressure"
    CPU_PRESSURE = "cpu_pressure"
    DISK_PRESSURE = "disk_pressure"
```

### Configuration

#### Environment Variables

```bash
# Enable chaos testing
META_V4_CHAOS_ENABLED=true
META_V4_CHAOS_INJECTION_PROBABILITY=0.1
META_V4_CHAOS_MAX_DURATION_SECONDS=30
META_V4_CHAOS_RECOVERY_TIMEOUT_SECONDS=60
```

#### ChaosConfig Class

```python
@dataclass
class ChaosConfig:
    enabled: bool = False
    chaos_types: List[ChaosType] = field(default_factory=list)
    injection_probability: float = 0.1  # 10% chance of injection
    max_duration_seconds: int = 30
    recovery_timeout_seconds: int = 60
```

### Fault Injection Logic

```python
async def should_inject_chaos(self, run_id: str, step_id: str) -> bool:
    """Determine if chaos should be injected for this step."""
    if not self.config.enabled:
        return False
    
    if not self.config.chaos_types:
        return False
    
    # Check probability
    if random.random() > self.config.injection_probability:
        return False
    
    # Check if we already have an active event for this run
    if any(event.run_id == run_id for event in self.active_events.values()):
        return False
    
    return True

async def inject_chaos(self, run_id: str, step_id: str) -> Optional[ChaosEvent]:
    """Inject chaos for a specific step."""
    if not await self.should_inject_chaos(run_id, step_id):
        return None
    
    # Select random chaos type
    chaos_type = random.choice(self.config.chaos_types)
    
    # Create chaos event
    event = ChaosEvent(
        id=f"chaos_{run_id}_{step_id}_{int(time.time())}",
        chaos_type=chaos_type,
        run_id=run_id,
        step_id=step_id,
        injected_at=datetime.utcnow()
    )
    
    # Inject the chaos
    await self._execute_chaos(event)
    
    # Track the event
    self.active_events[event.id] = event
    
    return event
```

### Chaos Types Implementation

#### Transient Errors

```python
async def _inject_transient_error(self, event: ChaosEvent):
    """Inject a transient error."""
    # Simulate random transient errors
    error_types = [
        "connection_timeout",
        "rate_limit_exceeded", 
        "service_unavailable",
        "internal_server_error"
    ]
    
    error_type = random.choice(error_types)
    event.metadata["error_type"] = error_type
    
    # Simulate error by raising exception
    if random.random() < 0.7:  # 70% chance of error
        raise Exception(f"Chaos: Transient error - {error_type}")
```

#### Network Latency

```python
async def _inject_network_latency(self, event: ChaosEvent):
    """Inject network latency."""
    latency_ms = random.randint(1000, 5000)  # 1-5 seconds
    event.metadata["latency_ms"] = latency_ms
    
    # Simulate latency
    await asyncio.sleep(latency_ms / 1000.0)
```

#### Memory Pressure

```python
async def _inject_memory_pressure(self, event: ChaosEvent):
    """Inject memory pressure."""
    # Simulate memory pressure by allocating memory
    memory_mb = random.randint(100, 500)
    event.metadata["memory_mb"] = memory_mb
    
    # In a real implementation, this would actually allocate memory
    # For now, just simulate the pressure
    await asyncio.sleep(1.0)
    
    if random.random() < 0.3:  # 30% chance of OOM
        raise Exception("Chaos: Out of memory")
```

### Recovery Tracking

```python
async def resolve_chaos(self, event_id: str, recovery_successful: bool = True):
    """Resolve a chaos event."""
    if event_id not in self.active_events:
        return
    
    event = self.active_events[event_id]
    event.resolved_at = datetime.utcnow()
    event.duration_seconds = (event.resolved_at - event.injected_at).total_seconds()
    event.recovery_successful = recovery_successful
    
    # Move to history
    self.event_history.append(event)
    del self.active_events[event_id]
```

### Statistics and Analysis

```python
async def get_chaos_stats(self) -> Dict[str, Any]:
    """Get chaos testing statistics."""
    total_events = len(self.event_history) + len(self.active_events)
    
    if total_events == 0:
        return {
            "total_events": 0,
            "active_events": 0,
            "recovery_rate": 0.0,
            "chaos_types": {},
            "avg_duration_seconds": 0.0
        }
    
    # Calculate recovery rate
    resolved_events = [e for e in self.event_history if e.recovery_successful is not None]
    successful_recoveries = [e for e in resolved_events if e.recovery_successful]
    recovery_rate = len(successful_recoveries) / len(resolved_events) if resolved_events else 0.0
    
    # Count by chaos type
    chaos_types = {}
    for event in self.event_history + list(self.active_events.values()):
        chaos_type = event.chaos_type.value
        chaos_types[chaos_type] = chaos_types.get(chaos_type, 0) + 1
    
    # Calculate average duration
    durations = [e.duration_seconds for e in self.event_history if e.duration_seconds is not None]
    avg_duration = sum(durations) / len(durations) if durations else 0.0
    
    return {
        "total_events": total_events,
        "active_events": len(self.active_events),
        "recovery_rate": recovery_rate,
        "chaos_types": chaos_types,
        "avg_duration_seconds": avg_duration,
        "config": {
            "enabled": self.config.enabled,
            "injection_probability": self.config.injection_probability,
            "max_duration_seconds": self.config.max_duration_seconds
        }
    }
```

### API Endpoints

#### Get Chaos Statistics

```http
GET /api/meta/v4/chaos/stats
```

Response:
```json
{
  "total_events": 25,
  "active_events": 2,
  "recovery_rate": 0.92,
  "chaos_types": {
    "transient_error": 10,
    "rate_limit": 5,
    "network_latency": 5,
    "timeout": 3,
    "memory_pressure": 2
  },
  "avg_duration_seconds": 15.5,
  "config": {
    "enabled": true,
    "injection_probability": 0.1,
    "max_duration_seconds": 30
  }
}
```

### Operational Procedures

#### Starting Chaos Testing

1. **Enable Chaos Testing**
   ```bash
   export META_V4_CHAOS_ENABLED=true
   export META_V4_CHAOS_INJECTION_PROBABILITY=0.05  # Start with 5%
   ```

2. **Configure Chaos Types**
   ```python
   chaos_config = ChaosConfig(
       enabled=True,
       chaos_types=[ChaosType.TRANSIENT_ERROR, ChaosType.NETWORK_LATENCY],
       injection_probability=0.05,
       max_duration_seconds=30
   )
   ```

3. **Monitor Recovery Rates**
   ```bash
   # Check chaos stats every 30 minutes
   curl -X GET "http://localhost:8000/api/meta/v4/chaos/stats" | jq '.recovery_rate'
   ```

#### Responding to Issues

1. **Low Recovery Rate**
   ```bash
   # Reduce injection probability
   export META_V4_CHAOS_INJECTION_PROBABILITY=0.01
   
   # Investigate specific chaos types
   curl -X GET "http://localhost:8000/api/meta/v4/chaos/stats" | jq '.chaos_types'
   ```

2. **Critical Recovery Failures**
   ```bash
   # Disable chaos testing
   export META_V4_CHAOS_ENABLED=false
   systemctl restart meta-builder
   ```

## Integration with Monitoring

### Prometheus Metrics

#### Canary Metrics

```python
# Canary runs counter
meta_builder_v4_canary_runs_total{canary_group="control", tenant_id="tenant_123", success="true"}

# Canary comparison gauge
meta_builder_v4_canary_comparison{metric_name="success_rate", canary_group="v4", tenant_id="tenant_123"}
```

#### Chaos Metrics

```python
# Chaos events counter
meta_builder_v4_chaos_events_total{chaos_type="transient_error", tenant_id="tenant_123", recovery_successful="true"}

# Chaos recovery time histogram
meta_builder_v4_chaos_recovery_seconds{chaos_type="network_latency", tenant_id="tenant_123"}
```

### Grafana Dashboards

#### Canary Dashboard

- **Canary Performance**: Success rate, cost, duration comparison
- **Statistical Significance**: Confidence intervals and p-values
- **Recommendation History**: Timeline of promotion/demotion decisions
- **Sample Distribution**: Control vs v4 run distribution

#### Chaos Dashboard

- **Recovery Rates**: Success rate by chaos type
- **Recovery Times**: Duration distribution by chaos type
- **Active Events**: Currently active chaos events
- **Failure Patterns**: Analysis of recovery failures

### Alerting Rules

#### Canary Alerts

```yaml
- alert: CanaryPerformanceDegradation
  expr: meta_builder_v4_canary_comparison{metric_name="success_rate"} < 0.95
  for: 10m
  labels:
    severity: critical
  annotations:
    summary: "Canary performance degradation"
    description: "v4 success rate below 95% threshold"

- alert: CanaryCostIncrease
  expr: meta_builder_v4_canary_comparison{metric_name="cost"} > 1.2
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Canary cost increase"
    description: "v4 cost exceeds control by 20%"
```

#### Chaos Alerts

```yaml
- alert: ChaosRecoveryFailure
  expr: rate(meta_builder_v4_chaos_events_total{recovery_successful="false"}[5m]) > 0.1
  for: 2m
  labels:
    severity: critical
  annotations:
    summary: "Chaos recovery failure"
    description: "High rate of chaos recovery failures"

- alert: ChaosRecoveryTime
  expr: histogram_quantile(0.95, rate(meta_builder_v4_chaos_recovery_seconds_bucket[5m])) > 60
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Slow chaos recovery"
    description: "95th percentile recovery time > 60 seconds"
```

## Best Practices

### Canary Testing

1. **Start Small**: Begin with 1-5% canary percentage
2. **Monitor Aggressively**: Check metrics every 15-30 minutes initially
3. **Gradual Increase**: Increase percentage only after sustained good performance
4. **Rollback Plan**: Have immediate rollback procedures ready
5. **Statistical Significance**: Ensure sufficient sample sizes before decisions

### Chaos Engineering

1. **Start Simple**: Begin with transient errors and network latency
2. **Controlled Environment**: Test in staging before production
3. **Gradual Complexity**: Increase chaos complexity over time
4. **Recovery Validation**: Ensure recovery mechanisms work as expected
5. **Documentation**: Document all chaos scenarios and expected behaviors

### Integration

1. **Coordinated Testing**: Run canary and chaos tests together
2. **Performance Baselines**: Establish baseline metrics before testing
3. **Automated Responses**: Implement automated rollback triggers
4. **Team Communication**: Ensure all stakeholders are aware of testing
5. **Post-Mortem Analysis**: Analyze results and improve procedures

## Future Enhancements

### Advanced Canary Testing

1. **Multi-Variant Testing**: Test multiple v4 configurations simultaneously
2. **Statistical Significance**: Implement proper statistical testing
3. **Automatic Rollback**: Trigger rollbacks based on performance thresholds
4. **User Segmentation**: Test with different user segments
5. **Feature Flags**: Integrate with feature flag management systems

### Advanced Chaos Engineering

1. **Custom Scenarios**: Allow custom chaos scenario definition
2. **Chaos Workflows**: Define complex chaos testing workflows
3. **Failure Injection APIs**: Provide APIs for external failure injection
4. **Chaos Scheduling**: Schedule chaos tests at specific times
5. **Chaos Reporting**: Comprehensive reporting and analysis tools

### Integration Improvements

1. **Kubernetes Integration**: Native K8s chaos testing
2. **Service Mesh**: Integrate with service mesh chaos testing
3. **Distributed Tracing**: Correlate chaos events with traces
4. **Machine Learning**: Use ML to predict failure modes
5. **Automated Remediation**: Automatic recovery and remediation

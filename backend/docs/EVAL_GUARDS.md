# Evaluation Lab Guards & Budgets

## Overview

Evaluation Lab v1.1 introduces comprehensive guard and budget management to ensure quality, performance, and cost control across all evaluation runs.

## KPI Guards

### Pass Rate Guards

```yaml
- name: "pass_rate_minimum"
  metric: "pass_rate"
  threshold: 0.95
  operator: ">="
  description: "Minimum 95% pass rate required"
  severity: "error"
```

### Latency Guards

```yaml
- name: "p95_latency_max"
  metric: "p95_latency_ms"
  threshold: 5000
  operator: "<="
  description: "P95 latency should be under 5 seconds"
  severity: "warning"
```

### Cost Guards

```yaml
- name: "cost_per_case_max"
  metric: "cost_per_case_usd"
  threshold: 0.10
  operator: "<="
  description: "Cost per case should be under $0.10"
  severity: "warning"
```

## Budget Guards

### Total Cost Budget

```yaml
budget_guards:
  - name: "max_total_cost_usd"
    threshold: 10.0
    description: "Maximum total cost per evaluation run"
    severity: "error"
```

### Per-Case Cost Budget

```yaml
budget_guards:
  - name: "max_cost_per_case_usd"
    threshold: 0.05
    description: "Maximum cost per individual test case"
    severity: "warning"
```

### Rerun Cost Budget

```yaml
budget_guards:
  - name: "max_rerun_cost_usd"
    threshold: 2.0
    description: "Maximum cost for reruns in a single evaluation"
    severity: "warning"
```

## Flake Guards

### Flake Score Thresholds

```yaml
flake_guards:
  - name: "max_flake_score"
    threshold: 0.7
    description: "Maximum flake score before quarantine recommendation"
    severity: "warning"
```

### Quarantine Management

```yaml
quarantine_settings:
  ttl_days: 7
  auto_expire: true
  manual_release: true
  exclude_from_gates: true
```

## Configuration

### Global Guards (eval_lab/guards.yaml)

```yaml
global_kpi_guards:
  - name: "overall_pass_rate_minimum"
    metric: "pass_rate"
    threshold: 0.90
    operator: ">="
    severity: "error"

  - name: "overall_latency_max"
    metric: "avg_latency_ms"
    threshold: 10000
    operator: "<="
    severity: "warning"

budget_guards:
  - name: "max_total_cost_usd"
    threshold: 20.0
    severity: "error"

  - name: "max_cost_per_case_usd"
    threshold: 0.10
    severity: "warning"

flake_guards:
  - name: "max_flake_score"
    threshold: 0.7
    severity: "warning"

quarantine_settings:
  ttl_days: 7
  auto_expire: true
  manual_release: true
  exclude_from_gates: true
```

### Suite-Specific Guards

```yaml
# In suite YAML files
kpi_guards:
  - name: "suite_pass_rate"
    metric: "pass_rate"
    threshold: 0.95
    operator: ">="
    description: "Suite-specific pass rate requirement"
    severity: "error"

metadata:
  max_reruns_on_flake: 2
  min_stable_passes: 2
  budget_limit_usd: 5.0
```

## Guard Evaluation

### Evaluation Process

1. **Pre-Run Checks**: Validate budget limits and resource availability
2. **During Execution**: Monitor real-time metrics and costs
3. **Post-Run Analysis**: Evaluate all guards and generate violations report
4. **Quarantine Processing**: Handle flaky cases and quarantine recommendations

### Guard Violations

```python
{
    "guard": "max_total_cost_usd",
    "current": 15.50,
    "threshold": 10.0,
    "excess": 5.50,
    "severity": "error"
}
```

### Response Actions

- **Error Severity**: Fail the evaluation run and block CI/CD
- **Warning Severity**: Log warning and continue, but flag for review
- **Info Severity**: Log information for monitoring

## Budget Management

### Cost Tracking

- **Base Costs**: Initial test execution costs
- **Rerun Costs**: Additional costs from flaky test reruns
- **Total Costs**: Combined base and rerun costs
- **Per-Case Costs**: Individual test case costs

### Budget Enforcement

```python
budget_check = cost_calculator.check_budget_guards(
    cost_breakdown,
    max_total_cost_usd=10.0,
    max_cost_per_case_usd=0.05,
    max_rerun_cost_usd=2.0
)
```

### Budget Alerts

- **Threshold Warnings**: When approaching budget limits
- **Exceeded Alerts**: When budgets are exceeded
- **Cost Optimization**: Recommendations for cost reduction

## Quarantine Management

### Automatic Quarantine

Cases are automatically quarantined when:
- Flake score > 0.7
- Consistent failures across multiple runs
- High variance in performance metrics

### Quarantine Effects

- **Excluded from Gates**: Quarantined cases don't block CI/CD
- **Still Executed**: Cases continue to run for data collection
- **Auto-Expiration**: Quarantines expire after TTL period
- **Manual Release**: Cases can be manually released from quarantine

### Quarantine Commands

```bash
# List quarantined cases
make eval-quarantine-list TENANT_ID=tenant123

# Release case from quarantine
make eval-quarantine-release TENANT_ID=tenant123 CASE_ID=case456

# Clean up expired quarantines
make eval-quarantine-cleanup
```

## Integration with CI/CD

### GitHub Actions Integration

```yaml
- name: Check for regressions
  run: |
    python -m src.eval_lab.runner check-regressions --run-id $RUN_ID

- name: Fail on guard violations
  if: contains(steps.check_guards.outputs.violations, 'error')
  run: |
    echo "❌ Guard violations detected!"
    exit 1
```

### PR Comments

Guard violations are automatically reported in PR comments:

```markdown
## Guard Violations

❌ **Error**: Total cost exceeded budget ($15.50 > $10.00)
⚠️ **Warning**: Average latency above threshold (12.5s > 10s)

## Quarantined Cases

- `contact_create`: High flake score (0.85)
- `deal_pipeline`: Inconsistent results
```

## Monitoring and Alerts

### Metrics

- `eval_guard_breaches_total`: Total number of guard violations
- `eval_budget_spent_usd`: Total budget spent
- `eval_quarantine_active`: Number of active quarantines
- `eval_flakes_detected_total`: Number of flaky cases detected

### Alerting

- **Slack Notifications**: Guard violations and budget alerts
- **PagerDuty Alerts**: Critical guard breaches
- **Email Notifications**: Weekly budget and performance reports

## Best Practices

### Guard Configuration

1. **Start Conservative**: Set strict thresholds initially
2. **Monitor and Adjust**: Refine thresholds based on historical data
3. **Suite-Specific**: Use different thresholds for different suites
4. **Environment-Aware**: Adjust thresholds for test vs production

### Budget Management

1. **Set Realistic Limits**: Base budgets on historical costs
2. **Monitor Trends**: Track cost trends over time
3. **Optimize Regularly**: Identify and address cost inefficiencies
4. **Plan for Growth**: Account for increased test coverage

### Quarantine Strategy

1. **Quick Response**: Quarantine flaky cases promptly
2. **Investigation**: Root cause analysis for quarantined cases
3. **Gradual Release**: Release cases after fixes are verified
4. **Documentation**: Maintain quarantine history and reasons

## Troubleshooting

### Common Issues

1. **False Positives**: Adjust flake detection thresholds
2. **Budget Overruns**: Review test efficiency and optimization
3. **Quarantine Overuse**: Investigate systemic flakiness causes
4. **Guard Conflicts**: Resolve conflicting guard requirements

### Debugging Commands

```bash
# Check guard status
python -m src.eval_lab.runner check-kpi-guards suites/core_crm.yaml

# Analyze flake patterns
python -m src.eval_lab.runner analyze-flakes --suite core_crm

# Review budget breakdown
python -m src.eval_lab.runner budget-report --run-id eval_run_123
```

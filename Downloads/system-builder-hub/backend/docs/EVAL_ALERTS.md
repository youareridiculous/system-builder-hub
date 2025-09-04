# Evaluation Lab Alerts

## Overview

Evaluation Lab v1.1 provides comprehensive alerting capabilities through Slack and PagerDuty integrations, ensuring timely notification of evaluation results, guard violations, and system issues.

## Alert Types

### Evaluation Summary Alerts

Sent after each evaluation run completion:

- **Pass Rate**: Overall test pass rate
- **Failed Cases**: Number and details of failed tests
- **Quarantined Cases**: Cases in quarantine
- **Performance Metrics**: Latency and cost information
- **Regressions**: New performance regressions detected

### Guard Violation Alerts

Sent when KPI guards or budget limits are exceeded:

- **Pass Rate Violations**: When pass rate falls below threshold
- **Latency Violations**: When performance degrades
- **Cost Violations**: When budgets are exceeded
- **Flake Violations**: When flaky tests are detected

### System Health Alerts

Sent for system-level issues:

- **Evaluation Failures**: When evaluation runs fail completely
- **Database Issues**: When data storage problems occur
- **Integration Failures**: When external service integrations fail

## Slack Integration

### Configuration

Set the Slack webhook URL in environment variables:

```bash
export SLACK_EVAL_WEBHOOK="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
```

### Message Format

#### Evaluation Summary

```json
{
  "attachments": [
    {
      "color": "#36a64f",
      "title": "Evaluation Results: Core CRM",
      "title_link": "https://github.com/org/repo/actions/runs/123",
      "fields": [
        {
          "title": "Pass Rate",
          "value": "95.2%",
          "short": true
        },
        {
          "title": "Total Cases",
          "value": "21",
          "short": true
        },
        {
          "title": "Failed Cases",
          "value": "1",
          "short": true
        },
        {
          "title": "Quarantined",
          "value": "0",
          "short": true
        },
        {
          "title": "Avg Latency",
          "value": "2.3s",
          "short": true
        },
        {
          "title": "Total Cost",
          "value": "$1.25",
          "short": true
        }
      ],
      "footer": "Run ID: eval_run_abc123",
      "ts": 1640995200
    }
  ]
}
```

#### Guard Violation Alert

```json
{
  "attachments": [
    {
      "color": "#ff0000",
      "title": "🚨 KPI Guard Breach: pass_rate_minimum",
      "fields": [
        {
          "title": "Metric",
          "value": "pass_rate",
          "short": true
        },
        {
          "title": "Current Value",
          "value": "0.85",
          "short": true
        },
        {
          "title": "Threshold",
          "value": "0.95",
          "short": true
        },
        {
          "title": "Severity",
          "value": "ERROR",
          "short": true
        }
      ],
      "ts": 1640995200
    }
  ]
}
```

### Privacy and Redaction

When privacy mode is not `local_only`, sensitive data is automatically redacted:

- **Input Prompts**: Redacted to prevent PII exposure
- **Error Messages**: Sanitized to remove sensitive information
- **Token Usage**: Aggregated to prevent detailed cost analysis
- **Case Details**: Summarized to maintain privacy

## PagerDuty Integration

### Configuration

Set the PagerDuty routing key in environment variables:

```bash
export PAGERDUTY_ROUTING_KEY="your-routing-key-here"
```

### Event Format

#### Critical Alert

```json
{
  "routing_key": "your-routing-key",
  "event_action": "trigger",
  "payload": {
    "summary": "Evaluation Guard Breaches: Core CRM",
    "severity": "critical",
    "source": "system-builder-hub-eval-lab",
    "custom_details": {
      "run_id": "eval_run_abc123",
      "guard_breaches": 3,
      "pass_rate": 0.85,
      "total_cases": 21
    }
  }
}
```

#### Warning Alert

```json
{
  "routing_key": "your-routing-key",
  "event_action": "trigger",
  "payload": {
    "summary": "Evaluation Performance Warning: Core CRM",
    "severity": "warning",
    "source": "system-builder-hub-eval-lab",
    "custom_details": {
      "run_id": "eval_run_abc123",
      "avg_latency_ms": 8500,
      "threshold_ms": 5000,
      "total_cases": 21
    }
  }
}
```

### Alert Resolution

Alerts are automatically resolved when:

- **Evaluation Completes**: Successful completion resolves failure alerts
- **Guards Pass**: When subsequent runs pass all guards
- **Manual Resolution**: Manual acknowledgment of resolved issues

## GitHub Actions Integration

### PR Comments

Evaluation results are automatically posted to PRs:

```markdown
## Evaluation Lab Results

**Suite:** Core CRM
**Run ID:** eval_run_abc123
**Status:** completed

### Summary
- **Pass Rate:** 95.2%
- **Total Cases:** 21
- **Failed Cases:** 1
- **Quarantined Cases:** 0
- **Avg Latency:** 2.3s
- **Total Cost:** $1.25

### Regressions
No regressions detected

[📊 View Full Report](https://github.com/org/repo/actions/runs/123/artifacts)
```

### Workflow Annotations

GitHub Actions annotations provide inline feedback:

```
::warning file=suites/core_crm.yaml,line=15::KPI Guard Warning: pass_rate (0.85 < 0.95)
::error file=suites/core_crm.yaml,line=20::KPI Guard Error: latency (12.5s > 5s)
```

## Alert Configuration

### Environment Variables

```bash
# Slack Configuration
SLACK_EVAL_WEBHOOK=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# PagerDuty Configuration
PAGERDUTY_ROUTING_KEY=your-routing-key-here

# Alert Settings
EVAL_ALERTS_ENABLED=true
EVAL_ALERTS_PRIVACY_MODE=private_cloud
EVAL_ALERTS_REDACT_SENSITIVE=true
```

### Feature Flags

```python
# In settings/feature_flags.py
FEATURE_EVAL_ALERTS = True
FEATURE_EVAL_SLACK_ALERTS = True
FEATURE_EVAL_PAGERDUTY_ALERTS = True
```

### Alert Thresholds

```yaml
# In eval_lab/guards.yaml
alert_settings:
  slack:
    enabled: true
    webhook_url: ${SLACK_EVAL_WEBHOOK}
    channels:
      - "#eval-lab"
      - "#engineering"
  
  pagerduty:
    enabled: true
    routing_key: ${PAGERDUTY_ROUTING_KEY}
    escalation_policy: "eval-lab-policy"
  
  thresholds:
    critical_pass_rate: 0.80
    warning_pass_rate: 0.90
    critical_latency_ms: 10000
    warning_latency_ms: 5000
    critical_cost_usd: 20.0
    warning_cost_usd: 10.0
```

## Alert Management

### Alert Lifecycle

1. **Detection**: System detects condition requiring alert
2. **Filtering**: Apply privacy and configuration filters
3. **Formatting**: Format message for target platform
4. **Delivery**: Send to configured channels
5. **Tracking**: Log alert delivery and response
6. **Resolution**: Mark alert as resolved when condition improves

### Alert Deduplication

- **Time Window**: Alerts for same condition within 5 minutes are deduplicated
- **Condition Matching**: Alerts with identical conditions are grouped
- **Escalation**: Repeated alerts escalate to higher severity

### Alert History

All alerts are logged for audit and analysis:

```python
{
    "alert_id": "alert_abc123",
    "timestamp": "2024-01-01T12:00:00Z",
    "type": "guard_violation",
    "severity": "critical",
    "platform": "slack",
    "delivered": true,
    "recipients": ["#eval-lab"],
    "content": {...}
}
```

## Privacy and Security

### Data Redaction

Sensitive data is automatically redacted based on privacy mode:

- **local_only**: No redaction (all data local)
- **byo_keys**: Redact API keys and sensitive tokens
- **private_cloud**: Redact PII and detailed cost information

### Redaction Rules

```python
SENSITIVE_KEYS = [
    "prompt", "input", "output", "error_message",
    "token_usage", "api_key", "password", "secret"
]

def redact_sensitive_data(data, privacy_mode):
    if privacy_mode == "local_only":
        return data
    
    # Apply redaction rules
    return apply_redaction_rules(data, SENSITIVE_KEYS)
```

### Audit Logging

All alert activities are logged for compliance:

```python
{
    "timestamp": "2024-01-01T12:00:00Z",
    "action": "alert_sent",
    "alert_type": "guard_violation",
    "privacy_mode": "private_cloud",
    "redacted": true,
    "recipients": ["#eval-lab"],
    "run_id": "eval_run_abc123"
}
```

## Troubleshooting

### Common Issues

1. **Webhook Failures**: Check webhook URL and permissions
2. **Rate Limiting**: Implement backoff for high-volume alerts
3. **Format Errors**: Validate message format for each platform
4. **Privacy Violations**: Review redaction rules and privacy settings

### Debug Commands

```bash
# Test Slack integration
python -c "
from src.eval_lab.alerts import SlackNotifier
notifier = SlackNotifier('your-webhook-url')
notifier.send_evaluation_summary(summary_data)
"

# Test PagerDuty integration
python -c "
from src.eval_lab.alerts import PagerDutyNotifier
notifier = PagerDutyNotifier('your-routing-key')
notifier.send_critical_alert('Test alert', {'test': 'data'})
"

# Check alert configuration
python -c "
from src.eval_lab.alerts import AlertManager
config = AlertConfig(
    slack_webhook_url='your-webhook',
    pagerduty_routing_key='your-key',
    privacy_mode='private_cloud'
)
manager = AlertManager(config)
print('Alert manager configured successfully')
"
```

### Monitoring

Monitor alert delivery and effectiveness:

- **Delivery Rate**: Track successful vs failed alert deliveries
- **Response Time**: Measure time from condition to alert delivery
- **Resolution Time**: Track time from alert to resolution
- **False Positives**: Monitor and reduce unnecessary alerts

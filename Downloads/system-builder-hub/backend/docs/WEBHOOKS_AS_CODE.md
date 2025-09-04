# Webhooks-as-Code Guide

This document explains the Webhooks-as-Code system for declarative webhook configuration.

## Overview

Webhooks-as-Code allows you to define webhook subscriptions declaratively using YAML files. This provides:

- **Version Control**: Webhook configurations are versioned with your code
- **Declarative**: Simple YAML syntax for webhook definitions
- **Transforms**: Custom data transformation scripts
- **Signing**: Automatic webhook signature generation
- **Retries**: Configurable retry logic with backoff
- **Testing**: Easy testing and validation

## Webhook Definition

### Basic Structure

```yaml
api_version: v1
on: ["build.completed", "auth.user.created"]
delivery:
  url: "${SECRET:WEBHOOK_URL}"
  headers:
    X-Source: "SBH"
    X-Tenant: "${TENANT_ID}"
  signing:
    alg: "HMAC-SHA256"
    secret: "${SECRET:WEBHOOK_SIGNING_KEY}"
transform:
  language: "python"
  entry: "transforms/build_completed.py#transform"
retry:
  max_attempts: 6
  backoff: "exponential"
```

### Configuration Fields

#### Event Subscription
- **on**: List of event types to subscribe to
- **api_version**: API version (currently "v1")

#### Delivery Configuration
- **url**: Webhook delivery URL (supports secret substitution)
- **headers**: Custom headers to include
- **signing**: Webhook signature configuration

#### Data Transformation
- **language**: Script language ("python", "javascript")
- **entry**: Path to transform function

#### Retry Configuration
- **max_attempts**: Maximum retry attempts
- **backoff**: Backoff strategy ("exponential", "linear")

## Event Types

### Available Events

#### Authentication Events
```yaml
on: ["auth.user.created", "auth.user.updated", "auth.user.deleted"]
```

#### Build Events
```yaml
on: ["build.completed", "build.failed", "build.started"]
```

#### Payment Events
```yaml
on: ["payments.subscription.created", "payments.subscription.updated"]
```

#### File Events
```yaml
on: ["files.uploaded", "files.deleted"]
```

#### Webhook Events
```yaml
on: ["webhook.received"]
```

#### Analytics Events
```yaml
on: ["analytics.rollup.completed"]
```

## Delivery Configuration

### URL Configuration

```yaml
delivery:
  url: "https://api.example.com/webhooks/sbh"
```

### Secret Substitution

```yaml
delivery:
  url: "${SECRET:WEBHOOK_URL}"
  headers:
    Authorization: "Bearer ${SECRET:API_TOKEN}"
```

### Custom Headers

```yaml
delivery:
  url: "https://api.example.com/webhooks"
  headers:
    X-Source: "SBH"
    X-Tenant: "${TENANT_ID}"
    X-Plugin: "my-plugin"
    Content-Type: "application/json"
```

## Webhook Signing

### HMAC-SHA256 Signing

```yaml
delivery:
  url: "https://api.example.com/webhooks"
  signing:
    alg: "HMAC-SHA256"
    secret: "${SECRET:WEBHOOK_SIGNING_KEY}"
```

### Signature Header

The signature is included in the `X-Signature` header:
```
X-Signature: sha256=abc123...
```

### Verification

Your webhook endpoint should verify the signature:

```python
import hmac
import hashlib

def verify_signature(payload, signature, secret):
    expected = hmac.new(
        secret.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return signature == f"sha256={expected}"
```

## Data Transformation

### Transform Script

Create a transform script to modify event data:

```python
# transforms/build_completed.py
def transform(event_data):
    """Transform build completion event"""
    return {
        "event_type": "build.completed",
        "build_id": event_data.get("build_id"),
        "status": event_data.get("status"),
        "project": event_data.get("project_name"),
        "timestamp": event_data.get("created_at"),
        "duration": event_data.get("duration_seconds"),
        "user": event_data.get("created_by")
    }
```

### Transform Configuration

```yaml
transform:
  language: "python"
  entry: "transforms/build_completed.py#transform"
```

### Multiple Transforms

You can chain multiple transforms:

```yaml
transform:
  language: "python"
  entry: "transforms/build_completed.py#transform"
  post_transform:
    language: "python"
    entry: "transforms/add_metadata.py#add_metadata"
```

## Retry Configuration

### Retry Strategies

#### Exponential Backoff
```yaml
retry:
  max_attempts: 6
  backoff: "exponential"
  initial_delay: 1000  # milliseconds
  max_delay: 30000     # milliseconds
```

#### Linear Backoff
```yaml
retry:
  max_attempts: 3
  backoff: "linear"
  delay: 5000  # milliseconds
```

#### No Retries
```yaml
retry:
  max_attempts: 1
```

### Retry Conditions

Webhooks are retried on:
- HTTP 5xx errors
- Network timeouts
- Connection failures

Webhooks are NOT retried on:
- HTTP 4xx errors (client errors)
- HTTP 2xx responses (success)

## Plugin Integration

### Webhook Location

Place webhook definitions in your plugin:

```
my-plugin/
├── plugin.json
├── main.py
├── webhooks/
│   ├── notifications.yaml
│   └── analytics.yaml
└── transforms/
    ├── build_completed.py
    └── user_created.py
```

### Loading Webhooks

Webhooks are automatically loaded when the plugin is installed:

```python
# In your plugin main.py
from src.ext.webhooks import webhook_manager

# Webhooks are loaded from webhooks/*.yaml files
# No additional code needed
```

## Testing Webhooks

### Local Testing

```python
# Test webhook delivery locally
from src.ext.webhooks import webhook_manager

event_data = {
    "build_id": "build-123",
    "status": "success",
    "project_name": "Test Project"
}

result = webhook_manager.deliver_webhook(
    "my-plugin",
    "build.completed",
    event_data,
    "test-tenant"
)

print(result)
```

### Test Event API

```bash
# Test webhook delivery via API
curl -X POST https://api.example.com/api/plugins/test-event \
  -H "Authorization: Bearer <token>" \
  -H "X-Tenant-Slug: <tenant>" \
  -d '{
    "event_type": "build.completed",
    "event_data": {
      "build_id": "build-123",
      "status": "success",
      "project_name": "Test Project"
    }
  }'
```

## Monitoring and Debugging

### Webhook Status

Check webhook delivery status:

```bash
# Get webhook metrics
curl -H "Authorization: Bearer <token>" \
  -H "X-Tenant-Slug: <tenant>" \
  https://api.example.com/api/plugins/metrics
```

### Logs

Webhook delivery logs include:
- Delivery attempts
- Response status codes
- Retry attempts
- Error messages

### Metrics

Webhook metrics include:
- `webhook_deliveries_total`: Total delivery attempts
- `webhook_deliveries_success`: Successful deliveries
- `webhook_deliveries_failed`: Failed deliveries
- `webhook_retry_attempts`: Retry attempts

## Best Practices

### Webhook Design

#### Idempotency
```python
def transform(event_data):
    # Include unique identifiers for idempotency
    return {
        "id": event_data.get("id"),
        "event_id": event_data.get("event_id"),
        "timestamp": event_data.get("created_at"),
        "data": event_data
    }
```

#### Error Handling
```python
def transform(event_data):
    try:
        return {
            "status": "success",
            "data": event_data
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "data": event_data
        }
```

#### Data Validation
```python
def transform(event_data):
    # Validate required fields
    required_fields = ["build_id", "status", "project_name"]
    for field in required_fields:
        if field not in event_data:
            raise ValueError(f"Missing required field: {field}")
    
    return event_data
```

### Security

#### Secret Management
```yaml
delivery:
  url: "${SECRET:WEBHOOK_URL}"
  signing:
    secret: "${SECRET:WEBHOOK_SIGNING_KEY}"
```

#### Input Validation
```python
def transform(event_data):
    # Validate and sanitize input
    if not isinstance(event_data, dict):
        raise ValueError("Invalid event data")
    
    # Sanitize sensitive data
    sanitized = event_data.copy()
    if "password" in sanitized:
        sanitized["password"] = "***"
    
    return sanitized
```

### Performance

#### Efficient Transforms
```python
def transform(event_data):
    # Only include necessary data
    return {
        "id": event_data.get("id"),
        "status": event_data.get("status"),
        "timestamp": event_data.get("created_at")
    }
```

#### Batch Processing
```yaml
# For high-volume events, consider batching
on: ["analytics.rollup.completed"]
delivery:
  url: "https://api.example.com/webhooks/batch"
transform:
  language: "python"
  entry: "transforms/batch_events.py#transform"
```

## Examples

### Slack Integration

```yaml
# webhooks/slack.yaml
api_version: v1
on: ["build.completed", "auth.user.created"]
delivery:
  url: "${SECRET:SLACK_WEBHOOK_URL}"
  headers:
    Content-Type: "application/json"
transform:
  language: "python"
  entry: "transforms/slack_notification.py#transform"
retry:
  max_attempts: 3
  backoff: "exponential"
```

```python
# transforms/slack_notification.py
def transform(event_data):
    event_type = event_data.get("event_type")
    
    if event_type == "build.completed":
        return {
            "text": f"Build {event_data.get('build_id')} completed with status: {event_data.get('status')}"
        }
    elif event_type == "auth.user.created":
        return {
            "text": f"New user created: {event_data.get('user', {}).get('email')}"
        }
    
    return {"text": "Unknown event"}
```

### GitHub Integration

```yaml
# webhooks/github.yaml
api_version: v1
on: ["build.completed"]
delivery:
  url: "https://api.github.com/repos/owner/repo/statuses/${SHA}"
  headers:
    Authorization: "token ${SECRET:GITHUB_TOKEN}"
    Accept: "application/vnd.github.v3+json"
transform:
  language: "python"
  entry: "transforms/github_status.py#transform"
retry:
  max_attempts: 5
  backoff: "exponential"
```

```python
# transforms/github_status.py
def transform(event_data):
    status = event_data.get("status")
    
    if status == "success":
        github_status = "success"
        description = "Build completed successfully"
    else:
        github_status = "failure"
        description = "Build failed"
    
    return {
        "state": github_status,
        "description": description,
        "context": "SBH Build",
        "target_url": f"https://app.example.com/builds/{event_data.get('build_id')}"
    }
```

### Custom API Integration

```yaml
# webhooks/custom_api.yaml
api_version: v1
on: ["payments.subscription.created"]
delivery:
  url: "${SECRET:CUSTOM_API_URL}/webhooks/subscription"
  headers:
    X-API-Key: "${SECRET:CUSTOM_API_KEY}"
    Content-Type: "application/json"
  signing:
    alg: "HMAC-SHA256"
    secret: "${SECRET:CUSTOM_API_SIGNING_KEY}"
transform:
  language: "python"
  entry: "transforms/subscription_event.py#transform"
retry:
  max_attempts: 6
  backoff: "exponential"
```

```python
# transforms/subscription_event.py
def transform(event_data):
    subscription = event_data.get("subscription", {})
    
    return {
        "event_type": "subscription.created",
        "subscription_id": subscription.get("id"),
        "customer_id": subscription.get("customer_id"),
        "plan_id": subscription.get("plan_id"),
        "status": subscription.get("status"),
        "created_at": subscription.get("created_at"),
        "amount": subscription.get("amount"),
        "currency": subscription.get("currency")
    }
```

## Troubleshooting

### Common Issues

#### Webhook Not Delivering
- Check webhook URL is correct
- Verify webhook is enabled
- Check event subscription
- Review error logs

#### Transform Errors
- Validate transform function syntax
- Check required fields
- Handle exceptions gracefully
- Test transform locally

#### Retry Failures
- Check destination service status
- Verify authentication credentials
- Review rate limits
- Check network connectivity

#### Signature Verification
- Verify signing secret is correct
- Check signature algorithm
- Validate payload format
- Test signature generation

### Debug Commands

```bash
# Test webhook delivery
curl -X POST https://api.example.com/api/plugins/test-event \
  -H "Authorization: Bearer <token>" \
  -H "X-Tenant-Slug: <tenant>" \
  -d '{"event_type": "build.completed", "event_data": {...}}'

# Check webhook status
curl -H "Authorization: Bearer <token>" \
  -H "X-Tenant-Slug: <tenant>" \
  https://api.example.com/api/plugins/metrics

# View webhook logs
# Check application logs for webhook delivery events
```

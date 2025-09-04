# Integrations Guide

This document explains how to use SBH's integration features: API keys, webhooks, and transactional emails.

## Overview

SBH provides three main integration capabilities:

1. **API Keys**: Secure authentication for programmatic access
2. **Webhooks**: Real-time event notifications to your applications
3. **Transactional Email**: Send emails via AWS SES with templates

## API Keys

### Creating API Keys

API keys provide secure authentication for programmatic access to SBH APIs.

#### Via UI
1. Navigate to `/ui/integrations`
2. Click "Create API Key"
3. Provide a name and select scope
4. Copy the generated key (shown only once)

#### Via API
```bash
curl -X POST https://myapp.com/api/keys \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "X-Tenant-Slug: your-tenant" \
  -d '{
    "name": "Production API Key",
    "scope": {
      "endpoints": ["read", "write"]
    },
    "rate_limit_per_min": 120
  }'
```

**Response:**
```json
{
  "success": true,
  "api_key": {
    "id": "key-123",
    "name": "Production API Key",
    "prefix": "sbh_prod_",
    "key": "sbh_prod_abc123def456ghi789jkl",
    "scope": {
      "endpoints": ["read", "write"]
    },
    "rate_limit_per_min": 120,
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

### Using API Keys

#### Authentication
```bash
# Using Authorization header
curl -H "Authorization: SBH sbh_prod_abc123def456ghi789jkl" \
  https://myapp.com/api/endpoint

# Using x-api-key header
curl -H "x-api-key: sbh_prod_abc123def456ghi789jkl" \
  https://myapp.com/api/endpoint
```

#### Scopes
API keys support granular scopes:
- `read`: Read-only access
- `write`: Read and write access
- `admin`: Full administrative access

#### Rate Limiting
Each API key has its own rate limit (default: 120 requests per minute). When exceeded, you'll receive a `429 Too Many Requests` response.

### Managing API Keys

#### List Keys
```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "X-Tenant-Slug: your-tenant" \
  https://myapp.com/api/keys
```

#### Rotate Key
```bash
curl -X POST https://myapp.com/api/keys/key-123/rotate \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "X-Tenant-Slug: your-tenant"
```

#### Revoke Key
```bash
curl -X POST https://myapp.com/api/keys/key-123/revoke \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "X-Tenant-Slug: your-tenant"
```

## Webhooks

### Creating Webhooks

Webhooks allow you to receive real-time notifications when events occur in SBH.

#### Via UI
1. Navigate to `/ui/integrations`
2. Click "Create Webhook"
3. Enter target URL and select events
4. Copy the webhook secret (shown only once)

#### Via API
```bash
curl -X POST https://myapp.com/api/webhooks \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "X-Tenant-Slug: your-tenant" \
  -d '{
    "target_url": "https://your-app.com/webhooks/sbh",
    "events": ["build.completed", "auth.user.created"]
  }'
```

**Response:**
```json
{
  "success": true,
  "webhook": {
    "id": "webhook-123",
    "target_url": "https://your-app.com/webhooks/sbh",
    "events": ["build.completed", "auth.user.created"],
    "status": "active",
    "secret": "abc123def456ghi789jkl012mno345pqr678",
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

### Available Events

| Event | Description | Payload |
|-------|-------------|---------|
| `build.started` | Build process started | `{project_id, build_id, tenant_id, started_at}` |
| `build.completed` | Build process completed | `{project_id, build_id, tenant_id, status, completed_at, pages_count, apis_count, tables_count}` |
| `auth.user.created` | New user created | `{user_id, tenant_id, email, created_at}` |
| `payments.subscription.updated` | Subscription status changed | `{tenant_id, subscription_id, status, plan, updated_at}` |
| `files.uploaded` | File uploaded | `{tenant_id, file_id, filename, size, uploaded_at}` |
| `domain.created` | Custom domain created | `{tenant_id, domain_id, hostname, status, created_at}` |
| `domain.activated` | Custom domain activated | `{tenant_id, domain_id, hostname, activated_at}` |

### Receiving Webhooks

#### Webhook Payload
```json
{
  "event_type": "build.completed",
  "data": {
    "project_id": "proj-123",
    "build_id": "build-456",
    "tenant_id": "tenant-789",
    "status": "success",
    "completed_at": "2024-01-15T10:30:00Z",
    "pages_count": 5,
    "apis_count": 3,
    "tables_count": 2
  },
  "timestamp": 1642234567890,
  "delivery_id": "delivery-123"
}
```

#### Headers
- `X-SBH-Event`: Event type
- `X-SBH-Timestamp`: Unix timestamp in milliseconds
- `X-SBH-Signature`: HMAC signature for verification
- `X-SBH-Delivery-Id`: Unique delivery ID for idempotency
- `X-SBH-Tenant`: Tenant slug (if available)

#### Signature Verification

**Python:**
```python
import hmac
import hashlib
import time

def verify_webhook_signature(secret, timestamp, body, signature):
    # Check timestamp tolerance (5 minutes)
    if abs(time.time() - int(timestamp) / 1000) > 300:
        return False
    
    # Create expected signature
    message = f"{timestamp}.{body}"
    expected_sig = hmac.new(
        secret.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(f"sha256={expected_sig}", signature)

# Usage
is_valid = verify_webhook_signature(
    secret="your-webhook-secret",
    timestamp=request.headers.get('X-SBH-Timestamp'),
    body=request.get_data(as_text=True),
    signature=request.headers.get('X-SBH-Signature')
)
```

**Node.js:**
```javascript
const crypto = require('crypto');

function verifyWebhookSignature(secret, timestamp, body, signature) {
  // Check timestamp tolerance (5 minutes)
  const tolerance = 5 * 60 * 1000; // 5 minutes in milliseconds
  const now = Date.now();
  if (Math.abs(now - parseInt(timestamp)) > tolerance) {
    return false;
  }
  
  // Create expected signature
  const message = `${timestamp}.${body}`;
  const expectedSig = crypto
    .createHmac('sha256', secret)
    .update(message)
    .digest('hex');
  
  return crypto.timingSafeEqual(
    Buffer.from(`sha256=${expectedSig}`),
    Buffer.from(signature)
  );
}

// Usage
const isValid = verifyWebhookSignature(
  secret: 'your-webhook-secret',
  timestamp: req.headers['x-sbh-timestamp'],
  body: req.body,
  signature: req.headers['x-sbh-signature']
);
```

### Webhook Delivery

#### Retry Logic
Webhooks are delivered with exponential backoff:
- 1st retry: 1 minute
- 2nd retry: 5 minutes
- 3rd retry: 15 minutes
- 4th retry: 1 hour
- 5th retry: 2 hours
- 6th retry: 4 hours

#### Idempotency
Use the `X-SBH-Delivery-Id` header to ensure idempotent processing:
```python
delivery_id = request.headers.get('X-SBH-Delivery-Id')

# Check if already processed
if is_already_processed(delivery_id):
    return 'OK', 200

# Process webhook
process_webhook(request.json)

# Mark as processed
mark_as_processed(delivery_id)
```

### Managing Webhooks

#### List Webhooks
```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "X-Tenant-Slug: your-tenant" \
  https://myapp.com/api/webhooks
```

#### Pause Webhook
```bash
curl -X POST https://myapp.com/api/webhooks/webhook-123/pause \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "X-Tenant-Slug: your-tenant"
```

#### Delete Webhook
```bash
curl -X DELETE https://myapp.com/api/webhooks/webhook-123 \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "X-Tenant-Slug: your-tenant"
```

#### View Deliveries
```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "X-Tenant-Slug: your-tenant" \
  "https://myapp.com/api/webhooks/deliveries?event=build.completed&limit=10"
```

#### Redeliver Failed Webhook
```bash
curl -X POST https://myapp.com/api/webhooks/deliveries/delivery-123/redeliver \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "X-Tenant-Slug: your-tenant"
```

## Transactional Email

### Email Templates

SBH provides several email templates:

#### Welcome Email
```json
{
  "template": "welcome",
  "payload": {
    "user_name": "John Doe",
    "email": "john@example.com",
    "app_url": "https://myapp.com"
  }
}
```

#### Password Reset Email
```json
{
  "template": "password_reset",
  "payload": {
    "user_name": "John Doe",
    "email": "john@example.com",
    "reset_url": "https://myapp.com/reset?token=abc123"
  }
}
```

### Sending Emails

#### Via API
```bash
curl -X POST https://myapp.com/api/email/test \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "X-Tenant-Slug: your-tenant" \
  -d '{
    "template": "welcome",
    "payload": {
      "user_name": "John Doe",
      "email": "john@example.com"
    }
  }'
```

#### Programmatically
```python
from src.email.sender import EmailSender

sender = EmailSender()
result = sender.send_email(
    tenant_id='tenant-123',
    to_email='user@example.com',
    template='welcome',
    payload={
        'user_name': 'John Doe',
        'email': 'user@example.com'
    }
)
```

### Development vs Production

#### Development
In development, emails are echoed to logs and stored in the database:
```bash
# Set environment variable
export DEV_EMAIL_ECHO=true
```

#### Production
In production, emails are sent via AWS SES:
```bash
# Set environment variables
export SES_REGION=us-east-1
export SES_FROM_ADDRESS=no-reply@myapp.com
```

### Email Status Tracking

#### List Recent Emails
```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "X-Tenant-Slug: your-tenant" \
  https://myapp.com/api/email/outbound?limit=50
```

**Response:**
```json
{
  "success": true,
  "emails": [
    {
      "id": "email-123",
      "to_email": "user@example.com",
      "template": "welcome",
      "status": "sent",
      "provider_message_id": "ses-message-456",
      "created_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

## Quotas and Rate Limits

### Default Limits
- **API Keys**: 5 active keys per tenant
- **Webhooks**: 10 webhooks per tenant
- **Webhook Deliveries**: 10,000 per day per tenant
- **Emails**: 1,000 per day per tenant

### Configuration
Limits can be configured via environment variables:
```bash
export MAX_API_KEYS_PER_TENANT=10
export MAX_WEBHOOKS_PER_TENANT=20
export MAX_WEBHOOK_DELIVERIES_PER_DAY=50000
export MAX_EMAILS_PER_DAY=5000
```

### Checking Limits
Limits are exposed in the readiness endpoint:
```bash
curl https://myapp.com/readiness
```

**Response:**
```json
{
  "status": "healthy",
  "integrations": {
    "api_keys": {
      "enabled": true,
      "active_count": 3,
      "limit": 5
    },
    "webhooks": {
      "enabled": true,
      "active_count": 2,
      "limit": 10
    },
    "email": {
      "enabled": true,
      "daily_sent": 45,
      "limit": 1000
    }
  }
}
```

## Security Best Practices

### API Keys
1. **Store securely**: Never commit API keys to version control
2. **Rotate regularly**: Rotate keys every 90 days
3. **Use minimal scopes**: Grant only necessary permissions
4. **Monitor usage**: Check last used timestamps regularly

### Webhooks
1. **Verify signatures**: Always verify webhook signatures
2. **Check timestamps**: Reject webhooks older than 5 minutes
3. **Use HTTPS**: Only accept webhooks over HTTPS
4. **Implement idempotency**: Use delivery IDs to prevent duplicates

### Email
1. **Validate recipients**: Always validate email addresses
2. **Use templates**: Use predefined templates for consistency
3. **Monitor bounces**: Track email delivery status
4. **Respect opt-outs**: Honor unsubscribe requests

## Error Handling

### API Key Errors
```json
{
  "error": "Invalid API key"
}
```

```json
{
  "error": "Insufficient scope: admin required"
}
```

```json
{
  "error": "Rate limit exceeded"
}
```

### Webhook Errors
```json
{
  "error": "Invalid webhook signature"
}
```

```json
{
  "error": "Webhook target URL unreachable"
}
```

### Email Errors
```json
{
  "error": "Invalid email template"
}
```

```json
{
  "error": "SES configuration error"
}
```

## Monitoring and Observability

### Metrics
Integration metrics are exposed via Prometheus:
- `keys_created_total`
- `keys_requests_total{key_id, status}`
- `webhooks_deliveries_total{status}`
- `emails_sent_total{provider}`

### Audit Logs
All integration actions are logged:
- API key creation, rotation, revocation
- Webhook creation, delivery, failure
- Email sending, success, failure

### Health Checks
Integration health is included in readiness checks:
```bash
curl https://myapp.com/readiness
```

## Troubleshooting

### Common Issues

#### API Key Not Working
1. Check if key is active (not revoked)
2. Verify key format and prefix
3. Check rate limits
4. Ensure proper scope permissions

#### Webhook Not Receiving Events
1. Verify webhook is active
2. Check target URL is accessible
3. Verify signature calculation
4. Check delivery logs for errors

#### Email Not Sending
1. Check SES configuration
2. Verify from address is verified
3. Check email template exists
4. Review error logs

### Debug Commands

#### Test API Key
```bash
curl -H "Authorization: SBH YOUR_API_KEY" \
  https://myapp.com/api/endpoint
```

#### Test Webhook
```bash
curl -X POST https://myapp.com/api/webhooks \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "target_url": "https://httpbin.org/post",
    "events": ["build.completed"]
  }'
```

#### Test Email
```bash
curl -X POST https://myapp.com/api/email/test \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "template": "welcome",
    "payload": {"user_name": "Test User"}
  }'
```

## Support

For integration support:
1. Check the logs for detailed error messages
2. Verify environment configuration
3. Test with the provided examples
4. Contact support with specific error details

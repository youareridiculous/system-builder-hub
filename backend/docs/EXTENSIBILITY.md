# SBH Extensibility Guide

## Overview

SBH provides a powerful extensibility system that allows you to create plugins, webhooks, and custom integrations. This guide covers the complete extensibility framework including plugins, webhooks-as-code, and the SDK.

## Table of Contents

1. [Plugin System](#plugin-system)
2. [Webhooks-as-Code](#webhooks-as-code)
3. [SDK Reference](#sdk-reference)
4. [Security Model](#security-model)
5. [Local Development](#local-development)
6. [Testing](#testing)
7. [Best Practices](#best-practices)

## Plugin System

### Plugin Structure

A plugin consists of the following files:

```
plugin-name/
├── plugin.json          # Plugin manifest
├── main.py             # Main plugin code
├── requirements.txt    # Python dependencies (optional)
├── static/            # Static assets (optional)
├── templates/         # Jinja2 templates (optional)
└── tests/            # Test files (optional)
```

### Plugin Manifest (plugin.json)

The plugin manifest defines the plugin's metadata, permissions, and configuration:

```json
{
  "slug": "my-plugin",
  "name": "My Plugin",
  "version": "1.0.0",
  "description": "Description of what this plugin does",
  "author": "Your Name",
  "entry": "main.py",
  "permissions": [
    "read_contacts",
    "send_email",
    "outbound_http"
  ],
  "routes": true,
  "events": [
    "contact.created",
    "deal.won"
  ],
  "jobs": [
    {
      "name": "daily_task",
      "schedule": "0 9 * * *",
      "description": "Daily scheduled task"
    }
  ],
  "secrets": [
    "API_KEY",
    "WEBHOOK_URL"
  ]
}
```

### Available Permissions

- `read_contacts` - Read contact data
- `write_contacts` - Create/update contacts
- `read_deals` - Read deal data
- `write_deals` - Create/update deals
- `read_tasks` - Read task data
- `write_tasks` - Create/update tasks
- `send_email` - Send emails via SES
- `outbound_http` - Make HTTP requests (allowlisted domains)
- `emit_webhook` - Emit webhook events
- `llm.use` - Use LLM orchestration
- `files.read` - Read files from S3
- `files.write` - Write files to S3

### Plugin Lifecycle

1. **Installation**: Plugin is uploaded and installed
2. **Configuration**: Secrets and settings are configured
3. **Activation**: Plugin is enabled and starts receiving events
4. **Execution**: Plugin code runs in response to events
5. **Deactivation**: Plugin is disabled and stops receiving events
6. **Uninstallation**: Plugin is removed from the system

## Webhooks-as-Code

### Webhook Configuration

Webhooks are configured using YAML files that define triggers, delivery settings, and transformations:

```yaml
api_version: v1
on: ["contact.created"]
delivery:
  url: "${SECRET:WEBHOOK_URL}"
  headers:
    X-Source: "SBH CRM"
    Content-Type: "application/json"
  signing:
    alg: "HMAC-SHA256"
    secret: "${SECRET:SIGNING_KEY}"
transform:
  language: "python"
  entry: "transforms/contact_transform.py#transform"
retry:
  max_attempts: 3
  backoff: "exponential"
  initial_delay: 1000
```

### Transform Functions

Transform functions modify event data before delivery:

```python
def transform(event_data):
    """Transform contact.created event data"""
    contact = event_data.get('contact', {})
    
    return {
        "event_type": "contact.created",
        "contact_id": contact.get('id'),
        "email": contact.get('email'),
        "name": f"{contact.get('first_name')} {contact.get('last_name')}",
        "company": contact.get('company'),
        "timestamp": event_data.get('timestamp')
    }
```

## SDK Reference

### Context Object

The `ctx` object provides access to SBH services and data:

```python
@hook("contact.created")
def handle_contact_created(event_data, ctx):
    # Access tenant and user information
    tenant_id = ctx.tenant_id
    user_id = ctx.user_id
    
    # Database operations
    contacts = ctx.db.query("SELECT * FROM contacts WHERE tenant_id = %s", [tenant_id])
    
    # HTTP requests (allowlisted domains only)
    response = ctx.http.get("https://api.example.com/data")
    
    # Send emails
    ctx.email.send(
        to="user@example.com",
        subject="Welcome!",
        body="Welcome to our platform"
    )
    
    # Access secrets
    api_key = ctx.secrets.get("API_KEY")
    
    # Use LLM
    response = ctx.llm.run("Summarize this text: ...")
    
    # Track analytics
    ctx.analytics.track("event_name", {"key": "value"})
    
    # Emit webhooks
    ctx.emit("custom.event", {"data": "value"})
```

### Available Decorators

#### @hook(event_type)

Register a function to handle specific events:

```python
@hook("contact.created")
def handle_contact_created(event_data, ctx):
    # Handle contact creation
    pass

@hook("deal.won")
def handle_deal_won(event_data, ctx):
    # Handle deal won
    pass
```

#### @route(path, methods)

Register HTTP routes for your plugin:

```python
@route("/ping", methods=["GET"])
def ping(ctx):
    return {"status": "ok"}

@route("/webhook", methods=["POST"])
def webhook(ctx):
    data = ctx.request.get_json()
    # Process webhook data
    return {"success": True}
```

#### @job(name, schedule)

Register scheduled jobs:

```python
@job("daily_cleanup")
def daily_cleanup(ctx):
    # Run daily cleanup tasks
    pass
```

### Database Operations

```python
# Query data
results = ctx.db.query("SELECT * FROM contacts WHERE tenant_id = %s", [ctx.tenant_id])

# Execute updates
ctx.db.execute("UPDATE contacts SET status = %s WHERE id = %s", ["active", contact_id])

# Insert data
ctx.db.execute("INSERT INTO contacts (name, email) VALUES (%s, %s)", ["John", "john@example.com"])
```

### HTTP Requests

```python
# GET request
response = ctx.http.get("https://api.example.com/data")

# POST request
response = ctx.http.post(
    "https://api.example.com/webhook",
    json={"key": "value"},
    headers={"Authorization": "Bearer token"}
)

# PUT request
response = ctx.http.put("https://api.example.com/resource", json={"data": "value"})

# DELETE request
response = ctx.http.delete("https://api.example.com/resource")
```

### Email Operations

```python
# Send email
result = ctx.email.send(
    to="user@example.com",
    subject="Welcome!",
    body="Welcome to our platform",
    from_email="noreply@company.com"
)
```

### LLM Operations

```python
# Run LLM prompt
response = ctx.llm.run(
    "Summarize this text: {text}",
    {"text": "Long text to summarize"},
    {"max_tokens": 100, "temperature": 0.7}
)
```

## Security Model

### Sandboxing

All plugin code runs in a secure sandbox with:

- **Timeouts**: 5 seconds for sync operations, 30 seconds for jobs
- **Memory limits**: 128MB per execution
- **Import restrictions**: Only allowed standard library modules
- **Network restrictions**: Only allowlisted domains
- **File system restrictions**: No direct file system access

### Permission Model

Plugins must explicitly request permissions for:

- Database access (read/write specific tables)
- Network access (specific domains)
- Email sending
- File operations
- LLM usage

### Secrets Management

Secrets are encrypted and stored securely:

```python
# Store secret
ctx.secrets.set("API_KEY", "your-api-key")

# Retrieve secret
api_key = ctx.secrets.get("API_KEY")

# Check if secret exists
if ctx.secrets.has("API_KEY"):
    # Use secret
    pass
```

### Network Allowlist

HTTP requests are restricted to allowlisted domains:

- Domains must be pre-approved
- HTTPS required for external requests
- Rate limiting applied per domain
- Request/response logging for audit

## Local Development

### Development Environment

1. **Install SBH CLI**:
   ```bash
   pip install sbh-cli
   ```

2. **Create plugin directory**:
   ```bash
   mkdir my-plugin
   cd my-plugin
   ```

3. **Initialize plugin**:
   ```bash
   sbh plugin init
   ```

4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### Testing Locally

1. **Start local SBH instance**:
   ```bash
   sbh dev start
   ```

2. **Upload plugin**:
   ```bash
   sbh plugin upload my-plugin.zip
   ```

3. **Test plugin**:
   ```bash
   sbh plugin test my-plugin
   ```

### Debugging

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Use the debug endpoint:

```python
@route("/debug", methods=["GET"])
def debug(ctx):
    return {
        "tenant_id": ctx.tenant_id,
        "user_id": ctx.user_id,
        "secrets": list(ctx.secrets.list()),
        "permissions": ctx.permissions
    }
```

## Testing

### Unit Tests

Create test files for your plugin:

```python
# test_my_plugin.py
import unittest
from unittest.mock import Mock

class TestMyPlugin(unittest.TestCase):
    def setUp(self):
        self.mock_ctx = Mock()
        self.mock_ctx.tenant_id = "test-tenant"
        self.mock_ctx.user_id = "test-user"
    
    def test_contact_created(self):
        from main import handle_contact_created
        
        event_data = {
            "contact": {
                "id": "contact-123",
                "email": "test@example.com"
            }
        }
        
        handle_contact_created(event_data, self.mock_ctx)
        
        # Assert expected behavior
        self.mock_ctx.email.send.assert_called_once()
```

### Integration Tests

Test with real SBH instance:

```python
# test_integration.py
import requests

def test_plugin_endpoint():
    response = requests.get("http://localhost:8000/ext/my-plugin/ping")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
```

### Load Testing

Test plugin performance:

```python
# test_load.py
import concurrent.futures
import requests

def test_concurrent_requests():
    def make_request():
        return requests.post("http://localhost:8000/ext/my-plugin/webhook", json={})
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(make_request) for _ in range(100)]
        results = [future.result() for future in futures]
    
    # Assert all requests succeeded
    assert all(r.status_code == 200 for r in results)
```

## Best Practices

### Code Organization

1. **Separate concerns**: Keep business logic separate from infrastructure code
2. **Error handling**: Always handle exceptions gracefully
3. **Logging**: Use appropriate log levels and include context
4. **Configuration**: Use secrets for sensitive configuration
5. **Testing**: Write comprehensive tests for all functionality

### Performance

1. **Database queries**: Use parameterized queries and indexes
2. **HTTP requests**: Implement retry logic and timeouts
3. **Caching**: Cache frequently accessed data
4. **Batch operations**: Process data in batches when possible
5. **Resource cleanup**: Clean up resources after use

### Security

1. **Input validation**: Validate all input data
2. **Output sanitization**: Sanitize output data
3. **Secret management**: Never log or expose secrets
4. **Rate limiting**: Respect rate limits for external APIs
5. **Error messages**: Don't expose sensitive information in error messages

### Monitoring

1. **Metrics**: Track important metrics and performance indicators
2. **Logging**: Log important events and errors
3. **Health checks**: Implement health check endpoints
4. **Alerts**: Set up alerts for critical failures
5. **Audit trails**: Maintain audit trails for important operations

### Deployment

1. **Versioning**: Use semantic versioning for your plugins
2. **Documentation**: Maintain up-to-date documentation
3. **Changelog**: Keep a changelog of changes
4. **Rollback**: Plan for rollback scenarios
5. **Monitoring**: Monitor plugin health in production

## Examples

### Complete Plugin Example

```python
# main.py
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

@hook("contact.created")
def send_welcome_email(event_data: Dict[str, Any], ctx) -> None:
    """Send welcome email when a new contact is created"""
    try:
        contact = event_data.get('contact', {})
        email = contact.get('email')
        name = contact.get('first_name', 'User')
        
        if not email:
            logger.warning("No email found for contact")
            return
        
        # Send welcome email
        result = ctx.email.send(
            to=email,
            subject="Welcome to our platform!",
            body=f"Hi {name},\n\nWelcome to our platform!",
            from_email="noreply@company.com"
        )
        
        logger.info(f"Welcome email sent to {email}: {result}")
        
        # Track analytics
        ctx.analytics.track("welcome_email.sent", {
            "contact_id": contact.get('id'),
            "email": email
        })
        
    except Exception as e:
        logger.error(f"Error sending welcome email: {e}")
        raise

@route("/ping", methods=["GET"])
def ping(ctx) -> Dict[str, str]:
    """Health check endpoint"""
    return {"status": "ok", "plugin": "welcome-email"}

@job("daily_cleanup")
def daily_cleanup(ctx) -> None:
    """Daily cleanup task"""
    try:
        # Clean up old data
        ctx.db.execute(
            "DELETE FROM temp_data WHERE created_at < NOW() - INTERVAL '7 days'"
        )
        
        logger.info("Daily cleanup completed")
        
    except Exception as e:
        logger.error(f"Error in daily cleanup: {e}")
        raise
```

### Webhook Example

```yaml
# webhook.yaml
api_version: v1
on: ["deal.won"]
delivery:
  url: "${SECRET:WEBHOOK_URL}"
  headers:
    X-Source: "SBH CRM"
    Content-Type: "application/json"
  signing:
    alg: "HMAC-SHA256"
    secret: "${SECRET:SIGNING_KEY}"
transform:
  language: "python"
  entry: "transforms/deal_transform.py#transform"
retry:
  max_attempts: 3
  backoff: "exponential"
```

```python
# transforms/deal_transform.py
def transform(event_data):
    deal = event_data.get('deal', {})
    
    return {
        "event_type": "deal.won",
        "deal_id": deal.get('id'),
        "title": deal.get('title'),
        "value": deal.get('value'),
        "owner": deal.get('owner_name'),
        "won_at": event_data.get('timestamp')
    }
```

## Support

For help with extensibility:

- **Documentation**: [https://docs.sbh.com/extensibility](https://docs.sbh.com/extensibility)
- **Community**: [https://community.sbh.com](https://community.sbh.com)
- **Support**: [https://support.sbh.com](https://support.sbh.com)
- **GitHub**: [https://github.com/sbh/extensibility-examples](https://github.com/sbh/extensibility-examples)

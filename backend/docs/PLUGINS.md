# Plugin Development Guide

This document explains how to develop, package, and deploy plugins for SBH.

## Overview

SBH provides a comprehensive plugin system that allows you to extend functionality without forking the main application. Plugins can:

- **React to Events**: Subscribe to system events and execute custom logic
- **Add Routes**: Create new API endpoints under `/ext/<plugin-slug>/`
- **Schedule Jobs**: Run background tasks on CRON schedules
- **Integrate with External Services**: Make HTTP calls to external APIs
- **Access System Resources**: Read from database, files, and use LLM services

## Plugin Structure

### Basic Plugin Structure
```
my-plugin/
├── plugin.json          # Plugin manifest (required)
├── main.py             # Entry point (required)
├── webhooks/           # Webhook definitions (optional)
│   └── notifications.yaml
├── transforms/         # Data transformation scripts (optional)
│   └── build_completed.py
├── static/            # Static files (optional)
│   └── logo.png
└── templates/         # HTML templates (optional)
    └── email.html
```

### Plugin Manifest (plugin.json)

```json
{
  "slug": "my-plugin",
  "name": "My Plugin",
  "version": "1.0.0",
  "description": "A description of what this plugin does",
  "author": "Your Name",
  "repo_url": "https://github.com/your-org/my-plugin",
  "entry": "main.py",
  "permissions": ["db.read", "outbound_http"],
  "routes": true,
  "events": ["auth.user.created", "build.completed"],
  "jobs": [
    {
      "name": "daily_cleanup",
      "schedule": "0 2 * * *"
    }
  ]
}
```

#### Manifest Fields

- **slug**: Unique identifier for the plugin (alphanumeric with hyphens/underscores)
- **name**: Human-readable name
- **version**: Semantic version (e.g., "1.0.0")
- **description**: Brief description of the plugin
- **author**: Plugin author name
- **repo_url**: Repository URL (optional)
- **entry**: Python file to load (usually "main.py")
- **permissions**: List of required permissions
- **routes**: Whether the plugin provides HTTP routes
- **events**: List of events the plugin subscribes to
- **jobs**: List of scheduled jobs

## Plugin Development

### Entry Point (main.py)

Your plugin's main entry point should use the SBH Plugin SDK:

```python
from src.ext.sdk import hook, route, job, PluginContext

# Event hook
@hook("auth.user.created")
def on_user_created(ctx: PluginContext, event_data):
    """Handle new user creation"""
    user_email = event_data.get('user', {}).get('email')
    print(f"New user created: {user_email}")
    
    # Send welcome email
    ctx.emit("email.welcome_sent", {"user_email": user_email})

# HTTP route
@route("/ping", methods=["GET"])
def ping_route(ctx: PluginContext):
    """Health check endpoint"""
    return {
        "status": "ok",
        "plugin": "my-plugin",
        "tenant": ctx.tenant_id
    }

# Scheduled job
@job("daily_cleanup", schedule="0 2 * * *")
def daily_cleanup_job(ctx: PluginContext):
    """Daily cleanup task"""
    # Clean up old data
    print("Running daily cleanup...")
    return {"status": "cleanup_completed"}
```

### Plugin Context

The `PluginContext` provides access to system resources:

```python
def my_function(ctx: PluginContext):
    # Access secrets
    api_key = ctx.secrets.get("API_KEY")
    
    # Make HTTP requests
    response = ctx.http.get("https://api.example.com/data")
    
    # Use LLM services
    result = ctx.llm.run("Summarize this text: ...")
    
    # Access files
    files = ctx.files.list("uploads/")
    
    # Query database (read-only)
    users = ctx.db.query("users", {"active": True})
    
    # Emit events
    ctx.emit("custom.event", {"data": "value"})
```

## Available Permissions

### Database Access
- **db.read**: Read from any table
- **db.write**: Write to any table

### File Access
- **files.read**: Read files from tenant storage
- **files.write**: Write files to tenant storage

### External Services
- **outbound_http**: Make HTTP requests to external APIs
- **send_email**: Send emails via the system email service
- **emit_webhook**: Emit webhook events

### LLM Services
- **llm.use**: Use LLM orchestration services

## Event System

### Available Events

#### Authentication Events
- `auth.user.created`: New user account created
- `auth.user.updated`: User account updated
- `auth.user.deleted`: User account deleted

#### Payment Events
- `payments.subscription.created`: New subscription created
- `payments.subscription.updated`: Subscription updated

#### File Events
- `files.uploaded`: File uploaded
- `files.deleted`: File deleted

#### Build Events
- `builder.generated`: New build generated

#### Webhook Events
- `webhook.received`: Webhook received from external service

#### Analytics Events
- `analytics.rollup.completed`: Analytics rollup completed

### Event Hook Example

```python
@hook("build.completed")
def on_build_completed(ctx: PluginContext, event_data):
    """Handle build completion"""
    build_id = event_data.get('build_id')
    status = event_data.get('status')
    project_name = event_data.get('project_name')
    
    if status == 'success':
        # Send success notification
        ctx.emit("notification.sent", {
            "type": "build_success",
            "build_id": build_id,
            "project": project_name
        })
    else:
        # Send failure notification
        ctx.emit("notification.sent", {
            "type": "build_failure",
            "build_id": build_id,
            "project": project_name
        })
```

## HTTP Routes

### Route Decorator

```python
@route("/users/<user_id>", methods=["GET"])
def get_user(ctx: PluginContext, user_id):
    """Get user information"""
    user = ctx.db.get_by_id("users", user_id)
    if user:
        return {"user": user}
    else:
        return {"error": "User not found"}, 404
```

### Route Features

- **Automatic RBAC**: Routes respect tenant isolation and user permissions
- **Request Data**: Access request data via `ctx.request`
- **Response Format**: Return dictionaries for JSON responses
- **Error Handling**: Return tuples with status codes for errors

### Route Example

```python
@route("/webhook", methods=["POST"])
def webhook_handler(ctx: PluginContext):
    """Handle incoming webhook"""
    data = ctx.request.get_json()
    
    # Validate webhook signature
    signature = ctx.request.headers.get('X-Signature')
    if not validate_signature(data, signature):
        return {"error": "Invalid signature"}, 401
    
    # Process webhook
    process_webhook_data(data)
    
    return {"status": "processed"}
```

## Scheduled Jobs

### Job Decorator

```python
@job("daily_report", schedule="0 9 * * *")
def daily_report_job(ctx: PluginContext):
    """Generate daily report"""
    # Generate report
    report_data = generate_daily_report()
    
    # Store report
    ctx.files.upload("reports/daily.json", json.dumps(report_data))
    
    # Send notification
    ctx.emit("report.generated", {"type": "daily", "data": report_data})
    
    return {"status": "report_generated"}
```

### CRON Schedule Format

Jobs use standard CRON format:
- `* * * * *` - Every minute
- `0 * * * *` - Every hour
- `0 0 * * *` - Every day at midnight
- `0 9 * * 1` - Every Monday at 9 AM
- `0 2 * * *` - Every day at 2 AM

## Webhooks-as-Code

### Webhook Definition (webhooks/notifications.yaml)

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

### Transform Script (transforms/build_completed.py)

```python
def transform(event_data):
    """Transform event data for webhook delivery"""
    return {
        "event_type": "build.completed",
        "build_id": event_data.get("build_id"),
        "status": event_data.get("status"),
        "project": event_data.get("project_name"),
        "timestamp": event_data.get("created_at")
    }
```

## Secrets Management

### Setting Secrets

Secrets are managed per plugin installation:

```python
# In your plugin code
api_key = ctx.secrets.get("API_KEY")
webhook_url = ctx.secrets.get("WEBHOOK_URL")
```

### Secret Types

- **API Keys**: External service API keys
- **Webhook URLs**: External webhook endpoints
- **Signing Keys**: Webhook signature keys
- **Database Credentials**: External database connections

## Security Considerations

### Sandboxing

All plugin code runs in a sandboxed environment:

- **Timeouts**: Default 5 seconds for sync operations, 30 seconds for jobs
- **Memory Limits**: 100MB memory limit per execution
- **Import Restrictions**: Limited to safe standard library modules
- **Network Access**: Only allowed domains via HTTP allowlist

### Safe Imports

Allowed imports:
```python
import json
import datetime
import time
import uuid
import hashlib
import base64
import urllib.parse
import collections
import itertools
import functools
import re
import math
import random
import string
```

### Forbidden Operations

- File system access outside plugin directory
- Network access to non-allowlisted domains
- Database write operations without permission
- System command execution
- Import of unsafe modules

## Testing Plugins

### Local Testing

```python
# Test your plugin locally
from src.ext.sdk import PluginContext

# Create test context
ctx = PluginContext("test-tenant", "test-user")

# Test your functions
result = your_plugin_function(ctx, test_data)
print(result)
```

### Unit Tests

```python
import unittest
from src.ext.sdk import PluginContext

class TestMyPlugin(unittest.TestCase):
    def setUp(self):
        self.ctx = PluginContext("test-tenant", "test-user")
    
    def test_my_function(self):
        result = my_function(self.ctx, {"test": "data"})
        self.assertEqual(result["status"], "success")
```

## Packaging and Deployment

### Creating Plugin Package

1. **Create plugin directory structure**
2. **Write plugin code**
3. **Create plugin.json manifest**
4. **Test locally**
5. **Create ZIP package**

```bash
# Create plugin package
cd my-plugin
zip -r my-plugin.zip .
```

### Installing Plugin

```bash
# Upload plugin via API
curl -X POST https://api.example.com/api/plugins/upload \
  -H "Authorization: Bearer <token>" \
  -H "X-Tenant-Slug: <tenant>" \
  -F "file=@my-plugin.zip"
```

### Plugin Lifecycle

1. **Upload**: Plugin ZIP uploaded via API
2. **Validation**: Manifest and code validated
3. **Installation**: Plugin installed for tenant
4. **Configuration**: Secrets and settings configured
5. **Enablement**: Plugin enabled and routes mounted
6. **Execution**: Plugin starts handling events and requests

## Best Practices

### Code Organization

- **Single Responsibility**: Each plugin should have one clear purpose
- **Error Handling**: Always handle exceptions gracefully
- **Logging**: Use print statements for debugging (captured in sandbox)
- **Configuration**: Use secrets for configuration, not hardcoded values

### Performance

- **Async Operations**: Use background jobs for long-running tasks
- **Caching**: Cache frequently accessed data
- **Batch Operations**: Process data in batches when possible
- **Resource Limits**: Respect memory and time limits

### Security

- **Input Validation**: Validate all inputs
- **Secret Management**: Never log or expose secrets
- **Permission Principle**: Request minimum required permissions
- **Error Messages**: Don't expose sensitive information in errors

### Monitoring

- **Health Checks**: Implement `/ping` endpoints
- **Metrics**: Emit events for important operations
- **Error Tracking**: Log errors for debugging
- **Performance**: Monitor execution times

## Troubleshooting

### Common Issues

#### Plugin Not Loading
- Check plugin.json syntax
- Verify entry point file exists
- Check for forbidden imports

#### Routes Not Working
- Ensure `routes: true` in manifest
- Check route decorator syntax
- Verify plugin is enabled

#### Events Not Firing
- Check event subscription in manifest
- Verify hook decorator syntax
- Check plugin is enabled

#### Permission Denied
- Request required permissions in manifest
- Check permission names are correct
- Verify tenant has permission

#### Sandbox Errors
- Check for forbidden imports
- Reduce memory usage
- Optimize execution time

### Debug Commands

```bash
# Check plugin status
curl -H "Authorization: Bearer <token>" \
  -H "X-Tenant-Slug: <tenant>" \
  https://api.example.com/api/plugins/

# Test plugin route
curl -H "Authorization: Bearer <token>" \
  -H "X-Tenant-Slug: <tenant>" \
  https://api.example.com/ext/my-plugin/ping

# Run plugin job
curl -X POST https://api.example.com/api/plugins/<id>/jobs/daily_cleanup/run-now \
  -H "Authorization: Bearer <token>" \
  -H "X-Tenant-Slug: <tenant>"

# Test event
curl -X POST https://api.example.com/api/plugins/test-event \
  -H "Authorization: Bearer <token>" \
  -H "X-Tenant-Slug: <tenant>" \
  -d '{"event_type": "auth.user.created", "event_data": {...}}'
```

## Examples

### Complete Plugin Example

See `examples/plugins/` for complete working examples:

- **welcome-email**: Sends welcome emails on user creation
- **slack-notifier**: Sends Slack notifications for events
- **daily-kpi**: Calculates daily KPIs and stores analytics

### Plugin Templates

Use these templates as starting points:

- **Event Handler**: React to system events
- **API Extension**: Add new API endpoints
- **Background Job**: Run scheduled tasks
- **Webhook Handler**: Process external webhooks
- **Data Processor**: Transform and analyze data

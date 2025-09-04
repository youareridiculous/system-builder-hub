# Agent Tools Guide

This document explains SBH's Agent Tools system for schema-grounded tool calling during code generation.

## Overview

The Agent Tools system provides:

1. **Tool Registry**: Centralized tool registration and management
2. **Tool Kernel**: Safe execution with validation and redaction
3. **Built-in Tools**: Database migrations, HTTP calls, file operations, email, and queues
4. **Safety Policy**: Domain allowlists, rate limits, and input validation
5. **Tool Calling**: LLM-powered tool selection and execution

## Tool Architecture

### Tool Registry

```python
from src.agent_tools.registry import tool_registry
from src.agent_tools.types import ToolSpec, ToolAuth

# Register a tool
spec = ToolSpec(
    name='my.tool',
    version='1.0.0',
    description='My custom tool',
    input_schema={'type': 'object'},
    output_schema={'type': 'object'},
    auth=ToolAuth.TENANT
)

tool_registry.register(spec, my_tool_handler)
```

### Tool Kernel

```python
from src.agent_tools.kernel import tool_kernel
from src.agent_tools.types import ToolCall, ToolContext

# Execute a tool
call = ToolCall(
    id='call-1',
    tool='db.migrate',
    args={'op': 'create_table', 'table': 'users'}
)

context = ToolContext(
    tenant_id='tenant-1',
    user_id='user-1',
    role='admin'
)

result = tool_kernel.execute(call, context)
```

## Built-in Tools

### Database Migration Tool

**Name**: `db.migrate`

**Description**: Generate and apply Alembic migrations for database schema changes

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "op": {
      "type": "string",
      "enum": ["create_table", "add_column", "drop_column", "modify_column"]
    },
    "table": {"type": "string"},
    "columns": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "name": {"type": "string"},
          "type": {"type": "string"},
          "nullable": {"type": "boolean"},
          "pk": {"type": "boolean"}
        }
      }
    },
    "column": {
      "type": "object",
      "properties": {
        "name": {"type": "string"},
        "type": {"type": "string"},
        "nullable": {"type": "boolean"}
      }
    },
    "dry_run": {"type": "boolean"}
  },
  "required": ["op", "table"]
}
```

**Usage Examples**:

```python
# Create table
{
  "op": "create_table",
  "table": "users",
  "columns": [
    {"name": "id", "type": "INTEGER", "nullable": False, "pk": True},
    {"name": "email", "type": "VARCHAR(255)", "nullable": False},
    {"name": "name", "type": "VARCHAR(255)", "nullable": True}
  ],
  "dry_run": True
}

# Add column
{
  "op": "add_column",
  "table": "users",
  "column": {
    "name": "phone",
    "type": "VARCHAR(20)",
    "nullable": True
  },
  "dry_run": True
}
```

### HTTP OpenAPI Tool

**Name**: `http.openapi`

**Description**: Make HTTP requests to allowlisted APIs using OpenAPI operations

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "base": {"type": "string"},
    "op_id": {"type": "string"},
    "params": {"type": "object"},
    "body": {"type": "object"},
    "headers": {"type": "object"}
  },
  "required": ["base", "op_id"]
}
```

**Usage Examples**:

```python
# Get posts from JSONPlaceholder
{
  "base": "https://jsonplaceholder.typicode.com",
  "op_id": "get_posts",
  "params": {"limit": 5}
}

# Create a post
{
  "base": "https://jsonplaceholder.typicode.com",
  "op_id": "create_post",
  "body": {
    "title": "New Post",
    "body": "Post content"
  }
}
```

### File Store Tool

**Name**: `files.store`

**Description**: List and get information about files in FileStore

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "action": {
      "type": "string",
      "enum": ["list", "info"]
    },
    "store": {"type": "string"},
    "prefix": {"type": "string"}
  },
  "required": ["action", "store"]
}
```

**Usage Examples**:

```python
# List files
{
  "action": "list",
  "store": "uploads",
  "prefix": "user/"
}

# Get store info
{
  "action": "info",
  "store": "uploads"
}
```

### Queue Enqueue Tool

**Name**: `queue.enqueue`

**Description**: Enqueue background jobs by name with payload

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "queue": {
      "type": "string",
      "enum": ["default", "low", "high"]
    },
    "job": {"type": "string"},
    "payload": {"type": "object"}
  },
  "required": ["job", "payload"]
}
```

**Usage Examples**:

```python
# Enqueue job
{
  "queue": "default",
  "job": "process_upload",
  "payload": {
    "file_id": "123",
    "user_id": "456"
  }
}
```

### Email Send Tool

**Name**: `email.send`

**Description**: Send transactional emails using existing SES pipeline

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "template": {"type": "string"},
    "to": {"type": "string"},
    "payload": {"type": "object"},
    "dry_run": {"type": "boolean"}
  },
  "required": ["template", "to", "payload"]
}
```

**Usage Examples**:

```python
# Send welcome email
{
  "template": "welcome",
  "to": "user@example.com",
  "payload": {
    "name": "John Doe",
    "activation_link": "https://example.com/activate"
  },
  "dry_run": True
}
```

## Safety & Policy

### Domain Allowlist

HTTP tools are restricted to allowlisted domains:

**Default Allowlist**:
- `jsonplaceholder.typicode.com`
- `api.stripe.com`
- `api.github.com`
- `api.openai.com`
- `api.anthropic.com`

**Configuration**:
```bash
TOOLS_HTTP_ALLOW_DOMAINS=jsonplaceholder.typicode.com,api.stripe.com
```

### Rate Limiting

Tools are rate-limited per tenant:

```bash
TOOLS_RATE_LIMIT_PER_MIN=60
```

### Input Validation

All tool inputs are validated against JSON schemas:

```python
# Schema validation
validation = tool_policy.validate_tool_call(call, context)
if not validation['valid']:
    # Handle validation errors
    for error in validation['errors']:
        print(f"Error: {error['message']}")
```

### Output Redaction

Sensitive information is automatically redacted:

```python
# Redact output
redacted = tool_policy.redact_output('http.openapi', output)

# Redacts:
# - Authorization headers
# - Cookies
# - Email addresses (keeps domain)
# - Phone numbers
```

## Tool Calling in Codegen

### Integration with Planner

The codegen planner supports tool calling:

```python
# Enable tools in goal
goal = CodegenGoal(
    repo_ref=repo_ref,
    goal_text='Add user authentication with database migration',
    tools_enabled=True
)

# Create tool context
tool_context = ToolContext(
    tenant_id=tenant_id,
    user_id=user_id,
    role=role
)

# Generate plan with tools
plan = planner.plan_changes(goal, workspace_path, tool_context, allow_tools=True)
```

### Tool Calling Loop

1. **LLM Analysis**: LLM analyzes goal and repository
2. **Tool Selection**: LLM selects appropriate tools
3. **Tool Execution**: Tools are executed with validation
4. **Result Processing**: Tool results are incorporated
5. **Plan Refinement**: Plan is refined based on tool results
6. **Final Plan**: Complete plan with diffs and tool transcript

### Tool Transcript

The plan includes a tool transcript:

```python
plan.tool_transcript = ToolTranscript(
    calls=[
        ToolCall(id='t1', tool='db.migrate', args={...}),
        ToolCall(id='t2', tool='http.openapi', args={...})
    ],
    results=[
        ToolResult(id='t1', ok=True, redacted_output={...}),
        ToolResult(id='t2', ok=True, redacted_output={...})
    ],
    total_time=2.5,
    errors=[]
)
```

## API Integration

### Plan with Tools

```http
POST /api/agent/codegen/plan
Content-Type: application/json
Authorization: Bearer <token>
X-Tenant-Slug: <tenant>

{
  "repo_ref": {
    "type": "local",
    "project_id": "project-123"
  },
  "goal_text": "Add user authentication with database migration",
  "tools": {
    "enabled": true,
    "allow_domains": ["jsonplaceholder.typicode.com"],
    "dry_run_tools": false
  }
}
```

### Response with Tool Transcript

```json
{
  "success": true,
  "data": {
    "summary": "Add user authentication with database migration",
    "diffs": [...],
    "risk": "low",
    "files_touched": ["src/auth.py", "tests/test_auth.py"],
    "tests_touched": ["tests/test_auth.py"],
    "tool_transcript": {
      "calls": [
        {
          "id": "t1",
          "tool": "db.migrate",
          "args": {
            "op": "create_table",
            "table": "users",
            "columns": [...]
          }
        }
      ],
      "results": [
        {
          "id": "t1",
          "ok": true,
          "redacted_output": {
            "sql": "CREATE TABLE users (...)",
            "operation": "create_table",
            "table": "users",
            "dry_run": true
          }
        }
      ],
      "total_time": 1.2,
      "errors": []
    }
  }
}
```

## Configuration

### Environment Variables

```bash
# Enable agent tools
FEATURE_AGENT_TOOLS=true

# HTTP domain allowlist
TOOLS_HTTP_ALLOW_DOMAINS=jsonplaceholder.typicode.com,api.stripe.com

# Rate limiting
TOOLS_RATE_LIMIT_PER_MIN=60

# Multi-tenant support
MULTI_TENANT=true
```

### Feature Flags

- `FEATURE_AGENT_TOOLS`: Enable/disable agent tools
- `FEATURE_CODEGEN_AGENT`: Enable/disable codegen agent
- `MULTI_TENANT`: Enable multi-tenant database operations

## Testing

### Tool Testing

```python
# Test database migration
def test_db_migrate_create_table_dry_run():
    args = {
        'op': 'create_table',
        'table': 'users',
        'columns': [...],
        'dry_run': True
    }
    result = db_migrate_handler(args, context)
    assert 'sql' in result
    assert result['dry_run'] == True

# Test HTTP OpenAPI
def test_http_openapi_allowlist():
    args = {
        'base': 'https://malicious-site.com',
        'op_id': 'get_data'
    }
    result = tool_policy.validate_tool_call(call, context)
    assert not result['valid']
    assert result['errors'][0]['code'] == 'domain_not_allowed'
```

### Integration Testing

```python
# Test end-to-end tool calling
def test_agent_codegen_with_tools_end_to_end():
    goal = CodegenGoal(
        repo_ref=repo_ref,
        goal_text='Add user authentication',
        tools_enabled=True
    )
    
    plan = planner.plan_changes(goal, workspace_path, tool_context, allow_tools=True)
    
    assert plan.tool_transcript is not None
    assert len(plan.tool_transcript.calls) > 0
    assert all(result.ok for result in plan.tool_transcript.results)
```

## Troubleshooting

### Common Issues

#### Tool Not Found
```
Error: Tool db.migrate is not registered
```
**Solution**: Ensure tools are registered during app startup

#### Domain Not Allowed
```
Error: Domain malicious-site.com is not in allowlist
```
**Solution**: Add domain to `TOOLS_HTTP_ALLOW_DOMAINS` or use allowed domain

#### Feature Disabled
```
Error: Database migration tools are disabled
```
**Solution**: Set `FEATURE_AGENT_TOOLS=true`

#### Rate Limit Exceeded
```
Error: Rate limit exceeded for tool http.openapi
```
**Solution**: Wait for rate limit reset or increase `TOOLS_RATE_LIMIT_PER_MIN`

#### Schema Validation Error
```
Error: Schema validation failed
```
**Solution**: Check tool input schema and ensure all required fields are provided

### Debug Commands

```python
# List registered tools
from src.agent_tools.registry import tool_registry
print(tool_registry.list_names())

# Check tool availability
from src.agent_tools.kernel import tool_kernel
print(tool_kernel.is_tool_available('db.migrate'))

# Get allowed domains
from src.agent_tools.policy import tool_policy
print(tool_policy.get_allowed_domains())
```

### Logging

Enable debug logging for tool execution:

```python
import logging
logging.getLogger('src.agent_tools').setLevel(logging.DEBUG)
```

## Best Practices

### Tool Design

1. **Clear Schemas**: Define comprehensive input/output schemas
2. **Error Handling**: Provide meaningful error messages
3. **Idempotency**: Tools should be safe to retry
4. **Dry Run Support**: Support dry-run mode for testing

### Security

1. **Input Validation**: Validate all inputs against schemas
2. **Output Redaction**: Redact sensitive information
3. **Rate Limiting**: Implement per-tenant rate limits
4. **Domain Allowlists**: Restrict HTTP calls to trusted domains

### Performance

1. **Caching**: Cache tool results when appropriate
2. **Parallel Execution**: Use parallel execution for independent tools
3. **Timeout Handling**: Implement timeouts for long-running tools
4. **Resource Limits**: Limit resource usage per tool call

### Monitoring

1. **Analytics**: Track tool usage and performance
2. **Error Monitoring**: Monitor tool failures and errors
3. **Rate Limit Monitoring**: Track rate limit violations
4. **Audit Logging**: Log all tool executions for audit

## Future Enhancements

### Planned Features

1. **Custom Tools**: Plugin architecture for custom tools
2. **Tool Composition**: Chain multiple tools together
3. **Advanced Caching**: Intelligent result caching
4. **Tool Metrics**: Detailed performance metrics
5. **Tool Versioning**: Support for tool versioning

### Advanced Options

1. **Tool Dependencies**: Declare tool dependencies
2. **Conditional Execution**: Execute tools based on conditions
3. **Tool Templates**: Reusable tool configurations
4. **Tool Testing**: Automated tool testing framework
5. **Tool Documentation**: Auto-generated tool documentation

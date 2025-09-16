# LLM Orchestration Guide

This document explains SBH's LLM orchestration system, including provider management, prompt library, safety filters, caching, and evaluation.

## Overview

The SBH LLM Orchestration system provides:

1. **Provider Management**: OpenAI, Anthropic, and local stub providers
2. **Prompt Library**: Template management with guided prompts
3. **Safety Filters**: Content filtering and PII redaction
4. **Caching**: Redis-based response caching
5. **Metering**: Usage tracking and quota management
6. **Evaluation**: Golden test harness for quality assurance

## Provider Management

### Supported Providers

#### OpenAI Provider
```python
from src.llm.providers import OpenAIProvider

provider = OpenAIProvider()
# Requires OPENAI_API_KEY environment variable
```

#### Anthropic Provider
```python
from src.llm.providers import AnthropicProvider

provider = AnthropicProvider()
# Requires ANTHROPIC_API_KEY environment variable
```

#### Local Stub Provider
```python
from src.llm.providers import LocalStubProvider

provider = LocalStubProvider()
# Always available for testing
```

### Provider Manager
```python
from src.llm.providers import LLMProviderManager

manager = LLMProviderManager()
provider = manager.get_provider('openai')  # or 'anthropic', 'local-stub'
```

## Prompt Library

### Template Structure

```python
from src.llm.schema import PromptTemplate

template = PromptTemplate(
    slug='support-email',
    title='Support Email Response',
    description='Generate professional support emails',
    structure={
        'role': 'Customer Support Representative',
        'context': 'Responding to customer inquiry',
        'task': 'Write a helpful and professional email response',
        'audience': 'Customer',
        'output': 'Professional email response'
    },
    examples=[
        {
            'input': {
                'role': 'Customer Support',
                'context': 'Password reset request',
                'custom_fields': {'customer_name': 'John Doe'}
            },
            'output': 'Dear John Doe,\n\nThank you for contacting our support team...'
        }
    ],
    system_preamble='You are a helpful customer support representative.',
    cot_enabled=True,
    json_mode=False,
    tool_schema=None,
    tenant_id='tenant-123'
)
```

### Guided Prompt Structure

The guided prompt system uses a structured approach:

- **Role**: Who is performing the task
- **Context**: Background information
- **Task**: What needs to be done
- **Audience**: Who the output is for
- **Output**: What type of output is expected

### Rendering Templates

```python
from src.llm.prompt_library import PromptLibrary

library = PromptLibrary()

guided_input = {
    'role': 'Customer Support',
    'context': 'Password reset request',
    'task': 'Help customer reset password',
    'audience': 'Customer',
    'output': 'Email response',
    'custom_fields': {
        'customer_name': 'John Doe',
        'issue_type': 'password_reset'
    }
}

messages = library.render('support-email', guided_input, 'tenant-123')
```

## Safety Filters

### Content Filtering

```python
from src.llm.safety import SafetyFilter

filter = SafetyFilter()

# Check for blocked content
result = filter.check_blocklist("This is a hack attempt")
print(result['blocked'])  # True

# Redact PII
redacted = filter.redact_pii("Contact me at john@example.com or call 555-1234")
print(redacted)  # "Contact me at [EMAIL] or call [PHONE]"

# Check for jailbreak attempts
jailbreak = filter.check_jailbreak("ignore previous instructions")
print(jailbreak['jailbreak_detected'])  # True
```

### PII Patterns

The safety filter detects and redacts:

- **Email addresses**: `user@domain.com`
- **Phone numbers**: `+1-555-123-4567`
- **Credit cards**: `1234-5678-9012-3456`
- **SSNs**: `123-45-6789`
- **IP addresses**: `192.168.1.1`
- **API keys**: `api_key: sk-1234567890abcdef`

## Caching

### Cache Configuration

```bash
# Environment variables
LLM_CACHE_ENABLED=true
LLM_CACHE_TTL_S=600  # 10 minutes
```

### Cache Usage

```python
from src.llm.cache import LLMCache

cache = LLMCache()

# Get cached response
cached_response = cache.get(request, tenant_id)
if cached_response:
    return cached_response

# Cache response
cache.set(request, response, tenant_id)
```

### Cache Keys

Cache keys are deterministic hashes of:
- Tenant ID
- Model
- Messages
- Parameters (temperature, max_tokens, etc.)

## Metering

### Usage Tracking

```python
from src.llm.metering import LLMMetering

metering = LLMMetering()

# Track request
metering.track_request(
    tenant_id='tenant-123',
    user_id='user-456',
    model='gpt-4o-mini',
    provider='openai',
    request_data={...}
)

# Track completion
metering.track_completion(
    tenant_id='tenant-123',
    user_id='user-456',
    model='gpt-4o-mini',
    provider='openai',
    usage={'prompt_tokens': 100, 'completion_tokens': 50},
    latency=1.5,
    cached=False
)
```

### Quota Management

```python
# Check quota
quota = metering.check_quota('tenant-123')
if quota['limited']:
    raise Exception('Daily token limit exceeded')

# Get usage stats
stats = metering.get_usage_stats('tenant-123', days=30)
print(f"Total tokens: {stats['total_tokens']}")
```

## API Endpoints

### Completions

```http
POST /api/llm/v1/completions
Content-Type: application/json
Authorization: Bearer <token>
X-Tenant-Slug: <tenant>

{
  "model": "gpt-4o-mini",
  "messages": [
    {"role": "user", "content": "Hello, world!"}
  ],
  "temperature": 0.7,
  "max_tokens": 500,
  "json_mode": false
}
```

### Render Prompt

```http
POST /api/llm/v1/render
Content-Type: application/json
Authorization: Bearer <token>
X-Tenant-Slug: <tenant>

{
  "slug": "support-email",
  "guided_input": {
    "role": "Customer Support",
    "context": "Password reset request",
    "custom_fields": {
      "customer_name": "John Doe"
    }
  }
}
```

### Run Prompt

```http
POST /api/llm/v1/run
Content-Type: application/json
Authorization: Bearer <token>
X-Tenant-Slug: <tenant>

{
  "slug": "support-email",
  "guided_input": {...},
  "provider": "openai",
  "model": "gpt-4o-mini",
  "temperature": 0.7
}
```

### Provider Status

```http
POST /api/llm/v1/providers/test
Authorization: Bearer <token>
X-Tenant-Slug: <tenant>
```

### System Status

```http
GET /api/llm/v1/status
Authorization: Bearer <token>
X-Tenant-Slug: <tenant>
```

## Evaluation Harness

### Golden Tests

Golden tests are defined in YAML files:

```yaml
# src/llm_eval/goldens/support_email.yaml
slug: support_email_test
description: Test support email generation
guided_input:
  role: Customer Support Representative
  context: Password reset request
  task: Write a helpful and professional email response
  audience: Customer
  output: Professional email response
  custom_fields:
    customer_name: John Doe
    issue_type: password_reset
assertions:
  - type: contains
    value: "Dear John Doe"
  - type: contains
    value: "password reset"
  - type: not_contains
    value: "hack"
```

### Running Evaluations

```python
from src.llm_eval.eval_runner import run_eval

# Run with local stub provider
results = run_eval('local-stub')

# Run with real provider
results = run_eval('openai')
```

### CLI Command

```bash
# Run all golden tests
make llm-eval

# Run with specific provider
DRY_EVAL=true make llm-eval
```

### Assertion Types

- **contains**: Response contains substring
- **not_contains**: Response does not contain substring
- **regex**: Response matches regex pattern
- **json_schema**: Response validates against JSON schema

## Configuration

### Environment Variables

```bash
# LLM Features
FEATURE_LLM_API=true
FEATURE_LLM_SAFETY=true

# Provider Configuration
LLM_DEFAULT_PROVIDER=openai
LLM_DEFAULT_MODEL=gpt-4o-mini
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key

# Caching
LLM_CACHE_ENABLED=true
LLM_CACHE_TTL_S=600

# Rate Limiting
LLM_RATE_LIMIT_DEFAULT=60 per minute
LLM_RATE_LIMIT_BURST=100 per hour

# Quotas
TENANT_LLM_DAILY_TOKENS_LIMIT=100000

# Timeouts
LLM_TIMEOUT_S=30
```

### Feature Flags

- `FEATURE_LLM_API`: Enable/disable LLM API
- `FEATURE_LLM_SAFETY`: Enable/disable safety filters
- `LLM_CACHE_ENABLED`: Enable/disable caching
- `LLM_RATE_LIMIT_ENABLED`: Enable/disable rate limiting

## Security & Privacy

### Token Security

- **Never log tokens**: Tokens are masked in logs (last 4 chars)
- **SSM Integration**: Provider keys stored in SSM
- **Scope Limitation**: Use minimal required permissions

### Content Safety

- **Blocklist Filtering**: Block harmful content
- **PII Redaction**: Automatically redact sensitive data
- **Jailbreak Detection**: Prevent prompt injection attacks

### Rate Limiting

- **Per-tenant limits**: Tenant-specific rate limits
- **Per-user limits**: User-specific rate limits
- **Burst protection**: Prevent abuse

## Usage Examples

### Basic Completion

```python
from src.llm.providers import LLMProviderManager
from src.llm.schema import LLMRequest, LLMMessage

manager = LLMProviderManager()
provider = manager.get_provider('openai')

request = LLMRequest(
    model='gpt-4o-mini',
    messages=[
        LLMMessage(role='user', content='Hello, world!')
    ],
    temperature=0.7
)

response = provider.complete(request)
print(response.text)
```

### Template Usage

```python
from src.llm.prompt_library import PromptLibrary
from src.llm.providers import LLMProviderManager

library = PromptLibrary()
manager = LLMProviderManager()

# Render template
guided_input = {
    'role': 'Customer Support',
    'context': 'Password reset request',
    'custom_fields': {'customer_name': 'John Doe'}
}

messages = library.render('support-email', guided_input, 'tenant-123')

# Get response
provider = manager.get_provider('openai')
request = LLMRequest(
    model='gpt-4o-mini',
    messages=messages,
    temperature=0.7
)

response = provider.complete(request)
print(response.text)
```

### Web Interface

```javascript
// Render prompt
const response = await fetch('/api/llm/v1/render', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
        'X-Tenant-Slug': tenant
    },
    body: JSON.stringify({
        slug: 'support-email',
        guided_input: {
            role: 'Customer Support',
            context: 'Password reset request',
            custom_fields: {
                customer_name: 'John Doe'
            }
        }
    })
});

const data = await response.json();
console.log('Messages:', data.data.messages);

// Run prompt
const runResponse = await fetch('/api/llm/v1/run', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
        'X-Tenant-Slug': tenant
    },
    body: JSON.stringify({
        slug: 'support-email',
        guided_input: {...},
        provider: 'openai',
        model: 'gpt-4o-mini'
    })
});

const runData = await runResponse.json();
console.log('Response:', runData.data.response.text);
```

## Troubleshooting

### Common Issues

#### Provider Not Configured
```bash
# Check environment variables
echo $OPENAI_API_KEY
echo $ANTHROPIC_API_KEY

# Test providers
curl -X POST /api/llm/v1/providers/test \
  -H "Authorization: Bearer <token>"
```

#### Cache Issues
```bash
# Check Redis connection
redis-cli ping

# Check cache stats
curl -X GET /api/llm/v1/status \
  -H "Authorization: Bearer <token>"
```

#### Rate Limiting
```bash
# Check rate limit status
curl -X GET /api/llm/v1/status \
  -H "Authorization: Bearer <token>"
```

### Debug Commands

```bash
# Test local stub provider
python -c "
from src.llm.providers import LocalStubProvider
provider = LocalStubProvider()
request = LLMRequest(model='stub', messages=[LLMMessage(role='user', content='test')])
response = provider.complete(request)
print(response.text)
"

# Test prompt library
python -c "
from src.llm.prompt_library import PromptLibrary
library = PromptLibrary()
templates = library.list_templates('test-tenant')
print(f'Found {len(templates)} templates')
"
```

### Error Handling

#### Network Errors
- Automatic retry with exponential backoff
- Fallback to local stub provider
- Structured error responses

#### Safety Violations
```json
{
  "error": "Safety check failed",
  "details": {
    "valid": false,
    "message_validations": [
      {
        "message_index": 0,
        "role": "user",
        "is_safe": false,
        "blocklist_check": {"blocked": true, "found_words": ["hack"]},
        "jailbreak_check": {"jailbreak_detected": false}
      }
    ]
  }
}
```

#### Quota Exceeded
```json
{
  "error": "Daily token limit exceeded",
  "details": {
    "limited": true,
    "current": 100000,
    "limit": 100000,
    "remaining": 0
  }
}
```

## Best Practices

### Prompt Design

1. **Use Guided Structure**: Leverage Role/Context/Task/Audience/Output
2. **Include Examples**: Provide clear input/output examples
3. **Set Safety Preamble**: Add system-level safety instructions
4. **Test Thoroughly**: Use golden tests for quality assurance

### Provider Management

1. **Fallback Strategy**: Always have local stub as fallback
2. **Monitor Usage**: Track token usage and costs
3. **Rate Limiting**: Implement appropriate rate limits
4. **Error Handling**: Graceful degradation on failures

### Security

1. **Token Management**: Secure API key storage
2. **Content Filtering**: Implement safety filters
3. **PII Protection**: Redact sensitive data
4. **Access Control**: Enforce RBAC and tenant isolation

### Performance

1. **Caching**: Cache responses for repeated requests
2. **Batch Processing**: Group similar requests
3. **Async Processing**: Use async for long-running requests
4. **Monitoring**: Track latency and success rates

## Future Enhancements

### Planned Features

1. **Streaming Responses**: Real-time response streaming
2. **Function Calling**: Tool/function integration
3. **Multi-Modal**: Image and audio support
4. **Fine-tuning**: Custom model fine-tuning
5. **A/B Testing**: Prompt version testing

### Advanced Options

1. **Custom Providers**: Plugin architecture for new providers
2. **Advanced Caching**: Semantic caching and similarity search
3. **Cost Optimization**: Token usage optimization
4. **Quality Metrics**: Response quality scoring
5. **Automated Testing**: Continuous evaluation pipeline

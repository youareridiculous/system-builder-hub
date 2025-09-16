# System Builder Hub - LLM Integration Runbook

## Overview

This runbook covers the LLM integration for the System Builder Hub, including configuration, testing, monitoring, and troubleshooting.

## Environment Setup

### Required Environment Variables

```bash
# LLM Encryption Key (Required in production)
export LLM_SECRET_KEY="your-32-byte-base64-encoded-key"

# LLM Provider Keys (Optional - can be configured via UI)
export LLM_PROVIDER="openai"  # openai, anthropic, groq, local
export LLM_API_KEY="your-api-key"
export LLM_DEFAULT_MODEL="gpt-3.5-turbo"

# Previous encryption keys for rotation (Optional)
export LLM_PREVIOUS_KEYS='["previous-key-1", "previous-key-2"]'
```

### Generating LLM Secret Key

```bash
# Generate a new 32-byte key
python3 -c "
import base64
import os
key = os.urandom(32)
print('LLM_SECRET_KEY=' + base64.urlsafe_b64encode(key).decode())
"
```

## Running E2E Tests

### Prerequisites

1. Install test dependencies:
```bash
pip install pytest pytest-cov
```

2. Set up test environment:
```bash
export LLM_SECRET_KEY="dGVzdC1rZXktZm9yLXRlc3Rpbmctc2VjcmV0cy0xMjM="
export FLASK_ENV=testing
```

### Running Tests

```bash
# Run all E2E tests
pytest tests/e2e/ -v

# Run specific test class
pytest tests/e2e/test_build_loop_llm.py::TestLLMPath -v

# Run with coverage
pytest tests/e2e/ --cov=src --cov-report=html

# Run in CI mode (no interactive prompts)
pytest tests/e2e/ --tb=short -x
```

### Test Categories

- **LLM Path Tests**: Provider configuration, connection testing, guided builds
- **Failure & Recovery Tests**: Circuit breaker, timeouts, rate limits
- **No-LLM Path Tests**: Template-only builds without LLM dependency
- **Metrics & Logging Tests**: Usage tracking and Prometheus metrics

## Monitoring & Status

### LLM Status Endpoint

```bash
# Get comprehensive LLM status
curl -H "X-Tenant-ID: your-tenant" http://localhost:5001/api/llm/status
```

**Response Format:**
```json
{
  "available": true,
  "provider": "openai",
  "model": "gpt-3.5-turbo",
  "providers": [
    {
      "name": "openai",
      "active": true,
      "model": "gpt-3.5-turbo",
      "last_ok": "2024-01-01T12:00:00Z",
      "failure_count": 0,
      "circuit_state": "closed",
      "today_requests": 45,
      "today_tokens": 12000,
      "rate_limit_remaining": 955,
      "tokens_remaining": 988000
    }
  ],
  "safety": {
    "timeouts": {"connect": 5, "read": 30},
    "model_allowlists": {"openai": ["gpt-3.5-turbo", "gpt-4"]}
  },
  "usage": {
    "today_requests": 45,
    "today_tokens": 12000,
    "success_rate": 98.5
  }
}
```

### Prometheus Metrics

```bash
# Get Prometheus-style metrics
curl -H "X-Tenant-ID: your-tenant" http://localhost:5001/api/llm/metrics
```

**Available Metrics:**
- `llm_requests_total{provider}` - Total requests by provider
- `llm_latency_ms{provider}` - Average latency by provider
- `llm_circuit_state{provider}` - Circuit breaker state (0=closed, 1=open)
- `llm_failure_count{provider}` - Failure count by provider
- `llm_rate_limit_remaining{provider}` - Rate limit remaining

### Health Check

```bash
# Check overall system health
curl http://localhost:5001/healthz
```

## Common Errors & Remedies

### 1. Invalid API Key

**Error:** `"Invalid API key"` or `"Authentication failed"`

**Causes:**
- Incorrect API key format
- Expired or revoked key
- Wrong provider for key type

**Remedies:**
```bash
# Verify key format
# OpenAI: sk-[48 chars]
# Anthropic: sk-ant-[48 chars]  
# Groq: gsk_[48 chars]

# Test key manually
curl -H "Authorization: Bearer YOUR_KEY" \
     -H "Content-Type: application/json" \
     https://api.openai.com/v1/models
```

### 2. Model Not Allowed

**Error:** `"Model not found"` or `"Model not allowed"`

**Causes:**
- Model not in allowlist
- Model doesn't exist for provider
- Insufficient quota for model

**Remedies:**
```bash
# Check allowed models
curl http://localhost:5001/api/llm/status | jq '.safety.model_allowlists'

# Use supported model
# OpenAI: gpt-3.5-turbo, gpt-4
# Anthropic: claude-3-sonnet-20240229
# Groq: llama2-70b-4096
```

### 3. Circuit Breaker Open

**Error:** `"Circuit breaker open"` or Start button disabled

**Causes:**
- Consecutive failures exceeded threshold
- Provider temporarily unavailable
- Rate limiting

**Remedies:**
```bash
# Check circuit state
curl http://localhost:5001/api/llm/status | jq '.providers[].circuit_state'

# Wait for recovery (default: 60 seconds)
# Or manually reset in development
```

### 4. Rate Limit Exceeded

**Error:** `"Rate limit exceeded"` or `"429 Too Many Requests"`

**Causes:**
- Daily request limit reached
- Token limit exceeded
- Provider rate limiting

**Remedies:**
```bash
# Check usage
curl http://localhost:5001/api/llm/status | jq '.usage'

# Check remaining limits
curl http://localhost:5001/api/llm/status | jq '.providers[].rate_limit_remaining'

# Wait for reset or upgrade plan
```

### 5. Timeout Errors

**Error:** `"Request timeout"` or `"Connection timeout"`

**Causes:**
- Network connectivity issues
- Provider slow response
- Firewall blocking requests

**Remedies:**
```bash
# Check network connectivity
ping api.openai.com

# Test with curl
curl --connect-timeout 5 --max-time 30 \
     -H "Authorization: Bearer YOUR_KEY" \
     https://api.openai.com/v1/chat/completions

# Adjust timeouts if needed
# Default: connect=5s, read=30s
```

### 6. LLM Secret Key Missing

**Error:** `"LLM_SECRET_KEY environment variable is required"`

**Causes:**
- Environment variable not set
- Invalid key format
- Key not 32 bytes

**Remedies:**
```bash
# Generate new key
python3 -c "
import base64
import os
key = os.urandom(32)
print('LLM_SECRET_KEY=' + base64.urlsafe_b64encode(key).decode())
"

# Set environment variable
export LLM_SECRET_KEY="your-generated-key"
```

## Debugging

### Enable Debug Logging

```bash
export LOG_LEVEL=DEBUG
export FLASK_ENV=development
```

### Check Database State

```bash
# SQLite database location
ls -la system_builder_hub.db

# Check provider configs
sqlite3 system_builder_hub.db "
SELECT provider, default_model, last_tested, test_latency_ms 
FROM llm_provider_configs 
WHERE is_active = 1;
"

# Check usage logs
sqlite3 system_builder_hub.db "
SELECT provider, endpoint, success, latency_ms, created_at 
FROM llm_usage_logs 
ORDER BY created_at DESC 
LIMIT 10;
"
```

### Test LLM Integration

```bash
# Test connection
curl -X POST -H "Content-Type: application/json" \
     -H "X-Tenant-ID: your-tenant" \
     http://localhost:5001/api/llm/test

# Dry-run prompt
curl -X POST -H "Content-Type: application/json" \
     -H "X-Tenant-ID: your-tenant" \
     -d '{"prompt": "echo ping"}' \
     http://localhost:5001/api/llm/dry-run
```

## Performance Tuning

### Timeout Configuration

```python
# Adjust timeouts in src/llm_safety.py
timeouts = {
    'connect': 5,   # Connection timeout (seconds)
    'read': 30      # Read timeout (seconds)
}
```

### Circuit Breaker Settings

```python
# Adjust in src/llm_safety.py
CircuitBreaker(
    failure_threshold=5,      # Failures before opening
    recovery_timeout=60,      # Seconds before half-open
    half_open_max_calls=3     # Calls to test recovery
)
```

### Rate Limiting

```python
# Adjust in src/llm_safety.py
RateLimiter(
    max_requests_per_day=1000,    # Daily request limit
    max_tokens_per_day=1000000    # Daily token limit
)
```

## Security Considerations

### API Key Management

- Never commit API keys to version control
- Use environment variables or secure key management
- Rotate keys regularly
- Monitor usage for anomalies

### Encryption

- LLM_SECRET_KEY must be 32 bytes
- Keys are encrypted at rest using Fernet
- Support key rotation for security updates

### Access Control

- All endpoints require authentication
- Tenant-scoped configurations
- Rate limiting per tenant

## Troubleshooting Checklist

- [ ] LLM_SECRET_KEY is set and valid
- [ ] Provider API key is correct and active
- [ ] Model is in allowlist for provider
- [ ] Network connectivity to provider API
- [ ] Circuit breaker state (should be 'closed')
- [ ] Rate limits not exceeded
- [ ] Database tables exist and accessible
- [ ] Logs show no encryption/decryption errors
- [ ] Metrics endpoint returns valid data

## Support

For issues not covered in this runbook:

1. Check application logs: `tail -f /var/log/sbh/app.log`
2. Verify environment configuration
3. Test with minimal example
4. Check provider status pages
5. Contact system administrator

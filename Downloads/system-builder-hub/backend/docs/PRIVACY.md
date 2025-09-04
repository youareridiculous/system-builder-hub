# Privacy Modes & Data Governance v1

## Overview

System Builder Hub (SBH) provides first-class privacy controls through three distinct privacy modes, enabling organizations to meet various compliance and security requirements.

## Privacy Modes

### 1. Local-Only Mode
**Use Case**: Maximum privacy, air-gapped environments
- **External Calls**: Blocked (except explicitly allowlisted domains)
- **Data Retention**: None (0 seconds)
- **Encryption**: Local Fernet keys only
- **LLM**: Local stub implementation
- **Storage**: Local file system only

**Configuration**:
```bash
DEFAULT_PRIVACY_MODE=local_only
CMK_BACKEND=local
```

### 2. Bring Your Own Keys (BYO) Mode
**Use Case**: Tenant-managed keys, no vendor data retention
- **External Calls**: Allowed with tenant-provided API keys
- **Data Retention**: None (0 seconds) - only hashes stored
- **Encryption**: Customer-managed keys (CMK) required
- **LLM**: Tenant API keys for OpenAI, Anthropic, etc.
- **Storage**: Tenant S3 buckets, encrypted credentials

**Configuration**:
```bash
DEFAULT_PRIVACY_MODE=byo_keys
CMK_BACKEND=aws_kms  # or vault
AWS_KMS_KEY_ID=arn:aws:kms:region:account:key/key-id
```

### 3. Private Cloud Mode
**Use Case**: Platform-managed with strict controls
- **External Calls**: Allowed with platform keys
- **Data Retention**: Configurable (default: 24 hours)
- **Encryption**: Customer-managed keys (CMK) required
- **LLM**: Platform-managed API keys
- **Storage**: Platform S3 with tenant isolation

**Configuration**:
```bash
DEFAULT_PRIVACY_MODE=private_cloud
CMK_BACKEND=aws_kms
PRIVACY_PROMPT_RETENTION_DEFAULT_SECONDS=86400
PRIVACY_RESPONSE_RETENTION_DEFAULT_SECONDS=86400
```

## Data Flow Transparency

### What Data Leaves Your Tenant?

| Data Category | Purpose | Retention | Redaction |
|---------------|---------|-----------|-----------|
| **Prompts** | AI processing | Configurable | Always applied |
| **Model Responses** | Service delivery | Configurable | Always applied |
| **Analytics** | Service improvement | 30 days | Always applied |
| **Files** | Feature functionality | Until deletion | Metadata only |
| **Audit Logs** | Compliance | 7 years | PII redacted |

### Domain Allowlist

Each privacy mode maintains a strict domain allowlist:

- **Local-Only**: Empty (no external calls)
- **BYO Keys**: LLM providers, email services, storage providers
- **Private Cloud**: Same as BYO Keys + platform services

## Configuration

### Environment Variables

```bash
# Privacy Mode
DEFAULT_PRIVACY_MODE=private_cloud

# Retention Settings
PRIVACY_PROMPT_RETENTION_DEFAULT_SECONDS=86400
PRIVACY_RESPONSE_RETENTION_DEFAULT_SECONDS=86400

# Domain Allowlist (comma-separated)
PRIVACY_ALLOWLIST_DOMAINS=api.openai.com,api.anthropic.com

# CMK Configuration
CMK_BACKEND=aws_kms
AWS_KMS_KEY_ID=arn:aws:kms:us-east-1:123456789012:key/abcd1234-5678-90ef-ghij-klmnopqrstuv
AWS_REGION=us-east-1

# Vault Configuration (alternative)
CMK_BACKEND=vault
VAULT_URL=http://vault:8200
VAULT_TOKEN=hvs.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Tenant-Level Overrides

Tenants can override platform defaults through the Admin UI:

1. Navigate to **Settings → Privacy & Data**
2. Select privacy mode
3. Configure retention policies
4. Set BYO keys (if applicable)
5. Toggle privacy features

## Data Redaction

### Automatic Redaction

The system automatically redacts sensitive data before logging:

- **Email addresses**: `john@example.com` → `[EMAIL_REDACTED]`
- **Phone numbers**: `(555) 123-4567` → `[PHONE_REDACTED]`
- **Credit cards**: `4111-1111-1111-1111` → `[CC_REDACTED]`
- **API keys**: `sk-1234567890abcdef` → `[API_KEY_REDACTED]`
- **AWS keys**: `AKIA1234567890ABCDEF` → `[AWS_KEY_REDACTED]`
- **JWT tokens**: `eyJhbGciOiJIUzI1NiIs...` → `[JWT_REDACTED]`

### Redaction Rules

Redaction is deterministic and configurable:

```python
# Example redaction configuration
redaction_rules = [
    {
        "name": "email",
        "pattern": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        "replacement": "[EMAIL_REDACTED]",
        "severity": "high"
    }
]
```

## Customer-Managed Keys (CMK)

### Supported Backends

1. **Local Fernet**: Development and testing
2. **AWS KMS**: Production environments
3. **HashiCorp Vault**: Enterprise deployments

### Key Rotation

```bash
# AWS KMS Key Rotation
aws kms enable-key-rotation --key-id arn:aws:kms:us-east-1:123456789012:key/abcd1234-5678-90ef-ghij-klmnopqrstuv

# Vault Key Rotation
vault write transit/keys/sbh-key type=rsa-4096
```

### Encrypted Data

The following data is encrypted at rest:

- BYO API keys and credentials
- Webhook secrets
- Plugin configuration secrets
- Tenant-specific encryption keys

## Verification

### How to Verify Privacy Controls

1. **Check Privacy Mode**:
   ```bash
   curl -H "Authorization: Bearer $TOKEN" \
        https://api.example.com/api/privacy/transparency
   ```

2. **Verify Data Retention**:
   ```bash
   # Check retention jobs
   curl -H "Authorization: Bearer $TOKEN" \
        https://api.example.com/api/privacy/audit
   ```

3. **Test Redaction**:
   ```bash
   # Send test data with PII
   curl -X POST -H "Authorization: Bearer $TOKEN" \
        -d '{"text": "Email: john@example.com, Phone: (555) 123-4567"}' \
        https://api.example.com/api/privacy/test-redaction
   ```

4. **Export Privacy Data**:
   ```bash
   curl -X POST -H "Authorization: Bearer $TOKEN" \
        https://api.example.com/api/privacy/export
   ```

### Monitoring

Monitor privacy controls through:

- **Privacy Transparency Panel**: Real-time privacy status
- **Audit Logs**: Privacy-related actions and changes
- **Retention Jobs**: Data cleanup execution
- **Metrics**: Redaction counts, retention compliance

## Compliance

### GDPR Compliance

- **Right to Access**: Export privacy data via API
- **Right to Erasure**: Delete all privacy-related data
- **Data Minimization**: Configurable retention policies
- **Transparency**: Clear data flow documentation

### SOC 2 Compliance

- **Access Controls**: RBAC for privacy settings
- **Audit Logging**: All privacy changes logged
- **Encryption**: Data encrypted at rest and in transit
- **Monitoring**: Continuous privacy compliance monitoring

### HIPAA Compliance

- **PHI Protection**: Automatic redaction of health information
- **Access Logs**: Detailed audit trails
- **Encryption**: FIPS 140-2 compliant encryption
- **Business Associate Agreement**: Available upon request

## Troubleshooting

### Common Issues

1. **Domain Blocked**: Check allowlist configuration
2. **Key Decryption Failed**: Verify CMK configuration
3. **Retention Not Applied**: Check retention job status
4. **Redaction Not Working**: Verify redaction rules

### Support

For privacy-related issues:

1. Check the privacy transparency panel
2. Review audit logs for recent changes
3. Verify environment configuration
4. Contact support with privacy compliance requirements

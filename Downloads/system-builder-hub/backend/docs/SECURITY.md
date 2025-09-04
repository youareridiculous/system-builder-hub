# Security Hardening & CMK Implementation

## Customer-Managed Keys (CMK)

### Overview

System Builder Hub implements customer-managed keys (CMK) for encryption at rest, ensuring that sensitive data is protected with keys that customers control and manage.

### Supported Backends

#### 1. Local Fernet (Development)
```bash
CMK_BACKEND=local
```
- **Use Case**: Development, testing, local deployments
- **Key Storage**: Local file system
- **Key Rotation**: Manual key file replacement
- **Security**: Suitable for non-production environments

#### 2. AWS KMS (Production)
```bash
CMK_BACKEND=aws_kms
AWS_KMS_KEY_ID=arn:aws:kms:us-east-1:123456789012:key/abcd1234-5678-90ef-ghij-klmnopqrstuv
AWS_REGION=us-east-1
```
- **Use Case**: Production environments on AWS
- **Key Storage**: AWS KMS (FIPS 140-2 Level 2)
- **Key Rotation**: Automatic (configurable)
- **Security**: Hardware security modules (HSM)

#### 3. HashiCorp Vault (Enterprise)
```bash
CMK_BACKEND=vault
VAULT_URL=http://vault:8200
VAULT_TOKEN=hvs.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```
- **Use Case**: Enterprise deployments, multi-cloud
- **Key Storage**: HashiCorp Vault
- **Key Rotation**: Policy-based automation
- **Security**: Enterprise-grade key management

### Encrypted Data Types

The following data is encrypted using CMK:

1. **BYO API Keys**: Tenant-provided API credentials
2. **Webhook Secrets**: Incoming webhook authentication
3. **Plugin Secrets**: Third-party integration credentials
4. **Tenant Keys**: Tenant-specific encryption keys
5. **Audit Data**: Sensitive audit log entries

### Key Management Operations

#### Key Creation
```python
from src.crypto.keys import get_key_manager

key_manager = get_key_manager()
encrypted_data = key_manager.encrypt_data(b"sensitive_data")
```

#### Key Retrieval
```python
decrypted_data = key_manager.decrypt_data(encrypted_data)
```

#### Secret Storage
```python
# Store encrypted secret
key_manager.encrypt_secret("tenant_openai_key", "sk-1234567890abcdef")

# Retrieve decrypted secret
api_key = key_manager.decrypt_secret("tenant_openai_key")
```

### Key Rotation

#### AWS KMS Rotation
```bash
# Enable automatic rotation
aws kms enable-key-rotation --key-id arn:aws:kms:us-east-1:123456789012:key/abcd1234-5678-90ef-ghij-klmnopqrstuv

# Manual rotation
aws kms create-alias --alias-name alias/sbh-key-v2 --target-key-id arn:aws:kms:us-east-1:123456789012:key/efgh5678-90ab-cdef-ghij-klmnopqrstuv
```

#### Vault Rotation
```bash
# Create new key version
vault write transit/keys/sbh-key type=rsa-4096

# Rotate key
vault write transit/keys/sbh-key/rotate
```

#### Local Key Rotation
```bash
# Backup current key
cp local.key local.key.backup

# Generate new key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" > local.key.new

# Update application
mv local.key.new local.key
```

## Secret Storage

### Database Encryption

Sensitive fields in the database are encrypted:

```sql
-- Example: BYO API keys are stored encrypted
CREATE TABLE privacy_settings (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL,
    byo_openai_key TEXT,  -- Encrypted
    byo_anthropic_key TEXT,  -- Encrypted
    byo_aws_access_key TEXT,  -- Encrypted
    byo_aws_secret_key TEXT,  -- Encrypted
    -- ... other fields
);
```

### Environment Variables

Sensitive environment variables should be encrypted or stored in secure parameter stores:

```bash
# AWS Systems Manager Parameter Store
aws ssm put-parameter \
    --name "/sbh/prod/aws-kms-key-id" \
    --value "arn:aws:kms:us-east-1:123456789012:key/abcd1234-5678-90ef-ghij-klmnopqrstuv" \
    --type "SecureString"

# Retrieve in application
AWS_KMS_KEY_ID=$(aws ssm get-parameter --name "/sbh/prod/aws-kms-key-id" --with-decryption --query 'Parameter.Value' --output text)
```

### Application Secrets

Application-level secrets are managed through the CMK system:

```python
# Store application secret
key_manager.store_secret("webhook_slack_secret", "xoxb-1234567890-abcdef")

# Retrieve application secret
slack_secret = key_manager.get_secret("webhook_slack_secret")
```

## Security Best Practices

### 1. Key Management
- Use hardware security modules (HSM) in production
- Implement automatic key rotation
- Monitor key usage and access
- Use least privilege access policies

### 2. Access Controls
- Implement RBAC for privacy settings
- Require multi-factor authentication for admin access
- Audit all key management operations
- Use temporary credentials where possible

### 3. Monitoring
- Monitor encryption/decryption operations
- Alert on key access anomalies
- Log all secret access attempts
- Regular security assessments

### 4. Compliance
- Maintain encryption key inventory
- Document key lifecycle procedures
- Regular compliance audits
- Incident response procedures

## Security Controls

### Network Security
- TLS 1.3 for all communications
- Certificate pinning for critical endpoints
- Network segmentation for sensitive data
- DDoS protection

### Application Security
- Input validation and sanitization
- SQL injection prevention
- XSS protection
- CSRF tokens

### Data Protection
- Encryption at rest and in transit
- Data classification and labeling
- Access logging and monitoring
- Data loss prevention (DLP)

## Incident Response

### Security Incident Procedures

1. **Detection**: Automated monitoring and alerting
2. **Assessment**: Impact analysis and containment
3. **Response**: Immediate mitigation actions
4. **Recovery**: System restoration and validation
5. **Lessons Learned**: Post-incident review

### Key Compromise Response

1. **Immediate Actions**:
   - Revoke compromised keys
   - Rotate all dependent keys
   - Audit key usage logs
   - Notify stakeholders

2. **Investigation**:
   - Root cause analysis
   - Impact assessment
   - Evidence preservation
   - Legal notification if required

3. **Recovery**:
   - Deploy new keys
   - Re-encrypt affected data
   - Validate system integrity
   - Update security procedures

## Compliance Frameworks

### SOC 2 Type II
- **CC1**: Control Environment
- **CC2**: Communication and Information
- **CC3**: Risk Assessment
- **CC4**: Monitoring Activities
- **CC5**: Control Activities
- **CC6**: Logical and Physical Access Controls
- **CC7**: System Operations
- **CC8**: Change Management
- **CC9**: Risk Mitigation

### ISO 27001
- **A.10**: Cryptography
- **A.12**: Operations Security
- **A.13**: Communications Security
- **A.18**: Compliance

### GDPR
- **Article 32**: Security of processing
- **Article 25**: Data protection by design and by default
- **Article 30**: Records of processing activities

## Security Testing

### Penetration Testing
- Regular external penetration tests
- Internal security assessments
- Vulnerability scanning
- Code security reviews

### Security Monitoring
- Real-time threat detection
- Anomaly detection
- Security event correlation
- Incident response automation

### Compliance Audits
- Annual security audits
- Third-party assessments
- Regulatory compliance reviews
- Continuous monitoring

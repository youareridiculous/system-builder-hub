# Settings Hub v1

## Overview

The Settings Hub provides a unified interface for managing both user account settings and tenant workspace configurations. It integrates with existing features including Privacy Modes, API Keys, Webhooks, LLM Orchestration, and RBAC.

## Information Architecture

### My Account (User Scope)

**Profile**
- Name, avatar, timezone, locale
- Avatar upload via file store

**Security**
- Password management
- Session management with device fingerprinting
- Two-factor authentication (TOTP)
- Recovery codes generation

**Notifications & Email Preferences**
- Email digest settings (daily/weekly)
- Mention notifications
- Approval notifications

**API Tokens (Personal)**
- Personal API token management
- Show-once secret display
- Token permissions and scopes

**Connected Apps**
- OAuth integrations (Google, Microsoft)
- Connect/disconnect functionality
- Status indicators

### Workspace (Tenant Scope - Owner/Admin Only)

**Overview**
- Workspace profile (name, logo, brand colors)
- Domain/slug configuration
- Basic workspace information

**Members & Roles**
- User invitation and management
- Role assignment (Owner, Admin, Member, Viewer)
- Permission matrix

**Privacy & Data**
- Privacy mode selection (Local-Only, BYO Keys, Private Cloud)
- Data retention policies
- BYO key configuration
- Data flow transparency

**Integrations**
- Slack integration
- Zapier webhooks
- Google Drive connection
- SES/S3 configuration

**Developer**
- LLM provider defaults
- Model routing configuration
- Temperature settings
- HTTP tool allowlist

**API & Webhooks**
- Tenant API key management
- Outbound webhook registry
- Webhook test delivery
- Signing key management

**Billing**
- Stripe customer portal integration
- Usage tracking
- Plan management

**Backups & Export**
- GDPR-compliant data export
- Backup creation and restoration
- Data retention compliance

**Diagnostics**
- System health monitoring
- Component status (Redis, RDS, S3, SES)
- Feature flag status
- Privacy mode indicators
- Metrics and logs access

**Danger Zone**
- Secret rotation
- Workspace deletion with guard phrases
- Audit trail preservation

## Data Models

### User Settings
```sql
user_settings (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) UNIQUE NOT NULL,
    name VARCHAR(255),
    avatar_url VARCHAR(500),
    timezone VARCHAR(50) DEFAULT 'UTC',
    locale VARCHAR(10) DEFAULT 'en-US',
    email_digest_daily BOOLEAN DEFAULT FALSE,
    email_digest_weekly BOOLEAN DEFAULT TRUE,
    mention_emails BOOLEAN DEFAULT TRUE,
    approvals_emails BOOLEAN DEFAULT TRUE,
    two_factor_enabled BOOLEAN DEFAULT FALSE,
    recovery_codes TEXT, -- Encrypted
    created_at TIMESTAMP,
    updated_at TIMESTAMP
)
```

### User Sessions
```sql
user_sessions (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    device_fingerprint VARCHAR(255),
    user_agent TEXT,
    ip_address VARCHAR(45),
    created_at TIMESTAMP,
    last_seen_at TIMESTAMP,
    revoked_at TIMESTAMP
)
```

### Tenant Settings
```sql
tenant_settings (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(36) UNIQUE NOT NULL,
    display_name VARCHAR(255),
    brand_color VARCHAR(7), -- Hex color
    logo_url VARCHAR(500),
    default_llm_provider VARCHAR(50),
    default_llm_model VARCHAR(100),
    temperature_default FLOAT DEFAULT 0.7,
    http_allowlist TEXT, -- JSON array
    privacy_settings_id VARCHAR(36), -- FK to privacy_settings
    allow_anonymous_metrics BOOLEAN DEFAULT TRUE,
    trace_sample_rate FLOAT DEFAULT 0.1,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
)
```

### Tenant API Tokens
```sql
tenant_api_tokens (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL,
    name VARCHAR(255) NOT NULL,
    token_prefix VARCHAR(8) NOT NULL,
    token_hash VARCHAR(255) NOT NULL,
    permissions TEXT, -- JSON array
    last_used_at TIMESTAMP,
    expires_at TIMESTAMP,
    created_at TIMESTAMP,
    created_by VARCHAR(36) NOT NULL,
    revoked_at TIMESTAMP
)
```

### Outbound Webhooks
```sql
outbound_webhooks (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL,
    name VARCHAR(255) NOT NULL,
    target_url VARCHAR(500) NOT NULL,
    events TEXT NOT NULL, -- JSON array
    signing_key TEXT, -- Encrypted
    enabled BOOLEAN DEFAULT TRUE,
    last_delivery_at TIMESTAMP,
    last_delivery_status INTEGER,
    created_at TIMESTAMP,
    created_by VARCHAR(36) NOT NULL,
    updated_at TIMESTAMP
)
```

### Audit Security Events
```sql
audit_security_events (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id VARCHAR(36),
    ip_address VARCHAR(45),
    user_agent TEXT,
    before_values TEXT, -- JSON, redacted
    after_values TEXT, -- JSON, redacted
    metadata TEXT, -- JSON
    created_at TIMESTAMP
)
```

## API Endpoints

### User Account Settings

#### Profile
- `GET /api/settings/account/profile` - Get user profile
- `PUT /api/settings/account/profile` - Update user profile

#### Security
- `GET /api/settings/account/security` - Get security settings
- `POST /api/settings/account/security/2fa/enable` - Enable 2FA
- `POST /api/settings/account/security/2fa/disable` - Disable 2FA
- `POST /api/settings/account/security/recovery-codes` - Generate recovery codes
- `GET /api/settings/account/sessions` - List user sessions
- `POST /api/settings/account/sessions/{id}/revoke` - Revoke session

#### Notifications
- `GET /api/settings/account/notifications` - Get notification settings
- `PUT /api/settings/account/notifications` - Update notification settings

### Workspace Settings

#### Overview
- `GET /api/settings/workspace/overview` - Get workspace overview
- `PUT /api/settings/workspace/overview` - Update workspace overview

#### Privacy
- `GET /api/settings/workspace/privacy` - Get privacy settings
- `PUT /api/settings/workspace/privacy` - Update privacy settings

#### Developer
- `GET /api/settings/workspace/developer` - Get developer settings
- `PUT /api/settings/workspace/developer` - Update developer settings

#### API Keys
- `GET /api/settings/workspace/api-keys` - List API keys
- `POST /api/settings/workspace/api-keys` - Create API key
- `POST /api/settings/workspace/api-keys/{id}/revoke` - Revoke API key

#### Webhooks
- `GET /api/settings/workspace/webhooks` - List webhooks
- `POST /api/settings/workspace/webhooks` - Create webhook
- `POST /api/settings/workspace/webhooks/{id}/test` - Test webhook

#### Diagnostics
- `GET /api/settings/workspace/diagnostics` - Get diagnostics data

#### Danger Zone
- `POST /api/settings/workspace/danger/rotate-secrets` - Rotate secrets
- `POST /api/settings/workspace/danger/delete` - Delete workspace

## RBAC Matrix

| Action | Owner | Admin | Member | Viewer |
|--------|-------|-------|--------|--------|
| View own account settings | ✅ | ✅ | ✅ | ✅ |
| Update own account settings | ✅ | ✅ | ✅ | ✅ |
| View workspace overview | ✅ | ✅ | ✅ | ✅ |
| Update workspace overview | ✅ | ✅ | ❌ | ❌ |
| View privacy settings | ✅ | ✅ | ❌ | ❌ |
| Update privacy settings | ✅ | ✅ | ❌ | ❌ |
| View developer settings | ✅ | ✅ | ❌ | ❌ |
| Update developer settings | ✅ | ✅ | ❌ | ❌ |
| Manage API keys | ✅ | ✅ | ❌ | ❌ |
| Manage webhooks | ✅ | ✅ | ❌ | ❌ |
| View diagnostics | ✅ | ✅ | ❌ | ❌ |
| Rotate secrets | ✅ | ❌ | ❌ | ❌ |
| Delete workspace | ✅ | ❌ | ❌ | ❌ |

## Security Features

### Show-Once Secrets
- API tokens are displayed only once upon creation
- Secrets are encrypted at rest using CMK
- Audit logging for all secret access

### Session Management
- Device fingerprinting for session tracking
- IP address and user agent logging
- Session revocation capabilities
- Automatic session cleanup

### Two-Factor Authentication
- TOTP-based 2FA implementation
- Recovery codes for account recovery
- QR code generation for authenticator apps
- Secure key generation and storage

### Audit Logging
- All settings changes are logged
- Before/after values are redacted
- IP address and user agent tracking
- Event categorization and filtering

## Privacy Integration

### Privacy Mode Routing
- Settings respect current privacy mode
- BYO keys integration for tenant-managed credentials
- Data retention policy enforcement
- Redaction applied to sensitive data

### Data Flow Transparency
- Real-time privacy status display
- Data retention compliance indicators
- Export capabilities for GDPR compliance
- Audit trail preservation

## Developer Integration

### LLM Orchestration
- Default provider/model configuration
- Temperature settings for consistency
- HTTP tool allowlist management
- Hot-reload capability for settings changes

### API Key Management
- Tenant-scoped API key creation
- Permission-based access control
- Key rotation and revocation
- Usage tracking and monitoring

### Webhook System
- Event-driven webhook delivery
- Signing key management
- Test delivery functionality
- Delivery status tracking

## UI Components

### Settings Layout
- Left navigation with user/workspace sections
- Responsive design for mobile/desktop
- Keyboard accessibility support
- Save bar for unsaved changes

### Form Components
- Consistent form styling
- Validation and error handling
- Auto-save functionality
- Confirmation modals for destructive actions

### Toast Notifications
- Success/error/info message display
- Auto-dismiss functionality
- Action confirmation feedback
- Non-intrusive design

## Testing Strategy

### Unit Tests
- Model validation and serialization
- Service layer business logic
- API endpoint functionality
- Security feature testing

### Integration Tests
- End-to-end settings workflows
- RBAC enforcement verification
- Privacy mode integration
- Webhook delivery testing

### Security Tests
- Authentication and authorization
- Session management security
- API key security
- Audit logging verification

## Deployment Considerations

### Database Migration
- Migration script for new tables
- Index optimization for performance
- Foreign key constraints
- Data integrity checks

### Environment Configuration
- Feature flag management
- Privacy mode defaults
- CMK configuration
- Monitoring setup

### Monitoring and Alerting
- Settings change monitoring
- Security event alerting
- Performance metrics
- Error tracking and reporting

## Future Enhancements

### Advanced Features
- Bulk settings import/export
- Settings templates and presets
- Advanced RBAC with custom roles
- Multi-workspace management

### Integration Expansions
- Additional OAuth providers
- Advanced webhook features
- Enhanced diagnostics
- Automated compliance reporting

### User Experience
- Settings search and filtering
- Settings comparison tools
- Guided setup wizards
- Mobile app support

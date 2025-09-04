# System Builder Hub - Enhanced Edition

## 🚀 Overview

The System Builder Hub has been completely refactored and enhanced with production-grade infrastructure, comprehensive monitoring, and **Priority 30: Real-Time Multi-Device Preview Engine**. This enhanced version includes enterprise-level features for scalability, security, and operational excellence.

## 🎯 Key Enhancements

### ✅ Production-Grade Infrastructure
- **Database Lifecycle & Migrations**: Alembic integration with startup validation
- **Idempotency System**: Request deduplication with 24h caching
- **Distributed Trace Context**: W3C TraceContext implementation
- **Cost & Compliance Hooks**: LLM cost tracking with PII redaction
- **Pagination & Ordering**: Standardized pagination with deterministic ordering
- **Streaming/Realtime**: Server-Sent Events (SSE) for live data
- **Feature Flags**: Environment and database-backed feature toggles
- **API Versioning**: Deprecation warnings and compatibility middleware
- **CLI Operations**: Click-based management commands
- **Export/Backup Hooks**: Automatic backup triggers with manifests

### 🎯 Priority 30: Real-Time Multi-Device Preview Engine
- **Device Presets**: iPhone, iPad, Pixel, Laptop, Desktop, Ultrawide
- **Interactive Toolbar**: Custom dimensions, orientation, zoom, network conditions
- **Hot Reload**: Live code changes with file monitoring
- **Visual QA**: Screenshot capture and comparison
- **Breakpoint Overlay**: CSS breakpoint visualization
- **Network Throttling**: 3G/4G/offline simulation
- **Accessibility**: Theme toggles and reduced motion support

## 🏗️ Architecture

### Core Components

```
src/
├── app.py                          # Main Flask application
├── config.py                       # Environment-driven configuration
├── database.py                     # Database management & migrations
├── background.py                   # Background task orchestration
├── metrics.py                      # Prometheus metrics collection
├── security.py                     # Security headers & validation
├── openapi.py                      # OpenAPI/Swagger documentation
├── idempotency.py                  # Request deduplication
├── trace.py                        # Distributed tracing
├── costs.py                        # Cost accounting & compliance
├── streaming.py                    # SSE streaming system
├── feature_flags.py                # Feature toggle management
├── api_versioning.py               # API versioning & deprecation
├── backups.py                      # Backup & restore system
├── preview_engine.py               # Priority 30: Preview Engine
├── cli.py                          # CLI operations
├── utils/
│   └── pagination.py               # Pagination utilities
├── templates/
│   └── preview_ui.html             # Preview UI interface
├── db_migrations/                  # Alembic migrations
│   ├── env.py
│   ├── alembic.ini
│   ├── script.py.mako
│   └── versions/
│       └── 0001_initial.py
└── blueprints/                     # Modular blueprints
    ├── core.py                     # P1-P10: Core Infrastructure
    ├── advanced.py                 # P11-P20: Advanced Features
    └── intelligence.py             # P21-P29: Intelligence & Diagnostics
```

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
cd system-builder-hub/backend

# Install dependencies
pip install -r requirements.txt

# Initialize database
python cli.py init-db

# Seed initial data
python cli.py seed

# Start the server
python cli.py run

## 🧪 Testing

We use pytest for all automated testing with comprehensive coverage of the marketplace templates and builds API.

### Running Tests Locally

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=term-missing

# Run specific test files
pytest tests/test_builds_api.py
pytest tests/test_crm_flagship_build.py
```

### Test Coverage

Our test suite covers:

- **Builds API Core**: 11 tests (CRUD operations, error handling)
- **CRM Flagship Template**: 9 tests (end-to-end build workflow)
- **Blank Canvas Template**: 9 tests (starter template validation)
- **Task Manager Template**: 9 tests (productivity template testing)

**Total: 38 tests passing in ~0.41s**

Each template test includes:
- Build creation and validation
- Auto-progression simulation
- Logs endpoint testing
- Tasks integration (CRUD operations)
- Error handling (400/404 cases)
- JSON consistency validation

### Continuous Integration

Tests run automatically in GitHub Actions on every push and pull request:
- Python 3.11 environment
- Coverage reporting with Codecov integration
- Fast execution (< 1 second)
- Comprehensive error reporting
```

### 2. Environment Configuration

Create a `.env` file:

```env
# Flask Configuration
FLASK_ENV=development
SECRET_KEY=your-secret-key-here
FLASK_DEBUG=true

# Database Configuration
DATABASE_URL=sqlite:///system_builder_hub.db
ALEMBIC_CHECK_ON_STARTUP=false
STRICT_DB_STARTUP=false

# Security Configuration
SECURITY_HEADERS_ENABLED=true
SECURITY_CSP_ENABLED=true
SECURITY_CSRF_ENABLED=true

# Feature Flags
ENABLE_IDEMPOTENCY=true
ENABLE_TRACE_CONTEXT=true
ENABLE_COST_ACCOUNTING=true
ENABLE_SSE=true
ENABLE_FEATURE_FLAGS=true
ENABLE_DEPRECATION_WARNINGS=false

# Preview Engine (Priority 30)
PREVIEW_TTL_MINUTES=60
PREVIEW_MAX_CONCURRENCY=10
PREVIEW_CPU_LIMIT=0.5
PREVIEW_MEM_LIMIT=512m
SNAPSHOT_RATE_PER_MINUTE=10

# CORS Configuration
CORS_ORIGINS=http://localhost:3000,http://localhost:5001
```

### 3. CLI Operations

```bash
# Run the server
python cli.py run --host 0.0.0.0 --port 5001

# Database operations
python cli.py init-db --force
python cli.py upgrade-db

# Feature flag management
python cli.py feature-flag --flag preview_engine --enable
python cli.py list-features

# System status
python cli.py status
python cli.py smoke-test

# Backup operations
python cli.py backup --output backup.json
python cli.py restore --backup-file backup.json
```

## 🎯 Priority 30: Preview Engine

### Features

#### Device Presets
- **iPhone**: 375×812, mobile, touch-enabled
- **iPad**: 768×1024, tablet, touch-enabled
- **Pixel**: 411×823, Android mobile
- **Laptop**: 1366×768, desktop
- **Desktop**: 1920×1080, full desktop
- **Ultrawide**: 2560×1080, wide desktop

#### Interactive Controls
- **Custom Dimensions**: Set any width/height
- **Orientation**: Portrait/landscape toggle
- **Zoom**: 50% to 150% scaling
- **Network Conditions**: Offline/3G/4G simulation
- **Theme**: Light/dark mode
- **Accessibility**: Reduced motion support

#### Visual QA
- **Screenshot Capture**: High-quality screenshots
- **Visual Comparison**: Diff detection between versions
- **Breakpoint Overlay**: CSS breakpoint visualization
- **Live Logs**: Real-time preview environment logs

### API Endpoints

```bash
# Create preview session
POST /api/preview/system
{
  "system_id": "my-system",
  "device_preset": "desktop",
  "ttl_minutes": 60
}

# Get preview status
GET /api/preview/status/{preview_id}

# Update device configuration
POST /api/preview/device/{preview_id}
{
  "width": 1920,
  "height": 1080,
  "orientation": "landscape"
}

# Take screenshot
POST /api/preview/screenshot
{
  "session_id": "preview_123",
  "route": "/"
}

# Compare screenshots
POST /api/preview/compare
{
  "baseline_session": "preview_123",
  "compare_session": "preview_456",
  "route": "/"
}

# Stream logs
GET /api/preview/logs/{preview_id}/app

# Stop preview
DELETE /api/preview/{preview_id}
```

### Preview UI

Access the interactive preview interface at:
```
http://localhost:5001/preview
```

## 📊 Monitoring & Observability

### Metrics Endpoints

```bash
# Prometheus metrics
GET /metrics

# JSON metrics summary
GET /api/v1/metrics/summary

# Cost accounting
GET /api/v1/costs/summary

# Compliance events
GET /api/v1/compliance/summary
```

### Health Checks

```bash
# Basic health
GET /health

# Kubernetes probes
GET /healthz
GET /readiness
GET /liveness

# Version info
GET /version
```

### Background Tasks

```bash
# Task status
GET /api/v1/background/tasks

# Start task
POST /api/v1/background/tasks/{task_name}/start

# Stop task
POST /api/v1/background/tasks/{task_name}/stop
```

## 🔒 Security Features

### Security Headers
- **Content Security Policy (CSP)**: XSS protection
- **HTTP Strict Transport Security (HSTS)**: HTTPS enforcement
- **X-Content-Type-Options**: MIME type sniffing prevention
- **X-Frame-Options**: Clickjacking protection
- **X-XSS-Protection**: Legacy XSS protection
- **Referrer-Policy**: Referrer information control
- **Permissions-Policy**: Feature policy enforcement

### Request Validation
- **Size Limits**: Configurable request size limits
- **MIME Validation**: Content-type validation
- **Input Sanitization**: SQL injection and XSS prevention
- **CSRF Protection**: Cross-site request forgery protection

### Authentication & Authorization
- **JWT Validation**: Bearer token authentication
- **Role-Based Access Control (RBAC)**: User role enforcement
- **Rate Limiting**: Request rate limiting per user

## 🚩 Feature Flags

### Management

```bash
# List all flags
GET /api/v1/feature-flags

# Toggle flag
POST /api/v1/feature-flags/{flag_name}
{
  "enabled": true
}
```

### Available Flags
- `preview_engine`: Priority 30 Preview Engine
- `blackbox_inspector`: Blackbox Inspector
- `agent_negotiation`: Agent Negotiation
- `redteam_simulator`: Red Team Simulator
- `advanced_analytics`: Advanced Analytics
- `cost_accounting`: Cost Accounting
- `compliance_engine`: Compliance Engine
- `multi_tenant`: Multi-tenancy
- `real_time_collaboration`: Real-time Collaboration
- `voice_processing`: Voice Processing
- `visual_processing`: Visual Processing
- `self_healing`: Self-healing Systems
- `federated_learning`: Federated Learning
- `edge_deployment`: Edge Deployment
- `quantum_optimization`: Quantum Optimization

## 🔄 Idempotency

### Usage

Include `Idempotency-Key` header in mutating requests:

```bash
POST /api/v1/feature-flags/preview_engine
Idempotency-Key: unique-request-id-123
Content-Type: application/json
{
  "enabled": true
}
```

### Features
- **24-hour caching**: Responses cached for 24 hours
- **Database fallback**: Persistent storage for reliability
- **Automatic cleanup**: Expired keys automatically removed
- **Replay detection**: Returns cached response with `Idempotent-Replay` header

## 📋 API Versioning

### Version Information

```bash
GET /api/v1/api-versioning/info
```

### Deprecation Warnings

Enable deprecation warnings:
```env
ENABLE_DEPRECATION_WARNINGS=true
```

Deprecated endpoints will include:
- `Deprecation: true` header
- `Sunset: 2024-12-31T23:59:59Z` header
- `Link: <new-endpoint>; rel="successor-version"` header
- `Warning: 299 - "This endpoint is deprecated"` header

## 💾 Backup & Restore

### Automatic Backups

Backups are automatically triggered on critical writes:
- Project creation/updates
- System creation/updates
- Database schema changes

### Manual Backups

```bash
# Trigger backup
POST /api/v1/backup/trigger
{
  "type": "full"  # or "database", "project", "system"
}

# List backups
GET /api/v1/backup/manifests

# Restore backup
POST /api/v1/backup/{backup_id}/restore
```

### Backup Types
- **Full**: Complete system backup (database + config + source)
- **Database**: Database-only backup
- **Project**: Individual project backup
- **System**: Individual system backup

- [API Reference](docs/API_REFERENCE.md) - Complete API documentation
- [Deployment Guide](docs/DEPLOY.md) - Production deployment instructions
- [AWS EB Deployment](docs/DEPLOY_AWS_EB.md) - AWS Elastic Beanstalk deployment
- [Security Guide](docs/SECURITY.md) - Security features and compliance

### 🔗 Integrations  Extensions
- [Integrations Guide](docs/INTEGRATIONS.md) - Third-party integrations
- [AI Copilot Guide](docs/AI_COPILOT_GUIDE.md) - AI features and capabilities
- [Extensibility Guide](docs/EXTENSIBILITY.md) - Plugin system and customization

### 🛠️ Operations  Support
- [Troubleshooting](docs/TROUBLESHOOTING.md) - Common issues and solutions
- [Release Notes](docs/RELEASE_NOTES.md) - Version history and updates
- [Marketplace Listing](docs/MARKETPLACE_LISTING.md) - Template information and features
## 📚 Documentation

### 🚀 Getting Started
- [Quick Start Guide](docs/QUICKSTART.md) - Get up and running in 10 minutes
- [User Guide](docs/USER_GUIDE.md) - Complete user documentation
- [Admin Guide](docs/ADMIN_GUIDE.md) - Administrative functions and settings

### 🔧 Technical Documentation
- [API Reference](docs/API_REFERENCE.md) - Complete API documentation
- [Deployment Guide](docs/DEPLOY.md) - Production deployment instructions
- [AWS EB Deployment](docs/DEPLOY_AWS_EB.md) - AWS Elastic Beanstalk deployment
- [Security Guide](docs/SECURITY.md) - Security features and compliance

### 🔗 Integrations ### OpenAPI/Swagger Extensions
- [Integrations Guide](docs/INTEGRATIONS.md) - Third-party integrations
- [AI Copilot Guide](docs/AI_COPILOT_GUIDE.md) - AI features and capabilities
- [Extensibility Guide](docs/EXTENSIBILITY.md) - Plugin system and customization

### 🛠️ Operations ### OpenAPI/Swagger Support
- [Troubleshooting](docs/TROUBLESHOOTING.md) - Common issues and solutions
- [Release Notes](docs/RELEASE_NOTES.md) - Version history and updates
- [Marketplace Listing](docs/MARKETPLACE_LISTING.md) - Template information and features
## 📚 Documentation

### 🚀 Getting Started
- [Quick Start Guide](docs/QUICKSTART.md) - Get up and running in 10 minutes
- [User Guide](docs/USER_GUIDE.md) - Complete user documentation
- [Admin Guide](docs/ADMIN_GUIDE.md) - Administrative functions and settings

### 🔧 Technical Documentation
- [API Reference](docs/API_REFERENCE.md) - Complete API documentation
- [Deployment Guide](docs/DEPLOY.md) - Production deployment instructions
- [AWS EB Deployment](docs/DEPLOY_AWS_EB.md) - AWS Elastic Beanstalk deployment
- [Security Guide](docs/SECURITY.md) - Security features and compliance

### 🔗 Integrations  Extensions
- [Integrations Guide](docs/INTEGRATIONS.md) - Third-party integrations
- [AI Copilot Guide](docs/AI_COPILOT_GUIDE.md) - AI features and capabilities
- [Extensibility Guide](docs/EXTENSIBILITY.md) - Plugin system and customization

### 🛠️ Operations  Support
- [Troubleshooting](docs/TROUBLESHOOTING.md) - Common issues and solutions
- [Release Notes](docs/RELEASE_NOTES.md) - Version history and updates
- [Marketplace Listing](docs/MARKETPLACE_LISTING.md) - Template information and features
## 📚 Documentation

### 🚀 Getting Started
- [Quick Start Guide](docs/QUICKSTART.md) - Get up and running in 10 minutes
- [User Guide](docs/USER_GUIDE.md) - Complete user documentation
- [Admin Guide](docs/ADMIN_GUIDE.md) - Administrative functions and settings

### 🔧 Technical Documentation
- [API Reference](docs/API_REFERENCE.md) - Complete API documentation
- [Deployment Guide](docs/DEPLOY.md) - Production deployment instructions
- [AWS EB Deployment](docs/DEPLOY_AWS_EB.md) - AWS Elastic Beanstalk deployment
- [Security Guide](docs/SECURITY.md) - Security features and compliance

### 🔗 Integrations ```bash Extensions
- [Integrations Guide](docs/INTEGRATIONS.md) - Third-party integrations
- [AI Copilot Guide](docs/AI_COPILOT_GUIDE.md) - AI features and capabilities
- [Extensibility Guide](docs/EXTENSIBILITY.md) - Plugin system and customization

### 🛠️ Operations ```bash Support
- [Troubleshooting](docs/TROUBLESHOOTING.md) - Common issues and solutions
- [Release Notes](docs/RELEASE_NOTES.md) - Version history and updates
- [Marketplace Listing](docs/MARKETPLACE_LISTING.md) - Template information and features
## 📚 Documentation

### 🚀 Getting Started
- [Quick Start Guide](docs/QUICKSTART.md) - Get up and running in 10 minutes
- [User Guide](docs/USER_GUIDE.md) - Complete user documentation
- [Admin Guide](docs/ADMIN_GUIDE.md) - Administrative functions and settings

### 🔧 Technical Documentation
- [API Reference](docs/API_REFERENCE.md) - Complete API documentation
- [Deployment Guide](docs/DEPLOY.md) - Production deployment instructions
- [AWS EB Deployment](docs/DEPLOY_AWS_EB.md) - AWS Elastic Beanstalk deployment
- [Security Guide](docs/SECURITY.md) - Security features and compliance

### 🔗 Integrations # OpenAPI specification Extensions
- [Integrations Guide](docs/INTEGRATIONS.md) - Third-party integrations
- [AI Copilot Guide](docs/AI_COPILOT_GUIDE.md) - AI features and capabilities
- [Extensibility Guide](docs/EXTENSIBILITY.md) - Plugin system and customization

### 🛠️ Operations # OpenAPI specification Support
- [Troubleshooting](docs/TROUBLESHOOTING.md) - Common issues and solutions
- [Release Notes](docs/RELEASE_NOTES.md) - Version history and updates
- [Marketplace Listing](docs/MARKETPLACE_LISTING.md) - Template information and features
## 📚 Documentation

### 🚀 Getting Started
- [Quick Start Guide](docs/QUICKSTART.md) - Get up and running in 10 minutes
- [User Guide](docs/USER_GUIDE.md) - Complete user documentation
- [Admin Guide](docs/ADMIN_GUIDE.md) - Administrative functions and settings

### 🔧 Technical Documentation
- [API Reference](docs/API_REFERENCE.md) - Complete API documentation
- [Deployment Guide](docs/DEPLOY.md) - Production deployment instructions
- [AWS EB Deployment](docs/DEPLOY_AWS_EB.md) - AWS Elastic Beanstalk deployment
- [Security Guide](docs/SECURITY.md) - Security features and compliance

### 🔗 Integrations GET /openapi.json Extensions
- [Integrations Guide](docs/INTEGRATIONS.md) - Third-party integrations
- [AI Copilot Guide](docs/AI_COPILOT_GUIDE.md) - AI features and capabilities
- [Extensibility Guide](docs/EXTENSIBILITY.md) - Plugin system and customization

### 🛠️ Operations GET /openapi.json Support
- [Troubleshooting](docs/TROUBLESHOOTING.md) - Common issues and solutions
- [Release Notes](docs/RELEASE_NOTES.md) - Version history and updates
- [Marketplace Listing](docs/MARKETPLACE_LISTING.md) - Template information and features
## 📚 Documentation

### 🚀 Getting Started
- [Quick Start Guide](docs/QUICKSTART.md) - Get up and running in 10 minutes
- [User Guide](docs/USER_GUIDE.md) - Complete user documentation
- [Admin Guide](docs/ADMIN_GUIDE.md) - Administrative functions and settings

### 🔧 Technical Documentation
- [API Reference](docs/API_REFERENCE.md) - Complete API documentation
- [Deployment Guide](docs/DEPLOY.md) - Production deployment instructions
- [AWS EB Deployment](docs/DEPLOY_AWS_EB.md) - AWS Elastic Beanstalk deployment
- [Security Guide](docs/SECURITY.md) - Security features and compliance

### 🔗 Integrations  Extensions
- [Integrations Guide](docs/INTEGRATIONS.md) - Third-party integrations
- [AI Copilot Guide](docs/AI_COPILOT_GUIDE.md) - AI features and capabilities
- [Extensibility Guide](docs/EXTENSIBILITY.md) - Plugin system and customization

### 🛠️ Operations  Support
- [Troubleshooting](docs/TROUBLESHOOTING.md) - Common issues and solutions
- [Release Notes](docs/RELEASE_NOTES.md) - Version history and updates
- [Marketplace Listing](docs/MARKETPLACE_LISTING.md) - Template information and features
## 📚 Documentation

### 🚀 Getting Started
- [Quick Start Guide](docs/QUICKSTART.md) - Get up and running in 10 minutes
- [User Guide](docs/USER_GUIDE.md) - Complete user documentation
- [Admin Guide](docs/ADMIN_GUIDE.md) - Administrative functions and settings

### 🔧 Technical Documentation
- [API Reference](docs/API_REFERENCE.md) - Complete API documentation
- [Deployment Guide](docs/DEPLOY.md) - Production deployment instructions
- [AWS EB Deployment](docs/DEPLOY_AWS_EB.md) - AWS Elastic Beanstalk deployment
- [Security Guide](docs/SECURITY.md) - Security features and compliance

### 🔗 Integrations # Swagger UI Extensions
- [Integrations Guide](docs/INTEGRATIONS.md) - Third-party integrations
- [AI Copilot Guide](docs/AI_COPILOT_GUIDE.md) - AI features and capabilities
- [Extensibility Guide](docs/EXTENSIBILITY.md) - Plugin system and customization

### 🛠️ Operations # Swagger UI Support
- [Troubleshooting](docs/TROUBLESHOOTING.md) - Common issues and solutions
- [Release Notes](docs/RELEASE_NOTES.md) - Version history and updates
- [Marketplace Listing](docs/MARKETPLACE_LISTING.md) - Template information and features
## 📚 Documentation

### 🚀 Getting Started
- [Quick Start Guide](docs/QUICKSTART.md) - Get up and running in 10 minutes
- [User Guide](docs/USER_GUIDE.md) - Complete user documentation
- [Admin Guide](docs/ADMIN_GUIDE.md) - Administrative functions and settings

### 🔧 Technical Documentation
- [API Reference](docs/API_REFERENCE.md) - Complete API documentation
- [Deployment Guide](docs/DEPLOY.md) - Production deployment instructions
- [AWS EB Deployment](docs/DEPLOY_AWS_EB.md) - AWS Elastic Beanstalk deployment
- [Security Guide](docs/SECURITY.md) - Security features and compliance

### 🔗 Integrations GET /docs Extensions
- [Integrations Guide](docs/INTEGRATIONS.md) - Third-party integrations
- [AI Copilot Guide](docs/AI_COPILOT_GUIDE.md) - AI features and capabilities
- [Extensibility Guide](docs/EXTENSIBILITY.md) - Plugin system and customization

### 🛠️ Operations GET /docs Support
- [Troubleshooting](docs/TROUBLESHOOTING.md) - Common issues and solutions
- [Release Notes](docs/RELEASE_NOTES.md) - Version history and updates
- [Marketplace Listing](docs/MARKETPLACE_LISTING.md) - Template information and features
## 📚 Documentation

### 🚀 Getting Started
- [Quick Start Guide](docs/QUICKSTART.md) - Get up and running in 10 minutes
- [User Guide](docs/USER_GUIDE.md) - Complete user documentation
- [Admin Guide](docs/ADMIN_GUIDE.md) - Administrative functions and settings

### 🔧 Technical Documentation
- [API Reference](docs/API_REFERENCE.md) - Complete API documentation
- [Deployment Guide](docs/DEPLOY.md) - Production deployment instructions
- [AWS EB Deployment](docs/DEPLOY_AWS_EB.md) - AWS Elastic Beanstalk deployment
- [Security Guide](docs/SECURITY.md) - Security features and compliance

### 🔗 Integrations ``` Extensions
- [Integrations Guide](docs/INTEGRATIONS.md) - Third-party integrations
- [AI Copilot Guide](docs/AI_COPILOT_GUIDE.md) - AI features and capabilities
- [Extensibility Guide](docs/EXTENSIBILITY.md) - Plugin system and customization

### 🛠️ Operations ``` Support
- [Troubleshooting](docs/TROUBLESHOOTING.md) - Common issues and solutions
- [Release Notes](docs/RELEASE_NOTES.md) - Version history and updates
- [Marketplace Listing](docs/MARKETPLACE_LISTING.md) - Template information and features
## 📚 Documentation

### 🚀 Getting Started
- [Quick Start Guide](docs/QUICKSTART.md) - Get up and running in 10 minutes
- [User Guide](docs/USER_GUIDE.md) - Complete user documentation
- [Admin Guide](docs/ADMIN_GUIDE.md) - Administrative functions and settings

### 🔧 Technical Documentation
- [API Reference](docs/API_REFERENCE.md) - Complete API documentation
- [Deployment Guide](docs/DEPLOY.md) - Production deployment instructions
- [AWS EB Deployment](docs/DEPLOY_AWS_EB.md) - AWS Elastic Beanstalk deployment
- [Security Guide](docs/SECURITY.md) - Security features and compliance

### 🔗 Integrations  Extensions
- [Integrations Guide](docs/INTEGRATIONS.md) - Third-party integrations
- [AI Copilot Guide](docs/AI_COPILOT_GUIDE.md) - AI features and capabilities
- [Extensibility Guide](docs/EXTENSIBILITY.md) - Plugin system and customization

### 🛠️ Operations  Support
- [Troubleshooting](docs/TROUBLESHOOTING.md) - Common issues and solutions
- [Release Notes](docs/RELEASE_NOTES.md) - Version history and updates
- [Marketplace Listing](docs/MARKETPLACE_LISTING.md) - Template information and features
## 📚 Documentation

### 🚀 Getting Started
- [Quick Start Guide](docs/QUICKSTART.md) - Get up and running in 10 minutes
- [User Guide](docs/USER_GUIDE.md) - Complete user documentation
- [Admin Guide](docs/ADMIN_GUIDE.md) - Administrative functions and settings

### 🔧 Technical Documentation
- [API Reference](docs/API_REFERENCE.md) - Complete API documentation
- [Deployment Guide](docs/DEPLOY.md) - Production deployment instructions
- [AWS EB Deployment](docs/DEPLOY_AWS_EB.md) - AWS Elastic Beanstalk deployment
- [Security Guide](docs/SECURITY.md) - Security features and compliance

### 🔗 Integrations ### Route Dump Extensions
- [Integrations Guide](docs/INTEGRATIONS.md) - Third-party integrations
- [AI Copilot Guide](docs/AI_COPILOT_GUIDE.md) - AI features and capabilities
- [Extensibility Guide](docs/EXTENSIBILITY.md) - Plugin system and customization

### 🛠️ Operations ### Route Dump Support
- [Troubleshooting](docs/TROUBLESHOOTING.md) - Common issues and solutions
- [Release Notes](docs/RELEASE_NOTES.md) - Version history and updates
- [Marketplace Listing](docs/MARKETPLACE_LISTING.md) - Template information and features
## 📚 Documentation

### 🚀 Getting Started
- [Quick Start Guide](docs/QUICKSTART.md) - Get up and running in 10 minutes
- [User Guide](docs/USER_GUIDE.md) - Complete user documentation
- [Admin Guide](docs/ADMIN_GUIDE.md) - Administrative functions and settings

### 🔧 Technical Documentation
- [API Reference](docs/API_REFERENCE.md) - Complete API documentation
- [Deployment Guide](docs/DEPLOY.md) - Production deployment instructions
- [AWS EB Deployment](docs/DEPLOY_AWS_EB.md) - AWS Elastic Beanstalk deployment
- [Security Guide](docs/SECURITY.md) - Security features and compliance

### 🔗 Integrations  Extensions
- [Integrations Guide](docs/INTEGRATIONS.md) - Third-party integrations
- [AI Copilot Guide](docs/AI_COPILOT_GUIDE.md) - AI features and capabilities
- [Extensibility Guide](docs/EXTENSIBILITY.md) - Plugin system and customization

### 🛠️ Operations  Support
- [Troubleshooting](docs/TROUBLESHOOTING.md) - Common issues and solutions
- [Release Notes](docs/RELEASE_NOTES.md) - Version history and updates
- [Marketplace Listing](docs/MARKETPLACE_LISTING.md) - Template information and features
## 📚 Documentation

### 🚀 Getting Started
- [Quick Start Guide](docs/QUICKSTART.md) - Get up and running in 10 minutes
- [User Guide](docs/USER_GUIDE.md) - Complete user documentation
- [Admin Guide](docs/ADMIN_GUIDE.md) - Administrative functions and settings

### 🔧 Technical Documentation
- [API Reference](docs/API_REFERENCE.md) - Complete API documentation
- [Deployment Guide](docs/DEPLOY.md) - Production deployment instructions
- [AWS EB Deployment](docs/DEPLOY_AWS_EB.md) - AWS Elastic Beanstalk deployment
- [Security Guide](docs/SECURITY.md) - Security features and compliance

### 🔗 Integrations ```bash Extensions
- [Integrations Guide](docs/INTEGRATIONS.md) - Third-party integrations
- [AI Copilot Guide](docs/AI_COPILOT_GUIDE.md) - AI features and capabilities
- [Extensibility Guide](docs/EXTENSIBILITY.md) - Plugin system and customization

### 🛠️ Operations ```bash Support
- [Troubleshooting](docs/TROUBLESHOOTING.md) - Common issues and solutions
- [Release Notes](docs/RELEASE_NOTES.md) - Version history and updates
- [Marketplace Listing](docs/MARKETPLACE_LISTING.md) - Template information and features
## 📚 Documentation

### 🚀 Getting Started
- [Quick Start Guide](docs/QUICKSTART.md) - Get up and running in 10 minutes
- [User Guide](docs/USER_GUIDE.md) - Complete user documentation
- [Admin Guide](docs/ADMIN_GUIDE.md) - Administrative functions and settings

### 🔧 Technical Documentation
- [API Reference](docs/API_REFERENCE.md) - Complete API documentation
- [Deployment Guide](docs/DEPLOY.md) - Production deployment instructions
- [AWS EB Deployment](docs/DEPLOY_AWS_EB.md) - AWS Elastic Beanstalk deployment
- [Security Guide](docs/SECURITY.md) - Security features and compliance

### 🔗 Integrations # List all routes Extensions
- [Integrations Guide](docs/INTEGRATIONS.md) - Third-party integrations
- [AI Copilot Guide](docs/AI_COPILOT_GUIDE.md) - AI features and capabilities
- [Extensibility Guide](docs/EXTENSIBILITY.md) - Plugin system and customization

### 🛠️ Operations # List all routes Support
- [Troubleshooting](docs/TROUBLESHOOTING.md) - Common issues and solutions
- [Release Notes](docs/RELEASE_NOTES.md) - Version history and updates
- [Marketplace Listing](docs/MARKETPLACE_LISTING.md) - Template information and features
## 📚 Documentation

### 🚀 Getting Started
- [Quick Start Guide](docs/QUICKSTART.md) - Get up and running in 10 minutes
- [User Guide](docs/USER_GUIDE.md) - Complete user documentation
- [Admin Guide](docs/ADMIN_GUIDE.md) - Administrative functions and settings

### 🔧 Technical Documentation
- [API Reference](docs/API_REFERENCE.md) - Complete API documentation
- [Deployment Guide](docs/DEPLOY.md) - Production deployment instructions
- [AWS EB Deployment](docs/DEPLOY_AWS_EB.md) - AWS Elastic Beanstalk deployment
- [Security Guide](docs/SECURITY.md) - Security features and compliance

### 🔗 Integrations GET /__routes Extensions
- [Integrations Guide](docs/INTEGRATIONS.md) - Third-party integrations
- [AI Copilot Guide](docs/AI_COPILOT_GUIDE.md) - AI features and capabilities
- [Extensibility Guide](docs/EXTENSIBILITY.md) - Plugin system and customization

### 🛠️ Operations GET /__routes Support
- [Troubleshooting](docs/TROUBLESHOOTING.md) - Common issues and solutions
- [Release Notes](docs/RELEASE_NOTES.md) - Version history and updates
- [Marketplace Listing](docs/MARKETPLACE_LISTING.md) - Template information and features
## 📚 Documentation

### 🚀 Getting Started
- [Quick Start Guide](docs/QUICKSTART.md) - Get up and running in 10 minutes
- [User Guide](docs/USER_GUIDE.md) - Complete user documentation
- [Admin Guide](docs/ADMIN_GUIDE.md) - Administrative functions and settings

### 🔧 Technical Documentation
- [API Reference](docs/API_REFERENCE.md) - Complete API documentation
- [Deployment Guide](docs/DEPLOY.md) - Production deployment instructions
- [AWS EB Deployment](docs/DEPLOY_AWS_EB.md) - AWS Elastic Beanstalk deployment
- [Security Guide](docs/SECURITY.md) - Security features and compliance

### 🔗 Integrations ``` Extensions
- [Integrations Guide](docs/INTEGRATIONS.md) - Third-party integrations
- [AI Copilot Guide](docs/AI_COPILOT_GUIDE.md) - AI features and capabilities
- [Extensibility Guide](docs/EXTENSIBILITY.md) - Plugin system and customization

### 🛠️ Operations ``` Support
- [Troubleshooting](docs/TROUBLESHOOTING.md) - Common issues and solutions
- [Release Notes](docs/RELEASE_NOTES.md) - Version history and updates
- [Marketplace Listing](docs/MARKETPLACE_LISTING.md) - Template information and features
## 📚 Documentation

### 🚀 Getting Started
- [Quick Start Guide](docs/QUICKSTART.md) - Get up and running in 10 minutes
- [User Guide](docs/USER_GUIDE.md) - Complete user documentation
- [Admin Guide](docs/ADMIN_GUIDE.md) - Administrative functions and settings

### 🔧 Technical Documentation
- [API Reference](docs/API_REFERENCE.md) - Complete API documentation
- [Deployment Guide](docs/DEPLOY.md) - Production deployment instructions
- [AWS EB Deployment](docs/DEPLOY_AWS_EB.md) - AWS Elastic Beanstalk deployment
- [Security Guide](docs/SECURITY.md) - Security features and compliance

### 🔗 Integrations  Extensions
- [Integrations Guide](docs/INTEGRATIONS.md) - Third-party integrations
- [AI Copilot Guide](docs/AI_COPILOT_GUIDE.md) - AI features and capabilities
- [Extensibility Guide](docs/EXTENSIBILITY.md) - Plugin system and customization

### 🛠️ Operations  Support
- [Troubleshooting](docs/TROUBLESHOOTING.md) - Common issues and solutions
- [Release Notes](docs/RELEASE_NOTES.md) - Version history and updates
- [Marketplace Listing](docs/MARKETPLACE_LISTING.md) - Template information and features
## 📚 Documentation

### 🚀 Getting Started
- [Quick Start Guide](docs/QUICKSTART.md) - Get up and running in 10 minutes
- [User Guide](docs/USER_GUIDE.md) - Complete user documentation
- [Admin Guide](docs/ADMIN_GUIDE.md) - Administrative functions and settings

### 🔧 Technical Documentation
- [API Reference](docs/API_REFERENCE.md) - Complete API documentation
- [Deployment Guide](docs/DEPLOY.md) - Production deployment instructions
- [AWS EB Deployment](docs/DEPLOY_AWS_EB.md) - AWS Elastic Beanstalk deployment
- [Security Guide](docs/SECURITY.md) - Security features and compliance

### 🔗 Integrations ## 🧪 Testing Extensions
- [Integrations Guide](docs/INTEGRATIONS.md) - Third-party integrations
- [AI Copilot Guide](docs/AI_COPILOT_GUIDE.md) - AI features and capabilities
- [Extensibility Guide](docs/EXTENSIBILITY.md) - Plugin system and customization

### 🛠️ Operations ## 🧪 Testing Support
- [Troubleshooting](docs/TROUBLESHOOTING.md) - Common issues and solutions
- [Release Notes](docs/RELEASE_NOTES.md) - Version history and updates
- [Marketplace Listing](docs/MARKETPLACE_LISTING.md) - Template information and features

### Run Test Suite

```bash
# Run enhanced features test
python test_enhanced_features.py

# Run architecture test
python test_architecture.py
```

### Test Coverage

The enhanced test suite covers:
- ✅ Database initialization and migrations
- ✅ Cost accounting and compliance
- ✅ Feature flags system
- ✅ API versioning
- ✅ Backup and restore
- ✅ Preview Engine (Priority 30)
- ✅ Security features
- ✅ Metrics and monitoring
- ✅ Background tasks
- ✅ OpenAPI documentation
- ✅ Idempotency
- ✅ Pagination

## 🔧 Configuration Reference

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FLASK_ENV` | `development` | Flask environment |
| `SECRET_KEY` | `dev-secret-key` | Flask secret key |
| `DATABASE_URL` | `sqlite:///system_builder_hub.db` | Database connection |
| `ALEMBIC_CHECK_ON_STARTUP` | `false` | Check migrations on startup |
| `STRICT_DB_STARTUP` | `false` | Fail startup if DB issues |
| `ENABLE_IDEMPOTENCY` | `true` | Enable idempotency system |
| `ENABLE_TRACE_CONTEXT` | `true` | Enable distributed tracing |
| `ENABLE_COST_ACCOUNTING` | `true` | Enable cost tracking |
| `ENABLE_SSE` | `true` | Enable Server-Sent Events |
| `ENABLE_FEATURE_FLAGS` | `true` | Enable feature flags |
| `ENABLE_DEPRECATION_WARNINGS` | `false` | Enable API deprecation warnings |
| `PREVIEW_TTL_MINUTES` | `60` | Preview session TTL |
| `PREVIEW_MAX_CONCURRENCY` | `10` | Max concurrent previews |
| `SNAPSHOT_RATE_PER_MINUTE` | `10` | Screenshot rate limit |

## 🚀 Deployment

### Production Checklist

- [ ] Set `FLASK_ENV=production`
- [ ] Configure `SECRET_KEY`
- [ ] Set up production database
- [ ] Enable `ALEMBIC_CHECK_ON_STARTUP`
- [ ] Enable `STRICT_DB_STARTUP`
- [ ] Configure CORS origins
- [ ] Set up monitoring and alerting
- [ ] Configure backup storage
- [ ] Set up SSL/TLS certificates
- [ ] Configure rate limiting
- [ ] Set up log aggregation

### Docker Deployment

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN python cli.py init-db

EXPOSE 5001
CMD ["python", "cli.py", "run", "--host", "0.0.0.0", "--port", "5001"]
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new features
5. Run the test suite
6. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue on GitHub
- Check the documentation at `/docs`
- Review the OpenAPI specification at `/openapi.json`

---

**System Builder Hub Enhanced Edition** - Production-ready infrastructure with Priority 30: Real-Time Multi-Device Preview Engine 🚀

## 📚 Documentation

### 🚀 Getting Started
- [Quick Start Guide](docs/QUICKSTART.md) - Get up and running in 10 minutes
- [User Guide](docs/USER_GUIDE.md) - Complete user documentation
- [Admin Guide](docs/ADMIN_GUIDE.md) - Administrative functions and settings

### 🔧 Technical Documentation
- [API Reference](docs/API_REFERENCE.md) - Complete API documentation
- [Deployment Guide](docs/DEPLOY.md) - Production deployment instructions
- [AWS EB Deployment](docs/DEPLOY_AWS_EB.md) - AWS Elastic Beanstalk deployment
- [Security Guide](docs/SECURITY.md) - Security features and compliance

### 🔗 Integrations & Extensions
- [Integrations Guide](docs/INTEGRATIONS.md) - Third-party integrations
- [AI Copilot Guide](docs/AI_COPILOT_GUIDE.md) - AI features and capabilities
- [Extensibility Guide](docs/EXTENSIBILITY.md) - Plugin system and customization

### 🛠️ Operations & Support
- [Troubleshooting](docs/TROUBLESHOOTING.md) - Common issues and solutions
- [Release Notes](docs/RELEASE_NOTES.md) - Version history and updates
- [Marketplace Listing](docs/MARKETPLACE_LISTING.md) - Template information and features


## 🔌 Connecting the LLM

Co-Builder supports multiple LLM providers. Configure your preferred provider in `.env`:

### OpenAI (Native)
```bash
OPENAI_API_KEY=your_openai_api_key_here
```

### Azure OpenAI
```bash
AZURE_OPENAI_API_KEY=your_azure_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
```

### Quick Test
Test your LLM connection:
```bash
curl -s -X POST http://127.0.0.1:5001/api/cobuilder/ask \
  -H "Content-Type: application/json" -H "X-Tenant-ID: demo" \

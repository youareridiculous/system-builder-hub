# CRM Flagship Template v1.0.1

A comprehensive, production-ready CRM application built with FastAPI, React, and modern web technologies. Features multi-tenant architecture, role-based access control, communication integrations, and advanced analytics.

**Status:** ✅ Production Ready - Final Release

## 🚀 Quick Start

### Option 1: System Builder Hub (Recommended)
```bash
# If using SBH, simply click "Launch" from the Builds UI
# The template will be automatically scaffolded and served
```

### Option 2: Manual Setup
```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py

# Frontend (in new terminal)
cd frontend
npm install
npm run dev

# Access the application
# Backend API: http://localhost:8000
# Frontend: http://localhost:5174
# API Docs: http://localhost:8000/docs
```

## 🧪 Testing & Verification

### Golden Smoke Test
Run the comprehensive smoke test to verify all functionality:

```bash
# Run the complete smoke test
make smoke

# Or run manually
./scripts/smoke_verify.sh

# Test against different URL
./scripts/smoke_verify.sh http://your-domain.com
```

The smoke test verifies:
- ✅ Authentication and RBAC for all roles
- ✅ CRUD operations (accounts, contacts, deals)
- ✅ Pipeline Kanban functionality
- ✅ Communications (email, SMS, voice)
- ✅ Automations and dry-run testing
- ✅ Analytics and reporting
- ✅ Webhooks and settings

### Reset Demo Data
Reset to a clean state for demos:

```bash
# Using the API endpoint (Owner/Admin only)
curl -X POST http://localhost:8000/api/settings/admin/reset-demo \
  -H "Authorization: Bearer YOUR_TOKEN"

# Or restart the backend to auto-reseed
```

## 🎯 First-Run Checklist

New users are guided through setup with an interactive checklist:

1. **Set Branding** - Customize company name, logo, and colors
2. **Configure Providers** - Set up email/SMS providers or keep Mock mode
3. **Invite Users** - Add team members and assign roles
4. **Create First Contact** - Add your first contact to get started
5. **Send First Communication** - Test your communication setup
6. **Set Up Automations** - Create automation rules to streamline workflows

The checklist appears on the Dashboard for users with `settings.read` permission and can be dismissed once completed.

## 🔧 Environment Configuration

### Required Environment Variables
```bash
# Authentication
AUTH_SECRET=your-super-secret-jwt-key-here

# Database (SQLite by default)
DATABASE_URL=sqlite:///data/app.db

# Optional: Real Provider Credentials
SENDGRID_API_KEY=SG.your-sendgrid-api-key
TWILIO_ACCOUNT_SID=ACyour-twilio-account-sid
TWILIO_AUTH_TOKEN=your-twilio-auth-token
```

### Provider Modes
- **Mock Mode (Default)**: No real credentials needed, simulates email/SMS
- **SendGrid**: Real email delivery via SendGrid API
- **Twilio**: Real SMS/voice via Twilio API

### Webhook Configuration
For real providers, configure webhooks at:
- **SendGrid**: `https://your-domain.com/api/webhooks/sendgrid`
- **Twilio SMS**: `https://your-domain.com/api/webhooks/twilio/sms`
- **Twilio Voice**: `https://your-domain.com/api/webhooks/twilio/voice`

## 👥 Authentication & RBAC

### User Roles & Permissions

| Role | Key Permissions | Description |
|------|----------------|-------------|
| **Owner** | `*` (all) | Full system access, user management |
| **Admin** | `settings.*`, `users.manage`, `analytics.*` | System administration, user management |
| **Manager** | `contacts.*`, `deals.*`, `pipelines.*`, `communications.*` | Sales management, pipeline oversight |
| **Sales** | `contacts.read`, `deals.*`, `communications.*` | Sales activities, deal management |
| **ReadOnly** | `contacts.read`, `deals.read`, `analytics.read` | View-only access to data |

### Permission Matrix
```
contacts.*     - Contact CRUD operations
deals.*        - Deal CRUD and pipeline management
pipelines.*    - Pipeline configuration
communications.* - Email/SMS sending and templates
templates.*    - Template management
automations.*  - Automation rule management
analytics.*    - Dashboard and reporting
settings.*     - System configuration
users.manage   - User and role management
webhooks.*     - Webhook event management
```

## 📊 Data Model

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     Accounts    │    │     Contacts    │    │       Deals     │
├─────────────────┤    ├─────────────────┤    ├─────────────────┤
│ id              │    │ id              │    │ id              │
│ name            │    │ first_name      │    │ title           │
│ industry        │    │ last_name       │    │ amount          │
│ website         │    │ email           │    │ stage           │
│ phone           │    │ phone           │    │ account_id      │
│ created_at      │    │ account_id      │    │ contact_id      │
└─────────────────┘    │ created_at      │    │ created_at      │
                       └─────────────────┘    └─────────────────┘
                                │                       │
                                │                       │
                       ┌─────────────────┐    ┌─────────────────┐
                       │   Activities    │    │ Communications  │
                       ├─────────────────┤    ├─────────────────┤
                       │ id              │    │ id              │
                       │ type            │    │ type            │
                       │ subject         │    │ subject         │
                       │ contact_id      │    │ contact_id      │
                       │ deal_id         │    │ deal_id         │
                       │ scheduled_at    │    │ status          │
                       │ completed_at    │    │ provider        │
                       └─────────────────┘    └─────────────────┘
```

## 🎯 Key Features

### Core CRM
- **Contact Management**: Full CRUD with account associations
- **Deal Pipeline**: Kanban board with drag & drop
- **Account Management**: Company information and relationships
- **Activity Tracking**: Tasks, calls, meetings, and notes

### Communications
- **Email/SMS Templates**: Token-based templates with preview
- **Provider Integration**: SendGrid (email) and Twilio (SMS/voice)
- **Webhook Handling**: Real-time delivery status updates
- **Call Recordings**: Audio playback for voice communications

### Automation
- **Rule Builder**: Visual automation rule creation
- **Triggers**: Contact creation, deal stage changes, activities
- **Conditions**: Field-based filtering and logic
- **Actions**: Send communications, update records, create activities
- **Dry-run Testing**: Test automation rules safely

### Analytics & Reporting
- **Dashboard**: KPIs and performance metrics
- **Time-series Charts**: Communication success rates over time
- **Pipeline Analytics**: Win rates, cycle times, stuck deals
- **Activity Heatmaps**: Team productivity visualization

### System Administration
- **Multi-tenant**: Isolated data per tenant
- **User Management**: Role assignment and permissions
- **Provider Configuration**: Email/SMS provider setup
- **Branding**: Custom logos, colors, and company information
- **Webhooks Console**: Event monitoring and replay

## 🧪 Testing & QA

See [docs/QA.md](docs/QA.md) for comprehensive testing checklist including:
- Role-based access testing
- Feature smoke tests
- Integration testing
- UI/UX validation

## 🐳 Docker Deployment

### Quick Start with Docker
```bash
# One-command demo setup
docker-compose up -d

# Access the application
# Frontend: http://localhost:5174
# Backend: http://localhost:8000
# API Docs: http://localhost:8000/docs

# Demo users (pre-seeded)
# Owner: owner@sbh.dev / Owner!123
# Admin: admin@sbh.dev / Admin!123
# Sales: sales@sbh.dev / Sales!123
# ReadOnly: readonly@sbh.dev / ReadOnly!123

# Run smoke test after startup
make smoke
```

### Docker Environment Variables
The following environment variables are supported in docker-compose:

```bash
# Required
AUTH_SECRET=your-super-secret-jwt-key-here

# Optional: Real providers
SENDGRID_API_KEY=SG.your-sendgrid-api-key
TWILIO_ACCOUNT_SID=ACyour-twilio-account-sid
TWILIO_AUTH_TOKEN=your-twilio-auth-token

# Optional: Environment
ENVIRONMENT=production
DEBUG=false
```

## 📚 API Documentation

- **Interactive Docs**: http://localhost:8000/docs
- **OpenAPI Spec**: http://localhost:8000/openapi.json
- **Health Check**: http://localhost:8000/health

## 🔒 Security Features

- **JWT Authentication**: Secure token-based auth
- **Role-Based Access Control**: Granular permission system
- **Multi-tenant Isolation**: Data separation per tenant
- **Input Validation**: Pydantic models for all data
- **CORS Protection**: Configurable cross-origin policies

## 🛠️ Development

### Backend (FastAPI)
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

### Frontend (React + Vite)
```bash
cd frontend
npm install
npm run dev
```

### Database
```bash
# SQLite (default)
# Database file: backend/data/app.db

# PostgreSQL (optional)
DATABASE_URL=postgresql://user:pass@localhost/crm
```

## 📝 License

This template is provided as-is for demonstration and development purposes.

---

**Ready to launch your CRM?** Start with the [Quick Start](#-quick-start) section above!

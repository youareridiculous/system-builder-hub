# System Builder Hub - Quick Start Guide

## Prerequisites

- Python 3.10 or higher
- pip (Python package installer)
- Git

## Setup

### 1. Clone and Navigate

```bash
git clone <repository-url>
cd system-builder-hub/backend
```

### 2. Create Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Verify Installation

```bash
python -m src.cli check
```

This command will verify that all required dependencies are installed and the environment is ready.

## Running the Application

### Start the Server

```bash
python -m src.cli run --port 5001 --debug
```

### Access the Application

- **Dashboard**: http://localhost:5001/
- **Builder UI**: http://localhost:5001/ui/build (or http://localhost:5001/builder)
- **Marketplace**: http://localhost:5001/ui/marketplace
- **Health Check**: http://localhost:5001/healthz
- **Readiness Check**: http://localhost:5001/readiness (includes dependency status)
- **API Documentation**: http://localhost:5001/openapi.json

## Templates & Marketplace

### CRM Flagship Template

The **CRM Flagship** template provides a production-grade CRM starter with comprehensive business functionality:

**Core Modules:**
- **Accounts**: Companies and organizations management
- **Contacts**: People linked to accounts with relationship tracking
- **Deals**: Opportunities tracked through customizable pipelines
- **Pipelines**: Sales stages and Kanban board views
- **Activities**: Tasks, notes, calls, and meetings
- **Permissions**: Role-based access control and user management

**Launch Options:**
1. **Marketplace**: Visit `/ui/marketplace` and click "Launch CRM"
2. **Direct URL**: `/ui/build?template=crm_flagship&prefill=1`
3. **Builder Wizard**: Select "CRM Flagship" from the template picker

**Features:**
- Pre-filled project name and description
- Automatic LLM prompt configuration
- Module badges and complexity indicators
- Featured template with special styling

**Development Mode:**
- Builds auto-progress through stages (initializing → building → generating → completed)
- LLM integration enabled by default
- Demo tenant isolation for testing

**Production Mode:**
- Worker processes builds via RQ queues
- Strict tenant isolation
- Real LLM provider integration required

## Testing

### Running Tests

We use pytest for comprehensive automated testing of the marketplace templates and builds API.

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=term-missing

# Run specific test suites
pytest tests/test_builds_api.py          # Builds API core tests
pytest tests/test_crm_flagship_build.py  # CRM Flagship template tests
pytest tests/test_blank_template_build.py # Blank Canvas template tests
pytest tests/test_tasks_template_build.py # Task Manager template tests
```

### Test Coverage

**Current Test Suite:**
- **Builds API Core**: 11 tests (CRUD operations, error handling, JSON consistency)
- **CRM Flagship Template**: 9 tests (end-to-end build workflow, tasks integration)
- **Blank Canvas Template**: 9 tests (starter template validation)
- **Task Manager Template**: 9 tests (productivity template testing)

**Total: 38 tests passing in ~0.41s**

Each template test validates:
- ✅ Build creation via API with proper JSON responses
- ✅ Auto-progression simulation (initializing → running → completed)
- ✅ Build logs endpoint functionality
- ✅ Tasks integration with tenant isolation
- ✅ Error handling (400 for missing fields, 404 for not found)
- ✅ JSON consistency across all endpoints

### Continuous Integration

Tests run automatically in GitHub Actions on every push and pull request:
- Python 3.11 environment
- Coverage reporting with Codecov integration
- Fast execution (< 1 second)
- Comprehensive error reporting

### Adding New Templates

When adding new templates to the marketplace:

1. Create the template in `marketplace/<template_name>/template.json`
2. Add a corresponding test file: `tests/test_<template>_build.py`
3. Follow the 9-test pattern established in existing template tests
4. Ensure all tests pass before merging

## Frontend UI

### Current Setup

The application currently uses Flask templates for the UI. The Builder interface is available at:

- **Builder Page**: http://localhost:5001/ui/build
- **Builder Alias**: http://localhost:5001/builder (redirects to /ui/build)

### Development Mode

In development mode, the Builder page includes helpful hints for setting up a modern frontend:

1. **Flask Templates Only**: The current setup uses Flask templates with embedded CSS/JS
2. **Modern Frontend Setup**: To add React/Vue/etc., see the development hints on the Builder page

### Production Deployment

For production, the UI is served directly by Flask:

```bash
# Build and serve (if you have a modern frontend)
make ui-build

# Run in production mode
python -m src.cli run --port 5001
```

### UI Development Commands

```bash
# Start UI development server (if modern frontend exists)
make ui-dev

# Build UI for production
make ui-build

# Clean UI build artifacts
make ui-clean
```

## Development Commands

### Health Checks

```bash
# Check dependencies and environment
python -m src.cli check

# Run smoke tests
python -m src.cli smoke

# Run diagnostics
python -m src.cli doctor
```

### Database Management

```bash
# Reset database and environment
python -m src.cli reset-db

# Reset with auto-start
python -m src.cli reset-db --with-server

# Create demo project
python -m src.cli demo --name "My Demo Project"
```

### Development Tools

```bash
# List all available routes
python -m src.cli dump-routes

# Start background worker (default queues: default,high,low)
python -m src.cli worker

# Start worker with specific queues
python -m src.cli worker --queues default,high,low

# Start worker in burst mode (exit when no jobs)
python -m src.cli worker --burst

# Start worker with verbose logging
python -m src.cli worker --verbose

# Start worker with custom name
python -m src.cli worker --name "my-worker"

# Start worker for specific queue only
python -m src.cli worker --queues high --name "high-priority-worker"
```

### Worker Management (Makefile)

```bash
# Start default worker
make worker

# Start worker with all queues
make worker-queues

# Start worker in burst mode
make worker-burst

# Start worker with verbose logging
make worker-verbose

# Start named worker
make worker-named

# Start individual queue workers
make worker-high    # High priority queue only
make worker-default # Default queue only
make worker-low     # Low priority queue only

# Start all workers (separate processes)
make workers-all

# Stop all workers
make workers-stop
```

### Background Jobs

The system uses Redis Queue (RQ) for background job processing. Jobs include:

- **Build Generation**: Creating projects from templates
- **Email Sending**: User notifications and alerts
- **Payment Processing**: Webhook handling
- **Session Cleanup**: Maintenance tasks

**Prerequisites for Workers:**
- Redis server running (optional - falls back to threading if not available)
- All Python dependencies installed

**Starting Redis:**
```bash
# macOS (using Homebrew)
brew install redis
brew services start redis

# Docker
docker run -d -p 6379:6379 redis:alpine

# Linux
sudo apt-get install redis-server
sudo systemctl start redis
```

**Redis Connection Issues (macOS):**

If you encounter Redis connection timeouts on macOS, it's likely due to IPv6/IPv4 resolution issues. The system now defaults to IPv4 (127.0.0.1) to avoid this problem.

**Solutions:**
```bash
# Use IPv4 explicitly (recommended)
python -m src.cli worker --redis-url "redis://127.0.0.1:6379/0"

# Or use the Makefile command
make worker-ipv4

# Force Redis to bind to IPv4 only
redis-server --bind 127.0.0.1

# Check Redis is listening on IPv4
netstat -an | grep 6379
```

**Worker Connection Retry:**
The worker now includes automatic retry logic with exponential backoff. If Redis is temporarily unavailable, the worker will:
- Retry up to 5 times with increasing delays
- Log clear error messages and retry attempts
- Provide helpful setup instructions if Redis is not running

**Redis Timeout Fix:**
If you previously saw "Redis connection timeout, quitting..." during idle periods, this has been fixed. The worker now:
- Disables socket timeout to support RQ's long BLPOP operations (~400s)
- Continues listening after Redis timeouts instead of exiting
- Automatically reconnects and resumes processing
- Works indefinitely in idle mode without timing out

## Local Development Authentication

The Builder Wizard requires authentication for API calls. For local development, several options are available:

### Option 1: Dev Anonymous Access (Easiest)

Enable anonymous access for development:

```bash
export SBH_DEV_ALLOW_ANON=1
python -m src.cli run --port 5001 --debug
```

This allows the wizard to work without any authentication headers.

### Option 2: Demo API Key

Use the built-in demo API key for development:

```bash
# Get the demo API key
curl http://localhost:5001/api/auth/dev-key

# Use the key in your requests
curl -H "X-API-Key: sbh-demo-key-..." http://localhost:5001/api/builds
```

**In the browser console:**
```javascript
// Get and store the demo key
fetch('/api/auth/dev-key')
  .then(r => r.json())
  .then(data => {
    localStorage.setItem('sbh.auth.apiKey', data.api_key);
    console.log('Demo key stored');
  });

// Or manually set a key
localStorage.setItem('sbh.auth.apiKey', 'your-api-key-here');
```

### Option 3: JWT Bearer Token

Use a JWT token for authentication:

```bash
# Login to get a token
curl -X POST http://localhost:5001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "demo@example.com", "password": "password"}'

# Use the token
curl -H "Authorization: Bearer <token>" http://localhost:5001/api/builds
```

**In the browser console:**
```javascript
localStorage.setItem('sbh.auth.bearer', 'your-jwt-token-here');
```

### Dev Auth Panel

When authentication is required, a "Dev Authentication" panel appears in the top-right corner of the Builder UI. You can:

1. **Use Demo Key**: Automatically fetch and store the demo API key
2. **Manual Token**: Enter a JWT token manually
3. **Check Status**: See current authentication status

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SBH_DEV_ALLOW_ANON` | Enable anonymous access in dev | `false` |
| `FLASK_ENV` | Flask environment | `development` |
| `SBH_ENV` | SBH environment | `dev` |

### Production Security

In production environments:
- `SBH_DEV_ALLOW_ANON` is ignored
- Anonymous access is never allowed
- Only valid JWT tokens are accepted
- API keys are not available

### Testing Authentication

Test your authentication setup:

```bash
# Check auth status
curl http://localhost:5001/api/auth/auth-status

# Test protected endpoint
curl http://localhost:5001/api/builds
```

## Tasks Management

### Tasks API

The Tasks API provides full CRUD operations for task management with tenant isolation:

```bash
# List tasks
curl http://localhost:5001/api/tasks

# Create a task
curl -X POST -H "Content-Type: application/json" \
  -d '{"title": "My new task"}' \
  http://localhost:5001/api/tasks

# Update a task
curl -X PATCH -H "Content-Type: application/json" \
  -d '{"completed": true}' \
  http://localhost:5001/api/tasks/1

# Delete a task
curl -X DELETE http://localhost:5001/api/tasks/1
```

### Tasks UI

Visit the Tasks management interface:

- **Tasks Page**: http://localhost:5001/ui/tasks

The Tasks UI provides a modern interface for:
- Adding new tasks
- Marking tasks as complete/incomplete
- Deleting tasks
- Viewing task history

### Tasks Tenancy

**Development Mode (`SBH_DEV_ALLOW_ANON=1`):**
- Tasks are automatically assigned to `demo-tenant`
- Legacy tasks with `NULL` tenant_id are automatically backfilled to `demo-tenant`
- All tasks are visible regardless of tenant for development convenience

**Production Mode:**
- Tasks are strictly scoped to the current tenant
- Legacy tasks with `NULL` tenant_id are ignored
- Only tasks belonging to the authenticated tenant are visible

**Database Schema:**
```sql
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT,
    title TEXT NOT NULL,
    completed INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

**Migration:**
The system automatically:
- Creates the tasks table if it doesn't exist
- Adds the `tenant_id` column if missing
- Backfills legacy `NULL` tenant_id rows in development mode
- Creates performance indexes for tenant queries

### Testing Tasks

```bash
# Test tasks API
curl http://localhost:5001/api/tasks

# Create a test task
curl -X POST -H "Content-Type: application/json" \
  -d '{"title": "Test task"}' \
  http://localhost:5001/api/tasks

# Verify in database
sqlite3 system_builder_hub.db \
  "SELECT id, title, completed, COALESCE(tenant_id,'<NULL>') tenant FROM tasks ORDER BY id DESC LIMIT 5;"
```

### Database Debug Information

**API Endpoint (dev-only):**
```bash
# Get database info via API
curl -s http://localhost:5001/api/dev/db-info | jq .
```

**CLI Command:**
```bash
# Get database info via CLI
python -m src.cli db-info
```

**Manual SQLite Query:**
```bash
# Copy the db_path from the API/CLI response, then run:
sqlite3 "<DB_PATH_FROM_RESPONSE>" \
  "SELECT id, title, completed, tenant_id, created_at FROM tasks ORDER BY id DESC LIMIT 10;"
```

**Example Output:**
```json
{
  "db_path": "/Users/username/Downloads/system-builder-hub/backend/system_builder_hub.db",
  "tables": ["alembic_version", "build_logs", "builds", "tasks", "users"],
  "tasks_preview": [
    {
      "id": 1,
      "title": "Test task",
      "completed": 0,
      "tenant_id": "demo-tenant",
      "created_at": "2024-01-15 10:30:00"
    }
  ]
}
```

**Server Logs:**
When the server starts or first connects to the database, you'll see:
```
[DB DEBUG] Using database at: /Users/username/Downloads/system-builder-hub/backend/system_builder_hub.db
```

## Troubleshooting

### Missing Dependencies

If you see dependency errors, run:

```bash
pip install -r requirements.txt
```

### Database Issues

If the database is corrupted or needs reset:

```bash
python -m src.cli reset-db
```

### Readiness Check

The `/readiness` endpoint provides detailed dependency status:

```bash
curl http://localhost:5001/readiness
```

Response includes:
- `deps`: Boolean indicating if all dependencies are available
- `missing_deps`: List of missing dependencies
- `total_deps`: Total number of required dependencies
- `available_deps`: Number of available dependencies

### UI Issues

1. **Builder page shows JSON instead of HTML**: Ensure the `build.html` template exists in `templates/ui/`
2. **Modern frontend not loading**: Check if you have a `package.json` in the `frontend/` directory
3. **Static assets not found**: Run `make ui-build` to build and copy assets

### Common Issues

1. **ModuleNotFoundError**: Run `python -m src.cli check` to identify missing dependencies
2. **Port already in use**: Change the port with `--port 5002`
3. **Database errors**: Run `python -m src.cli reset-db` to reset the database
4. **Redis connection**: Ensure Redis is running or the app will continue without it

## Environment Variables

Create a `.env` file for custom configuration:

```bash
# Database
DATABASE_URL=sqlite:///./system_builder_hub.db

# Authentication
AUTH_SECRET_KEY=your-secret-key-here

# LLM Configuration
LLM_SECRET_KEY=your-llm-key-here

# Redis (optional)
REDIS_URL=redis://localhost:6379/0
```

## Next Steps

1. Visit the Builder UI at http://localhost:5001/ui/build
2. Explore the API documentation at http://localhost:5001/openapi.json
3. Create your first project using the Builder interface
4. Check out the Marketplace for templates and components
5. Review the full documentation in the `docs/` directory

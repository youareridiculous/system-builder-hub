# System Builder Hub Operations Guide

## Database + Environment Reset for Local Development

System Builder Hub provides automated reset workflows for local development environments. These commands ensure a clean, consistent state for development and testing.

### Quick Reset Commands

#### Basic Reset (Database Only)
```bash
make reset-db
# OR
python src/cli.py reset-db
```

**What it does:**
- Stops running services gracefully
- Resets Redis (FLUSHALL)
- Removes existing database file
- Runs all migrations from scratch
- Seeds demo data (tenant + projects + meta-builder templates)
- Runs verification checks
- **Does NOT start services**

#### Reset with Auto-Start
```bash
make reset-db-with-server
# OR
python src/cli.py reset-db --with-server
```

**What it does:**
- Performs all basic reset steps
- Automatically starts Flask server and workers
- Provides access URLs

#### Quick Reset (Minimal)
```bash
make reset-quick
```

**What it does:**
- Removes database file
- Runs migrations
- Seeds demo project
- No service management or verification

### Reset Process Details

#### 1. Service Management
- **Detection**: Automatically finds running `python src/cli.py run` and `python src/cli.py worker` processes
- **Graceful Stop**: Sends SIGTERM, waits 5 seconds, then SIGKILL if needed
- **Confirmation**: Reports number of processes stopped

#### 2. Redis Reset
- **Method**: Uses `redis-cli FLUSHALL`
- **Fallback**: If Redis unavailable, logs warning but continues
- **Safety**: Won't fail the reset if Redis is down

#### 3. Database Reset
- **File Removal**: Deletes `system_builder_hub.db` if exists
- **Migration State**: Ensures clean Alembic state
- **Fresh Schema**: Runs `alembic upgrade head` from scratch

#### 4. Demo Data Seeding
- **Tenant**: Creates `demo_tenant`
- **Project**: Creates "Demo Project" with system
- **Meta-Builder**: Seeds patterns, templates, and evaluation cases
- **Confirmation**: Reports seeding success

#### 5. Verification Checks
- **Database**: Verifies file exists and tables populated
- **Counts**: Reports project and system counts
- **Health Check**: Tests `/healthz` endpoint (if server running)
- **Routes**: Dumps available API endpoints

### Example Output

#### Successful Reset
```
🔄 Starting System Builder Hub database reset...
⏹️  Stopping running services...
ℹ️  No running processes to stop
🗑️  Resetting Redis...
✅ Redis flushed successfully
🗑️  Removing existing database...
✅ Database file removed
📦 Running database migrations...
   Current migration: 5ecd76ed3373 (eval_lab_v1_1_upgrade)
✅ Migrations completed successfully
🌱 Seeding demo data...
   Meta-builder data seeded: 10 patterns
✅ Demo tenant + projects seeded
🔍 Running verification checks...
   📊 Projects: 1
   📊 Systems: 1
   ℹ️  Server not running (expected if --with-server not used)
   📋 Routes: 219 endpoints available
✅ Environment healthy

🎉 Database reset completed successfully!
```

#### Reset with Auto-Start
```
🚀 Starting services...
✅ Services started successfully

🌐 Access URLs:
   Dashboard: http://localhost:5001/
   Builder: http://localhost:5001/builder
   Marketplace: http://localhost:5001/marketplace
   Settings: http://localhost:5001/settings
   Eval Lab: http://localhost:5001/eval-lab
   API Docs: http://localhost:5001/openapi.json
```

### Troubleshooting

#### Migration Errors
```bash
# Check migration status
alembic current

# If stuck, force stamp current version
alembic stamp head
alembic upgrade head
```

#### Redis Issues
```bash
# Check Redis status
redis-cli ping

# Start Redis if needed
brew services start redis  # macOS
sudo systemctl start redis  # Linux
```

#### Service Start Failures
```bash
# Check if port is in use
lsof -i :5001

# Use different port
python src/cli.py run --port 5002 --debug
```

#### Database Lock Issues
```bash
# Force remove database
rm -f system_builder_hub.db

# Check for SQLite locks
sqlite3 system_builder_hub.db "PRAGMA busy_timeout = 30000;"
```

### Access URLs After Reset

Once reset is complete, access the system at:

- **Dashboard**: http://localhost:5001/
- **Builder**: http://localhost:5001/builder
- **Marketplace**: http://localhost:5001/marketplace
- **Settings**: http://localhost:5001/settings
- **Evaluation Lab**: http://localhost:5001/eval-lab
- **API Documentation**: http://localhost:5001/openapi.json
- **Health Check**: http://localhost:5001/healthz

### Demo Data

After reset, the system includes:

- **Demo Tenant**: `demo_tenant`
- **Demo Project**: "Demo Project" with system
- **Meta-Builder Patterns**: 10 common application patterns
- **Templates**: CRM, LMS, Marketplace, etc.
- **Evaluation Cases**: 5 golden test cases

### Best Practices

1. **Use Before Development**: Run reset before starting new features
2. **Use for Testing**: Reset provides clean state for testing
3. **Check Output**: Verify all steps complete successfully
4. **Monitor Services**: Use `--with-server` for immediate access
5. **Backup First**: Consider backing up important data before reset

### Integration with CI/CD

The reset workflow can be integrated into CI/CD pipelines:

```yaml
# GitHub Actions example
- name: Reset Database
  run: |
    make reset-db
    # Run tests
    python -m pytest tests/
```

### Performance Notes

- **Reset Time**: Typically 30-60 seconds
- **Database Size**: Fresh database ~50MB
- **Memory Usage**: ~100MB for server + workers
- **Startup Time**: 5-10 seconds for services

### Safety Features

- **Graceful Shutdown**: Services stopped safely
- **Error Handling**: Continues on non-critical failures
- **Verification**: Multiple health checks
- **Rollback**: Can re-run if issues occur
- **Logging**: Detailed progress reporting

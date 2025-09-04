# Deployment Guide

This guide covers deploying System Builder Hub to production environments.

## Quick Start - AWS Elastic Beanstalk

### Prerequisites
- AWS CLI configured with appropriate permissions
- S3 bucket for file storage
- Domain name (optional, for custom domain)

### 1. Bootstrap S3 Bucket
```bash
# Create S3 bucket for file storage
python scripts/bootstrap_s3.py sbh-files-us-east-1 us-east-1
```

### 2. Create Elastic Beanstalk Application
```bash
# Create EB application
eb init sbh --platform docker --region us-east-1

# Create environment
eb create sbh-prod --instance-type t3.small --single-instance
```

### 3. Configure Environment Variables
Update `.ebextensions/01-options.config` with your values:
- `PUBLIC_BASE_URL`: Your domain or ALB DNS name
- `S3_BUCKET_NAME`: Your S3 bucket name
- `AUTH_SECRET_KEY`: Strong secret key for authentication
- `LLM_SECRET_KEY`: 32-byte base64 encoded key
- `DATABASE_URL_PROD`: PostgreSQL connection string (see RDS setup below)
- `REDIS_URL`: ElastiCache Redis endpoint (see Redis setup below)
- `SENTRY_DSN`: Sentry error reporting DSN (optional)
- `OTEL_EXPORTER_OTLP_ENDPOINT`: OpenTelemetry collector endpoint (optional)
- `SSM_PATH`: SSM Parameter Store path (e.g., `/sbh/prod/`) (optional)

### 4. Deploy
```bash
# Tag and push to trigger deployment
git tag v1.0.0
git push origin v1.0.0
```

### 5. Verify Deployment
```bash
# Run smoke tests
python scripts/smoke_prod.py https://your-eb-domain.elasticbeanstalk.com
```

## Database Configuration

### PostgreSQL (Production Default)
SBH uses PostgreSQL in production environments with connection pooling:

**Environment Variables:**
```bash
ENV=production
DATABASE_URL_PROD=postgresql+psycopg2://USER:PASSWORD@HOST:5432/DBNAME
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=1800
```

**RDS Setup:**
1. Create RDS PostgreSQL instance (free-tier: db.t4g.micro)
2. Configure security group to allow EB instance access
3. Get connection details: hostname, username, password, database name
4. Update `DATABASE_URL_PROD` in EB environment variables

**Connection Pooling:**
- Default pool size: 10 connections
- Max overflow: 10 additional connections
- Pool timeout: 30 seconds
- Pool recycle: 30 minutes (prevents stale connections)

**Migration:**
```bash
# Apply migrations
make db-up

# Create new migration
make db-rev MESSAGE="description"

# Rollback migration
make db-down
```

### SQLite (Development Default)
For local development, SBH uses SQLite:
```bash
ENV=development
DATABASE_URL=sqlite:///./instance/app.db
```

## Storage Providers
SBH defaults to S3 storage in production environments:

**Environment Variables:**
```bash
STORAGE_PROVIDER=s3
S3_BUCKET_NAME=your-bucket-name
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=us-east-1
S3_PRESIGN_EXPIRY_SECONDS=900
```

**IAM Policy Required:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject", 
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::your-bucket-name",
        "arn:aws:s3:::your-bucket-name/stores/*"
      ]
    }
  ]
}
```

### Local Storage (Development)
For local development, SBH uses local file storage:
```bash
STORAGE_PROVIDER=local
```

## Redis Configuration

### ElastiCache Redis (Production Default)
SBH uses Redis for sessions, caching, rate limiting, and background jobs:

**Environment Variables:**
```bash
FEATURE_REDIS=true
FEATURE_RATE_LIMITS=true
FEATURE_BG_JOBS=true
REDIS_URL=redis://your-elasticache-endpoint:6379/0
RATE_LIMIT_STORAGE_URL=redis://your-elasticache-endpoint:6379/1
SESSION_REDIS_URL=redis://your-elasticache-endpoint:6379/2
REDIS_QUEUE_URL=redis://your-elasticache-endpoint:6379/3
```

**ElastiCache Setup:**
1. Create ElastiCache Redis cluster (free-tier: cache.t4.micro)
2. Configure security groups to allow EB instance access
3. Get primary endpoint from ElastiCache console
4. Update `REDIS_URL` in EB environment variables

**Features Enabled:**
- **Server-side Sessions**: Redis-based session storage
- **Global Caching**: Application-level caching
- **Rate Limiting**: API rate limiting with Redis storage
- **Background Jobs**: RQ-based job queue for async processing

### Local Redis (Development)
For local development, SBH can use local Redis:
```bash
REDIS_URL=redis://localhost:6379/0
```

**Running Local Redis:**
```bash
# macOS
brew install redis
brew services start redis

# Ubuntu
sudo apt-get install redis-server
sudo systemctl start redis-server

# Docker
docker run -d -p 6379:6379 redis:7-alpine
```

### Background Worker
For production, run a separate worker process:

**Option 1: Separate EB Environment**
```bash
# Create worker environment
eb create sbh-worker --instance-type t3.micro --single-instance

# Configure worker environment variables
# Set REDIS_URL and other required variables
```

**Option 2: ECS Fargate**
```bash
# Deploy worker as ECS Fargate service
# Use the same Docker image with different entrypoint
```

**Option 3: EC2 with systemd**
```bash
# Create EC2 instance
# Install Docker and run worker container
# Configure systemd service for auto-restart
```

**Worker Commands:**
```bash
# Start worker
python -m src.jobs.worker

# Or using Docker
docker run -e REDIS_URL=... sbh:latest python -m src.jobs.worker
```

## Observability Configuration

### Sentry Error Reporting (Optional)
```bash
# Set up Sentry project and get DSN
SENTRY_DSN=https://your-key@your-org.ingest.sentry.io/project-id
SENTRY_ENVIRONMENT=production
```

### OpenTelemetry Tracing (Optional)
```bash
# Set up OTEL collector endpoint
OTEL_EXPORTER_OTLP_ENDPOINT=http://your-collector:4317
OTEL_SERVICE_NAME=sbh
```

### Prometheus Metrics
```bash
# Enable metrics (default: true)
PROMETHEUS_METRICS_ENABLED=true
```

### CloudWatch Alarms
Create CloudWatch alarms for monitoring:

```bash
# High error rate alarm
aws cloudwatch put-metric-alarm \
  --alarm-name "SBH-HighErrorRate" \
  --alarm-description "High error rate in SBH application" \
  --metric-name "ErrorCount" \
  --namespace "SBH/Logs" \
  --statistic Sum \
  --period 300 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --alarm-actions arn:aws:sns:region:account:topic-name
```

For detailed observability setup, see [docs/OBSERVABILITY.md](OBSERVABILITY.md).

## HTTPS Configuration

### ACM Certificate Setup
1. **Request Certificate**:
   ```bash
   aws acm request-certificate \
     --domain-name your-domain.com \
     --validation-method DNS \
     --region us-east-1
   ```

2. **Validate Certificate**:
   - Add DNS records as specified in ACM console
   - Wait for validation to complete

3. **Attach to ALB**:
   - Go to EC2 > Load Balancers
   - Select your ALB
   - Edit listeners
   - Add HTTPS listener (port 443) with your certificate
   - Set default action to forward to target group

### Security Headers
The application automatically includes security headers:
- **HSTS**: Strict-Transport-Security with 1-year max-age
- **X-Content-Type-Options**: nosniff
- **X-Frame-Options**: SAMEORIGIN
- **Referrer-Policy**: strict-origin-when-cross-origin
- **Content-Security-Policy**: Restricts resource loading

## Autoscaling Configuration

### Web Environment
- **Min Instances**: 2
- **Max Instances**: 6
- **Target CPU**: 50%
- **Scale Up Cooldown**: 120 seconds
- **Scale Down Cooldown**: 120 seconds

### Worker Environment
- **Min Instances**: 1
- **Max Instances**: 4
- **Target CPU**: 60%
- **Scale Up Cooldown**: 120 seconds
- **Scale Down Cooldown**: 120 seconds

## Worker Environment Setup

### 1. Create Worker Environment
```bash
# Create worker environment
eb create sbh-worker \
  --instance-type t3.small \
  --single-instance \
  --vpc.id vpc-xxxxx \
  --vpc.subnets subnet-xxxxx,subnet-yyyyy \
  --vpc.securitygroups sg-xxxxx
```

### 2. Configure Worker Environment
Update `deploy/worker/.ebextensions/01-options.config`:
- Set `REDIS_URL` to your ElastiCache endpoint
- Set `DATABASE_URL_PROD` to your RDS endpoint
- Configure `SSM_PATH` for secrets

### 3. Deploy Worker
```bash
# Deploy worker environment
eb deploy sbh-worker
```

## SSM Parameter Store Setup

### 1. Create Parameters
```bash
# Create parameters in SSM
aws ssm put-parameter \
  --name "/sbh/prod/AUTH_SECRET_KEY" \
  --value "your-secret-key" \
  --type "SecureString" \
  --region us-east-1

aws ssm put-parameter \
  --name "/sbh/prod/LLM_SECRET_KEY" \
  --value "your-llm-secret-key" \
  --type "SecureString" \
  --region us-east-1

aws ssm put-parameter \
  --name "/sbh/prod/STRIPE_SECRET_KEY" \
  --value "sk_live_..." \
  --type "SecureString" \
  --region us-east-1
```

### 2. IAM Policy for EC2
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ssm:GetParametersByPath",
        "ssm:GetParameter"
      ],
      "Resource": [
        "arn:aws:ssm:us-east-1:ACCOUNT-ID:parameter/sbh/prod/*"
      ]
    }
  ]
}
```

### 3. Attach to Instance Profile
- Go to IAM > Roles
- Find your EB instance profile role
- Attach the SSM policy

## Rolling Deployment Checklist

### Pre-Deployment
- [ ] Verify database migrations are ready
- [ ] Check Redis connectivity
- [ ] Validate SSM parameters
- [ ] Confirm worker environment is healthy

### During Deployment
- [ ] Monitor CloudWatch metrics
- [ ] Check health endpoint responses
- [ ] Verify autoscaling behavior
- [ ] Monitor worker job processing

### Post-Deployment
- [ ] Run smoke tests
- [ ] Verify HTTPS enforcement
- [ ] Check security headers
- [ ] Validate metrics endpoint
- [ ] Test async job processing

## Production Requirements

## Health Checks & Monitoring

### Health Endpoints
SBH provides two health check endpoints:

- **`/healthz`**: Basic health check (always returns 200 if app is running)
- **`/readiness`**: Readiness check (validates database, LLM, and production config)

### Elastic Beanstalk Health Check
The EB environment is configured to use `/readiness` for health checks:
- **Health Check URL**: `/readiness`
- **Interval**: 30 seconds
- **Timeout**: 5 seconds
- **Retries**: 3
- **Start Period**: 30 seconds

### Production Validation
The readiness check validates:
- Database connectivity and migrations
- LLM configuration (optional)
- Production environment variables:
  - `PUBLIC_BASE_URL` (required in production)
  - S3 configuration (if using S3 storage)

### Monitoring
```bash
# Check application health
curl https://your-domain/healthz

# Check readiness (includes production validation)
curl https://your-domain/readiness

# Check metrics
curl https://your-domain/metrics
```

## Production Requirements
- **CPU**: 2+ cores (4+ recommended)
- **Memory**: 4GB+ RAM (8GB+ recommended)
- **Storage**: 20GB+ disk space
- **Network**: HTTPS support required

### Software Requirements
- **Docker**: 20.10+ (for containerized deployment)
- **Python**: 3.9+ (for direct deployment)
- **Database**: SQLite (default) or PostgreSQL/MySQL

## Environment Configuration

### Required Environment Variables
```bash
# Application
FLASK_ENV=production
SBH_PORT=5001

# Security (CRITICAL)
LLM_SECRET_KEY=your-32-byte-base64-encoded-key
SECRET_KEY=your-flask-secret-key

# Database
DATABASE_URL=sqlite:///./db/sbh.db
# OR for PostgreSQL:
# DATABASE_URL=postgresql://user:pass@localhost/sbh

# CORS (restrict in production)
CORS_ORIGINS=https://yourdomain.com

# Logging
LOG_LEVEL=INFO
```

### Security Checklist
- [ ] `LLM_SECRET_KEY` is 32 bytes, base64 encoded
- [ ] `SECRET_KEY` is strong and unique
- [ ] `CORS_ORIGINS` is restricted to your domain
- [ ] HTTPS is enabled
- [ ] Firewall rules are configured
- [ ] Database is secured

## Versioning

### Version Management
SBH uses semantic versioning with automatic version detection from git tags:

```bash
# Create a new version tag
git tag v1.0.0
git push origin v1.0.0

# Check current version
python version.py
```

### Version Information
- **APP_VERSION**: Semantic version (e.g., "1.0.0")
- **VERSION_STRING**: Full version with branch/commit (e.g., "1.0.0-main-abc123")
- **COMMIT_HASH**: Git commit hash
- **BRANCH**: Git branch name

Version information is available in:
- `/healthz` endpoint
- CLI `check` command
- Docker image tags

## Deployment Methods

### 1. Docker Deployment (Recommended)

#### Using Docker Compose with Versioning
```bash
# Clone and setup
git clone <repository-url>
cd system-builder-hub/backend

# Configure environment
cp .env.sample .env
# Edit .env with production values

# Set version (optional - defaults to git tag or 0.1.0)
export APP_VERSION=$(python version.py | grep "Version:" | cut -d' ' -f2)

# Build and start with versioned image
docker-compose up -d

# Check status
docker-compose ps
docker-compose logs -f

# Verify deployment
python scripts/deploy_verify.py http://localhost:5001
```

#### Using Docker directly with versioning
```bash
# Build versioned image
export APP_VERSION=$(python version.py | grep "Version:" | cut -d' ' -f2)
docker build --build-arg APP_VERSION=$APP_VERSION -t sbh:$APP_VERSION .

# Run container
docker run -d \
  --name sbh \
  -p 5001:5001 \
  -e FLASK_ENV=production \
  -e LLM_SECRET_KEY=your-key \
  -e DATABASE_URL=sqlite:///./db/sbh.db \
  -v $(pwd)/db:/app/db \
  sbh:$APP_VERSION

# Verify deployment
python scripts/deploy_verify.py http://localhost:5001
```

#### Using Docker directly
```bash
# Build image
docker build -t sbh:latest .

# Run container
docker run -d \
  --name sbh \
  -p 5001:5001 \
  -e FLASK_ENV=production \
  -e LLM_SECRET_KEY=your-key \
  -e DATABASE_URL=sqlite:///./db/sbh.db \
  -v $(pwd)/db:/app/db \
  sbh:latest
```

### 2. PostgreSQL Deployment

#### Using Docker Compose with PostgreSQL
```bash
# Clone and setup
git clone <repository-url>
cd system-builder-hub/backend

# Configure environment
cp .env.sample .env

# Edit .env to use PostgreSQL
DATABASE_URL=postgresql://sbh:sbh_password@postgres:5432/sbh

# Uncomment PostgreSQL service in docker-compose.yml
# postgres:
#   image: postgres:15
#   environment:
#     POSTGRES_DB: sbh
#     POSTGRES_USER: sbh
#     POSTGRES_PASSWORD: sbh_password
#   volumes:
#     - postgres_data:/var/lib/postgresql/data
#   ports:
#     - "5432:5432"

# Build and start with PostgreSQL
docker-compose up -d

# Initialize database
docker-compose exec sbh python cli.py init-db

# Verify deployment
python scripts/deploy_verify.py http://localhost:5001
```

#### External PostgreSQL Setup
```bash
# Install PostgreSQL
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib

# Create database and user
sudo -u postgres psql
CREATE DATABASE sbh;
CREATE USER sbh WITH PASSWORD 'sbh_password';
GRANT ALL PRIVILEGES ON DATABASE sbh TO sbh;
\q

# Configure application
export DATABASE_URL=postgresql://sbh:sbh_password@localhost:5432/sbh

# Run migrations
python cli.py init-db
```

### 3. Direct Python Deployment

#### System Setup
```bash
# Install Python dependencies
sudo apt-get update
sudo apt-get install python3 python3-pip python3-venv

# Install PostgreSQL client (if using PostgreSQL)
sudo apt-get install libpq-dev python3-dev

# Create application user
sudo useradd -r -s /bin/false sbh
sudo mkdir -p /opt/sbh
sudo chown sbh:sbh /opt/sbh
```

#### Application Setup
```bash
# Clone application
sudo -u sbh git clone <repository-url> /opt/sbh
cd /opt/sbh/backend

# Setup virtual environment
sudo -u sbh python3 -m venv venv
sudo -u sbh venv/bin/pip install -r requirements.txt

# Configure environment
sudo -u sbh cp .env.sample .env
# Edit .env with production values

# Initialize database
sudo -u sbh venv/bin/python cli.py init-db
```

#### Systemd Service
Create `/etc/systemd/system/sbh.service`:
```ini
[Unit]
Description=System Builder Hub
After=network.target

[Service]
Type=simple
User=sbh
Group=sbh
WorkingDirectory=/opt/sbh/backend
Environment=PATH=/opt/sbh/backend/venv/bin
ExecStart=/opt/sbh/backend/venv/bin/python cli.py run
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable sbh
sudo systemctl start sbh
sudo systemctl status sbh
```

### 3. Cloud Deployment

#### AWS ECS
```yaml
# task-definition.json
{
  "family": "sbh",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "sbh",
      "image": "sbh:latest",
      "portMappings": [
        {
          "containerPort": 5001,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "FLASK_ENV", "value": "production"},
        {"name": "LLM_SECRET_KEY", "value": "your-key"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/sbh",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:5001/healthz || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
```

#### Google Cloud Run
```bash
# Build and push to Container Registry
gcloud builds submit --tag gcr.io/PROJECT_ID/sbh

# Deploy to Cloud Run
gcloud run deploy sbh \
  --image gcr.io/PROJECT_ID/sbh \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars FLASK_ENV=production,LLM_SECRET_KEY=your-key
```

## Upgrades and Migrations

### Version Upgrade Process
```bash
# 1. Backup current deployment
docker-compose exec sbh python cli.py check > backup-health-$(date +%Y%m%d).log
docker-compose exec postgres pg_dump sbh > backup-db-$(date +%Y%m%d).sql

# 2. Pull latest code
git pull origin main
git fetch --tags

# 3. Check new version
python version.py

# 4. Update environment (if needed)
# Edit .env file with any new required variables

# 5. Build new version
export APP_VERSION=$(python version.py | grep "Version:" | cut -d' ' -f2)
docker-compose build

# 6. Run database migrations
docker-compose exec sbh python cli.py init-db

# 7. Deploy new version
docker-compose up -d

# 8. Verify deployment
python scripts/deploy_verify.py http://localhost:5001

# 9. Monitor logs
docker-compose logs -f sbh
```

### Database Migrations
```bash
# Check migration status
docker-compose exec sbh python -m alembic current

# Run pending migrations
docker-compose exec sbh python -m alembic upgrade head

# Rollback migration (if needed)
docker-compose exec sbh python -m alembic downgrade -1

# Check migration history
docker-compose exec sbh python -m alembic history
```

### Rollback Procedure
```bash
# 1. Stop current deployment
docker-compose down

# 2. Restore previous version
git checkout v1.0.0  # Previous version tag
export APP_VERSION=1.0.0

# 3. Rebuild and deploy
docker-compose build
docker-compose up -d

# 4. Verify rollback
python scripts/deploy_verify.py http://localhost:5001
```

## Monitoring and Health Checks

### Health Check Endpoints
- **Health**: `GET /healthz` - Basic service health with version info
- **Readiness**: `GET /readiness` - Service readiness (DB, LLM, migrations)
- **LLM Status**: `GET /api/llm/status` - LLM provider status

### Monitoring Setup
```bash
# Test health endpoints
curl -f http://localhost:5001/healthz
curl -f http://localhost:5001/readiness

# Run smoke tests
python scripts/smoke.py http://localhost:5001
```

### Logging
```bash
# View application logs
docker-compose logs -f sbh

# Or for systemd
sudo journalctl -u sbh -f

# Check for errors
grep -i error /var/log/sbh/app.log
```

## Backup and Recovery

### Database Backup
```bash
# SQLite backup
cp /opt/sbh/backend/db/sbh.db /backup/sbh-$(date +%Y%m%d).db

# PostgreSQL backup
pg_dump $DATABASE_URL > /backup/sbh-$(date +%Y%m%d).sql
```

### Application Backup
```bash
# Backup application data
tar -czf /backup/sbh-app-$(date +%Y%m%d).tar.gz \
  /opt/sbh/backend/db \
  /opt/sbh/backend/logs \
  /opt/sbh/backend/backups
```

## Security Hardening

### Network Security
```bash
# Configure firewall (Ubuntu/Debian)
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# Configure firewall (CentOS/RHEL)
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

### SSL/TLS Configuration
```bash
# Using Let's Encrypt with Certbot
sudo certbot --nginx -d yourdomain.com

# Or with Apache
sudo certbot --apache -d yourdomain.com
```

### Reverse Proxy (Nginx)
```nginx
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://localhost:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Troubleshooting

### Common Issues

**1. Application won't start**
```bash
# Check logs
docker-compose logs sbh
# Or
sudo journalctl -u sbh -n 50

# Check environment
python cli.py check
```

**2. Database connection issues**
```bash
# Test database connectivity
python cli.py init-db

# Check database file permissions
ls -la db/
```

**3. LLM configuration issues**
```bash
# Check LLM status
curl http://localhost:5001/api/llm/status

# Test LLM connection
curl -X POST http://localhost:5001/api/llm/test
```

**4. Health check failures**
```bash
# Run comprehensive health check
python cli.py check --verbose

# Check individual components
curl http://localhost:5001/healthz
curl http://localhost:5001/readiness
```

### Performance Tuning

**1. Database Optimization**
```sql
-- For SQLite
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA cache_size=10000;
```

**2. Application Tuning**
```bash
# Increase worker processes
export GUNICORN_WORKERS=4
export GUNICORN_THREADS=2

# Memory optimization
export PYTHONOPTIMIZE=1
```

## Maintenance

### Regular Maintenance Tasks
```bash
# Daily
- Check application logs for errors
- Monitor disk space usage
- Verify health endpoints

# Weekly
- Review and rotate logs
- Check for security updates
- Backup database

# Monthly
- Update application dependencies
- Review performance metrics
- Test disaster recovery procedures
```

### Update Procedures
```bash
# 1. Backup current installation
cp -r /opt/sbh /opt/sbh-backup-$(date +%Y%m%d)

# 2. Pull latest code
cd /opt/sbh/backend
git pull origin main

# 3. Update dependencies
venv/bin/pip install -r requirements.txt

# 4. Run migrations
venv/bin/python cli.py init-db

# 5. Restart service
sudo systemctl restart sbh

# 6. Verify deployment
python scripts/smoke.py
```

---

For additional support, see the main documentation and runbook.

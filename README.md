# System Builder Hub (SBH)

A system that builds systems, taking specs as input and outputting bootable applications.

## Phase 3 Deployment Setup

### GitHub Repository Setup

1. Create a new private repository on GitHub: `youareridiculous/system-builder-hub`
2. Set up the following repository variables (Settings > Secrets and variables > Actions > Variables):
   - `AWS_REGION`: `us-west-2`
   - `AWS_ACCOUNT_ID`: `776567512687`
   - `ECR_REPO`: `sbh-repo-dev`
   - `ECS_CLUSTER`: `sbh-cluster-dev`
   - `ECS_SERVICE`: `sbh-service-dev`
   - `APP_URL`: `https://sbh.umbervale.com`
   - `S3_BUCKET_NAME`: `sbh-workspace-dev-b8aedb34`

### AWS IAM Configuration

The following IAM role has been created for GitHub Actions OIDC:

- **Role ARN**: `arn:aws:iam::776567512687:role/sbh-github-oidc-deployer-dev`
- **Trust Policy**: Allows GitHub Actions from `repo:youareridiculous/system-builder-hub:*`
- **Permissions**: ECR push, ECS deploy, CloudWatch Logs, S3 read (least-privilege)

### Deployment Process

Once the repository is created and variables are set:

1. Push this code to the `main` branch
2. The GitHub Actions workflow will automatically:
   - Build ARM64 Docker image with context validation
   - Push to ECR with image verification
   - Deploy to ECS with health checks
   - Apply database schema migrations
   - Verify Phase-3 APIs and S3 functionality

### Guardrails

- **Context Budget**: Max 50MB, 5,000 files
- **Forbidden Paths**: `.venv`, `node_modules`, `__pycache__`, etc.
- **Platform Validation**: ARM64 manifest required
- **Image Size**: Minimum 50MB
- **Health Checks**: All subsystems must be healthy

### Migration Path

- **Primary**: Alembic migrations via `/api/migrate/up`
- **Fallback**: Direct schema fix via `/api/fix-db-schema`
- **Reliability**: Runs in same VPC as application

## Current Status

Phase 3 infrastructure is ready for deployment. The workflow includes:
- Backend-only build context with strict exclusions
- ARM64 Docker builds with validation
- ECS deployment with health monitoring
- Database schema management
- API verification and S3 testing
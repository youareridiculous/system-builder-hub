# System Builder Hub (SBH)

A system that builds systems - takes specs as input and outputs bootable applications.

## �� Current Status

**✅ LIVE AND SECURED**
- **Frontend**: https://sbh.umbervale.com (with authentication)
- **Backend API**: https://sbh.umbervale.com/api/ai-chat/health
- **Authentication**: Login required (admin@sbh.com / TempPass123!@#)

## Architecture

- **One AWS account + one VPC + one ECR repo per env** (dev/prod)
- **SBH backend** runs on ECS Fargate behind ALB with HTTPS and `/api/ai-chat/health` probe
- **SBH frontend** served via CloudFront with custom domain
- **Postgres (RDS) + S3** for workspace storage
- **Secrets in AWS Secrets Manager**
- **GitHub Actions (OIDC)** builds/pushes image → deploys to ECS
- **Terraform** defines everything; one `terraform apply` per env
- **SBH "builder outputs"**: each generated system ships in its own repo with the same pipeline pattern

## 🔐 Authentication

The System Builder Hub is secured with a simple authentication system:

- **Login Required**: All access requires authentication
- **Current Credentials**: 
  - Email: `admin@sbh.com`
  - Password: `TempPass123!@#`
- **Session Management**: Persistent login until logout
- **Future**: Can be upgraded to AWS Cognito for enterprise features

## Configuration

The following environment variables can be configured:

### Required (Production)
- `OPENAI_API_KEY` - OpenAI API key for AI chat functionality (required in production)

### Optional
- `OPENAI_MODEL` - OpenAI model to use (default: gpt-4o-mini)
- `OPENAI_TIMEOUT_SECONDS` - Timeout for OpenAI requests in seconds (default: 20)
- `SECRET_KEY` - Flask secret key (default: dev-secret-key)
- `FLASK_ENV` - Flask environment (default: production)

### AWS ECS Configuration
In production, `OPENAI_API_KEY` is provided via ECS task definition secrets or environment variables. The application will gracefully fall back to echo behavior if the key is not configured.

## Repository Structure
├── infra/ # Terraform for AWS infrastructure
│ ├── modules/ # Reusable Terraform modules
│ │ ├── network/ # VPC, subnets, NAT
│ │ ├── db/ # RDS Postgres
│ │ ├── storage/ # S3 buckets
│ │ ├── ecr/ # Container registries
│ │ ├── iam/ # IAM roles and policies
│ │ ├── alb/ # Application Load Balancer
│ │ └── ecs/ # ECS cluster and service
│ ├── envs/ # Environment-specific configurations
│ │ ├── dev/ # Development environment
│ │ └── prod/ # Production environment
│ └── scripts/ # One-time setup scripts
├── apps/
│ └── backend/ # SBH API application
├── components/ # React UI components
├── app/ # Next.js app directory
├── templates/ # Templates for generated systems
├── .github/
│ └── workflows/ # CI/CD pipelines
└── README.md # This file


## Quick Start

### Prerequisites
- AWS CLI configured
- Terraform >= 1.0
- GitHub repository with Actions enabled
- Node.js >= 18.0.0

### Bootstrap (One-time setup)

1. **Setup GitHub OIDC to AWS**:
   ```bash
   cd infra/scripts
   ./setup-oidc.sh
   # Note the role ARN for GitHub Actions
   ```

2. **Configure secrets in AWS Secrets Manager**:
   ```bash
   # Set these values (one-time)
   aws secretsmanager put-secret-value --secret-id sbh-dev/db-url --secret-string "postgresql://..."
   aws secretsmanager put-secret-value --secret-id sbh-dev/openai-key --secret-string "sk-..."
   aws secretsmanager put-secret-value --secret-id sbh-dev/s3-bucket --secret-string "sbh-workspace-dev-..."
   ```

3. **Deploy infrastructure**:
   ```bash
   cd infra/envs/dev
   terraform init
   terraform plan
   terraform apply
   ```

4. **Configure GitHub repository variables**:
   - `AWS_ACCOUNT_ID`: 776567512687
   - `AWS_REGION`: us-west-2
   - `ECR_REPO`: sbh-repo-dev
   - `ECS_CLUSTER`: sbh-cluster-dev
   - `ECS_SERVICE`: sbh-service-dev
   - `OIDC_ROLE_ARN`: (from step 1)
   - `DOMAIN_NAME`: sbh.umbervale.com

## Frontend Development

### Install dependencies:
```bash
npm install
```

### Run development server:
```bash
npm run dev
```

### Build for production:
```bash
npm run build
npm run export
```

## Deploy

### Build and push image:
- Push to `main` branch triggers build workflow
- Image is pushed to ECR with tag = short SHA

### Deploy to ECS:
- Run "Deploy" workflow manually or on release tags
- New task definition is registered
- ECS service is updated with `--force-new-deployment`

### Verify deployment:
```bash
curl -sS "https://sbh.umbervale.com/api/ai-chat/health" | jq .
# Should return: {"status":"healthy",...}
```

## Rollback

### Quick rollback:
- Run "Deploy" workflow with previous image tag
- ECS will roll back to previous task definition

### Emergency rollback:
```bash
aws ecs update-service \
  --cluster sbh-cluster-dev \
  --service sbh-service-dev \
  --task-definition sbh-task-dev:PREVIOUS_REVISION \
  --force-new-deployment
```

## Development

### Local Development
```bash
cd apps/backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m src.server
```

### Database Migrations
```bash
# Run migrations
make migrate

# Run migrations online (during deployment)
make migrate:online
```

## Monitoring

### Health Checks
- **Application**: `https://sbh.umbervale.com/api/ai-chat/health`
- **Load Balancer**: ALB health checks on `/api/ai-chat/health`
- **ECS**: Service health via CloudWatch

### Logs
```bash
# Get last 200 lines of container logs
aws logs tail /ecs/sbh-backend --follow --since 1h
```

### Alarms
- **Target Group Unhealthy Hosts** > 0 for 5 minutes → SNS notification
- **ECS Service CPU/Memory** utilization alarms

## Generated Systems

Each system built by SBH follows the same pattern:
- Independent repository
- Same infrastructure pattern (VPC, ECS, ALB, RDS, S3)
- Same CI/CD pipeline (GitHub Actions + OIDC)
- Health endpoint for monitoring
- Rollback capabilities

See `templates/TEMPLATE_GUIDE.md` for the contract each generated system must follow.

## Troubleshooting

See `apps/backend/RUNBOOK.md` for common issues and solutions.

## Security

- **No hardcoded secrets** - all secrets in AWS Secrets Manager
- **OIDC authentication** - no long-lived AWS access keys
- **Least privilege IAM** - minimal required permissions
- **HTTPS only** - HTTP redirects to HTTPS
- **Private subnets** - database and ECS tasks in private subnets
- **Frontend Authentication** - Login required for all access

## Frontend Features

- **AI Chat Interface** - Real-time chat with OpenAI models
- **System Builder** - Step-by-step system configuration
- **Model Selection** - Choose between GPT-4o, GPT-4o Mini, and GPT-4 Turbo
- **Responsive Design** - Mobile-first approach with Tailwind CSS
- **TypeScript** - Full type safety and IntelliSense
- **Component Library** - Reusable UI components
- **Authentication** - Secure login system

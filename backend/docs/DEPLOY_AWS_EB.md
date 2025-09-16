# Deploying Flagship CRM & Ops to AWS Elastic Beanstalk

This guide provides step-by-step instructions for deploying the Flagship CRM & Ops template to AWS Elastic Beanstalk.

## 🎯 Prerequisites

### AWS Account Setup
- AWS account with appropriate permissions
- AWS CLI installed and configured
- EB CLI installed (`pip install awsebcli`)

### Required AWS Services
- **Elastic Beanstalk**: Application hosting
- **RDS PostgreSQL**: Database
- **ElastiCache Redis**: Caching and sessions
- **S3**: File storage
- **SES**: Email service
- **IAM**: Service roles and permissions

## 🚀 Quick Deployment

### 1. Environment Setup

```bash
# Clone the repository
git clone <repository-url>
cd flagship-crm-ops

# Initialize EB application
eb init flagship-crm-ops \
  --platform python-3.9 \
  --region us-east-1

# Create environment
eb create flagship-crm-ops-prod \
  --instance-type t3.medium \
  --database.engine postgres \
  --database.instance db.t3.micro \
  --database.username sbh_user \
  --database.password <secure-password> \
  --elb-type application \
  --envvars \
    FLASK_ENV=production \
    SECRET_KEY=<your-secret-key> \
    JWT_SECRET_KEY=<your-jwt-secret>
```

### 2. Configure Environment Variables

```bash
# Set required environment variables
eb setenv \
  DATABASE_URL=postgresql://sbh_user:<password>@<rds-endpoint>:5432/sbh_crm \
  REDIS_URL=redis://<elasticache-endpoint>:6379/0 \
  S3_BUCKET_NAME=sbh-crm-files-<unique-id> \
  STRIPE_SECRET_KEY=<your-stripe-secret> \
  SES_ACCESS_KEY=<your-ses-access-key> \
  SES_SECRET_KEY=<your-ses-secret-key>
```

### 3. Deploy Application

```bash
# Deploy to EB
eb deploy

# Check deployment status
eb status
eb health
```

## 🔧 Advanced Configuration

### Database Configuration

#### RDS PostgreSQL Setup
```bash
# Create RDS instance
aws rds create-db-instance \
  --db-instance-identifier sbh-crm-db \
  --db-instance-class db.t3.micro \
  --engine postgresql \
  --master-username sbh_user \
  --master-user-password <secure-password> \
  --allocated-storage 20 \
  --storage-type gp2 \
  --backup-retention-period 7 \
  --multi-az \
  --vpc-security-group-ids sg-xxxxxxxxx

# Get connection details
aws rds describe-db-instances \
  --db-instance-identifier sbh-crm-db
```

#### Database Migrations
```bash
# Run migrations
eb ssh
cd /var/app/current
python -m alembic upgrade head
```

### Redis Configuration

#### ElastiCache Setup
```bash
# Create ElastiCache cluster
aws elasticache create-cache-cluster \
  --cache-cluster-id sbh-crm-redis \
  --cache-node-type cache.t3.micro \
  --engine redis \
  --num-cache-nodes 1 \
  --vpc-security-group-ids sg-xxxxxxxxx

# Get endpoint
aws elasticache describe-cache-clusters \
  --cache-cluster-id sbh-crm-redis
```

### S3 Configuration

#### File Storage Setup
```bash
# Create S3 bucket
aws s3 mb s3://sbh-crm-files-<unique-id>

# Configure CORS
aws s3api put-bucket-cors \
  --bucket sbh-crm-files-<unique-id> \
  --cors-configuration '{
    "CORSRules": [
      {
        "AllowedHeaders": ["*"],
        "AllowedMethods": ["GET", "POST", "PUT", "DELETE"],
        "AllowedOrigins": ["*"],
        "ExposeHeaders": []
      }
    ]
  }'

# Create IAM user for S3 access
aws iam create-user --user-name sbh-crm-s3-user

# Attach S3 policy
aws iam attach-user-policy \
  --user-name sbh-crm-s3-user \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
```

### Email Configuration

#### SES Setup
```bash
# Verify domain
aws ses verify-domain-identity --domain yourdomain.com

# Create SES user
aws iam create-user --user-name sbh-crm-ses-user

# Attach SES policy
aws iam attach-user-policy \
  --user-name sbh-crm-ses-user \
  --policy-arn arn:aws:iam::aws:policy/AmazonSESFullAccess
```

## 🛡️ Security Configuration

### VPC and Security Groups

#### VPC Setup
```bash
# Create VPC
aws ec2 create-vpc \
  --cidr-block 10.0.0.0/16 \
  --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=sbh-crm-vpc}]'

# Create subnets
aws ec2 create-subnet \
  --vpc-id vpc-xxxxxxxxx \
  --cidr-block 10.0.1.0/24 \
  --availability-zone us-east-1a

aws ec2 create-subnet \
  --vpc-id vpc-xxxxxxxxx \
  --cidr-block 10.0.2.0/24 \
  --availability-zone us-east-1b
```

#### Security Groups
```bash
# EB security group
aws ec2 create-security-group \
  --group-name sbh-crm-eb-sg \
  --description "Security group for EB application" \
  --vpc-id vpc-xxxxxxxxx

# RDS security group
aws ec2 create-security-group \
  --group-name sbh-crm-rds-sg \
  --description "Security group for RDS" \
  --vpc-id vpc-xxxxxxxxx

# Redis security group
aws ec2 create-security-group \
  --group-name sbh-crm-redis-sg \
  --description "Security group for Redis" \
  --vpc-id vpc-xxxxxxxxx
```

### SSL/TLS Configuration

#### Certificate Setup
```bash
# Request certificate
aws acm request-certificate \
  --domain-name yourdomain.com \
  --subject-alternative-names *.yourdomain.com \
  --validation-method DNS

# Configure ALB listener
aws elbv2 create-listener \
  --load-balancer-arn arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/sbh-crm/xxxxxxxxx \
  --protocol HTTPS \
  --port 443 \
  --certificates CertificateArn=arn:aws:acm:us-east-1:123456789012:certificate/xxxxxxxxx \
  --default-actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:us-east-1:123456789012:targetgroup/sbh-crm/xxxxxxxxx
```

## 📊 Monitoring and Logging

### CloudWatch Configuration

#### Log Groups
```bash
# Create log groups
aws logs create-log-group --log-group-name /aws/elasticbeanstalk/sbh-crm/application
aws logs create-log-group --log-group-name /aws/elasticbeanstalk/sbh-crm/environment-health
aws logs create-log-group --log-group-name /aws/elasticbeanstalk/sbh-crm/performance
```

#### Alarms
```bash
# CPU utilization alarm
aws cloudwatch put-metric-alarm \
  --alarm-name sbh-crm-cpu-high \
  --alarm-description "High CPU utilization" \
  --metric-name CPUUtilization \
  --namespace AWS/ElasticBeanstalk \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2

# Memory utilization alarm
aws cloudwatch put-metric-alarm \
  --alarm-name sbh-crm-memory-high \
  --alarm-description "High memory utilization" \
  --metric-name MemoryUtilization \
  --namespace AWS/ElasticBeanstalk \
  --statistic Average \
  --period 300 \
  --threshold 85 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2
```

### Application Monitoring

#### Health Checks
```bash
# Configure health check endpoint
eb config
# Add to .ebextensions/healthcheck.config:
option_settings:
  aws:elasticbeanstalk:application:
    Application Healthcheck URL: /healthz
  aws:elasticbeanstalk:environment:process:default:
    HealthCheckPath: /healthz
    HealthCheckInterval: 30
    HealthCheckTimeout: 5
    HealthyThresholdCount: 3
    UnhealthyThresholdCount: 5
```

## 🔄 CI/CD Pipeline

### GitHub Actions Setup

#### Workflow Configuration
```yaml
# .github/workflows/deploy.yml
name: Deploy to EB

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v1
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      
      - name: Deploy to EB
        run: |
          eb deploy flagship-crm-ops-prod
```

### Deployment Scripts

#### Automated Deployment
```bash
#!/bin/bash
# scripts/deploy.sh

set -e

echo "🚀 Starting deployment..."

# Run tests
echo "🧪 Running tests..."
python -m pytest tests/ -v

# Run smoke tests
echo "🔥 Running smoke tests..."
python scripts/smoke_e2e.py

# Deploy to EB
echo "📦 Deploying to Elastic Beanstalk..."
eb deploy flagship-crm-ops-prod

# Wait for deployment
echo "⏳ Waiting for deployment to complete..."
eb status

# Run post-deployment checks
echo "✅ Running post-deployment checks..."
python scripts/smoke_e2e.py $EB_URL $AUTH_TOKEN $TENANT_ID

echo "🎉 Deployment completed successfully!"
```

## 🔧 Environment-Specific Configuration

### Development Environment
```bash
# Create dev environment
eb create flagship-crm-ops-dev \
  --instance-type t3.small \
  --database.instance db.t3.micro \
  --envvars FLASK_ENV=development
```

### Staging Environment
```bash
# Create staging environment
eb create flagship-crm-ops-staging \
  --instance-type t3.medium \
  --database.instance db.t3.small \
  --envvars FLASK_ENV=staging
```

### Production Environment
```bash
# Create production environment
eb create flagship-crm-ops-prod \
  --instance-type t3.large \
  --database.instance db.t3.medium \
  --envvars FLASK_ENV=production
```

## 🚨 Troubleshooting

### Common Issues

#### Database Connection Issues
```bash
# Check RDS connectivity
eb ssh
telnet <rds-endpoint> 5432

# Check database logs
aws logs describe-log-streams \
  --log-group-name /aws/rds/instance/sbh-crm-db/postgresql
```

#### Redis Connection Issues
```bash
# Check Redis connectivity
eb ssh
telnet <elasticache-endpoint> 6379

# Check Redis logs
aws logs describe-log-streams \
  --log-group-name /aws/elasticache/sbh-crm-redis
```

#### Application Errors
```bash
# Check application logs
eb logs

# SSH into instance
eb ssh

# Check application status
sudo systemctl status web
sudo systemctl status worker
```

### Performance Optimization

#### Auto Scaling Configuration
```bash
# Configure auto scaling
eb config
# Add to .ebextensions/autoscaling.config:
option_settings:
  aws:autoscaling:asg:
    MinSize: 2
    MaxSize: 10
  aws:autoscaling:trigger:
    BreachDuration: 5
    LowerBreachScaleIncrement: -1
    UpperBreachScaleIncrement: 1
    LowerThreshold: 30
    UpperThreshold: 70
```

#### Database Optimization
```bash
# Enable RDS Performance Insights
aws rds modify-db-instance \
  --db-instance-identifier sbh-crm-db \
  --enable-performance-insights \
  --performance-insights-retention-period 7
```

## 📋 Maintenance

### Backup Strategy
```bash
# Automated backups
aws rds create-db-snapshot \
  --db-instance-identifier sbh-crm-db \
  --db-snapshot-identifier sbh-crm-backup-$(date +%Y%m%d)

# Cross-region backup
aws rds copy-db-snapshot \
  --source-db-snapshot-identifier sbh-crm-backup-20240826 \
  --target-db-snapshot-identifier sbh-crm-backup-20240826-dr \
  --source-region us-east-1 \
  --target-region us-west-2
```

### Updates and Patches
```bash
# Update application
eb deploy

# Update database
aws rds modify-db-instance \
  --db-instance-identifier sbh-crm-db \
  --apply-immediately

# Update EB platform
eb platform upgrade
```

## 📞 Support

### Getting Help
- **Documentation**: [SBH Documentation](https://docs.sbh.com)
- **Community**: [SBH Community Forum](https://community.sbh.com)
- **Support**: support@sbh.com
- **Emergency**: +1-555-0123 (24/7)

### Useful Commands
```bash
# Check environment status
eb status

# View logs
eb logs

# SSH into environment
eb ssh

# Open application
eb open

# Terminate environment
eb terminate flagship-crm-ops-prod
```

---

*This guide covers the essential steps for deploying Flagship CRM & Ops to AWS Elastic Beanstalk. For advanced configurations and troubleshooting, refer to the AWS documentation and SBH support resources.*

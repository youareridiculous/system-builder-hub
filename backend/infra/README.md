# SBH AWS Infrastructure - Phase 1 Cloud Migration

This directory contains Terraform configuration for deploying SBH to AWS with ECS, RDS, S3, and Application Load Balancer.

## Prerequisites

1. **AWS CLI configured** with appropriate credentials
2. **Terraform installed** (version >= 1.0)
3. **Required variables** set in `terraform.tfvars`

## Quick Start

### 1. Configure Variables

```bash
# Copy the example variables file
cp terraform.tfvars.example terraform.tfvars

# Edit terraform.tfvars with your actual values
nano terraform.tfvars
```

### 2. Initialize and Deploy

```bash
# Initialize Terraform
terraform init

# Plan the deployment
terraform plan

# Apply the configuration
terraform apply
```

### 3. Get Outputs

```bash
# View all outputs
terraform output

# Get specific outputs
terraform output alb_dns_name
terraform output rds_endpoint
terraform output s3_bucket_name
```

## Infrastructure Components

### VPC and Networking
- **VPC**: 10.0.0.0/16 CIDR block
- **Public Subnets**: 2 subnets across AZs for ALB
- **Private Subnets**: 2 subnets across AZs for RDS
- **Internet Gateway**: For public internet access
- **Route Tables**: Proper routing configuration

### Security Groups
- **ALB Security Group**: Allows HTTP/HTTPS traffic from internet
- **ECS Security Group**: Allows traffic from ALB to ECS tasks
- **RDS Security Group**: Allows PostgreSQL traffic from ECS

### RDS PostgreSQL Database
- **Engine**: PostgreSQL 15.4
- **Instance Class**: db.t3.micro (configurable)
- **Storage**: 20GB allocated, up to 100GB auto-scaling
- **Backup**: 7-day retention (configurable)
- **Encryption**: Enabled at rest

### S3 Bucket
- **Purpose**: Store workspace files and build artifacts
- **Versioning**: Enabled
- **Encryption**: AES256 server-side encryption
- **Naming**: Unique bucket name with random suffix

### ECS Cluster
- **Type**: Fargate-ready cluster
- **Container Insights**: Enabled for monitoring
- **Auto Scaling**: Ready for future implementation

### Application Load Balancer
- **Type**: Application Load Balancer
- **Health Checks**: Configured for `/api/health` endpoint
- **Target Group**: Routes traffic to ECS tasks on port 8000

## Environment-Specific Configuration

### Development Environment
```hcl
environment = "dev"
enable_deletion_protection = false
db_instance_class = "db.t3.micro"
```

### Production Environment
```hcl
environment = "prod"
enable_deletion_protection = true
db_instance_class = "db.t3.small"
backup_retention_period = 30
```

## Security Considerations

1. **Database Password**: Use a strong, unique password
2. **OpenAI API Key**: Keep secure and rotate regularly
3. **Security Groups**: Follow principle of least privilege
4. **Encryption**: All data encrypted at rest and in transit
5. **Backup**: Regular automated backups enabled

## Cost Optimization

- **RDS**: Start with db.t3.micro, scale as needed
- **ECS**: Use Fargate for serverless container management
- **S3**: Lifecycle policies can be added for cost optimization
- **ALB**: Only pay for actual usage

## Monitoring and Logging

- **CloudWatch**: Container insights enabled
- **RDS**: Enhanced monitoring available
- **ALB**: Access logs can be enabled
- **ECS**: Task logs go to CloudWatch

## Next Steps (Phase 2)

1. **ECS Task Definition**: Deploy SBH backend containers
2. **Service Discovery**: Configure ECS service
3. **Auto Scaling**: Implement scaling policies
4. **SSL/TLS**: Add HTTPS with ACM certificates
5. **CloudFront**: Add CDN for global distribution

## Troubleshooting

### Common Issues

1. **Terraform State**: Keep state file secure and backed up
2. **Resource Limits**: Check AWS service limits
3. **Permissions**: Ensure IAM user has required permissions
4. **Networking**: Verify security group rules

### Useful Commands

```bash
# Refresh state
terraform refresh

# Import existing resources
terraform import aws_instance.example i-1234567890abcdef0

# Destroy infrastructure (use with caution)
terraform destroy
```

## Support

For issues with this infrastructure:
1. Check Terraform documentation
2. Review AWS service documentation
3. Check security group and networking configuration
4. Verify IAM permissions

# SBH AWS Infrastructure - Phase 1 Cloud Migration
# Terraform configuration for ECS, RDS, S3, and ALB

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Configure the AWS Provider
provider "aws" {
  region = var.aws_region
}

# Variables are defined in variables.tf

# =============================================================================
# DATA SOURCES
# =============================================================================

data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_caller_identity" "current" {}

# Get AWS Account ID for ECR repository
locals {
  aws_account_id = data.aws_caller_identity.current.account_id
}

# =============================================================================
# VPC AND NETWORKING
# =============================================================================

resource "aws_vpc" "sbh_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name        = "${var.project_name}-vpc-${var.environment}"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_internet_gateway" "sbh_igw" {
  vpc_id = aws_vpc.sbh_vpc.id

  tags = {
    Name        = "${var.project_name}-igw-${var.environment}"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_subnet" "sbh_public_subnets" {
  count = 2

  vpc_id                  = aws_vpc.sbh_vpc.id
  cidr_block              = "10.0.${count.index + 1}.0/24"
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name        = "${var.project_name}-public-subnet-${count.index + 1}-${var.environment}"
    Environment = var.environment
    Project     = var.project_name
    Type        = "public"
  }
}

resource "aws_subnet" "sbh_private_subnets" {
  count = 2

  vpc_id            = aws_vpc.sbh_vpc.id
  cidr_block        = "10.0.${count.index + 10}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name        = "${var.project_name}-private-subnet-${count.index + 1}-${var.environment}"
    Environment = var.environment
    Project     = var.project_name
    Type        = "private"
  }
}

resource "aws_route_table" "sbh_public_rt" {
  vpc_id = aws_vpc.sbh_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.sbh_igw.id
  }

  tags = {
    Name        = "${var.project_name}-public-rt-${var.environment}"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_route_table_association" "sbh_public_rta" {
  count = 2

  subnet_id      = aws_subnet.sbh_public_subnets[count.index].id
  route_table_id = aws_route_table.sbh_public_rt.id
}

# =============================================================================
# SECURITY GROUPS
# =============================================================================

resource "aws_security_group" "sbh_alb_sg" {
  name_prefix = "${var.project_name}-alb-sg-${var.environment}"
  vpc_id      = aws_vpc.sbh_vpc.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.project_name}-alb-sg-${var.environment}"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_security_group" "sbh_ecs_sg" {
  name_prefix = "${var.project_name}-ecs-sg-${var.environment}"
  vpc_id      = aws_vpc.sbh_vpc.id

  ingress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.sbh_alb_sg.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.project_name}-ecs-sg-${var.environment}"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_security_group" "sbh_rds_sg" {
  name_prefix = "${var.project_name}-rds-sg-${var.environment}"
  vpc_id      = aws_vpc.sbh_vpc.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.sbh_ecs_sg.id]
  }

  tags = {
    Name        = "${var.project_name}-rds-sg-${var.environment}"
    Environment = var.environment
    Project     = var.project_name
  }
}

# =============================================================================
# S3 BUCKET FOR WORKSPACE FILES
# =============================================================================

resource "aws_s3_bucket" "sbh_workspace" {
  bucket = "${var.project_name}-workspace-${var.environment}-${random_id.bucket_suffix.hex}"

  tags = {
    Name        = "${var.project_name}-workspace-${var.environment}"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "random_id" "bucket_suffix" {
  byte_length = 4
}

resource "aws_s3_bucket_versioning" "sbh_workspace_versioning" {
  bucket = aws_s3_bucket.sbh_workspace.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "sbh_workspace_encryption" {
  bucket = aws_s3_bucket.sbh_workspace.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# =============================================================================
# RDS POSTGRESQL DATABASE
# =============================================================================

resource "aws_db_subnet_group" "sbh_db_subnet_group" {
  name       = "${var.project_name}-db-subnet-group-${var.environment}"
  subnet_ids = aws_subnet.sbh_private_subnets[*].id

  tags = {
    Name        = "${var.project_name}-db-subnet-group-${var.environment}"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_db_instance" "sbh_db" {
  identifier = "${var.project_name}-db-${var.environment}"

  engine         = "postgres"
  engine_version = "15.12"
  instance_class = "db.t3.micro"

  allocated_storage     = 20
  max_allocated_storage = 100
  storage_type          = "gp2"
  storage_encrypted     = true

  db_name  = "sbh_db"
  username = var.db_username
  password = var.db_password

  vpc_security_group_ids = [aws_security_group.sbh_rds_sg.id]
  db_subnet_group_name   = aws_db_subnet_group.sbh_db_subnet_group.name

  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"

  skip_final_snapshot = var.environment != "prod"
  deletion_protection = var.environment == "prod"

  tags = {
    Name        = "${var.project_name}-db-${var.environment}"
    Environment = var.environment
    Project     = var.project_name
  }
}

# =============================================================================
# ECS CLUSTER
# =============================================================================

resource "aws_ecs_cluster" "sbh_cluster" {
  name = "${var.project_name}-cluster-${var.environment}"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Name        = "${var.project_name}-cluster-${var.environment}"
    Environment = var.environment
    Project     = var.project_name
  }
}

# =============================================================================
# APPLICATION LOAD BALANCER
# =============================================================================

resource "aws_lb" "sbh_alb" {
  name               = "${var.project_name}-alb-${var.environment}"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.sbh_alb_sg.id]
  subnets            = aws_subnet.sbh_public_subnets[*].id

  enable_deletion_protection = var.environment == "prod"

  tags = {
    Name        = "${var.project_name}-alb-${var.environment}"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_lb_target_group" "sbh_tg" {
  name        = "${var.project_name}-tg-${var.environment}"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.sbh_vpc.id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 2
    timeout             = 5
    interval            = 30
    path                = "/api/health"
    matcher             = "200"
    port                = "traffic-port"
    protocol            = "HTTP"
  }

  tags = {
    Name        = "${var.project_name}-tg-${var.environment}"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_lb_listener" "sbh_listener" {
  load_balancer_arn = aws_lb.sbh_alb.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.sbh_tg.arn
  }

  tags = {
    Name        = "${var.project_name}-http-listener-${var.environment}"
    Environment = var.environment
    Project     = var.project_name
  }
}

# =============================================================================
# OUTPUTS
# =============================================================================

output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.sbh_vpc.id
}

output "alb_dns_name" {
  description = "DNS name of the load balancer - Copy this for GoDaddy CNAME record"
  value       = aws_lb.sbh_alb.dns_name
}

output "alb_zone_id" {
  description = "Zone ID of the load balancer"
  value       = aws_lb.sbh_alb.zone_id
}

output "rds_endpoint" {
  description = "RDS instance endpoint"
  value       = aws_db_instance.sbh_db.endpoint
}

output "s3_bucket_name" {
  description = "Name of the S3 bucket"
  value       = aws_s3_bucket.sbh_workspace.bucket
}

output "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  value       = aws_ecs_cluster.sbh_cluster.name
}

output "ecs_cluster_arn" {
  description = "ARN of the ECS cluster"
  value       = aws_ecs_cluster.sbh_cluster.arn
}

output "ecr_repository_uri" {
  description = "URI of the ECR repository"
  value       = aws_ecr_repository.sbh_repo.repository_url
}

output "ecr_repository_name" {
  description = "Name of the ECR repository"
  value       = aws_ecr_repository.sbh_repo.name
}

output "ecs_service_name" {
  description = "Name of the ECS service"
  value       = aws_ecs_service.sbh_service.name
}


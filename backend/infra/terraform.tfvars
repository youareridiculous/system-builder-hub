# SBH Terraform Variables - Phase 2 Cloud Deployment
# Production configuration for sbh.umbervale.com

# =============================================================================
# REQUIRED VARIABLES
# =============================================================================

# AWS Configuration
aws_region   = "us-west-2"
environment  = "dev"
project_name = "sbh"

# Database Configuration
db_username  = "sbhadmin"
db_password  = "BrokenWood2025!"

# OpenAI Configuration
openai_api_key = "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"

# Flask Configuration
secret_key     = "N8U0ScucZ7e67JvLYZi1gflAr_4Jq8amhOiCwf5APcmstrS6hNYXSFSFXzqGaCZy"

# =============================================================================
# OPTIONAL VARIABLES
# =============================================================================

# Database Configuration
db_instance_class        = "db.t3.micro"
db_allocated_storage     = 20
db_max_allocated_storage = 100

# Security Configuration
enable_deletion_protection = false
backup_retention_period    = 7

# Additional Tags
tags = {
  Owner      = "Eric Larson"
  Project    = "sbh"
  Environment = "dev"
  ManagedBy  = "terraform"
}
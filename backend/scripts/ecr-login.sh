#!/bin/bash
set -euo pipefail

# ECR Login Script for SBH Deployment
# Logs into ECR for us-west-2 region

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
AWS_REGION="${AWS_REGION:-us-west-2}"
ACCOUNT_ID="${ACCOUNT_ID:-776567512687}"

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Check required tools
check_dependencies() {
    local missing_deps=()
    
    if ! command -v aws &> /dev/null; then
        missing_deps+=("aws")
    fi
    
    if ! command -v docker &> /dev/null; then
        missing_deps+=("docker")
    fi
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        error "Missing required dependencies: ${missing_deps[*]}"
        error "Please install:"
        for dep in "${missing_deps[@]}"; do
            case $dep in
                aws) error "  - AWS CLI: https://aws.amazon.com/cli/" ;;
                docker) error "  - Docker: https://docs.docker.com/get-docker/" ;;
            esac
        done
        exit 1
    fi
}

# Verify AWS credentials
verify_aws_credentials() {
    log "Verifying AWS credentials..."
    if ! aws sts get-caller-identity --region "$AWS_REGION" &> /dev/null; then
        error "AWS credentials not configured or invalid"
        error "Run: aws configure"
        exit 1
    fi
    
    local caller_identity
    caller_identity=$(aws sts get-caller-identity --region "$AWS_REGION" --output text --query 'Account')
    log "AWS Account: $caller_identity"
    
    if [ "$caller_identity" != "$ACCOUNT_ID" ]; then
        warn "Expected account ID: $ACCOUNT_ID, got: $caller_identity"
    fi
}

# Login to ECR
ecr_login() {
    log "Logging into ECR for region: $AWS_REGION"
    
    if aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"; then
        success "Successfully logged into ECR"
    else
        error "Failed to login to ECR"
        exit 1
    fi
}

# Main execution
main() {
    log "Starting ECR login process..."
    
    check_dependencies
    verify_aws_credentials
    ecr_login
    
    success "ECR login completed successfully"
}

# Run main function
main "$@"

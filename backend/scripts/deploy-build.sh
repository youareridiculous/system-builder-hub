#!/bin/bash
set -euo pipefail

# Build and Push Script for SBH Deployment
# Builds Docker image and pushes to ECR

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
AWS_REGION="${AWS_REGION:-us-west-2}"
ECR_REPO="${ECR_REPO:-sbh-repo-dev}"
ACCOUNT_ID="${ACCOUNT_ID:-776567512687}"
DOCKERFILE="${DOCKERFILE:-backend/Dockerfile}"
CONTEXT="${CONTEXT:-.}"

# Generate image tag
if [ -n "${IMAGE_TAG:-}" ]; then
    IMAGE_TAG="$IMAGE_TAG"
else
    # Default: timestamp + git SHA
    TIMESTAMP=$(date +%Y%m%d%H%M)
    GIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "local")
    IMAGE_TAG="${TIMESTAMP}-${GIT_SHA}"
fi

# Full image URI
IMAGE_URI="$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO:$IMAGE_TAG"

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
    
    if ! command -v git &> /dev/null; then
        missing_deps+=("git")
    fi
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        error "Missing required dependencies: ${missing_deps[*]}"
        exit 1
    fi
}

# Source ECR login script
source_ecr_login() {
    local script_dir
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    
    if [ -f "$script_dir/ecr-login.sh" ]; then
        log "Sourcing ECR login script..."
        source "$script_dir/ecr-login.sh"
    else
        error "ECR login script not found at: $script_dir/ecr-login.sh"
        exit 1
    fi
}

# Verify build context
verify_build_context() {
    log "Verifying build context..."
    
    # Check if we're in the right directory
    if [ ! -f "$DOCKERFILE" ]; then
        error "Dockerfile not found at: $DOCKERFILE"
        error "Current directory: $(pwd)"
        error "Expected to find: $DOCKERFILE"
        exit 1
    fi
    
    # Check if backend directory exists
    if [ ! -d "backend" ]; then
        error "backend directory not found"
        error "Please run this script from the repository root"
        exit 1
    fi
    
    log "Build context verified"
    log "Dockerfile: $DOCKERFILE"
    log "Context: $CONTEXT"
}

# Build Docker image
build_image() {
    log "Building Docker image..."
    log "Image tag: $IMAGE_TAG"
    log "Full URI: $IMAGE_URI"
    
    # Build the image
    if docker build -f "$DOCKERFILE" -t "$IMAGE_URI" "$CONTEXT"; then
        success "Docker image built successfully"
    else
        error "Failed to build Docker image"
        exit 1
    fi
}

# Push image to ECR
push_image() {
    log "Pushing image to ECR..."
    
    if docker push "$IMAGE_URI"; then
        success "Image pushed to ECR successfully"
    else
        error "Failed to push image to ECR"
        exit 1
    fi
}

# Verify image exists in ECR
verify_image() {
    log "Verifying image exists in ECR..."
    
    if aws ecr describe-images --repository-name "$ECR_REPO" --region "$AWS_REGION" --image-ids imageTag="$IMAGE_TAG" &> /dev/null; then
        success "Image verified in ECR"
    else
        error "Image not found in ECR after push"
        exit 1
    fi
}

# Main execution
main() {
    log "Starting build and push process..."
    log "Configuration:"
    log "  AWS Region: $AWS_REGION"
    log "  ECR Repo: $ECR_REPO"
    log "  Account ID: $ACCOUNT_ID"
    log "  Image Tag: $IMAGE_TAG"
    log "  Image URI: $IMAGE_URI"
    
    check_dependencies
    source_ecr_login
    verify_build_context
    build_image
    push_image
    verify_image
    
    success "Build and push completed successfully"
    echo ""
    echo -e "${GREEN}Image URI:${NC} $IMAGE_URI"
    echo -e "${GREEN}Image Tag:${NC} $IMAGE_TAG"
    echo ""
    
    # Export for use by other scripts
    export IMAGE_URI
    export IMAGE_TAG
}

# Run main function
main "$@"

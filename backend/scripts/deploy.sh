#!/bin/bash
set -euo pipefail

# Main Deployment Orchestrator for SBH
# Orchestrates the complete deployment process

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
HOST="${HOST:-sbh.umbervale.com}"
ALB_DNS="${ALB_DNS:-}"

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

info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

header() {
    echo -e "${PURPLE}================================${NC}"
    echo -e "${PURPLE}$1${NC}"
    echo -e "${PURPLE}================================${NC}"
}

# Get script directory
get_script_dir() {
    local script_dir
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    echo "$script_dir"
}

# Check if we're in the right directory
check_directory() {
    if [ ! -f "backend/Dockerfile" ]; then
        error "backend/Dockerfile not found"
        error "Please run this script from the repository root"
        exit 1
    fi
}

# Run build and push
run_build() {
    local script_dir
    script_dir=$(get_script_dir)
    
    header "STEP 1: BUILD AND PUSH"
    
    if [ -f "$script_dir/deploy-build.sh" ]; then
        log "Running build and push script..."
        source "$script_dir/deploy-build.sh"
        
        # Extract IMAGE_URI from the output
        if [ -n "${IMAGE_URI:-}" ]; then
            success "Build completed successfully"
            info "Image URI: $IMAGE_URI"
            info "Image Tag: $IMAGE_TAG"
        else
            error "Failed to get IMAGE_URI from build script"
            exit 1
        fi
    else
        error "Build script not found: $script_dir/deploy-build.sh"
        exit 1
    fi
}

# Run ECS rollout
run_rollout() {
    local script_dir
    script_dir=$(get_script_dir)
    
    header "STEP 2: ECS ROLLOUT"
    
    if [ -n "${IMAGE_URI:-}" ]; then
        log "Running ECS rollout with image: $IMAGE_URI"
        
        if [ -f "$script_dir/ecs-rollout.sh" ]; then
            IMAGE_URI="$IMAGE_URI" source "$script_dir/ecs-rollout.sh"
            
            if [ -n "${NEW_TASK_DEF_ARN:-}" ] && [ -n "${TASK_REVISION:-}" ]; then
                success "ECS rollout completed successfully"
                info "New Task Definition: $NEW_TASK_DEF_ARN"
                info "Revision: $TASK_REVISION"
            else
                error "Failed to get task definition info from rollout script"
                exit 1
            fi
        else
            error "Rollout script not found: $script_dir/ecs-rollout.sh"
            exit 1
        fi
    else
        error "IMAGE_URI not available for rollout"
        exit 1
    fi
}

# Run verification
run_verification() {
    local script_dir
    script_dir=$(get_script_dir)
    
    header "STEP 3: DEPLOYMENT VERIFICATION"
    
    if [ -f "$script_dir/verify-deploy.sh" ]; then
        log "Running deployment verification..."
        
        # Set environment variables for verification
        export HOST="$HOST"
        if [ -n "$ALB_DNS" ]; then
            export ALB_DNS="$ALB_DNS"
        fi
        
        source "$script_dir/verify-deploy.sh"
        
        success "Verification completed successfully"
    else
        error "Verification script not found: $script_dir/verify-deploy.sh"
        exit 1
    fi
}

# Print final summary
print_summary() {
    header "DEPLOYMENT SUMMARY"
    
    info "🎉 SBH Deployment Completed Successfully!"
    echo ""
    info "Deployment Details:"
    info "  Image URI: ${IMAGE_URI:-'N/A'}"
    info "  Image Tag: ${IMAGE_TAG:-'N/A'}"
    info "  Task Definition: ${NEW_TASK_DEF_ARN:-'N/A'}"
    info "  Revision: ${TASK_REVISION:-'N/A'}"
    info "  Service: sbh-service-dev"
    info "  Cluster: sbh-cluster-dev"
    echo ""
    info "Access URLs:"
    info "  HTTPS: https://$HOST"
    info "  Health: https://$HOST/api/health"
    if [ -n "$ALB_DNS" ]; then
        info "  ALB Direct: http://$ALB_DNS"
    fi
    echo ""
    success "Deployment is live and healthy! 🚀"
}

# Main execution
main() {
    header "SBH DEPLOYMENT ORCHESTRATOR"
    
    log "Starting complete deployment process..."
    log "Configuration:"
    log "  Host: $HOST"
    log "  ALB DNS: ${ALB_DNS:-'not provided'}"
    echo ""
    
    # Check directory
    check_directory
    
    # Run deployment steps
    run_build
    echo ""
    run_rollout
    echo ""
    run_verification
    echo ""
    
    # Print summary
    print_summary
}

# Handle script arguments
if [ $# -gt 0 ]; then
    case "$1" in
        --help|-h)
            echo "SBH Deployment Orchestrator"
            echo ""
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --help, -h     Show this help message"
            echo "  --alb-dns      ALB DNS name for direct testing"
            echo ""
            echo "Environment Variables:"
            echo "  HOST           Target hostname (default: sbh.umbervale.com)"
            echo "  ALB_DNS        ALB DNS name for direct testing"
            echo ""
            echo "Examples:"
            echo "  $0"
            echo "  $0 --alb-dns sbh-alb-dev-123456.us-west-2.elb.amazonaws.com"
            echo "  HOST=my-sbh.example.com $0"
            exit 0
            ;;
        --alb-dns)
            if [ -n "${2:-}" ]; then
                ALB_DNS="$2"
                shift 2
            else
                error "--alb-dns requires a value"
                exit 1
            fi
            ;;
        *)
            error "Unknown option: $1"
            error "Use --help for usage information"
            exit 1
            ;;
    esac
fi

# Run main function
main "$@"

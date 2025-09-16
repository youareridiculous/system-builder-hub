#!/bin/bash
set -euo pipefail

# ECS Rollout Script for SBH Deployment
# Updates ECS service with new task definition

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
CLUSTER="${CLUSTER:-sbh-cluster-dev}"
SERVICE="${SERVICE:-sbh-service-dev}"
AWS_REGION="${AWS_REGION:-us-west-2}"
CONTAINER_NAME="${CONTAINER_NAME:-sbh-backend}"

# Required parameter
if [ -z "${IMAGE_URI:-}" ]; then
    echo -e "${RED}[ERROR]${NC} IMAGE_URI is required"
    echo "Usage: $0 IMAGE_URI=<full-image-uri>"
    echo "Example: $0 IMAGE_URI=776567512687.dkr.ecr.us-west-2.amazonaws.com/sbh-repo-dev:202501130400-abc123"
    exit 1
fi

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
    
    if ! command -v jq &> /dev/null; then
        missing_deps+=("jq")
    fi
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        error "Missing required dependencies: ${missing_deps[*]}"
        error "Please install:"
        for dep in "${missing_deps[@]}"; do
            case $dep in
                aws) error "  - AWS CLI: https://aws.amazon.com/cli/" ;;
                jq) error "  - jq: https://stedolan.github.io/jq/" ;;
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
}

# Get current task definition
get_current_task_definition() {
    log "Getting current task definition for service: $SERVICE"
    
    local task_def_arn
    task_def_arn=$(aws ecs describe-services \
        --cluster "$CLUSTER" \
        --services "$SERVICE" \
        --region "$AWS_REGION" \
        --query 'services[0].taskDefinition' \
        --output text)
    
    if [ "$task_def_arn" = "None" ] || [ -z "$task_def_arn" ]; then
        error "Could not get task definition for service: $SERVICE"
        exit 1
    fi
    
    log "Current task definition: $task_def_arn"
    echo "$task_def_arn"
}

# Get task definition JSON
get_task_definition_json() {
    local task_def_arn="$1"
    
    log "Fetching task definition JSON..."
    
    aws ecs describe-task-definition \
        --task-definition "$task_def_arn" \
        --region "$AWS_REGION" \
        --query 'taskDefinition'
}

# Update container image in task definition
update_container_image() {
    local task_def_json="$1"
    local new_image_uri="$2"
    
    log "Updating container image to: $new_image_uri"
    
    # Find the container name and update its image
    # If container name is not found, use the first container
    local updated_json
    updated_json=$(echo "$task_def_json" | jq --arg image "$new_image_uri" --arg container "$CONTAINER_NAME" '
        .containerDefinitions = [
            .containerDefinitions[] | 
            if .name == $container then 
                .image = $image 
            else 
                . 
            end
        ]
    ')
    
    # If no container with the specified name was found, update the first container
    if [ "$(echo "$updated_json" | jq '.containerDefinitions[0].image')" != "\"$new_image_uri\"" ]; then
        log "Container '$CONTAINER_NAME' not found, updating first container"
        updated_json=$(echo "$task_def_json" | jq --arg image "$new_image_uri" '
            .containerDefinitions[0].image = $image
        ')
    fi
    
    echo "$updated_json"
}

# Register new task definition
register_new_task_definition() {
    local task_def_json="$1"
    
    log "Registering new task definition..."
    
    # Remove fields that shouldn't be included in registration
    local clean_json
    clean_json=$(echo "$task_def_json" | jq 'del(.taskDefinitionArn, .revision, .status, .requiresAttributes, .placementConstraints, .compatibilities, .registeredAt, .registeredBy)')
    
    # Register the new task definition
    local new_task_def_arn
    new_task_def_arn=$(aws ecs register-task-definition \
        --cli-input-json "$clean_json" \
        --region "$AWS_REGION" \
        --query 'taskDefinition.taskDefinitionArn' \
        --output text)
    
    if [ -z "$new_task_def_arn" ] || [ "$new_task_def_arn" = "None" ]; then
        error "Failed to register new task definition"
        exit 1
    fi
    
    log "New task definition registered: $new_task_def_arn"
    echo "$new_task_def_arn"
}

# Update ECS service
update_ecs_service() {
    local new_task_def_arn="$1"
    
    log "Updating ECS service to use new task definition..."
    
    if aws ecs update-service \
        --cluster "$CLUSTER" \
        --service "$SERVICE" \
        --task-definition "$new_task_def_arn" \
        --force-new-deployment \
        --region "$AWS_REGION" &> /dev/null; then
        success "ECS service updated successfully"
    else
        error "Failed to update ECS service"
        exit 1
    fi
}

# Wait for service stability
wait_for_stability() {
    log "Waiting for service to reach stable state..."
    log "This may take several minutes..."
    
    if aws ecs wait services-stable \
        --cluster "$CLUSTER" \
        --services "$SERVICE" \
        --region "$AWS_REGION"; then
        success "Service is now stable"
    else
        error "Service failed to reach stable state"
        exit 1
    fi
}

# Get task definition revision
get_task_revision() {
    local task_def_arn="$1"
    
    echo "$task_def_arn" | sed 's/.*://'
}

# Main execution
main() {
    log "Starting ECS rollout process..."
    log "Configuration:"
    log "  Cluster: $CLUSTER"
    log "  Service: $SERVICE"
    log "  Region: $AWS_REGION"
    log "  Container: $CONTAINER_NAME"
    log "  New Image: $IMAGE_URI"
    
    check_dependencies
    verify_aws_credentials
    
    # Get current task definition
    local current_task_def_arn
    current_task_def_arn=$(get_current_task_definition)
    
    # Get task definition JSON
    local task_def_json
    task_def_json=$(get_task_definition_json "$current_task_def_arn")
    
    # Update container image
    local updated_task_def_json
    updated_task_def_json=$(update_container_image "$task_def_json" "$IMAGE_URI")
    
    # Register new task definition
    local new_task_def_arn
    new_task_def_arn=$(register_new_task_definition "$updated_task_def_json")
    
    # Update ECS service
    update_ecs_service "$new_task_def_arn"
    
    # Wait for stability
    wait_for_stability
    
    # Get revision number
    local revision
    revision=$(get_task_revision "$new_task_def_arn")
    
    success "ECS rollout completed successfully"
    echo ""
    echo -e "${GREEN}New Task Definition:${NC} $new_task_def_arn"
    echo -e "${GREEN}Revision:${NC} $revision"
    echo -e "${GREEN}Service:${NC} $SERVICE"
    echo ""
    
    # Export for use by other scripts
    export NEW_TASK_DEF_ARN="$new_task_def_arn"
    export TASK_REVISION="$revision"
}

# Run main function
main "$@"

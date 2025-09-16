#!/bin/bash
set -e

# Build script with guardrails for Phase-3 ARM64 deployment
# Usage: ./scripts/build-with-guardrails.sh [tag]

TAG=${1:-"phase3-$(date +%Y%m%d%H%M%S)"}
ECR_REPO="776567512687.dkr.ecr.us-west-2.amazonaws.com/sbh-repo-dev"
REGION="us-west-2"

echo "🚀 Starting Phase-3 ARM64 build with guardrails..."
echo "Tag: $TAG"
echo "ECR Repo: $ECR_REPO"

# Guardrail 1: Check build context size and forbidden paths
echo "📊 Checking build context size and forbidden paths..."
CONTEXT_SIZE=$(du -sh . | cut -f1)
CONTEXT_SIZE_BYTES=$(du -sb . | cut -f1)
CONTEXT_FILES=$(find . -type f | wc -l)

echo "Build context: $CONTEXT_SIZE ($CONTEXT_SIZE_BYTES bytes, $CONTEXT_FILES files)"

# Check for forbidden paths that should never be in build context
FORBIDDEN_PATHS=(".venv" "node_modules" "__pycache__" ".pytest_cache" ".mypy_cache")
for path in "${FORBIDDEN_PATHS[@]}"; do
    if find . -name "$path" -type d | grep -q .; then
        echo "❌ Forbidden path found in build context: $path"
        echo "💡 Check .dockerignore and exclude $path"
        find . -name "$path" -type d
        exit 1
    fi
done

# Fail if context is too large (> 50MB or > 5,000 files for backend-only)
MAX_SIZE_BYTES=52428800   # 50MB (reduced for backend-only)
MAX_FILES=5000

if [ "$CONTEXT_SIZE_BYTES" -gt "$MAX_SIZE_BYTES" ]; then
    echo "❌ Build context too large: $CONTEXT_SIZE_BYTES bytes (max: $MAX_SIZE_BYTES)"
    echo "💡 Check .dockerignore and exclude unnecessary files"
    echo "📁 Largest directories:"
    du -sh * | sort -hr | head -10
    exit 1
fi

if [ "$CONTEXT_FILES" -gt "$MAX_FILES" ]; then
    echo "❌ Too many files in context: $CONTEXT_FILES (max: $MAX_FILES)"
    echo "💡 Check .dockerignore and exclude unnecessary files"
    exit 1
fi

echo "✅ Build context size check passed"
echo "✅ No forbidden paths (.venv, node_modules, __pycache__) found"

# Guardrail 2: Verify .dockerignore is present and comprehensive
echo "🔍 Checking .dockerignore..."
if [ ! -f ".dockerignore" ]; then
    echo "❌ .dockerignore file not found"
    exit 1
fi

# Check for key exclusions
REQUIRED_EXCLUSIONS=("node_modules" "__pycache__" ".git" "*.log" "generated" "workspace")
for exclusion in "${REQUIRED_EXCLUSIONS[@]}"; do
    if ! grep -q "$exclusion" .dockerignore; then
        echo "⚠️  Warning: .dockerignore missing '$exclusion' exclusion"
    fi
done

echo "✅ .dockerignore validation passed"

# Authenticate with ECR
echo "🔐 Authenticating with ECR..."
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR_REPO

# Build the image
echo "🔨 Building ARM64 image..."
docker buildx build \
    --platform linux/arm64 \
    --tag $ECR_REPO:$TAG \
    --tag $ECR_REPO:latest \
    --push \
    .

echo "✅ Image built and pushed successfully"

# Guardrail 3: Verify image manifest and size
echo "🔍 Verifying image manifest..."
IMAGE_MANIFEST=$(aws ecr describe-images \
    --repository-name sbh-repo-dev \
    --image-ids imageTag=$TAG \
    --region $REGION \
    --query 'imageDetails[0]')

IMAGE_SIZE=$(echo "$IMAGE_MANIFEST" | jq -r '.imageSizeInBytes')
IMAGE_DIGEST=$(echo "$IMAGE_MANIFEST" | jq -r '.imageDigest')

echo "Image size: $IMAGE_SIZE bytes"
echo "Image digest: $IMAGE_DIGEST"

# Check minimum size (should be > 10MB for our app)
MIN_SIZE=10485760  # 10MB
if [ "$IMAGE_SIZE" -lt "$MIN_SIZE" ]; then
    echo "❌ Image too small: $IMAGE_SIZE bytes (min: $MIN_SIZE)"
    echo "💡 Check Dockerfile and ensure all necessary files are copied"
    exit 1
fi

# Verify ARM64 platform in manifest
echo "🔍 Checking platform architecture..."
MANIFEST_JSON=$(aws ecr batch-get-image \
    --repository-name sbh-repo-dev \
    --image-ids imageTag=$TAG \
    --region $REGION \
    --query 'images[0].imageManifest' \
    --output text)

PLATFORM=$(echo "$MANIFEST_JSON" | jq -r '.mediaType // empty')
if [[ "$PLATFORM" != *"arm64"* ]]; then
    echo "❌ Image does not contain ARM64 platform"
    exit 1
fi

echo "✅ Image verification passed"
echo "✅ Platform: ARM64 confirmed"
echo "✅ Size: $IMAGE_SIZE bytes (realistic for our app)"

# Create new task definition
echo "📝 Creating new task definition..."
CURRENT_TD=$(aws ecs describe-task-definition \
    --task-definition sbh-task-dev \
    --region $REGION \
    --query 'taskDefinition')

NEW_TD=$(echo "$CURRENT_TD" | jq --arg image "$ECR_REPO:$TAG" \
    '.containerDefinitions[0].image = $image')

CLEAN_TD=$(echo "$NEW_TD" | jq 'del(.taskDefinitionArn, .revision, .status, .requiresAttributes, .compatibilities, .registeredAt, .registeredBy)')

echo "$CLEAN_TD" > new_task_def.json

NEW_REVISION=$(aws ecs register-task-definition \
    --cli-input-json file://new_task_def.json \
    --region $REGION \
    --query 'taskDefinition.revision' \
    --output text)

echo "✅ New task definition created: revision $NEW_REVISION"

# Deploy to ECS
echo "🚀 Deploying to ECS..."
aws ecs update-service \
    --cluster sbh-cluster-dev \
    --service sbh-service-dev \
    --task-definition sbh-task-dev:$NEW_REVISION \
    --region $REGION

echo "⏳ Waiting for deployment to stabilize..."
aws ecs wait services-stable \
    --cluster sbh-cluster-dev \
    --services sbh-service-dev \
    --region $REGION

echo "✅ Deployment completed successfully"

# Final health check
echo "🏥 Performing final health check..."
for i in {1..30}; do
    HEALTH=$(curl -s https://sbh.umbervale.com/api/health | jq -r '.ok // false')
    if [ "$HEALTH" = "true" ]; then
        echo "✅ Health check passed"
        break
    fi
    echo "Attempt $i: Health check failed, retrying in 10 seconds..."
    sleep 10
done

if [ "$HEALTH" != "true" ]; then
    echo "❌ Health check failed after 30 attempts"
    exit 1
fi

echo ""
echo "🎉 Phase-3 ARM64 deployment completed successfully!"
echo "📊 Summary:"
echo "  - Build context: $CONTEXT_SIZE ($CONTEXT_FILES files)"
echo "  - Image: $ECR_REPO:$TAG"
echo "  - Size: $IMAGE_SIZE bytes"
echo "  - Platform: ARM64"
echo "  - Task revision: $NEW_REVISION"
echo "  - Health: ✅ Healthy"
echo ""
echo "🔗 Service URL: https://sbh.umbervale.com"
echo "📋 Next steps: Apply database schema and verify Phase-3 APIs"

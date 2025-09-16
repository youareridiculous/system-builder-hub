# SBH ECR Repository - Phase 2 Cloud Deployment

# =============================================================================
# ECR REPOSITORY
# =============================================================================

resource "aws_ecr_repository" "sbh_repo" {
  name                 = "${var.project_name}-repo-${var.environment}"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = {
    Name        = "${var.project_name}-ecr-repo-${var.environment}"
    Environment = var.environment
    Project     = var.project_name
  }
}

# =============================================================================
# ECR LIFECYCLE POLICY
# =============================================================================

resource "aws_ecr_lifecycle_policy" "sbh_repo_policy" {
  repository = aws_ecr_repository.sbh_repo.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 10 images"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["v"]
          countType     = "imageCountMoreThan"
          countNumber   = 10
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 2
        description  = "Delete untagged images older than 1 day"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 1
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

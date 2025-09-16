# SBH IAM Roles and Policies - Phase 2 Cloud Deployment

# =============================================================================
# ECS EXECUTION ROLE
# =============================================================================

resource "aws_iam_role" "ecs_execution_role" {
  name = "${var.project_name}-ecs-execution-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "${var.project_name}-ecs-execution-role-${var.environment}"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_iam_role_policy_attachment" "ecs_execution_role_policy" {
  role       = aws_iam_role.ecs_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# =============================================================================
# ECS TASK ROLE
# =============================================================================

resource "aws_iam_role" "ecs_task_role" {
  name = "${var.project_name}-ecs-task-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "${var.project_name}-ecs-task-role-${var.environment}"
    Environment = var.environment
    Project     = var.project_name
  }
}

# =============================================================================
# S3 ACCESS POLICY
# =============================================================================

resource "aws_iam_policy" "s3_workspace_policy" {
  name        = "${var.project_name}-s3-workspace-policy-${var.environment}"
  description = "Policy for SBH to access workspace S3 bucket"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.sbh_workspace.arn,
          "${aws_s3_bucket.sbh_workspace.arn}/*"
        ]
      }
    ]
  })

  tags = {
    Name        = "${var.project_name}-s3-workspace-policy-${var.environment}"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_iam_role_policy_attachment" "ecs_task_s3_policy" {
  role       = aws_iam_role.ecs_task_role.name
  policy_arn = aws_iam_policy.s3_workspace_policy.arn
}

# =============================================================================
# CLOUDWATCH LOGS POLICY
# =============================================================================

resource "aws_iam_policy" "cloudwatch_logs_policy" {
  name        = "${var.project_name}-cloudwatch-logs-policy-${var.environment}"
  description = "Policy for SBH to write to CloudWatch logs"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogStreams"
        ]
        Resource = [
          aws_cloudwatch_log_group.sbh_logs.arn,
          "${aws_cloudwatch_log_group.sbh_logs.arn}:*"
        ]
      }
    ]
  })

  tags = {
    Name        = "${var.project_name}-cloudwatch-logs-policy-${var.environment}"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_iam_role_policy_attachment" "ecs_task_cloudwatch_policy" {
  role       = aws_iam_role.ecs_task_role.name
  policy_arn = aws_iam_policy.cloudwatch_logs_policy.arn
}

# =============================================================================
# ECR ACCESS POLICY
# =============================================================================

resource "aws_iam_policy" "ecr_access_policy" {
  name        = "${var.project_name}-ecr-access-policy-${var.environment}"
  description = "Policy for ECS to pull images from ECR"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage"
        ]
        Resource = "*"
      }
    ]
  })

  tags = {
    Name        = "${var.project_name}-ecr-access-policy-${var.environment}"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_iam_role_policy_attachment" "ecs_execution_ecr_policy" {
  role       = aws_iam_role.ecs_execution_role.name
  policy_arn = aws_iam_policy.ecr_access_policy.arn
}

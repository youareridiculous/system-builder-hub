# ECS Cluster (defined in main.tf)

# ECS Task Definition
resource "aws_ecs_task_definition" "sbh_task" {
  family                   = "${var.project_name}-task-${var.environment}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "ARM64"
  }

  # Override the command to use server.py directly instead of wsgi.py
  container_definitions = jsonencode([
    {
      name  = "sbh-backend"
      image = "${local.aws_account_id}.dkr.ecr.${var.aws_region}.amazonaws.com/${var.project_name}-repo-${var.environment}:202509122256-35e7bbb"

      portMappings = [
        {
          containerPort = 8000
          protocol      = "tcp"
        }
      ]

      environment = [
        {
          name  = "FLASK_ENV"
          value = "production"
        },
        {
          name  = "ENV"
          value = "production"
        },
        {
          name  = "SECRET_KEY"
          value = var.secret_key
        },
        {
          name  = "DATABASE_URL"
          value = "postgresql://${var.db_username}:${var.db_password}@${aws_db_instance.sbh_db.endpoint}/sbh_db"
        },
        {
          name  = "OPENAI_API_KEY"
          value = var.openai_api_key
        },
        {
          name  = "AWS_REGION"
          value = var.aws_region
        },
        {
          name  = "AWS_BUCKET_NAME"
          value = aws_s3_bucket.sbh_workspace.bucket
        },
        {
          name  = "S3_BUCKET_NAME"
          value = aws_s3_bucket.sbh_workspace.bucket
        },
        {
          name  = "S3_REGION"
          value = var.aws_region
        },
        {
          name  = "STORAGE_PROVIDER"
          value = "s3"
        },
        {
          name  = "CORS_ORIGINS"
          value = "https://sbh.umbervale.com,https://${aws_lb.sbh_alb.dns_name}"
        },
        {
          name  = "LOG_LEVEL"
          value = "INFO"
        },
        {
          name  = "LLM_SECRET_KEY"
          value = "XSUk+pEd/rDzttilHZobhcpW+LOgGifmCeTM1Ylou/k="
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.sbh_logs.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8000/api/health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }

      # Override the command to use server.py directly
      command = ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120", "--keep-alive", "2", "--max-requests", "1000", "--max-requests-jitter", "100", "wsgi:app"]

      essential = true
    }
  ])

  tags = {
    Name        = "${var.project_name}-task-${var.environment}"
    Environment = var.environment
    Project     = var.project_name
  }
}

# ECS Service
resource "aws_ecs_service" "sbh_service" {
  name            = "${var.project_name}-service-${var.environment}"
  cluster         = aws_ecs_cluster.sbh_cluster.id
  task_definition = aws_ecs_task_definition.sbh_task.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.sbh_public_subnets[*].id
    security_groups  = [aws_security_group.sbh_ecs_sg.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.sbh_tg.arn
    container_name   = "sbh-backend"
    container_port   = 8000
  }

  service_registries {
    registry_arn = aws_service_discovery_service.sbh_service.arn
  }

  depends_on = [
    aws_lb_listener.sbh_listener,
    aws_iam_role_policy_attachment.ecs_task_cloudwatch_policy
  ]

  tags = {
    Name        = "${var.project_name}-service-${var.environment}"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Service Discovery
resource "aws_service_discovery_private_dns_namespace" "sbh_namespace" {
  name        = "${var.project_name}.local"
  description = "SBH service discovery namespace"
  vpc         = aws_vpc.sbh_vpc.id

  tags = {
    Name        = "${var.project_name}-namespace-${var.environment}"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_service_discovery_service" "sbh_service" {
  name = "${var.project_name}-service"

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.sbh_namespace.id

    dns_records {
      ttl  = 10
      type = "A"
    }

    routing_policy = "MULTIVALUE"
  }

  tags = {
    Name        = "${var.project_name}-service-discovery-${var.environment}"
    Environment = var.environment
    Project     = var.project_name
  }
}

# CloudWatch resources defined in cloudwatch.tf
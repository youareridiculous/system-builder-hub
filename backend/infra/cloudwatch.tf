# SBH CloudWatch Logs - Phase 2 Cloud Deployment

# =============================================================================
# CLOUDWATCH LOG GROUP
# =============================================================================

resource "aws_cloudwatch_log_group" "sbh_logs" {
  name              = "/ecs/${var.project_name}-${var.environment}"
  retention_in_days = var.log_retention_days

  tags = {
    Name        = "${var.project_name}-logs-${var.environment}"
    Environment = var.environment
    Project     = var.project_name
  }
}

# =============================================================================
# CLOUDWATCH ALARMS
# =============================================================================

resource "aws_cloudwatch_metric_alarm" "sbh_high_cpu" {
  alarm_name          = "${var.project_name}-high-cpu-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors ECS CPU utilization"
  alarm_actions       = var.sns_topic_arn != "" ? [var.sns_topic_arn] : []

  dimensions = {
    ServiceName = aws_ecs_service.sbh_service.name
    ClusterName = aws_ecs_cluster.sbh_cluster.name
  }

  tags = {
    Name        = "${var.project_name}-high-cpu-alarm-${var.environment}"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_cloudwatch_metric_alarm" "sbh_high_memory" {
  alarm_name          = "${var.project_name}-high-memory-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "MemoryUtilization"
  namespace           = "AWS/ECS"
  period              = "300"
  statistic           = "Average"
  threshold           = "85"
  alarm_description   = "This metric monitors ECS memory utilization"
  alarm_actions       = var.sns_topic_arn != "" ? [var.sns_topic_arn] : []

  dimensions = {
    ServiceName = aws_ecs_service.sbh_service.name
    ClusterName = aws_ecs_cluster.sbh_cluster.name
  }

  tags = {
    Name        = "${var.project_name}-high-memory-alarm-${var.environment}"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_cloudwatch_metric_alarm" "sbh_task_count" {
  alarm_name          = "${var.project_name}-task-count-${var.environment}"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "RunningTaskCount"
  namespace           = "AWS/ECS"
  period              = "300"
  statistic           = "Average"
  threshold           = "1"
  alarm_description   = "This metric monitors ECS running task count"
  alarm_actions       = var.sns_topic_arn != "" ? [var.sns_topic_arn] : []

  dimensions = {
    ServiceName = aws_ecs_service.sbh_service.name
    ClusterName = aws_ecs_cluster.sbh_cluster.name
  }

  tags = {
    Name        = "${var.project_name}-task-count-alarm-${var.environment}"
    Environment = var.environment
    Project     = var.project_name
  }
}

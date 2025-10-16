# ===================================
# CloudWatch Log Groups
# ===================================

# Log group for API container
resource "aws_cloudwatch_log_group" "api" {
  name              = "/ecs/${local.name}/api"
  retention_in_days = var.log_retention_days

  tags = {
    Name        = "${local.name}-api-logs"
    Environment = var.environment
  }
}

# Log group for Web container
resource "aws_cloudwatch_log_group" "web" {
  name              = "/ecs/${local.name}/web"
  retention_in_days = var.log_retention_days

  tags = {
    Name        = "${local.name}-web-logs"
    Environment = var.environment
  }
}

# ALB Access Logs S3 Bucket
resource "aws_s3_bucket" "alb_logs" {
  bucket = "${local.name}-alb-logs"
  force_destroy = var.environment != "prod"

  tags = {
    Name        = "${local.name}-alb-logs"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "alb_logs" {
  bucket = aws_s3_bucket.alb_logs.id

  rule {
    id     = "delete-old-logs"
    status = "Enabled"

    expiration {
      days = var.alb_logs_retention_days
    }
  }
}

resource "aws_s3_bucket_public_access_block" "alb_logs" {
  bucket = aws_s3_bucket.alb_logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ALB Access Logs Bucket Policy
data "aws_elb_service_account" "main" {}

resource "aws_s3_bucket_policy" "alb_logs" {
  bucket = aws_s3_bucket.alb_logs.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          AWS = data.aws_elb_service_account.main.arn
        }
        Action   = "s3:PutObject"
        Resource = "${aws_s3_bucket.alb_logs.arn}/*"
      }
    ]
  })
}

# CloudWatch Log Stream for application insights
resource "aws_cloudwatch_log_stream" "api" {
  name           = "api-stream"
  log_group_name = aws_cloudwatch_log_group.api.name
}

resource "aws_cloudwatch_log_stream" "web" {
  name           = "web-stream"
  log_group_name = aws_cloudwatch_log_group.web.name
}

# ===================================
# SNS Topic for Alarms
# ===================================

resource "aws_sns_topic" "alarms" {
  name = "${local.name}-alarms"

  tags = {
    Name        = "${local.name}-alarms"
    Environment = var.environment
  }
}

resource "aws_sns_topic_subscription" "alarm_email" {
  count     = var.alarm_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.alarms.arn
  protocol  = "email"
  endpoint  = var.alarm_email
}

# ===================================
# CloudWatch Alarms - ALB
# ===================================

# API 5xx errors alarm - Rate-based (percentage)
resource "aws_cloudwatch_metric_alarm" "api_5xx_rate" {
  alarm_name          = "${local.name}-api-5xx-rate-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  threshold           = 1.0  # 1% error rate
  alarm_description   = "API 5xx error rate >1% for 10 minutes"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  treat_missing_data  = "notBreaching"

  metric_query {
    id          = "error_rate"
    expression  = "errors / requests * 100"
    label       = "5xx Error Rate"
    return_data = true
  }

  metric_query {
    id = "errors"
    metric {
      metric_name = "HTTPCode_Target_5XX_Count"
      namespace   = "AWS/ApplicationELB"
      period      = 300
      stat        = "Sum"
      dimensions = {
        LoadBalancer = aws_lb.app.arn_suffix
        TargetGroup  = aws_lb_target_group.api.arn_suffix
      }
    }
  }

  metric_query {
    id = "requests"
    metric {
      metric_name = "RequestCount"
      namespace   = "AWS/ApplicationELB"
      period      = 300
      stat        = "Sum"
      dimensions = {
        LoadBalancer = aws_lb.app.arn_suffix
        TargetGroup  = aws_lb_target_group.api.arn_suffix
      }
    }
  }

  tags = {
    Name        = "${local.name}-api-5xx-rate-alarm"
    Environment = var.environment
    Severity    = "Critical"
  }
}

# API response time alarm (P95)
resource "aws_cloudwatch_metric_alarm" "api_response_time" {
  alarm_name          = "${local.name}-api-response-time-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  datapoints_to_alarm = 2
  metric_name         = "TargetResponseTime"
  namespace           = "AWS/ApplicationELB"
  period              = 300
  statistic           = "p95"
  threshold           = 2.0  # 2 seconds
  alarm_description   = "API P95 response time >2s"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    LoadBalancer = aws_lb.app.arn_suffix
    TargetGroup  = aws_lb_target_group.api.arn_suffix
  }

  tags = {
    Name        = "${local.name}-api-response-time-alarm"
    Environment = var.environment
    Severity    = "Warning"
  }
}

# ALB unhealthy target count
resource "aws_cloudwatch_metric_alarm" "api_unhealthy_targets" {
  alarm_name          = "${local.name}-api-unhealthy-targets"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "UnHealthyHostCount"
  namespace           = "AWS/ApplicationELB"
  period              = 60
  statistic           = "Average"
  threshold           = 0
  alarm_description   = "API has unhealthy targets"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    LoadBalancer = aws_lb.app.arn_suffix
    TargetGroup  = aws_lb_target_group.api.arn_suffix
  }

  tags = {
    Name        = "${local.name}-api-unhealthy-targets-alarm"
    Environment = var.environment
    Severity    = "Critical"
  }
}

# ===================================
# CloudWatch Alarms - RDS
# ===================================

# RDS CPU utilization alarm
resource "aws_cloudwatch_metric_alarm" "rds_cpu" {
  alarm_name          = "${local.name}-rds-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  datapoints_to_alarm = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "RDS CPU >80% for 10+ minutes"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.id
  }

  tags = {
    Name        = "${local.name}-rds-cpu-alarm"
    Environment = var.environment
    Severity    = "Warning"
  }
}

# RDS free storage space alarm
resource "aws_cloudwatch_metric_alarm" "rds_storage" {
  alarm_name          = "${local.name}-rds-storage-low"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 1
  metric_name         = "FreeStorageSpace"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = var.db_allocated_storage * 1073741824 * 0.2  # 20% of allocated storage in bytes
  alarm_description   = "RDS free storage <20%"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.id
  }

  tags = {
    Name        = "${local.name}-rds-storage-alarm"
    Environment = var.environment
    Severity    = "Critical"
  }
}

# RDS connection count alarm
resource "aws_cloudwatch_metric_alarm" "rds_connections" {
  alarm_name          = "${local.name}-rds-connections-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "DatabaseConnections"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = var.db_max_connections * 0.8  # 80% of max connections
  alarm_description   = "RDS connections >80% of max"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.id
  }

  tags = {
    Name        = "${local.name}-rds-connections-alarm"
    Environment = var.environment
    Severity    = "Warning"
  }
}

# RDS read/write latency alarm
resource "aws_cloudwatch_metric_alarm" "rds_write_latency" {
  alarm_name          = "${local.name}-rds-write-latency-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  datapoints_to_alarm = 2
  metric_name         = "WriteLatency"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 0.1  # 100ms
  alarm_description   = "RDS write latency >100ms"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.id
  }

  tags = {
    Name        = "${local.name}-rds-write-latency-alarm"
    Environment = var.environment
    Severity    = "Warning"
  }
}

# ===================================
# CloudWatch Alarms - ECS
# ===================================

# ECS service CPU utilization (informational, auto-scaling handles this)
resource "aws_cloudwatch_metric_alarm" "ecs_api_cpu_high" {
  alarm_name          = "${local.name}-ecs-api-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = 300
  statistic           = "Average"
  threshold           = 85  # Higher than auto-scaling threshold
  alarm_description   = "ECS API CPU >85% (check if auto-scaling is working)"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    ClusterName = aws_ecs_cluster.this.name
    ServiceName = aws_ecs_service.api.name
  }

  tags = {
    Name        = "${local.name}-ecs-api-cpu-alarm"
    Environment = var.environment
    Severity    = "Warning"
  }
}

# ECS service memory utilization
resource "aws_cloudwatch_metric_alarm" "ecs_api_memory_high" {
  alarm_name          = "${local.name}-ecs-api-memory-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "MemoryUtilization"
  namespace           = "AWS/ECS"
  period              = 300
  statistic           = "Average"
  threshold           = 90
  alarm_description   = "ECS API memory >90%"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    ClusterName = aws_ecs_cluster.this.name
    ServiceName = aws_ecs_service.api.name
  }

  tags = {
    Name        = "${local.name}-ecs-api-memory-alarm"
    Environment = var.environment
    Severity    = "Critical"
  }
}

# ECS service running task count
resource "aws_cloudwatch_metric_alarm" "ecs_api_no_tasks" {
  alarm_name          = "${local.name}-ecs-api-no-tasks"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 1
  metric_name         = "RunningTaskCount"
  namespace           = "ECS/ContainerInsights"
  period              = 60
  statistic           = "Average"
  threshold           = 1
  alarm_description   = "No running API tasks"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  treat_missing_data  = "breaching"

  dimensions = {
    ClusterName = aws_ecs_cluster.this.name
    ServiceName = aws_ecs_service.api.name
  }

  tags = {
    Name        = "${local.name}-ecs-api-no-tasks-alarm"
    Environment = var.environment
    Severity    = "Critical"
  }
}

# ===================================
# CloudWatch Dashboards
# ===================================

resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${local.name}-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/ApplicationELB", "RequestCount", { stat = "Sum", label = "Total Requests" }],
            [".", "HTTPCode_Target_5XX_Count", { stat = "Sum", label = "5xx Errors" }],
            [".", "HTTPCode_Target_4XX_Count", { stat = "Sum", label = "4xx Errors" }]
          ]
          period = 300
          stat   = "Sum"
          region = var.region
          title  = "ALB Requests & Errors"
          dimensions = {
            LoadBalancer = [aws_lb.app.arn_suffix]
          }
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/ApplicationELB", "TargetResponseTime", { stat = "p50", label = "P50" }],
            ["...", { stat = "p95", label = "P95" }],
            ["...", { stat = "p99", label = "P99" }]
          ]
          period = 300
          region = var.region
          title  = "API Response Time (seconds)"
          yAxis = {
            left = {
              min = 0
            }
          }
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/RDS", "CPUUtilization", { stat = "Average" }],
            [".", "DatabaseConnections", { stat = "Average", yAxis = "right" }]
          ]
          period = 300
          region = var.region
          title  = "RDS CPU & Connections"
          dimensions = {
            DBInstanceIdentifier = [aws_db_instance.main.id]
          }
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/ECS", "CPUUtilization", { stat = "Average", label = "CPU %" }],
            [".", "MemoryUtilization", { stat = "Average", label = "Memory %" }]
          ]
          period = 300
          region = var.region
          title  = "ECS API Service Utilization"
          dimensions = {
            ClusterName = [aws_ecs_cluster.this.name]
            ServiceName = [aws_ecs_service.api.name]
          }
        }
      }
    ]
  })
}

# ===================================
# Outputs
# ===================================

output "api_log_group" {
  description = "CloudWatch log group for API container"
  value       = aws_cloudwatch_log_group.api.name
}

output "web_log_group" {
  description = "CloudWatch log group for Web container"
  value       = aws_cloudwatch_log_group.web.name
}

output "alb_logs_bucket" {
  description = "S3 bucket for ALB access logs"
  value       = aws_s3_bucket.alb_logs.bucket
}

output "sns_topic_arn" {
  description = "SNS topic ARN for CloudWatch alarms"
  value       = aws_sns_topic.alarms.arn
}

output "dashboard_url" {
  description = "CloudWatch dashboard URL"
  value       = "https://console.aws.amazon.com/cloudwatch/home?region=${var.region}#dashboards:name=${aws_cloudwatch_dashboard.main.dashboard_name}"
}

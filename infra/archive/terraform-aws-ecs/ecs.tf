# ECS Task Definitions and Services

# IAM role for ECS tasks (application runtime)
resource "aws_iam_role" "task_role" {
  name = "${local.name}-task-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })

  tags = {
    Name        = "${local.name}-task-role"
    Environment = var.environment
  }
}

# Policy for task role to access S3 bucket
resource "aws_iam_policy" "s3_access" {
  name        = "${local.name}-s3-access"
  description = "Allow ECS tasks to access S3 media bucket"

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
          aws_s3_bucket.media.arn,
          "${aws_s3_bucket.media.arn}/*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "task_s3" {
  role       = aws_iam_role.task_role.name
  policy_arn = aws_iam_policy.s3_access.arn
}

# ECS Task Definition for API
resource "aws_ecs_task_definition" "api" {
  family                   = "${local.name}-api"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.api_cpu
  memory                   = var.api_memory
  execution_role_arn       = aws_iam_role.task_exec.arn
  task_role_arn            = aws_iam_role.task_role.arn

  container_definitions = jsonencode([
    {
      name      = "api"
      image     = "${aws_ecr_repository.api.repository_url}:latest"
      essential = true

      portMappings = [
        {
          containerPort = 8000
          protocol      = "tcp"
        }
      ]

      environment = [
        {
          name  = "APP_ENV"
          value = var.environment
        },
        {
          name  = "STORAGE_BACKEND"
          value = "s3"
        },
        {
          name  = "CORS_ORIGINS"
          value = var.cors_origins
        }
      ]

      secrets = [
        {
          name      = "SECRET_KEY"
          valueFrom = "${aws_secretsmanager_secret.app_config.arn}:SECRET_KEY::"
        },
        {
          name      = "DATABASE_URL"
          valueFrom = "${aws_secretsmanager_secret.app_config.arn}:DATABASE_URL::"
        },
        {
          name      = "S3_ACCESS_KEY"
          valueFrom = "${aws_secretsmanager_secret.s3_credentials.arn}:S3_ACCESS_KEY::"
        },
        {
          name      = "S3_SECRET_KEY"
          valueFrom = "${aws_secretsmanager_secret.s3_credentials.arn}:S3_SECRET_KEY::"
        },
        {
          name      = "S3_BUCKET"
          valueFrom = "${aws_secretsmanager_secret.s3_credentials.arn}:S3_BUCKET::"
        },
        {
          name      = "S3_REGION"
          valueFrom = "${aws_secretsmanager_secret.s3_credentials.arn}:S3_REGION::"
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.api.name
          "awslogs-region"        = var.region
          "awslogs-stream-prefix" = "ecs"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
    }
  ])

  tags = {
    Name        = "${local.name}-api-task"
    Environment = var.environment
  }
}

# ECS Task Definition for Web
resource "aws_ecs_task_definition" "web" {
  family                   = "${local.name}-web"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.web_cpu
  memory                   = var.web_memory
  execution_role_arn       = aws_iam_role.task_exec.arn
  task_role_arn            = aws_iam_role.task_role.arn

  container_definitions = jsonencode([
    {
      name      = "web"
      image     = "${aws_ecr_repository.web.repository_url}:latest"
      essential = true

      portMappings = [
        {
          containerPort = 80
          protocol      = "tcp"
        }
      ]

      environment = [
        {
          name  = "VITE_API_URL"
          value = "https://${var.domain_name}/api"
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.web.name
          "awslogs-region"        = var.region
          "awslogs-stream-prefix" = "ecs"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:80/ || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
    }
  ])

  tags = {
    Name        = "${local.name}-web-task"
    Environment = var.environment
  }
}

# ECS Service for API
resource "aws_ecs_service" "api" {
  name            = "${local.name}-api"
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = var.api_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnets
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"
    container_port   = 8000
  }

  # Enable ECS Exec for debugging
  enable_execute_command = true

  # Health check grace period
  health_check_grace_period_seconds = 60

  # Deployment configuration
  deployment_configuration {
    maximum_percent         = 200
    minimum_healthy_percent = 100
  }

  # Wait for ALB to be ready
  depends_on = [
    aws_lb_listener.https,
    aws_lb_listener_rule.api
  ]

  tags = {
    Name        = "${local.name}-api-service"
    Environment = var.environment
  }
}

# ECS Service for Web
resource "aws_ecs_service" "web" {
  name            = "${local.name}-web"
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.web.arn
  desired_count   = var.web_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnets
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.web.arn
    container_name   = "web"
    container_port   = 80
  }

  # Enable ECS Exec for debugging
  enable_execute_command = true

  # Health check grace period
  health_check_grace_period_seconds = 60

  # Deployment configuration
  deployment_configuration {
    maximum_percent         = 200
    minimum_healthy_percent = 100
  }

  # Wait for ALB to be ready
  depends_on = [
    aws_lb_listener.https,
    aws_lb_listener_rule.web
  ]

  tags = {
    Name        = "${local.name}-web-service"
    Environment = var.environment
  }
}

# ===================================
# Auto-scaling for API Service
# ===================================

resource "aws_appautoscaling_target" "api" {
  max_capacity       = var.api_max_capacity
  min_capacity       = var.api_min_capacity
  resource_id        = "service/${aws_ecs_cluster.this.name}/${aws_ecs_service.api.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"

  tags = {
    Name        = "${local.name}-api-autoscaling-target"
    Environment = var.environment
  }
}

# CPU-based autoscaling for API
resource "aws_appautoscaling_policy" "api_cpu" {
  name               = "${local.name}-api-cpu-autoscaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.api.resource_id
  scalable_dimension = aws_appautoscaling_target.api.scalable_dimension
  service_namespace  = aws_appautoscaling_target.api.service_namespace

  target_tracking_scaling_policy_configuration {
    target_value = 70.0  # Target 70% CPU utilization

    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }

    scale_in_cooldown  = 300  # 5 minutes before scaling in
    scale_out_cooldown = 60   # 1 minute before scaling out
  }
}

# Memory-based autoscaling for API
resource "aws_appautoscaling_policy" "api_memory" {
  name               = "${local.name}-api-memory-autoscaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.api.resource_id
  scalable_dimension = aws_appautoscaling_target.api.scalable_dimension
  service_namespace  = aws_appautoscaling_target.api.service_namespace

  target_tracking_scaling_policy_configuration {
    target_value = 80.0  # Target 80% memory utilization

    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageMemoryUtilization"
    }

    scale_in_cooldown  = 300  # 5 minutes before scaling in
    scale_out_cooldown = 60   # 1 minute before scaling out
  }
}

# ALB request count-based autoscaling for API (additional scaling dimension)
resource "aws_appautoscaling_policy" "api_requests" {
  name               = "${local.name}-api-requests-autoscaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.api.resource_id
  scalable_dimension = aws_appautoscaling_target.api.scalable_dimension
  service_namespace  = aws_appautoscaling_target.api.service_namespace

  target_tracking_scaling_policy_configuration {
    target_value = 1000.0  # Target 1000 requests per minute per task

    predefined_metric_specification {
      predefined_metric_type = "ALBRequestCountPerTarget"
      resource_label         = "${aws_lb.app.arn_suffix}/${aws_lb_target_group.api.arn_suffix}"
    }

    scale_in_cooldown  = 300  # 5 minutes before scaling in
    scale_out_cooldown = 60   # 1 minute before scaling out
  }
}

# ===================================
# Auto-scaling for Web Service
# ===================================

resource "aws_appautoscaling_target" "web" {
  max_capacity       = var.web_max_capacity
  min_capacity       = var.web_min_capacity
  resource_id        = "service/${aws_ecs_cluster.this.name}/${aws_ecs_service.web.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"

  tags = {
    Name        = "${local.name}-web-autoscaling-target"
    Environment = var.environment
  }
}

# CPU-based autoscaling for Web
resource "aws_appautoscaling_policy" "web_cpu" {
  name               = "${local.name}-web-cpu-autoscaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.web.resource_id
  scalable_dimension = aws_appautoscaling_target.web.scalable_dimension
  service_namespace  = aws_appautoscaling_target.web.service_namespace

  target_tracking_scaling_policy_configuration {
    target_value = 70.0  # Target 70% CPU utilization

    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }

    scale_in_cooldown  = 300  # 5 minutes before scaling in
    scale_out_cooldown = 60   # 1 minute before scaling out
  }
}

# Memory-based autoscaling for Web
resource "aws_appautoscaling_policy" "web_memory" {
  name               = "${local.name}-web-memory-autoscaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.web.resource_id
  scalable_dimension = aws_appautoscaling_target.web.scalable_dimension
  service_namespace  = aws_appautoscaling_target.web.service_namespace

  target_tracking_scaling_policy_configuration {
    target_value = 80.0  # Target 80% memory utilization

    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageMemoryUtilization"
    }

    scale_in_cooldown  = 300  # 5 minutes before scaling in
    scale_out_cooldown = 60   # 1 minute before scaling out
  }
}

# Outputs
output "api_service_name" {
  description = "Name of the API ECS service"
  value       = aws_ecs_service.api.name
}

output "web_service_name" {
  description = "Name of the Web ECS service"
  value       = aws_ecs_service.web.name
}

output "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  value       = aws_ecs_cluster.this.name
}

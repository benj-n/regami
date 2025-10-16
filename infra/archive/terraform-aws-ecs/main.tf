terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}

locals {
  name = var.project
}

# ECR repos
resource "aws_ecr_repository" "api" {
  name = "${local.name}-api"
}
resource "aws_ecr_repository" "web" {
  name = "${local.name}-web"
}

# ===================================
# S3 Bucket for Media (with Versioning)
# ===================================
resource "aws_s3_bucket" "media" {
  bucket = "${local.name}-media"
  force_destroy = var.environment != "prod"

  tags = {
    Name        = "${local.name}-media"
    Environment = var.environment
  }
}

# Enable versioning for data protection
resource "aws_s3_bucket_versioning" "media" {
  bucket = aws_s3_bucket.media.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Lifecycle rules to manage old versions
resource "aws_s3_bucket_lifecycle_configuration" "media" {
  bucket = aws_s3_bucket.media.id

  rule {
    id     = "delete-old-versions"
    status = "Enabled"

    noncurrent_version_expiration {
      noncurrent_days = var.s3_version_retention_days
    }
  }

  rule {
    id     = "abort-incomplete-multipart-uploads"
    status = "Enabled"

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# Enable server-side encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "media" {
  bucket = aws_s3_bucket.media.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Block public access (photos served via signed URLs or CloudFront)
resource "aws_s3_bucket_public_access_block" "media" {
  bucket = aws_s3_bucket.media.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# CORS configuration for web uploads
resource "aws_s3_bucket_cors_configuration" "media" {
  bucket = aws_s3_bucket.media.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "PUT", "POST", "DELETE"]
    allowed_origins = split(",", var.cors_origins)
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}

# VPC & Subnets are provided via variables to keep this scaffold simple.
# ECS cluster
resource "aws_ecs_cluster" "this" {
  name = local.name
}

# Task roles
resource "aws_iam_role" "task_exec" {
  name = "${local.name}-task-exec"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "exec_attach" {
  role       = aws_iam_role.task_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# ALB
resource "aws_lb" "app" {
  name               = "${local.name}-alb"
  load_balancer_type = "application"
  subnets            = var.public_subnets
  security_groups    = [aws_security_group.alb.id]

  enable_deletion_protection       = var.environment == "prod" ? true : false
  enable_http2                     = true
  enable_cross_zone_load_balancing = true

  # Enable ALB access logs
  access_logs {
    bucket  = aws_s3_bucket.alb_logs.bucket
    enabled = true
  }

  depends_on = [aws_s3_bucket_policy.alb_logs]

  tags = {
    Name        = "${local.name}-alb"
    Environment = var.environment
  }
}

resource "aws_lb_target_group" "api" {
  name     = "${local.name}-api-tg"
  port     = 8000
  protocol = "HTTP"
  vpc_id   = var.vpc_id
  health_check {
    path = "/health"
  }
}

resource "aws_lb_target_group" "web" {
  name     = "${local.name}-web-tg"
  port     = 80
  protocol = "HTTP"
  vpc_id   = var.vpc_id
}

# HTTP and HTTPS listeners are configured in alb_https.tf

# RDS PostgreSQL database
resource "aws_db_subnet_group" "main" {
  name       = "${local.name}-db-subnet"
  subnet_ids = var.private_subnets

  tags = {
    Name        = "${local.name}-db-subnet"
    Environment = var.environment
  }
}

resource "aws_security_group" "rds" {
  name        = "${local.name}-rds-sg"
  description = "Security group for RDS PostgreSQL"
  vpc_id      = var.vpc_id

  ingress {
    description = "PostgreSQL from ECS tasks"
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"]  # Adjust based on VPC CIDR
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${local.name}-rds-sg"
    Environment = var.environment
  }
}

resource "aws_db_instance" "main" {
  identifier           = "${local.name}-db"
  engine               = "postgres"
  engine_version       = "15.4"
  instance_class       = var.db_instance_class
  allocated_storage    = var.db_allocated_storage
  storage_type         = "gp3"
  storage_encrypted    = true

  db_name  = var.db_name
  username = var.db_username
  password = var.db_password

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  # ===================================
  # Backup Configuration (ENHANCED)
  # ===================================
  backup_retention_period = var.db_backup_retention_days
  backup_window          = "03:00-04:00"  # 3-4 AM UTC
  maintenance_window     = "Mon:04:00-Mon:05:00"  # After backups

  # Enable automated backups
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]  # Export slow queries and upgrades to CloudWatch

  # Copy backups to another region for disaster recovery
  copy_tags_to_snapshot = true

  skip_final_snapshot       = var.environment != "prod"
  final_snapshot_identifier = "${local.name}-db-final-snapshot-${formatdate("YYYY-MM-DD-hhmm", timestamp())}"

  # Enable deletion protection in production
  deletion_protection = var.environment == "prod" ? true : false

  # Enable automatic minor version upgrades
  auto_minor_version_upgrade = true

  # Enable performance insights
  performance_insights_enabled = true
  performance_insights_retention_period = 7

  tags = {
    Name        = "${local.name}-db"
    Environment = var.environment
  }
}

# Security groups, ECS task definitions and services would follow here.
# This scaffold keeps them minimal to avoid overreach; extend as needed for production.

output "alb_dns_name" { value = aws_lb.app.dns_name }
output "media_bucket" { value = aws_s3_bucket.media.bucket }
output "rds_endpoint" {
  description = "RDS instance endpoint"
  value       = aws_db_instance.main.endpoint
}
output "rds_address" {
  description = "RDS instance address (hostname only)"
  value       = aws_db_instance.main.address
}

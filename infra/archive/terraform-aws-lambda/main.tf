# Serverless Infrastructure for Regami
# Full serverless architecture with AWS Lambda, API Gateway, Aurora Serverless v2, S3, CloudFront

terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Store state in S3 (create this bucket first)
  backend "s3" {
    bucket = "regami-terraform-state"
    key    = "serverless/terraform.tfstate"
    region = "ca-central-1"
  }
}

provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "ca-central-1"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "regami"
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "domain_name" {
  description = "Domain name for CloudFront (optional)"
  type        = string
  default     = ""
}

# ============================================
# VPC Configuration (for Aurora Serverless)
# ============================================

resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name        = "${var.project_name}-vpc"
    Environment = var.environment
  }
}

resource "aws_subnet" "private_a" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = "${var.aws_region}a"

  tags = {
    Name = "${var.project_name}-private-a"
  }
}

resource "aws_subnet" "private_b" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.2.0/24"
  availability_zone = "${var.aws_region}b"

  tags = {
    Name = "${var.project_name}-private-b"
  }
}

resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-db-subnet"
  subnet_ids = [aws_subnet.private_a.id, aws_subnet.private_b.id]

  tags = {
    Name = "${var.project_name}-db-subnet"
  }
}

resource "aws_security_group" "aurora" {
  name_prefix = "${var.project_name}-aurora-"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]  # Allow from VPC
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-aurora-sg"
  }
}

resource "aws_security_group" "lambda" {
  name_prefix = "${var.project_name}-lambda-"
  vpc_id      = aws_vpc.main.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-lambda-sg"
  }
}

# ============================================
# Aurora Serverless v2 PostgreSQL
# ============================================

resource "aws_rds_cluster" "main" {
  cluster_identifier      = "${var.project_name}-cluster"
  engine                  = "aurora-postgresql"
  engine_mode             = "provisioned"
  engine_version          = "15.4"
  database_name           = "regami"
  master_username         = "regami_admin"
  master_password         = random_password.db_password.result

  db_subnet_group_name    = aws_db_subnet_group.main.name
  vpc_security_group_ids  = [aws_security_group.aurora.id]

  skip_final_snapshot     = var.environment != "prod"
  final_snapshot_identifier = var.environment == "prod" ? "${var.project_name}-final-snapshot" : null

  backup_retention_period = var.environment == "prod" ? 7 : 1
  preferred_backup_window = "03:00-04:00"

  serverlessv2_scaling_configuration {
    max_capacity = 2.0   # 2 ACU = 4GB RAM (scales down during low traffic)
    min_capacity = 0.5   # 0.5 ACU = 1GB RAM (minimal cost during idle)
  }

  tags = {
    Name        = "${var.project_name}-aurora"
    Environment = var.environment
  }
}

resource "aws_rds_cluster_instance" "main" {
  identifier         = "${var.project_name}-instance-1"
  cluster_identifier = aws_rds_cluster.main.id
  instance_class     = "db.serverless"
  engine             = aws_rds_cluster.main.engine
  engine_version     = aws_rds_cluster.main.engine_version

  tags = {
    Name = "${var.project_name}-aurora-instance"
  }
}

resource "random_password" "db_password" {
  length  = 32
  special = true
}

# Store DB password in Secrets Manager
resource "aws_secretsmanager_secret" "db_password" {
  name = "${var.project_name}-db-password"
}

resource "aws_secretsmanager_secret_version" "db_password" {
  secret_id     = aws_secretsmanager_secret.db_password.id
  secret_string = random_password.db_password.result
}

# ============================================
# S3 Bucket for Uploads
# ============================================

resource "aws_s3_bucket" "uploads" {
  bucket = "${var.project_name}-uploads-${var.environment}"

  tags = {
    Name        = "${var.project_name}-uploads"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_public_access_block" "uploads" {
  bucket = aws_s3_bucket.uploads.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# S3 lifecycle policy to move old files to Intelligent-Tiering
resource "aws_s3_bucket_lifecycle_configuration" "uploads" {
  bucket = aws_s3_bucket.uploads.id

  rule {
    id     = "move-to-intelligent-tiering"
    status = "Enabled"

    transition {
      days          = 30
      storage_class = "INTELLIGENT_TIERING"
    }

    noncurrent_version_transition {
      noncurrent_days = 30
      storage_class   = "GLACIER"
    }
  }
}

# Enable versioning for uploads
resource "aws_s3_bucket_versioning" "uploads" {
  bucket = aws_s3_bucket.uploads.id

  versioning_configuration {
    status = "Enabled"
  }
}

# ============================================
# CloudFront Distribution
# ============================================

resource "aws_cloudfront_origin_access_control" "s3" {
  name                              = "${var.project_name}-s3-oac"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_distribution" "main" {
  enabled             = true
  is_ipv6_enabled     = true
  comment             = "${var.project_name} CDN"
  default_root_object = "index.html"
  price_class         = "PriceClass_100"  # US, Canada, Europe only (cheaper)

  # S3 origin for uploads
  origin {
    domain_name              = aws_s3_bucket.uploads.bucket_regional_domain_name
    origin_id                = "S3-${aws_s3_bucket.uploads.id}"
    origin_access_control_id = aws_cloudfront_origin_access_control.s3.id
  }

  # API Gateway origin (will be added after API Gateway is created)
  origin {
    domain_name = aws_apigatewayv2_api.main.api_endpoint
    origin_id   = "API-Gateway"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  default_cache_behavior {
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "S3-${aws_s3_bucket.uploads.id}"
    viewer_protocol_policy = "redirect-to-https"
    compress               = true
    min_ttl                = 0
    default_ttl            = 3600
    max_ttl                = 86400

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }
  }

  # Cache behavior for API (don't cache)
  ordered_cache_behavior {
    path_pattern           = "/api/*"
    allowed_methods        = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "API-Gateway"
    viewer_protocol_policy = "redirect-to-https"
    compress               = true
    min_ttl                = 0
    default_ttl            = 0
    max_ttl                = 0

    forwarded_values {
      query_string = true
      headers      = ["Authorization", "Accept-Language", "X-CSRF-Token"]
      cookies {
        forward = "all"
      }
    }
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = var.domain_name == ""
    # If you have a domain, configure ACM certificate here
  }

  tags = {
    Name        = "${var.project_name}-cdn"
    Environment = var.environment
  }
}

# Update S3 bucket policy to allow CloudFront
resource "aws_s3_bucket_policy" "uploads" {
  bucket = aws_s3_bucket.uploads.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowCloudFrontServicePrincipal"
        Effect = "Allow"
        Principal = {
          Service = "cloudfront.amazonaws.com"
        }
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.uploads.arn}/*"
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = aws_cloudfront_distribution.main.arn
          }
        }
      }
    ]
  })
}

# ============================================
# Lambda Function
# ============================================

resource "aws_iam_role" "lambda" {
  name = "${var.project_name}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_vpc" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Lambda policy for S3, Secrets Manager, etc.
resource "aws_iam_role_policy" "lambda" {
  name = "${var.project_name}-lambda-policy"
  role = aws_iam_role.lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:DeleteObject"
        ]
        Resource = "${aws_s3_bucket.uploads.arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          aws_secretsmanager_secret.db_password.arn
        ]
      }
    ]
  })
}

resource "aws_lambda_function" "api" {
  function_name = "${var.project_name}-api"
  role          = aws_iam_role.lambda.arn

  # This will be updated by CI/CD - create a dummy deployment package first
  filename         = "lambda_deployment.zip"
  source_code_hash = filebase64sha256("lambda_deployment.zip")

  handler = "lambda_handler.lambda_handler"
  runtime = "python3.12"
  timeout = 30
  memory_size = 512  # Start with 512MB, adjust based on usage

  vpc_config {
    subnet_ids         = [aws_subnet.private_a.id, aws_subnet.private_b.id]
    security_group_ids = [aws_security_group.lambda.id]
  }

  environment {
    variables = merge(
      {
        DATABASE_URL    = "postgresql+psycopg2://${aws_rds_cluster.main.master_username}:${random_password.db_password.result}@${aws_rds_cluster.main.endpoint}:5432/${aws_rds_cluster.main.database_name}"
        S3_BUCKET       = aws_s3_bucket.uploads.id
        S3_REGION       = var.aws_region
        STORAGE_BACKEND = "s3"
        APP_ENV         = var.environment
        SECRET_KEY      = random_password.jwt_secret.result
        CORS_ORIGINS    = var.environment == "prod" ? "https://regami.com,https://www.regami.com" : "https://staging.regami.com,http://localhost:5173"
      },
      # Add Basic Auth for staging environment only
      var.environment == "staging" ? {
        BASIC_AUTH_USERNAME = "regami-team"
        BASIC_AUTH_PASSWORD = random_password.staging_basic_auth.result
      } : {}
    )
  }

  tags = {
    Name        = "${var.project_name}-api"
    Environment = var.environment
  }
}

resource "random_password" "jwt_secret" {
  length  = 32
  special = true
}

resource "random_password" "staging_basic_auth" {
  length  = 20
  special = false  # Easier to type for manual auth
}

# CloudWatch Log Group for Lambda
resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${aws_lambda_function.api.function_name}"
  retention_in_days = 7  # Keep logs for 7 days only (cost optimization)
}

# ============================================
# API Gateway (HTTP API - cheaper than REST API)
# ============================================

resource "aws_apigatewayv2_api" "main" {
  name          = "${var.project_name}-api"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = [
      "https://regami.com",
      "https://www.regami.com",
      "https://staging.regami.com",
      "http://localhost:5173",
      "http://127.0.0.1:5173"
    ]
    allow_methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
    allow_headers = ["*"]
    allow_credentials = true
    max_age       = 300
  }

  tags = {
    Name        = "${var.project_name}-api-gateway"
    Environment = var.environment
  }
}

resource "aws_apigatewayv2_integration" "lambda" {
  api_id           = aws_apigatewayv2_api.main.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.api.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "default" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "$default"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_stage" "main" {
  api_id      = aws_apigatewayv2_api.main.id
  name        = "$default"
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gateway.arn
    format = jsonencode({
      requestId      = "$context.requestId"
      ip             = "$context.identity.sourceIp"
      requestTime    = "$context.requestTime"
      httpMethod     = "$context.httpMethod"
      routeKey       = "$context.routeKey"
      status         = "$context.status"
      protocol       = "$context.protocol"
      responseLength = "$context.responseLength"
    })
  }

  tags = {
    Name        = "${var.project_name}-api-stage"
    Environment = var.environment
  }
}

resource "aws_cloudwatch_log_group" "api_gateway" {
  name              = "/aws/apigateway/${var.project_name}"
  retention_in_days = 7
}

resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

# ============================================
# Outputs
# ============================================

output "api_gateway_url" {
  description = "API Gateway URL"
  value       = aws_apigatewayv2_api.main.api_endpoint
}

output "cloudfront_url" {
  description = "CloudFront distribution URL"
  value       = "https://${aws_cloudfront_distribution.main.domain_name}"
}

output "database_endpoint" {
  description = "Aurora Serverless endpoint"
  value       = aws_rds_cluster.main.endpoint
  sensitive   = true
}

output "s3_bucket" {
  description = "S3 uploads bucket"
  value       = aws_s3_bucket.uploads.id
}

output "lambda_function_name" {
  description = "Lambda function name"
  value       = aws_lambda_function.api.function_name
}

output "staging_basic_auth_password" {
  description = "Basic Auth password for staging environment"
  value       = var.environment == "staging" ? random_password.staging_basic_auth.result : "N/A (Production)"
  sensitive   = true
}

output "estimated_monthly_cost" {
  description = "Estimated monthly cost for low traffic (<10K requests/day)"
  value       = <<-EOT
    Estimated Monthly Costs (Low Traffic):
    - Lambda: $2-5 (100K-500K requests, 512MB, 1s avg)
    - API Gateway: $1-3 (100K-500K requests)
    - Aurora Serverless v2: $10-30 (0.5-1 ACU avg, scales to zero)
    - S3: $1-3 (10GB storage, compressed images)
    - CloudFront: $1-2 (10GB transfer)
    - CloudWatch Logs: $1-2 (7-day retention)
    ----------------------------------------
    TOTAL: $16-45/month (vs $250-400 with ECS/RDS)
    SAVINGS: $205-355/month (82-89% reduction)
  EOT
}

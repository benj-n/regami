# AWS Secrets Manager resources for secure credential storage

# Secret for application configuration
resource "aws_secretsmanager_secret" "app_config" {
  name                    = "${local.name}-app-config"
  description             = "Application configuration secrets (SECRET_KEY, DATABASE_URL, etc.)"
  recovery_window_in_days = 7

  tags = {
    Name        = "${local.name}-app-config"
    Environment = var.environment
    Project     = var.project
  }
}

# Secret value for app config (JSON format)
resource "aws_secretsmanager_secret_version" "app_config" {
  secret_id = aws_secretsmanager_secret.app_config.id
  secret_string = jsonencode({
    SECRET_KEY   = var.secret_key
    DATABASE_URL = "postgresql://${var.db_username}:${var.db_password}@${aws_db_instance.main.endpoint}/${var.db_name}"
  })
}

# Secret for S3 credentials (if using custom S3/MinIO)
resource "aws_secretsmanager_secret" "s3_credentials" {
  name                    = "${local.name}-s3-credentials"
  description             = "S3/MinIO access credentials"
  recovery_window_in_days = 7

  tags = {
    Name        = "${local.name}-s3-credentials"
    Environment = var.environment
    Project     = var.project
  }
}

resource "aws_secretsmanager_secret_version" "s3_credentials" {
  secret_id = aws_secretsmanager_secret.s3_credentials.id
  secret_string = jsonencode({
    S3_ACCESS_KEY     = var.s3_access_key
    S3_SECRET_KEY     = var.s3_secret_key
    S3_BUCKET         = aws_s3_bucket.media.bucket
    S3_REGION         = var.region
    S3_ENDPOINT_URL   = var.s3_endpoint_url != "" ? var.s3_endpoint_url : null
    S3_PUBLIC_BASE_URL = var.s3_public_base_url != "" ? var.s3_public_base_url : "https://${aws_s3_bucket.media.bucket}.s3.${var.region}.amazonaws.com"
  })
}

# Secret for SMTP credentials (optional, for email notifications)
resource "aws_secretsmanager_secret" "smtp_credentials" {
  count                   = var.smtp_host != "" ? 1 : 0
  name                    = "${local.name}-smtp-credentials"
  description             = "SMTP server credentials for email notifications"
  recovery_window_in_days = 7

  tags = {
    Name        = "${local.name}-smtp-credentials"
    Environment = var.environment
    Project     = var.project
  }
}

resource "aws_secretsmanager_secret_version" "smtp_credentials" {
  count     = var.smtp_host != "" ? 1 : 0
  secret_id = aws_secretsmanager_secret.smtp_credentials[0].id
  secret_string = jsonencode({
    SMTP_HOST     = var.smtp_host
    SMTP_PORT     = var.smtp_port
    SMTP_USERNAME = var.smtp_username
    SMTP_PASSWORD = var.smtp_password
    SMTP_FROM     = var.smtp_from
  })
}

# IAM policy for ECS tasks to read secrets
resource "aws_iam_policy" "secrets_read" {
  name        = "${local.name}-secrets-read"
  description = "Allow ECS tasks to read application secrets from Secrets Manager"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = concat(
          [
            aws_secretsmanager_secret.app_config.arn,
            aws_secretsmanager_secret.s3_credentials.arn
          ],
          var.smtp_host != "" ? [aws_secretsmanager_secret.smtp_credentials[0].arn] : []
        )
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:DescribeKey"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "kms:ViaService" = "secretsmanager.${var.region}.amazonaws.com"
          }
        }
      }
    ]
  })
}

# Attach secrets read policy to ECS task execution role
resource "aws_iam_role_policy_attachment" "exec_secrets" {
  role       = aws_iam_role.task_exec.name
  policy_arn = aws_iam_policy.secrets_read.arn
}

# Outputs for reference in ECS task definitions
output "app_config_secret_arn" {
  description = "ARN of the app config secret for ECS task definition"
  value       = aws_secretsmanager_secret.app_config.arn
}

output "s3_credentials_secret_arn" {
  description = "ARN of the S3 credentials secret for ECS task definition"
  value       = aws_secretsmanager_secret.s3_credentials.arn
}

output "smtp_credentials_secret_arn" {
  description = "ARN of the SMTP credentials secret for ECS task definition"
  value       = var.smtp_host != "" ? aws_secretsmanager_secret.smtp_credentials[0].arn : null
}

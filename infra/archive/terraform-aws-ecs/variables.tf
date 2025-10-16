variable "region" { type = string }
variable "project" { type = string }
variable "environment" {
  type    = string
  default = "prod"
  description = "Environment name (dev, staging, prod)"
}

# Database variables
variable "db_name" {
  type        = string
  default     = "regami"
  description = "Database name"
}
variable "db_username" {
  type        = string
  description = "Database master username"
}
variable "db_password" {
  type        = string
  sensitive   = true
  description = "Database master password (minimum 16 characters)"
}
variable "db_instance_class" {
  type    = string
  default = "db.t4g.micro"
  description = "RDS instance class"
}
variable "db_allocated_storage" {
  type    = number
  default = 20
  description = "Allocated storage for RDS in GB"
}
variable "db_backup_retention_days" {
  type    = number
  default = 7
  description = "Number of days to retain automated RDS backups (7-35)"
}
variable "s3_version_retention_days" {
  type    = number
  default = 90
  description = "Number of days to retain old S3 object versions"
}

# Networking variables
variable "vpc_id" {
  type        = string
  description = "VPC ID where resources will be created"
}
variable "public_subnets" {
  type        = list(string)
  description = "List of public subnet IDs for ALB"
}
variable "private_subnets" {
  type        = list(string)
  description = "List of private subnet IDs for ECS tasks and RDS"
}

# Application secrets
variable "secret_key" {
  type        = string
  sensitive   = true
  description = "Application SECRET_KEY for JWT signing (minimum 32 characters)"
}

# S3/Storage variables
variable "s3_access_key" {
  type        = string
  sensitive   = true
  default     = ""
  description = "S3 access key (leave empty to use IAM role)"
}
variable "s3_secret_key" {
  type        = string
  sensitive   = true
  default     = ""
  description = "S3 secret key (leave empty to use IAM role)"
}
variable "s3_endpoint_url" {
  type        = string
  default     = ""
  description = "Custom S3 endpoint URL (for MinIO or other S3-compatible storage)"
}
variable "s3_public_base_url" {
  type        = string
  default     = ""
  description = "Public base URL for S3 objects (leave empty to use default AWS URL)"
}

# SMTP variables (optional)
variable "smtp_host" {
  type        = string
  default     = ""
  description = "SMTP server hostname (leave empty to disable email)"
}
variable "smtp_port" {
  type        = number
  default     = 587
  description = "SMTP server port"
}
variable "smtp_username" {
  type        = string
  sensitive   = true
  default     = ""
  description = "SMTP username"
}
variable "smtp_password" {
  type        = string
  sensitive   = true
  default     = ""
  description = "SMTP password"
}
variable "smtp_from" {
  type        = string
  default     = "noreply@regami.com"
  description = "From email address for notifications"
}

# ECS configuration
variable "api_cpu" {
  type        = number
  default     = 256
  description = "CPU units for API task (256 = 0.25 vCPU)"
}
variable "api_memory" {
  type        = number
  default     = 512
  description = "Memory (MB) for API task"
}
variable "api_desired_count" {
  type        = number
  default     = 2
  description = "Desired number of API tasks"
}
variable "api_min_capacity" {
  type        = number
  default     = 1
  description = "Minimum number of API tasks for auto-scaling"
}
variable "api_max_capacity" {
  type        = number
  default     = 10
  description = "Maximum number of API tasks for auto-scaling"
}

variable "web_cpu" {
  type        = number
  default     = 256
  description = "CPU units for Web task (256 = 0.25 vCPU)"
}
variable "web_memory" {
  type        = number
  default     = 512
  description = "Memory (MB) for Web task"
}
variable "web_desired_count" {
  type        = number
  default     = 2
  description = "Desired number of Web tasks"
}
variable "web_min_capacity" {
  type        = number
  default     = 1
  description = "Minimum number of Web tasks for auto-scaling"
}
variable "web_max_capacity" {
  type        = number
  default     = 10
  description = "Maximum number of Web tasks for auto-scaling"
}

# CloudWatch configuration
variable "log_retention_days" {
  type        = number
  default     = 30
  description = "Number of days to retain CloudWatch logs"
}
variable "alb_logs_retention_days" {
  type        = number
  default     = 90
  description = "Number of days to retain ALB access logs in S3"
}
variable "alarm_email" {
  type        = string
  default     = ""
  description = "Email address for CloudWatch alarm notifications (leave empty to skip)"
}
variable "db_max_connections" {
  type        = number
  default     = 100
  description = "Maximum database connections for alarm threshold calculation"
}

# Domain and SSL configuration
variable "domain_name" {
  type        = string
  description = "Domain name for the application (e.g., regami.com)"
}
variable "domain_aliases" {
  type        = list(string)
  default     = []
  description = "Additional domain aliases for SSL certificate (e.g., www.regami.com)"
}
variable "route53_zone_id" {
  type        = string
  default     = ""
  description = "Route53 hosted zone ID (leave empty if managing DNS elsewhere)"
}
variable "create_certificate" {
  type        = bool
  default     = true
  description = "Whether to create ACM certificate (set false if providing existing cert)"
}
variable "certificate_arn" {
  type        = string
  default     = ""
  description = "ARN of existing ACM certificate (if create_certificate is false)"
}
variable "enable_ipv6" {
  type        = bool
  default     = false
  description = "Enable IPv6 support for ALB"
}

# CORS configuration
variable "cors_origins" {
  type        = string
  default     = ""
  description = "Comma-separated list of allowed CORS origins"
}

# CloudFront configuration
variable "enable_cloudfront" {
  type        = bool
  default     = false
  description = "Enable CloudFront CDN for web frontend"
}
variable "cloudfront_price_class" {
  type        = string
  default     = "PriceClass_100"
  description = "CloudFront price class (PriceClass_100, PriceClass_200, PriceClass_All)"
}
variable "cloudfront_aliases" {
  type        = list(string)
  default     = []
  description = "Custom domain names for CloudFront distribution"
}
variable "cloudfront_logging_enabled" {
  type        = bool
  default     = false
  description = "Enable CloudFront access logging"
}

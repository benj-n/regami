# ===================================
# CloudFront Distribution for Web Frontend
# ===================================

# CloudFront Origin Access Control (recommended over OAI)
resource "aws_cloudfront_origin_access_control" "web" {
  count                             = var.enable_cloudfront ? 1 : 0
  name                              = "${local.name}-web-oac"
  description                       = "OAC for ${local.name} web frontend"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# S3 bucket for web static hosting
resource "aws_s3_bucket" "web" {
  count         = var.enable_cloudfront ? 1 : 0
  bucket        = "${local.name}-web-static"
  force_destroy = var.environment != "prod"

  tags = {
    Name        = "${local.name}-web-static"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_public_access_block" "web" {
  count  = var.enable_cloudfront ? 1 : 0
  bucket = aws_s3_bucket.web[0].id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# S3 bucket policy to allow CloudFront access
resource "aws_s3_bucket_policy" "web" {
  count  = var.enable_cloudfront ? 1 : 0
  bucket = aws_s3_bucket.web[0].id

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
        Resource = "${aws_s3_bucket.web[0].arn}/*"
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = aws_cloudfront_distribution.web[0].arn
          }
        }
      }
    ]
  })
}

# CloudFront Distribution
resource "aws_cloudfront_distribution" "web" {
  count               = var.enable_cloudfront ? 1 : 0
  enabled             = true
  is_ipv6_enabled     = var.enable_ipv6
  comment             = "${local.name} web frontend"
  default_root_object = "index.html"
  price_class         = var.cloudfront_price_class
  aliases             = var.cloudfront_aliases

  # S3 origin for static assets
  origin {
    domain_name              = aws_s3_bucket.web[0].bucket_regional_domain_name
    origin_id                = "S3-web"
    origin_access_control_id = aws_cloudfront_origin_access_control.web[0].id
  }

  # ALB origin for API (optional, if you want API through CloudFront)
  origin {
    domain_name = aws_lb.app.dns_name
    origin_id   = "ALB-api"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  # Default cache behavior for web assets
  default_cache_behavior {
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "S3-web"
    compress               = true
    viewer_protocol_policy = "redirect-to-https"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    min_ttl     = 0
    default_ttl = 3600    # 1 hour
    max_ttl     = 86400   # 24 hours

    function_association {
      event_type   = "viewer-request"
      function_arn = aws_cloudfront_function.spa_routing[0].arn
    }
  }

  # Cache behavior for static assets (JS, CSS, images)
  ordered_cache_behavior {
    path_pattern           = "/assets/*"
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "S3-web"
    compress               = true
    viewer_protocol_policy = "redirect-to-https"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    min_ttl     = 31536000  # 1 year
    default_ttl = 31536000  # 1 year
    max_ttl     = 31536000  # 1 year
  }

  # Cache behavior for API requests
  ordered_cache_behavior {
    path_pattern           = "/api/*"
    allowed_methods        = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "ALB-api"
    compress               = true
    viewer_protocol_policy = "redirect-to-https"

    forwarded_values {
      query_string = true
      headers      = ["Authorization", "Accept", "Content-Type"]
      cookies {
        forward = "all"
      }
    }

    min_ttl     = 0
    default_ttl = 0
    max_ttl     = 0
  }

  # Custom error responses for SPA routing
  custom_error_response {
    error_code         = 404
    response_code      = 200
    response_page_path = "/index.html"
  }

  custom_error_response {
    error_code         = 403
    response_code      = 200
    response_page_path = "/index.html"
  }

  # SSL/TLS configuration
  viewer_certificate {
    acm_certificate_arn      = var.create_certificate ? aws_acm_certificate.main[0].arn : var.certificate_arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }

  # Geo restrictions (if needed)
  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  # Logging configuration
  dynamic "logging_config" {
    for_each = var.cloudfront_logging_enabled ? [1] : []
    content {
      include_cookies = false
      bucket          = aws_s3_bucket.cloudfront_logs[0].bucket_domain_name
      prefix          = "cloudfront/"
    }
  }

  tags = {
    Name        = "${local.name}-web-distribution"
    Environment = var.environment
  }

  depends_on = [
    aws_acm_certificate_validation.main
  ]
}

# CloudFront Function for SPA routing (redirects to index.html)
resource "aws_cloudfront_function" "spa_routing" {
  count   = var.enable_cloudfront ? 1 : 0
  name    = "${local.name}-spa-routing"
  runtime = "cloudfront-js-1.0"
  comment = "Redirect SPA routes to index.html"
  publish = true
  code    = <<-EOT
function handler(event) {
    var request = event.request;
    var uri = request.uri;

    // Check if URI has a file extension
    if (!uri.includes('.')) {
        request.uri = '/index.html';
    }

    return request;
}
EOT
}

# S3 bucket for CloudFront logs
resource "aws_s3_bucket" "cloudfront_logs" {
  count         = var.enable_cloudfront && var.cloudfront_logging_enabled ? 1 : 0
  bucket        = "${local.name}-cloudfront-logs"
  force_destroy = var.environment != "prod"

  tags = {
    Name        = "${local.name}-cloudfront-logs"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_public_access_block" "cloudfront_logs" {
  count  = var.enable_cloudfront && var.cloudfront_logging_enabled ? 1 : 0
  bucket = aws_s3_bucket.cloudfront_logs[0].id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "cloudfront_logs" {
  count  = var.enable_cloudfront && var.cloudfront_logging_enabled ? 1 : 0
  bucket = aws_s3_bucket.cloudfront_logs[0].id

  rule {
    id     = "delete-old-logs"
    status = "Enabled"

    expiration {
      days = 90
    }
  }
}

# ===================================
# Outputs
# ===================================

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID"
  value       = var.enable_cloudfront ? aws_cloudfront_distribution.web[0].id : null
}

output "cloudfront_domain_name" {
  description = "CloudFront distribution domain name"
  value       = var.enable_cloudfront ? aws_cloudfront_distribution.web[0].domain_name : null
}

output "cloudfront_url" {
  description = "CloudFront distribution HTTPS URL"
  value       = var.enable_cloudfront ? "https://${aws_cloudfront_distribution.web[0].domain_name}" : null
}

output "web_s3_bucket" {
  description = "S3 bucket for web static files"
  value       = var.enable_cloudfront ? aws_s3_bucket.web[0].bucket : null
}

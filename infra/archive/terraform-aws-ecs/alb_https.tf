# HTTPS Configuration for Application Load Balancer

# ACM Certificate for HTTPS
resource "aws_acm_certificate" "main" {
  count             = var.create_certificate ? 1 : 0
  domain_name       = var.domain_name
  validation_method = "DNS"

  subject_alternative_names = var.domain_aliases

  lifecycle {
    create_before_destroy = true
  }

  tags = {
    Name        = "${local.name}-cert"
    Environment = var.environment
  }
}

# Route53 Zone (data source - assumes zone exists)
data "aws_route53_zone" "main" {
  count        = var.create_certificate && var.route53_zone_id != "" ? 1 : 0
  zone_id      = var.route53_zone_id
  private_zone = false
}

# Route53 records for ACM certificate validation
resource "aws_route53_record" "cert_validation" {
  for_each = var.create_certificate && var.route53_zone_id != "" ? {
    for dvo in aws_acm_certificate.main[0].domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  } : {}

  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = data.aws_route53_zone.main[0].zone_id
}

# ACM certificate validation
resource "aws_acm_certificate_validation" "main" {
  count                   = var.create_certificate && var.route53_zone_id != "" ? 1 : 0
  certificate_arn         = aws_acm_certificate.main[0].arn
  validation_record_fqdns = [for record in aws_route53_record.cert_validation : record.fqdn]
}

# Update ALB to use security group
resource "aws_lb" "app_updated" {
  count              = 0  # Disabled - will update existing ALB
  name               = "${local.name}-alb"
  load_balancer_type = "application"
  subnets            = var.public_subnets
  security_groups    = [aws_security_group.alb.id]

  enable_deletion_protection = var.environment == "prod" ? true : false
  enable_http2              = true
  enable_cross_zone_load_balancing = true

  tags = {
    Name        = "${local.name}-alb"
    Environment = var.environment
  }
}

# HTTPS Listener
resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.app.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.create_certificate ? aws_acm_certificate.main[0].arn : var.certificate_arn

  default_action {
    type = "fixed-response"
    fixed_response {
      content_type = "text/plain"
      message_body = "Not Found"
      status_code  = "404"
    }
  }

  tags = {
    Name        = "${local.name}-https-listener"
    Environment = var.environment
  }
}

# Update HTTP listener to redirect to HTTPS
resource "aws_lb_listener" "http_redirect" {
  load_balancer_arn = aws_lb.app.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "redirect"
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }

  tags = {
    Name        = "${local.name}-http-redirect"
    Environment = var.environment
  }
}

# HTTPS Listener Rules for API
resource "aws_lb_listener_rule" "api_https" {
  listener_arn = aws_lb_listener.https.arn
  priority     = 10

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }

  condition {
    path_pattern {
      values = ["/api/*", "/auth/*", "/users/*", "/dogs/*", "/notifications/*", "/availability/*", "/health"]
    }
  }

  tags = {
    Name        = "${local.name}-api-https-rule"
    Environment = var.environment
  }
}

# HTTPS Listener Rules for Web
resource "aws_lb_listener_rule" "web_https" {
  listener_arn = aws_lb_listener.https.arn
  priority     = 20

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.web.arn
  }

  condition {
    path_pattern {
      values = ["/*"]
    }
  }

  tags = {
    Name        = "${local.name}-web-https-rule"
    Environment = var.environment
  }
}

# Route53 A record for domain
resource "aws_route53_record" "app" {
  count   = var.route53_zone_id != "" ? 1 : 0
  zone_id = var.route53_zone_id
  name    = var.domain_name
  type    = "A"

  alias {
    name                   = aws_lb.app.dns_name
    zone_id                = aws_lb.app.zone_id
    evaluate_target_health = true
  }
}

# Route53 AAAA record for IPv6 (optional)
resource "aws_route53_record" "app_ipv6" {
  count   = var.route53_zone_id != "" && var.enable_ipv6 ? 1 : 0
  zone_id = var.route53_zone_id
  name    = var.domain_name
  type    = "AAAA"

  alias {
    name                   = aws_lb.app.dns_name
    zone_id                = aws_lb.app.zone_id
    evaluate_target_health = true
  }
}

# Outputs
output "certificate_arn" {
  description = "ARN of the ACM certificate"
  value       = var.create_certificate ? aws_acm_certificate.main[0].arn : var.certificate_arn
}

output "https_listener_arn" {
  description = "ARN of the HTTPS listener"
  value       = aws_lb_listener.https.arn
}

output "app_url" {
  description = "Application URL"
  value       = "https://${var.domain_name}"
}

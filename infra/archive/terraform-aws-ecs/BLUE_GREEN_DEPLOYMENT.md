# Blue/Green Deployment Strategy for Regami ECS

## Overview

Blue/green deployment enables zero-downtime releases with instant rollback capability by maintaining two identical production environments.

## Architecture

```
┌─────────────┐
│   Route53   │ (DNS)
└──────┬──────┘
       │
┌──────▼──────┐
│     ALB     │ (Application Load Balancer)
└──────┬──────┘
       │
       ├──────────────┬──────────────┐
       │              │              │
┌──────▼──────┐  ┌───▼────────┐ ┌──▼─────────┐
│Target Group │  │Target Group│ │Target Group│
│   Blue      │  │   Green    │ │  Canary    │
│  (Current)  │  │   (New)    │ │  (10%)     │
└──────┬──────┘  └────┬───────┘ └────┬───────┘
       │              │              │
┌──────▼──────┐  ┌───▼────────┐ ┌──▼─────────┐
│ ECS Service │  │ECS Service │ │ECS Service │
│    Blue     │  │   Green    │ │   Canary   │
└─────────────┘  └────────────┘ └────────────┘
```

## Terraform Configuration

### Add to `infra/aws/ecs.tf`

```hcl
# Blue/Green Deployment Configuration

# Blue Target Group (current production)
resource "aws_lb_target_group" "app_blue" {
  name     = "${var.app_name}-blue-tg"
  port     = 8000
  protocol = "HTTP"
  vpc_id   = aws_vpc.main.id

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 2
  }

  deregistration_delay = 30

  tags = {
    Name        = "${var.app_name}-blue-tg"
    Environment = var.environment
    Deployment  = "blue"
  }
}

# Green Target Group (new deployment)
resource "aws_lb_target_group" "app_green" {
  name     = "${var.app_name}-green-tg"
  port     = 8000
  protocol = "HTTP"
  vpc_id   = aws_vpc.main.id

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/health?check=db"  # More thorough check for green
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 2
  }

  deregistration_delay = 30

  tags = {
    Name        = "${var.app_name}-green-tg"
    Environment = var.environment
    Deployment  = "green"
  }
}

# ALB Listener Rule - Initially points to Blue
resource "aws_lb_listener" "app_https" {
  load_balancer_arn = aws_lb.main.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS-1-2-2017-01"
  certificate_arn   = aws_acm_certificate.app.arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app_blue.arn
  }

  lifecycle {
    ignore_changes = [
      default_action  # Managed by CodeDeploy during deployment
    ]
  }
}

# ECS Service with Blue/Green Deployment
resource "aws_ecs_service" "app" {
  name            = "${var.app_name}-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = var.ecs_desired_count
  launch_type     = "FARGATE"

  deployment_controller {
    type = "CODE_DEPLOY"  # Enable CodeDeploy for blue/green
  }

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.app_blue.arn
    container_name   = "app"
    container_port   = 8000
  }

  lifecycle {
    ignore_changes = [
      desired_count,
      task_definition,
      load_balancer
    ]
  }

  depends_on = [aws_lb_listener.app_https]
}

# CodeDeploy Application
resource "aws_codedeploy_app" "app" {
  name             = "${var.app_name}-codedeploy"
  compute_platform = "ECS"
}

# CodeDeploy Deployment Group
resource "aws_codedeploy_deployment_group" "app" {
  app_name               = aws_codedeploy_app.app.name
  deployment_group_name  = "${var.app_name}-deployment-group"
  service_role_arn       = aws_iam_role.codedeploy.arn
  deployment_config_name = "CodeDeployDefault.ECSCanary10Percent5Minutes"

  auto_rollback_configuration {
    enabled = true
    events  = ["DEPLOYMENT_FAILURE", "DEPLOYMENT_STOP_ON_ALARM"]
  }

  blue_green_deployment_config {
    deployment_ready_option {
      action_on_timeout = "CONTINUE_DEPLOYMENT"
    }

    terminate_blue_instances_on_deployment_success {
      action                           = "TERMINATE"
      termination_wait_time_in_minutes = 5
    }
  }

  deployment_style {
    deployment_option = "WITH_TRAFFIC_CONTROL"
    deployment_type   = "BLUE_GREEN"
  }

  ecs_service {
    cluster_name = aws_ecs_cluster.main.name
    service_name = aws_ecs_service.app.name
  }

  load_balancer_info {
    target_group_pair_info {
      prod_traffic_route {
        listener_arns = [aws_lb_listener.app_https.arn]
      }

      target_group {
        name = aws_lb_target_group.app_blue.name
      }

      target_group {
        name = aws_lb_target_group.app_green.name
      }
    }
  }

  # Automatic rollback on CloudWatch alarms
  alarm_configuration {
    enabled = true
    alarms  = [
      aws_cloudwatch_metric_alarm.ecs_high_5xx_rate.alarm_name,
      aws_cloudwatch_metric_alarm.ecs_low_health_check.alarm_name
    ]
  }
}

# IAM Role for CodeDeploy
resource "aws_iam_role" "codedeploy" {
  name = "${var.app_name}-codedeploy-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "codedeploy.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "codedeploy" {
  role       = aws_iam_role.codedeploy.name
  policy_arn = "arn:aws:iam::aws:policy/AWSCodeDeployRoleForECS"
}

# CloudWatch Alarms for Rollback
resource "aws_cloudwatch_metric_alarm" "ecs_high_5xx_rate" {
  alarm_name          = "${var.app_name}-high-5xx-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "HTTPCode_Target_5XX_Count"
  namespace           = "AWS/ApplicationELB"
  period              = "60"
  statistic           = "Sum"
  threshold           = "10"
  alarm_description   = "Triggers rollback if 5XX errors exceed threshold"

  dimensions = {
    LoadBalancer = aws_lb.main.arn_suffix
  }
}

resource "aws_cloudwatch_metric_alarm" "ecs_low_health_check" {
  alarm_name          = "${var.app_name}-low-health-check"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "HealthyHostCount"
  namespace           = "AWS/ApplicationELB"
  period              = "60"
  statistic           = "Average"
  threshold           = "1"
  alarm_description   = "Triggers rollback if healthy hosts drop below 1"

  dimensions = {
    TargetGroup  = aws_lb_target_group.app_green.arn_suffix
    LoadBalancer = aws_lb.main.arn_suffix
  }
}
```

## Deployment Process

### 1. Build New Image

```bash
# Build and push new Docker image
docker build -t regami-api:v1.2.0 .
docker tag regami-api:v1.2.0 123456789.dkr.ecr.us-east-1.amazonaws.com/regami-api:v1.2.0
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/regami-api:v1.2.0
```

### 2. Create New Task Definition

```bash
# Update task definition with new image
aws ecs register-task-definition \
  --cli-input-json file://task-definition.json \
  --region us-east-1
```

### 3. Create AppSpec File

Create `appspec.yaml`:

```yaml
version: 0.0
Resources:
  - TargetService:
      Type: AWS::ECS::Service
      Properties:
        TaskDefinition: "arn:aws:ecs:us-east-1:123456789:task-definition/regami-api:42"
        LoadBalancerInfo:
          ContainerName: "app"
          ContainerPort: 8000
        PlatformVersion: "LATEST"
        NetworkConfiguration:
          AwsvpcConfiguration:
            Subnets:
              - "subnet-xxx"
              - "subnet-yyy"
            SecurityGroups:
              - "sg-xxx"
            AssignPublicIp: "DISABLED"

Hooks:
  - BeforeInstall: "LambdaFunctionToRunBeforeInstall"
  - AfterInstall: "LambdaFunctionToRunAfterInstall"
  - AfterAllowTestTraffic: "LambdaFunctionToRunAfterTestTraffic"
  - BeforeAllowTraffic: "LambdaFunctionToRunBeforeTraffic"
  - AfterAllowTraffic: "LambdaFunctionToRunAfterTraffic"
```

### 4. Deploy with CodeDeploy

```bash
# Create deployment
aws deploy create-deployment \
  --application-name regami-codedeploy \
  --deployment-group-name regami-deployment-group \
  --revision '{
    "revisionType": "AppSpecContent",
    "appSpecContent": {
      "content": "'$(cat appspec.yaml)'"
    }
  }' \
  --description "Deploy v1.2.0" \
  --region us-east-1
```

### 5. Monitor Deployment

```bash
# Get deployment status
aws deploy get-deployment \
  --deployment-id d-XXXXXXXXX \
  --region us-east-1

# Watch deployment progress
aws deploy get-deployment-target \
  --deployment-id d-XXXXXXXXX \
  --target-id xxx \
  --region us-east-1
```

## Traffic Shifting Strategies

### Canary (Recommended)

**CodeDeployDefault.ECSCanary10Percent5Minutes**
- Shifts 10% of traffic to green
- Waits 5 minutes
- Monitors alarms
- Shifts remaining 90% if healthy

### Linear

**CodeDeployDefault.ECSLinear10PercentEvery3Minutes**
- Shifts 10% every 3 minutes
- Total deployment time: ~30 minutes
- More gradual rollout

### All-at-Once

**CodeDeployDefault.ECSAllAtOnce**
- Shifts 100% immediately
- Fastest but riskiest

## Rollback Procedures

### Automatic Rollback

Triggered by:
- CloudWatch alarm breaches (5XX errors, unhealthy hosts)
- Failed health checks
- Manual stop

### Manual Rollback

```bash
# Stop deployment (triggers automatic rollback)
aws deploy stop-deployment \
  --deployment-id d-XXXXXXXXX \
  --auto-rollback-enabled \
  --region us-east-1
```

### Emergency Rollback (ALB Listener)

```bash
# Switch listener back to blue target group
aws elbv2 modify-listener \
  --listener-arn arn:aws:elasticloadbalancing:us-east-1:123456789:listener/app/xxx \
  --default-actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:us-east-1:123456789:targetgroup/regami-blue-tg/xxx \
  --region us-east-1
```

## Testing Green Environment

### Pre-Production Smoke Tests

```bash
# Test green target group before traffic shift
curl -H "Host: regami.com" \
  http://internal-alb-xxx.us-east-1.elb.amazonaws.com/health?check=db

# Run integration tests against green
pytest tests/integration/ --target=green
```

### Canary Testing

During 10% traffic phase:
- Monitor error rates
- Check latency (p50, p95, p99)
- Verify database connections
- Test critical user flows

## Monitoring During Deployment

Key metrics to watch:
- **Error Rate**: Target < 0.1% (5XX responses)
- **Latency**: p95 < 500ms, p99 < 1000ms
- **Health Checks**: 100% healthy hosts
- **Database Connections**: Stable connection pool
- **Memory/CPU**: Within normal ranges

## Best Practices

1. **Test in staging first** with identical blue/green setup
2. **Deploy during low-traffic periods** (early morning UTC)
3. **Monitor for 30 minutes** after 100% traffic shift
4. **Keep blue environment running** for 1 hour before termination
5. **Use feature flags** for risky changes
6. **Database migrations** should be backward compatible
7. **Automated smoke tests** before traffic shift
8. **Notify team** in Slack/Discord before deployment

## Troubleshooting

### Deployment Stuck

- Check ECS service events: `aws ecs describe-services`
- Verify new tasks are healthy
- Check application logs in CloudWatch

### High Error Rate After Deploy

- Stop deployment immediately
- Check application logs for errors
- Verify environment variables
- Check database connectivity

### Rollback Failed

- Manually switch ALB listener to blue
- Scale up blue ECS service
- Investigate root cause before retry

## GitHub Actions Integration

```yaml
# .github/workflows/deploy-production.yml
name: Deploy to Production (Blue/Green)

on:
  push:
    tags:
      - 'v*'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Configure AWS
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1

      - name: Login to ECR
        run: |
          aws ecr get-login-password --region us-east-1 | \
          docker login --username AWS --password-stdin ${{ secrets.ECR_REGISTRY }}

      - name: Build and Push
        run: |
          docker build -t regami-api:${{ github.ref_name }} .
          docker tag regami-api:${{ github.ref_name }} ${{ secrets.ECR_REGISTRY }}/regami-api:${{ github.ref_name }}
          docker push ${{ secrets.ECR_REGISTRY }}/regami-api:${{ github.ref_name }}

      - name: Deploy with CodeDeploy
        run: |
          # Create new task definition
          # Create CodeDeploy deployment
          # Wait for deployment to complete
          ./scripts/deploy-blue-green.sh ${{ github.ref_name }}
```

## Cost Optimization

- Blue and green environments run concurrently only during deployment (~15 minutes)
- Use Fargate Spot for green environment testing
- Automatically terminate blue after successful deployment
- Estimated additional cost: ~$5-10 per deployment

## Next Steps

1. Implement blue/green infrastructure with Terraform
2. Create AppSpec templates
3. Set up CloudWatch alarms
4. Test deployment in staging
5. Document runbook for production deployments
6. Train team on rollback procedures

# Disaster Recovery Plan for Regami

## Overview

Multi-region disaster recovery strategy with RDS read replicas, automated DNS failover, and documented recovery procedures.

**RTO (Recovery Time Objective):** 15 minutes
**RPO (Recovery Point Objective):** 5 minutes

## Architecture

```
Primary Region (us-east-1)          Secondary Region (us-west-2)
┌─────────────────────────┐        ┌─────────────────────────┐
│      Route53 (DNS)      │◄──────►│      Route53 (DNS)      │
│   Health Check Primary  │        │  Health Check Secondary │
└────────────┬────────────┘        └────────────┬────────────┘
             │                                  │
      ┌──────▼──────┐                    ┌─────▼───────┐
      │     ALB     │                    │     ALB     │
      │  (Active)   │                    │  (Standby)  │
      └──────┬──────┘                    └─────┬───────┘
             │                                  │
      ┌──────▼──────┐                    ┌─────▼───────┐
      │ ECS Service │                    │ ECS Service │
      │  (Running)  │                    │  (Stopped)  │
      └──────┬──────┘                    └─────┬───────┘
             │                                  │
      ┌──────▼──────┐                    ┌─────▼───────┐
      │ RDS Primary │──────Replication──►│ RDS Replica │
      │   (Master)  │                    │  (Read-Only)│
      └─────────────┘                    └─────────────┘
```

## Terraform Configuration

```hcl
# Secondary Region RDS Read Replica
provider "aws" {
  alias  = "secondary"
  region = "us-west-2"
}

# KMS Key in secondary region for encryption
resource "aws_kms_key" "rds_secondary" {
  provider    = aws.secondary
  description = "RDS encryption key for secondary region"

  tags = {
    Name        = "${var.app_name}-rds-key-secondary"
    Environment = var.environment
  }
}

resource "aws_kms_alias" "rds_secondary" {
  provider      = aws.secondary
  name          = "alias/${var.app_name}-rds-secondary"
  target_key_id = aws_kms_key.rds_secondary.key_id
}

# Cross-Region Read Replica
resource "aws_db_instance" "replica" {
  provider               = aws.secondary
  identifier             = "${var.app_name}-db-replica"
  replicate_source_db    = aws_db_instance.main.arn
  instance_class         = var.db_instance_class
  publicly_accessible    = false
  skip_final_snapshot    = false
  final_snapshot_identifier = "${var.app_name}-db-replica-final-snapshot"
  backup_retention_period   = 7
  kms_key_id            = aws_kms_key.rds_secondary.arn
  storage_encrypted     = true

  tags = {
    Name        = "${var.app_name}-db-replica"
    Environment = var.environment
    Region      = "us-west-2"
  }
}

# Route53 Health Checks
resource "aws_route53_health_check" "primary" {
  fqdn              = aws_lb.main.dns_name
  port              = 443
  type              = "HTTPS"
  resource_path     = "/health?check=db"
  failure_threshold = "3"
  request_interval  = "30"

  tags = {
    Name = "${var.app_name}-primary-health-check"
  }
}

resource "aws_route53_health_check" "secondary" {
  provider          = aws.secondary
  fqdn              = aws_lb.secondary.dns_name
  port              = 443
  type              = "HTTPS"
  resource_path     = "/health"
  failure_threshold = "3"
  request_interval  = "30"

  tags = {
    Name = "${var.app_name}-secondary-health-check"
  }
}

# Route53 Failover Records
resource "aws_route53_record" "primary" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "api.regami.com"
  type    = "A"

  set_identifier = "primary"
  failover_routing_policy {
    type = "PRIMARY"
  }
  health_check_id = aws_route53_health_check.primary.id

  alias {
    name                   = aws_lb.main.dns_name
    zone_id                = aws_lb.main.zone_id
    evaluate_target_health = true
  }
}

resource "aws_route53_record" "secondary" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "api.regami.com"
  type    = "A"

  set_identifier = "secondary"
  failover_routing_policy {
    type = "SECONDARY"
  }

  alias {
    name                   = aws_lb.secondary.dns_name
    zone_id                = aws_lb.secondary.zone_id
    evaluate_target_health = true
  }
}

# CloudWatch Alarm for Failover
resource "aws_cloudwatch_metric_alarm" "primary_unhealthy" {
  alarm_name          = "${var.app_name}-primary-region-unhealthy"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "3"
  metric_name         = "HealthCheckStatus"
  namespace           = "AWS/Route53"
  period              = "60"
  statistic           = "Minimum"
  threshold           = "1"
  alarm_description   = "Primary region health check failing"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    HealthCheckId = aws_route53_health_check.primary.id
  }
}
```

## Failover Procedures

### Automatic Failover

Route53 automatically fails over when:
1. Primary health check fails 3 consecutive times (90 seconds)
2. DNS TTL expires (60 seconds)
3. Traffic routes to secondary region

**Total Failover Time:** ~3-5 minutes

### Manual Failover (Planned Maintenance)

```bash
# 1. Promote read replica to standalone instance
aws rds promote-read-replica \
  --db-instance-identifier regami-db-replica \
  --region us-west-2

# 2. Wait for promotion to complete
aws rds wait db-instance-available \
  --db-instance-identifier regami-db-replica \
  --region us-west-2

# 3. Update secondary ECS service to use promoted database
aws ecs update-service \
  --cluster regami-cluster-secondary \
  --service regami-service-secondary \
  --desired-count 2 \
  --region us-west-2

# 4. Switch Route53 to secondary (disable primary)
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1234567890ABC \
  --change-batch file://failover-to-secondary.json
```

### Failback to Primary

```bash
# 1. Ensure primary region is healthy
curl https://api-primary.regami.com/health?check=db

# 2. Create new read replica from secondary (now primary)
aws rds create-db-instance-read-replica \
  --db-instance-identifier regami-db-primary-new \
  --source-db-instance-identifier regami-db-replica \
  --region us-east-1

# 3. Wait for replication to catch up
aws rds wait db-instance-available \
  --db-instance-identifier regami-db-primary-new \
  --region us-east-1

# 4. Promote new primary
aws rds promote-read-replica \
  --db-instance-identifier regami-db-primary-new \
  --region us-east-1

# 5. Update Route53 back to primary
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1234567890ABC \
  --change-batch file://failover-to-primary.json
```

## Data Backup Strategy

### Automated RDS Snapshots
- **Frequency:** Daily at 3:00 AM UTC
- **Retention:** 7 days (primary), 14 days (compliance snapshots)
- **Cross-Region Copy:** Daily snapshots copied to us-west-2

### Manual Snapshots
- Before major deployments
- Before database migrations
- Monthly compliance snapshots (retained 1 year)

### S3 Data Backup
```hcl
# S3 Cross-Region Replication
resource "aws_s3_bucket_replication_configuration" "uploads" {
  bucket = aws_s3_bucket.uploads.id
  role   = aws_iam_role.s3_replication.arn

  rule {
    id     = "replicate-all"
    status = "Enabled"

    destination {
      bucket        = aws_s3_bucket.uploads_replica.arn
      storage_class = "STANDARD_IA"

      replication_time {
        status = "Enabled"
        time {
          minutes = 15
        }
      }
    }
  }
}
```

## Testing DR Plan

### Quarterly DR Drill

**Checklist:**
- [ ] Schedule drill during low-traffic period
- [ ] Notify team 24 hours in advance
- [ ] Document start time
- [ ] Execute manual failover to secondary
- [ ] Verify application functionality
- [ ] Check data consistency
- [ ] Measure RTO/RPO
- [ ] Execute failback to primary
- [ ] Document issues and improvements
- [ ] Update runbook based on learnings

### DR Drill Script

```bash
#!/bin/bash
# dr-drill.sh - Disaster Recovery Drill

echo "=== Regami DR Drill ==="
echo "Start Time: $(date)"

# Step 1: Health check primary
echo "1. Checking primary region health..."
PRIMARY_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" https://api.regami.com/health?check=db)
echo "Primary health: $PRIMARY_HEALTH"

# Step 2: Promote replica
echo "2. Promoting read replica..."
aws rds promote-read-replica \
  --db-instance-identifier regami-db-replica \
  --region us-west-2

# Step 3: Wait for promotion
echo "3. Waiting for replica promotion..."
aws rds wait db-instance-available \
  --db-instance-identifier regami-db-replica \
  --region us-west-2

# Step 4: Scale up secondary ECS
echo "4. Scaling up secondary ECS service..."
aws ecs update-service \
  --cluster regami-cluster-secondary \
  --service regami-service-secondary \
  --desired-count 2 \
  --region us-west-2

# Step 5: Health check secondary
echo "5. Checking secondary region health..."
sleep 60
SECONDARY_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" https://api-secondary.regami.com/health?check=db)
echo "Secondary health: $SECONDARY_HEALTH"

# Step 6: Verify application
echo "6. Running smoke tests..."
pytest tests/smoke/ --target=secondary

echo "=== DR Drill Complete ==="
echo "End Time: $(date)"
echo "Duration: Calculate manually"
echo "Results: Review test output above"
```

## Monitoring

### CloudWatch Dashboards

Create dashboard with:
- Route53 health check status (primary & secondary)
- RDS replication lag
- Cross-region latency
- S3 replication status
- ECS service health (both regions)

### Alarms

```hcl
resource "aws_cloudwatch_metric_alarm" "replication_lag" {
  alarm_name          = "${var.app_name}-high-replication-lag"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "ReplicaLag"
  namespace           = "AWS/RDS"
  period              = "60"
  statistic           = "Average"
  threshold           = "300"  # 5 minutes
  alarm_description   = "RDS replication lag exceeds 5 minutes"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.replica.id
  }
}
```

## Cost Estimate

**Monthly Costs:**
- RDS Read Replica (us-west-2): ~$100-200
- Cross-region data transfer: ~$20-50
- Route53 health checks: ~$1
- S3 replication: ~$10-30
- **Total:** ~$130-280/month

## Recovery Scenarios

### Scenario 1: Primary Region Outage
- **Detection:** Route53 health check fails
- **Action:** Automatic failover to secondary
- **RTO:** 3-5 minutes
- **RPO:** 5 minutes (replication lag)

### Scenario 2: Database Corruption
- **Detection:** Application errors, data inconsistencies
- **Action:** Restore from latest snapshot
- **RTO:** 15-30 minutes
- **RPO:** Up to 1 hour (snapshot frequency)

### Scenario 3: Accidental Data Deletion
- **Detection:** User report, monitoring alerts
- **Action:** Point-in-time recovery from RDS
- **RTO:** 10-20 minutes
- **RPO:** 5 minutes

### Scenario 4: Complete AWS Outage (Rare)
- **Detection:** All AWS services down
- **Action:** Restore on alternative cloud (pre-prepared)
- **RTO:** 4-8 hours
- **RPO:** Up to 1 day

## Compliance

### Data Residency
- Primary data in France-preferred AWS region (eu-west-3 recommended)
- Cross-region replica in eu-central-1 (Frankfurt)
- GDPR compliance maintained

### Audit Trail
- All failover events logged to CloudWatch
- S3 access logs enabled
- Database query logs enabled
- Retained for 90 days

## Contact Information

**During DR Event:**
1. Incident Commander: [Name] - [Phone]
2. Database Lead: [Name] - [Phone]
3. DevOps Lead: [Name] - [Phone]
4. AWS Support: Premium Support - [Case Portal]

**Escalation:**
- Severity 1 (complete outage): Page all leads immediately
- Severity 2 (degraded): Notify in Slack, email
- Severity 3 (potential issue): Monitor, no immediate action

## Next Steps

1. Implement cross-region RDS replica
2. Configure Route53 health checks and failover
3. Set up S3 replication
4. Create CloudWatch alarms
5. Schedule first DR drill
6. Document lessons learned
7. Refine RTO/RPO targets based on business needs

```

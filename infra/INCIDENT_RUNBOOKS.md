# Regami Incident Runbooks

Complete operational procedures for common incidents and maintenance tasks.

---

## Table of Contents

1. [Database Failover](#runbook-1-database-failover)
2. [Rollback Deployment](#runbook-2-rollback-deployment)
3. [Scale ECS Tasks Manually](#runbook-3-scale-ecs-tasks-manually)
4. [Investigate High 5XX Error Rate](#runbook-4-investigate-high-5xx-error-rate)
5. [Restore from Backup](#runbook-5-restore-from-backup)

---

## Runbook 1: Database Failover

**When to use:** Primary RDS instance is down or degraded

**Prerequisites:**
- AWS CLI configured
- Cross-region read replica exists
- Access to Route53

**Estimated Time:** 15-20 minutes

### Steps

#### 1. Verify Primary Database Status

```bash
# Check primary database status
aws rds describe-db-instances \
  --db-instance-identifier regami-db-primary \
  --region us-east-1 \
  --query 'DBInstances[0].DBInstanceStatus'

# Expected output: "available", "failed", "inaccessible-encryption-credentials", etc.
```

#### 2. Check Read Replica Health

```bash
# Check replica status
aws rds describe-db-instances \
  --db-instance-identifier regami-db-replica \
  --region us-west-2 \
  --query 'DBInstances[0].[DBInstanceStatus,ReplicationSourceIdentifier]'

# Check replication lag
aws rds describe-db-instances \
  --db-instance-identifier regami-db-replica \
  --region us-west-2 \
  --query 'DBInstances[0].ReplicaLag'
```

#### 3. Pause Application (Optional)

```bash
# Scale down ECS to prevent writes during failover
aws ecs update-service \
  --cluster regami-cluster \
  --service regami-service \
  --desired-count 0 \
  --region us-east-1
```

#### 4. Promote Read Replica

```bash
# Promote replica to standalone database
aws rds promote-read-replica \
  --db-instance-identifier regami-db-replica \
  --backup-retention-period 7 \
  --region us-west-2

# Wait for promotion to complete (5-10 minutes)
aws rds wait db-instance-available \
  --db-instance-identifier regami-db-replica \
  --region us-west-2
```

#### 5. Update Application Configuration

```bash
# Update ECS task definition with new database endpoint
# Edit task-definition.json:
{
  "environment": [
    {
      "name": "DATABASE_URL",
      "value": "postgresql://regami-db-replica.xxx.us-west-2.rds.amazonaws.com:5432/regami"
    }
  ]
}

# Register new task definition
aws ecs register-task-definition \
  --cli-input-json file://task-definition.json \
  --region us-west-2
```

#### 6. Start Application in Secondary Region

```bash
# Update ECS service in secondary region
aws ecs update-service \
  --cluster regami-cluster-secondary \
  --service regami-service-secondary \
  --desired-count 2 \
  --task-definition regami-api:LATEST \
  --region us-west-2

# Wait for tasks to be running
aws ecs wait services-stable \
  --cluster regami-cluster-secondary \
  --services regami-service-secondary \
  --region us-west-2
```

#### 7. Update DNS (Route53)

```bash
# Switch Route53 to point to secondary region ALB
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1234567890ABC \
  --change-batch file://failover-to-secondary.json

# failover-to-secondary.json:
{
  "Changes": [{
    "Action": "UPSERT",
    "ResourceRecordSet": {
      "Name": "api.regami.com",
      "Type": "A",
      "SetIdentifier": "secondary",
      "Failover": "PRIMARY",
      "AliasTarget": {
        "HostedZoneId": "Z3AADJGX6KTTL2",
        "DNSName": "regami-alb-secondary.us-west-2.elb.amazonaws.com",
        "EvaluateTargetHealth": true
      }
    }
  }]
}
```

#### 8. Verify Application

```bash
# Test health endpoint
curl -v https://api.regami.com/health?check=db

# Test authentication
curl -X POST https://api.regami.com/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test"}'

# Check CloudWatch logs
aws logs tail /ecs/regami-api --follow --region us-west-2
```

#### 9. Document Incident

- Time of detection
- Time of failover start
- Time of failover complete
- Root cause
- Actions taken
- Downtime duration
- Lessons learned

### Rollback Procedure

If failover causes issues:

```bash
# Scale down secondary
aws ecs update-service \
  --cluster regami-cluster-secondary \
  --service regami-service-secondary \
  --desired-count 0 \
  --region us-west-2

# Restore primary (if possible)
# OR
# Switch DNS back to primary
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1234567890ABC \
  --change-batch file://failback-to-primary.json
```

---

## Runbook 2: Rollback Deployment

**When to use:** New deployment causing errors or degraded performance

**Prerequisites:**
- Previous task definition ARN
- AWS CLI configured
- CodeDeploy access (for blue/green)

**Estimated Time:** 5-10 minutes

### Quick Rollback (ECS)

#### 1. Identify Previous Task Definition

```bash
# List recent task definitions
aws ecs list-task-definitions \
  --family-prefix regami-api \
  --sort DESC \
  --max-results 5

# Example output:
# regami-api:42  <- Current (broken)
# regami-api:41  <- Previous (known good)
# regami-api:40
```

#### 2. Rollback to Previous Version

```bash
# Update ECS service to use previous task definition
aws ecs update-service \
  --cluster regami-cluster \
  --service regami-service \
  --task-definition regami-api:41 \
  --force-new-deployment \
  --region us-east-1

# Monitor rollback progress
watch 'aws ecs describe-services \
  --cluster regami-cluster \
  --services regami-service \
  --region us-east-1 \
  --query "services[0].[deployments,events[0:3]]"'
```

#### 3. Verify Rollback

```bash
# Check running tasks are using correct version
aws ecs list-tasks \
  --cluster regami-cluster \
  --service-name regami-service \
  --region us-east-1

aws ecs describe-tasks \
  --cluster regami-cluster \
  --tasks <task-arn> \
  --region us-east-1 \
  --query 'tasks[0].taskDefinitionArn'

# Test application
curl https://api.regami.com/health?check=db
```

### Rollback Blue/Green Deployment (CodeDeploy)

#### 1. Stop Deployment

```bash
# Find deployment ID
aws deploy list-deployments \
  --application-name regami-codedeploy \
  --deployment-group-name regami-deployment-group \
  --include-only-statuses InProgress \
  --region us-east-1

# Stop deployment (triggers automatic rollback)
aws deploy stop-deployment \
  --deployment-id d-XXXXXXXXX \
  --auto-rollback-enabled \
  --region us-east-1
```

#### 2. Monitor Rollback

```bash
# Watch rollback progress
aws deploy get-deployment \
  --deployment-id d-XXXXXXXXX \
  --region us-east-1 \
  --query 'deploymentInfo.[status,creator,description]'
```

### Emergency Rollback (ALB Listener)

If CodeDeploy rollback fails:

```bash
# Manually switch ALB listener to blue target group
aws elbv2 modify-listener \
  --listener-arn arn:aws:elasticloadbalancing:us-east-1:123456789:listener/app/regami-alb/xxx \
  --default-actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:us-east-1:123456789:targetgroup/regami-blue-tg/xxx \
  --region us-east-1
```

### Post-Rollback

1. Identify root cause of deployment failure
2. Fix issue in code/configuration
3. Test in staging environment
4. Create incident post-mortem
5. Update deployment procedures if needed

---

## Runbook 3: Scale ECS Tasks Manually

**When to use:** Handle traffic spikes or performance issues

**Prerequisites:**
- AWS CLI configured
- Knowledge of current capacity

**Estimated Time:** 2-5 minutes

### Scale Up (Increase Capacity)

#### 1. Check Current Capacity

```bash
# Get current desired count
aws ecs describe-services \
  --cluster regami-cluster \
  --services regami-service \
  --region us-east-1 \
  --query 'services[0].[desiredCount,runningCount,pendingCount]'
```

#### 2. Scale Up

```bash
# Increase desired count
aws ecs update-service \
  --cluster regami-cluster \
  --service regami-service \
  --desired-count 4 \  # Increase from 2 to 4
  --region us-east-1

# Monitor scale-up
watch 'aws ecs describe-services \
  --cluster regami-cluster \
  --services regami-service \
  --region us-east-1 \
  --query "services[0].[desiredCount,runningCount,pendingCount]"'
```

#### 3. Verify Health

```bash
# Check all tasks are healthy
aws ecs list-tasks \
  --cluster regami-cluster \
  --service-name regami-service \
  --desired-status RUNNING \
  --region us-east-1

# Check ALB target health
aws elbv2 describe-target-health \
  --target-group-arn arn:aws:elasticloadbalancing:us-east-1:123456789:targetgroup/regami-tg/xxx \
  --region us-east-1
```

### Scale Down (Reduce Capacity)

```bash
# Decrease desired count
aws ecs update-service \
  --cluster regami-cluster \
  --service regami-service \
  --desired-count 1 \  # Decrease from 2 to 1
  --region us-east-1
```

### Auto Scaling Configuration

```hcl
# infra/aws/autoscaling.tf
resource "aws_appautoscaling_target" "ecs" {
  max_capacity       = 10
  min_capacity       = 2
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.app.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

# Scale up on high CPU
resource "aws_appautoscaling_policy" "ecs_scale_up" {
  name               = "ecs-scale-up"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ecs.resource_id
  scalable_dimension = aws_appautoscaling_target.ecs.scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value = 70.0
  }
}
```

---

## Runbook 4: Investigate High 5XX Error Rate

**When to use:** CloudWatch alarm for high 5XX errors

**Prerequisites:**
- AWS CLI configured
- Access to CloudWatch Logs
- Access to Sentry (if configured)

**Estimated Time:** 10-30 minutes

### Investigation Steps

#### 1. Check Current Error Rate

```bash
# Get 5XX count from CloudWatch
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name HTTPCode_Target_5XX_Count \
  --dimensions Name=LoadBalancer,Value=app/regami-alb/xxx \
  --start-time $(date -u -d '30 minutes ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum \
  --region us-east-1
```

#### 2. Check Application Logs

```bash
# Search for 500 errors in last hour
aws logs filter-log-events \
  --log-group-name /ecs/regami-api \
  --start-time $(date -d '1 hour ago' +%s)000 \
  --filter-pattern '"500" "POST"' \
  --region us-east-1

# Get most recent errors
aws logs tail /ecs/regami-api \
  --since 30m \
  --filter-pattern "?ERROR ?Exception" \
  --region us-east-1
```

#### 3. Check Database Connectivity

```bash
# Test database connection from task
aws ecs execute-command \
  --cluster regami-cluster \
  --task <task-id> \
  --container app \
  --interactive \
  --command "/bin/bash"

# Inside container:
python3 -c "
from sqlalchemy import create_engine
engine = create_engine('postgresql://...')
with engine.connect() as conn:
    result = conn.execute('SELECT 1')
    print('Database OK')
"
```

#### 4. Check Resource Utilization

```bash
# Check ECS task CPU/Memory
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ClusterName,Value=regami-cluster Name=ServiceName,Value=regami-service \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average,Maximum \
  --region us-east-1
```

#### 5. Check External Dependencies

```bash
# Test S3 connectivity
aws s3 ls s3://regami-uploads --region us-east-1

# Test Redis connectivity
redis-cli -h regami-redis.xxx.cache.amazonaws.com ping

# Check RDS connections
aws rds describe-db-instances \
  --db-instance-identifier regami-db-primary \
  --region us-east-1 \
  --query 'DBInstances[0].DBInstanceStatus'
```

### Common Causes and Solutions

#### Database Connection Pool Exhausted

**Symptoms:** `sqlalchemy.exc.TimeoutError`, connection timeouts

**Solution:**
```python
# Increase pool size in config.py
engine = create_engine(
    settings.database_url,
    pool_size=20,  # Increase from 10
    max_overflow=40,  # Increase from 20
    pool_pre_ping=True
)
```

#### Memory Leak

**Symptoms:** Gradually increasing memory, eventual OOM kills

**Solution:**
```bash
# Increase task memory
# Update task definition memory from 512 to 1024 MB
aws ecs register-task-definition --cli-input-json file://task-def-updated.json

# Force new deployment
aws ecs update-service \
  --cluster regami-cluster \
  --service regami-service \
  --force-new-deployment
```

#### Unhandled Exceptions

**Symptoms:** Stack traces in logs, Sentry errors

**Solution:**
1. Check Sentry for error details
2. Add try/except blocks
3. Deploy hotfix
4. Add tests to prevent regression

---

## Runbook 5: Restore from Backup

**When to use:** Data corruption, accidental deletion, ransomware

**Prerequisites:**
- AWS CLI configured
- Knowledge of backup retention
- Database admin access

**Estimated Time:** 20-60 minutes

### RDS Snapshot Restore

#### 1. List Available Snapshots

```bash
# List automated snapshots
aws rds describe-db-snapshots \
  --db-instance-identifier regami-db-primary \
  --snapshot-type automated \
  --query 'DBSnapshots[].[DBSnapshotIdentifier,SnapshotCreateTime]' \
  --output table

# List manual snapshots
aws rds describe-db-snapshots \
  --db-instance-identifier regami-db-primary \
  --snapshot-type manual \
  --query 'DBSnapshots[].[DBSnapshotIdentifier,SnapshotCreateTime]' \
  --output table
```

#### 2. Create Snapshot (Before Restore)

```bash
# Create manual snapshot of current state (for rollback)
aws rds create-db-snapshot \
  --db-instance-identifier regami-db-primary \
  --db-snapshot-identifier regami-db-before-restore-$(date +%Y%m%d-%H%M%S) \
  --region us-east-1

# Wait for snapshot to complete
aws rds wait db-snapshot-completed \
  --db-snapshot-identifier regami-db-before-restore-xxx \
  --region us-east-1
```

#### 3. Restore from Snapshot

```bash
# Restore to new instance (recommended)
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier regami-db-restored \
  --db-snapshot-identifier rds:regami-db-primary-2024-01-15-03-00 \
  --db-instance-class db.t3.medium \
  --vpc-security-group-ids sg-xxx \
  --db-subnet-group-name regami-db-subnet-group \
  --publicly-accessible false \
  --region us-east-1

# Wait for restore to complete (10-30 minutes)
aws rds wait db-instance-available \
  --db-instance-identifier regami-db-restored \
  --region us-east-1
```

#### 4. Verify Restored Data

```bash
# Connect to restored database
psql -h regami-db-restored.xxx.us-east-1.rds.amazonaws.com \
     -U regami_admin \
     -d regami

# Verify row counts
SELECT 'users' as table_name, COUNT(*) FROM users
UNION ALL
SELECT 'dogs', COUNT(*) FROM dogs
UNION ALL
SELECT 'availability', COUNT(*) FROM availability;

# Check for specific data
SELECT * FROM users WHERE email = 'affected-user@example.com';
```

#### 5. Switch Application to Restored Database

```bash
# Update ECS task definition with restored database endpoint
# OR
# Rename restored instance to replace primary (requires downtime)

# Option 1: Update task definition (no downtime)
aws ecs register-task-definition --cli-input-json file://task-def-restored.json

aws ecs update-service \
  --cluster regami-cluster \
  --service regami-service \
  --task-definition regami-api:LATEST \
  --force-new-deployment

# Option 2: Rename database (requires downtime)
# 1. Stop application
aws ecs update-service --desired-count 0 ...

# 2. Rename primary to old
aws rds modify-db-instance \
  --db-instance-identifier regami-db-primary \
  --new-db-instance-identifier regami-db-primary-old

# 3. Rename restored to primary
aws rds modify-db-instance \
  --db-instance-identifier regami-db-restored \
  --new-db-instance-identifier regami-db-primary

# 4. Restart application
aws ecs update-service --desired-count 2 ...
```

### Point-in-Time Recovery (PITR)

For more precise recovery:

```bash
# Restore to specific timestamp
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier regami-db-primary \
  --target-db-instance-identifier regami-db-pitr \
  --restore-time 2024-01-15T14:30:00Z \
  --region us-east-1
```

### S3 Backup Restore

#### 1. List Versioned Objects

```bash
# List all versions of a file
aws s3api list-object-versions \
  --bucket regami-uploads \
  --prefix dogs/photos/123.jpg
```

#### 2. Restore Previous Version

```bash
# Copy previous version
aws s3api copy-object \
  --bucket regami-uploads \
  --copy-source regami-uploads/dogs/photos/123.jpg?versionId=xxx \
  --key dogs/photos/123.jpg
```

#### 3. Bulk Restore

```bash
# Restore entire prefix to specific date
aws s3 sync s3://regami-uploads-backup s3://regami-uploads \
  --delete \
  --dryrun  # Remove --dryrun to execute
```

### Post-Restore Validation

1. **Smoke Tests**
   ```bash
   pytest tests/smoke/ --target=production
   ```

2. **User Verification**
   - Ask affected users to verify their data
   - Check recent transactions/updates

3. **Monitoring**
   - Watch error rates for 1 hour
   - Check application logs
   - Verify no data inconsistencies

4. **Documentation**
   - Document incident timeline
   - Record restore procedure
   - Update runbook with lessons learned

---

## Emergency Contacts

**On-Call Engineer:** Check PagerDuty schedule
**Database Admin:** [Name] - [Phone]
**DevOps Lead:** [Name] - [Phone]
**AWS Support:** Premium Support - Call +1-XXX-XXX-XXXX

## Escalation Matrix

| Severity | Response Time | Escalation |
|----------|--------------|------------|
| P1 (Critical Outage) | 15 minutes | Page all engineers |
| P2 (Degraded Service) | 1 hour | Notify on-call + lead |
| P3 (Minor Issue) | 4 hours | Email team |
| P4 (Maintenance) | Next business day | Slack notification |

## Post-Incident Procedures

After resolving any incident:

1. Document incident in post-mortem template
2. Schedule blameless post-mortem meeting
3. Create action items for prevention
4. Update runbooks with new learnings
5. Notify stakeholders of resolution
6. Update monitoring/alerting if needed

---

**Last Updated:** 2024-01-15
**Next Review:** 2024-04-15 (Quarterly)

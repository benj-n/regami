# Infrastructure Deployment Guide

This guide covers deploying the complete Regami infrastructure observability stack to AWS.

## Prerequisites

- AWS CLI configured with appropriate credentials
- Terraform >= 1.5.0 installed
- Docker and Docker Compose (for local Grafana)
- AWS account with permissions for: ECS, ALB, RDS, CloudWatch, S3, CloudFront, SNS

## Phase 1: CloudWatch Monitoring

### Step 1: Update Terraform Variables

Edit `infra/aws/terraform.tfvars` and add:

```hcl
# CloudWatch configuration
log_retention_days       = 30
alb_logs_retention_days = 90
alarm_email              = "oncall@regami.com"  # Your alert email
db_max_connections       = 100  # Based on your RDS instance class

# RDS backup configuration
db_backup_retention_days = 7   # Increase to 30 for production
s3_version_retention_days = 90

# CloudFront (optional, can enable later)
enable_cloudfront         = false
cloudfront_price_class    = "PriceClass_100"
cloudfront_aliases        = []  # ["app.regami.com"] if using custom domain
cloudfront_logging_enabled = false
```

### Step 2: Plan and Apply Terraform Changes

```bash
cd infra/aws

# Review changes
terraform plan -out=tfplan

# Apply changes (this will create CloudWatch resources, enable S3 versioning, etc.)
terraform apply tfplan
```

### Step 3: Confirm SNS Email Subscription

After applying, check your email for AWS SNS subscription confirmation and click the link.

### Step 4: Verify CloudWatch Dashboard

Visit the dashboard URL (output from terraform apply):
```
https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=regami-dashboard
```

## Phase 2: RDS Backups

### Verify Backup Configuration

```bash
# Check RDS backup retention
aws rds describe-db-instances \
  --db-instance-identifier regami-db \
  --query 'DBInstances[0].[BackupRetentionPeriod,PreferredBackupWindow]'

# List automated snapshots
aws rds describe-db-snapshots \
  --db-instance-identifier regami-db \
  --snapshot-type automated
```

### Test Restore Procedure (staging environment)

```bash
# Create manual snapshot before testing
aws rds create-db-snapshot \
  --db-instance-identifier regami-db \
  --db-snapshot-identifier regami-db-test-$(date +%Y%m%d)

# Restore from snapshot to new instance (test only)
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier regami-db-restored \
  --db-snapshot-identifier regami-db-test-YYYYMMDD
```

### Verify S3 Versioning

```bash
# Check versioning status
aws s3api get-bucket-versioning --bucket regami-media

# List object versions
aws s3api list-object-versions --bucket regami-media --prefix photos/ --max-items 5

# Test restore (download specific version)
aws s3api get-object \
  --bucket regami-media \
  --key photos/example.jpg \
  --version-id <version-id> \
  restored-photo.jpg
```

## Phase 3: S3 Versioning

Already configured in Phase 1 Terraform apply. Verify:

```bash
aws s3api get-bucket-versioning --bucket regami-media
```

Expected output:
```json
{
    "Status": "Enabled"
}
```

## Phase 4: ECS Autoscaling

Already configured in Phase 1 Terraform apply. Monitor:

```bash
# View autoscaling policies
aws application-autoscaling describe-scaling-policies \
  --service-namespace ecs \
  --resource-id service/regami/regami-api

# View scaling activities
aws application-autoscaling describe-scaling-activities \
  --service-namespace ecs \
  --resource-id service/regami/regami-api \
  --max-results 10
```

### Load Testing to Trigger Autoscaling

```bash
# Install hey for load testing
go install github.com/rakyll/hey@latest

# Generate load (replace with your ALB URL)
hey -z 5m -c 50 https://your-alb-url/health

# Watch ECS service scale
watch "aws ecs describe-services \
  --cluster regami \
  --services regami-api \
  --query 'services[0].[desiredCount,runningCount]'"
```

## Phase 5: CloudFront (Optional)

### Enable CloudFront

Edit `terraform.tfvars`:
```hcl
enable_cloudfront = true
cloudfront_aliases = ["app.regami.com"]  # Optional custom domain
```

Apply changes:
```bash
terraform apply
```

### Deploy Web Frontend to CloudFront

```bash
# Build web frontend
cd ../../web
npm run build

# Get S3 bucket name from Terraform output
cd ../infra/aws
WEB_BUCKET=$(terraform output -raw web_s3_bucket)

# Upload to S3
aws s3 sync ../../web/dist/ s3://$WEB_BUCKET/ --delete

# Invalidate CloudFront cache
DISTRIBUTION_ID=$(terraform output -raw cloudfront_distribution_id)
aws cloudfront create-invalidation \
  --distribution-id $DISTRIBUTION_ID \
  --paths "/*"

# Wait for invalidation to complete (2-3 minutes)
aws cloudfront wait invalidation-completed \
  --distribution-id $DISTRIBUTION_ID \
  --id <invalidation-id-from-above>
```

### Configure Custom Domain (Optional)

1. Create Route53 A record (alias):
```bash
aws route53 change-resource-record-sets \
  --hosted-zone-id <your-zone-id> \
  --change-batch file://cloudfront-alias.json
```

cloudfront-alias.json:
```json
{
  "Changes": [{
    "Action": "CREATE",
    "ResourceRecordSet": {
      "Name": "app.regami.com",
      "Type": "A",
      "AliasTarget": {
        "DNSName": "d1234567890.cloudfront.net",
        "HostedZoneId": "Z2FDTNDATAQYW2",
        "EvaluateTargetHealth": false
      }
    }
  }]
}
```

2. Wait for DNS propagation (5-60 minutes)
3. Test: `curl https://app.regami.com`

## Phase 6: Grafana Monitoring

### Start Grafana Stack Locally

```bash
cd infra

# Set environment variables (optional)
export GRAFANA_ADMIN_PASSWORD=strong-password-here
export ENVIRONMENT=production

# Start stack
docker-compose -f docker-compose-grafana.yml up -d

# Check status
docker-compose -f docker-compose-grafana.yml ps

# View logs
docker-compose -f docker-compose-grafana.yml logs -f grafana
```

### Configure Prometheus to Scrape Production API

Edit `infra/grafana/prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'regami-api'
    metrics_path: '/metrics'
    static_configs:
      - targets:
          - 'your-alb-domain.amazonaws.com'  # Replace with your ALB DNS
        labels:
          service: 'api'
          environment: 'production'
```

Restart Prometheus:
```bash
docker-compose -f docker-compose-grafana.yml restart prometheus
```

### Access Grafana

1. Open http://localhost:3000
2. Login with `admin` / `admin` (or your custom password)
3. Navigate to Dashboards → Regami folder
4. View "Regami - Overview" and "Regami - Business Metrics"

### Configure AlertManager (Optional)

Edit `infra/grafana/alertmanager.yml` and uncomment email/Slack configuration:

```yaml
global:
  smtp_from: 'alerts@regami.com'
  smtp_smarthost: 'smtp.gmail.com:587'
  smtp_auth_username: 'your-email@gmail.com'
  smtp_auth_password: 'your-app-password'

receivers:
  - name: 'critical'
    email_configs:
      - to: 'oncall@regami.com'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/YOUR/WEBHOOK'
        channel: '#alerts-critical'
```

Restart AlertManager:
```bash
docker-compose -f docker-compose-grafana.yml restart alertmanager
```

## Verification Checklist

### CloudWatch

- [ ] Log groups created for API and Web containers
- [ ] ALB access logs flowing to S3
- [ ] SNS email subscription confirmed
- [ ] CloudWatch alarms visible in console
- [ ] Dashboard showing metrics
- [ ] Test alarm: Manually trigger 5xx errors, check email alert

### RDS Backups

- [ ] Automated backups enabled (retention >= 7 days)
- [ ] Backup window configured (off-peak hours)
- [ ] CloudWatch Logs exports enabled (postgresql, upgrade)
- [ ] Manual snapshot created
- [ ] Restore procedure tested in staging

### S3 Versioning

- [ ] Versioning enabled on media bucket
- [ ] Lifecycle rules configured (90-day expiration)
- [ ] Encryption enabled (AES256)
- [ ] Public access blocked
- [ ] Test: Upload file, delete, restore from version

### ECS Autoscaling

- [ ] Autoscaling targets configured for API and Web
- [ ] CPU, memory, and request-based policies created
- [ ] Min/max capacity set appropriately
- [ ] Load test triggers scale-out
- [ ] Tasks scale back down after cooldown

### CloudFront (if enabled)

- [ ] Distribution created and deployed
- [ ] S3 bucket policy allows CloudFront
- [ ] Web frontend deployed to S3
- [ ] Cache behaviors configured correctly
- [ ] Custom domain configured (if applicable)
- [ ] Test: Access via CloudFront URL, verify caching

### Grafana

- [ ] Grafana accessible at http://localhost:3000
- [ ] Prometheus scraping API /metrics endpoint
- [ ] "Regami - Overview" dashboard showing data
- [ ] "Regami - Business Metrics" dashboard showing data
- [ ] AlertManager configured for notifications
- [ ] Test: Trigger alert, verify notification

## Monitoring in Production

### Daily Checks

- Check CloudWatch alarms for any active alerts
- Review Grafana dashboards for anomalies
- Check ECS task health and autoscaling activity

### Weekly Reviews

- Review CloudWatch Dashboard for trends
- Check RDS backup completion
- Review autoscaling events and tune thresholds
- Check S3 storage costs and lifecycle effectiveness

### Monthly Tasks

- Test RDS restore procedure
- Review and update alarm thresholds
- Check CloudWatch and S3 costs
- Update Grafana dashboards based on team feedback
- Review AlertManager notification effectiveness

## Troubleshooting

### CloudWatch Alarms Not Triggering

```bash
# Check alarm state
aws cloudwatch describe-alarms --alarm-names regami-api-5xx-rate-high

# Check if metrics are being published
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name HTTPCode_Target_5XX_Count \
  --dimensions Name=LoadBalancer,Value=<alb-arn-suffix> \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-01T23:59:59Z \
  --period 300 \
  --statistics Sum
```

### Grafana Not Showing Metrics

1. Check Prometheus is scraping:
   - Visit http://localhost:9090/targets
   - Ensure `regami-api` target is UP

2. Check API metrics endpoint:
   ```bash
   curl https://your-api-url/metrics
   ```

3. Check Prometheus logs:
   ```bash
   docker-compose -f docker-compose-grafana.yml logs prometheus
   ```

### ECS Not Autoscaling

```bash
# Check if policies are active
aws application-autoscaling describe-scaling-policies \
  --service-namespace ecs \
  --resource-id service/regami/regami-api

# Check CloudWatch metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ServiceName,Value=regami-api Name=ClusterName,Value=regami \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average
```

### CloudFront Cache Not Working

```bash
# Check cache hit rate
aws cloudwatch get-metric-statistics \
  --namespace AWS/CloudFront \
  --metric-name CacheHitRate \
  --dimensions Name=DistributionId,Value=<distribution-id> \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average

# View cache behavior
curl -I https://your-cloudfront-url/assets/main.js
# Look for: X-Cache: Hit from cloudfront
```

## Cost Estimates

### CloudWatch
- Logs ingestion: $0.50/GB
- Alarms: $0.10/alarm/month
- Dashboard: Free (first 3 dashboards)
- **Estimated**: $20-50/month

### S3
- Storage: $0.023/GB/month (Standard)
- Versioning: ~2x storage cost
- Lifecycle transitions: $0.01/1000 requests
- **Estimated**: $10-30/month

### RDS Backups
- Automated backups: Free up to 100% of DB storage
- Manual snapshots: $0.095/GB/month
- **Estimated**: Free - $10/month

### CloudFront
- Data transfer: $0.085/GB (first 10TB, varies by region)
- HTTPS requests: $0.010/10,000 requests
- Invalidations: $0.005/path (first 1000 free)
- **Estimated**: $20-100/month (depends on traffic)

### Grafana Stack (self-hosted)
- EC2 t3.small (if deployed): $15/month
- Local Docker: Free (uses existing compute)
- **Estimated**: Free - $15/month

**Total Infrastructure Observability Cost: $50-200/month**

## Next Steps

1. **Deploy to staging first**: Test all changes in staging environment
2. **Monitor costs**: Set up AWS Budget alerts
3. **Tune thresholds**: Adjust alarm thresholds based on actual traffic patterns
4. **Document runbooks**: Create incident response procedures
5. **Train team**: Ensure team knows how to use dashboards and respond to alerts
6. **Automate deployments**: Integrate Terraform into CI/CD pipeline
7. **Regular testing**: Schedule quarterly disaster recovery drills

## References

- [AWS CloudWatch Documentation](https://docs.aws.amazon.com/cloudwatch/)
- [AWS RDS Backup Documentation](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_WorkingWithAutomatedBackups.html)
- [AWS CloudFront Documentation](https://docs.aws.amazon.com/cloudfront/)
- [ECS Autoscaling Documentation](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/service-autoscaling.html)
- [Grafana Documentation](https://grafana.com/docs/)
- [Prometheus Documentation](https://prometheus.io/docs/)

# Grafana Monitoring Stack

This directory contains the Grafana monitoring stack configuration for Regami, including Prometheus for metrics collection, Grafana for visualization, and AlertManager for alerting.

## Quick Start

### 1. Start the Monitoring Stack

```bash
# From the repository root
cd infra
docker-compose -f docker-compose-grafana.yml up -d
```

### 2. Access the Services

- **Grafana**: http://localhost:3000
  - Default credentials: `admin` / `admin` (change on first login)

- **Prometheus**: http://localhost:9090
  - No authentication required (use in trusted environment only)

- **AlertManager**: http://localhost:9093
  - No authentication required (use in trusted environment only)

### 3. Configure Your API Endpoint

Edit `grafana/prometheus.yml` and update the `regami-api` scrape target:

```yaml
- job_name: 'regami-api'
  static_configs:
    - targets:
        - 'your-api-host:8000'  # Update this
```

Then restart Prometheus:

```bash
docker-compose -f docker-compose-grafana.yml restart prometheus
```

## Architecture

```
┌─────────────┐     scrapes     ┌─────────────┐
│   FastAPI   │ ───────────────> │ Prometheus  │
│   /metrics  │                  │             │
└─────────────┘                  └──────┬──────┘
                                        │
                                        │ queries
                                        │
┌─────────────┐     alerts      ┌──────▼──────┐
│AlertManager │ <─────────────── │   Grafana   │
│             │                  │ Dashboards  │
└──────┬──────┘                  └─────────────┘
       │
       │ notifications
       ▼
  Email/Slack/Webhook
```

## Dashboards

### 1. Regami Overview Dashboard

Location: `dashboards/regami-overview.json`

Displays:
- API request rate and response times
- HTTP status code distribution
- Error rates and active users
- Database connection pool status
- Database query performance

### 2. Business Metrics Dashboard

Location: `dashboards/regami-business.json`

Displays:
- User registrations and match creation
- Message activity and notifications
- Photo upload statistics
- Match status distribution
- Time-series trends for business KPIs

## Prometheus Configuration

### Scrape Targets

Edit `grafana/prometheus.yml` to add or modify scrape targets:

```yaml
scrape_configs:
  - job_name: 'regami-api'
    metrics_path: '/metrics'
    static_configs:
      - targets: ['your-host:8000']
        labels:
          environment: 'prod'
```

### Adding Exporters

To monitor additional services, add exporters:

#### PostgreSQL Exporter

```yaml
# In docker-compose-grafana.yml
postgres-exporter:
  image: prometheuscommunity/postgres-exporter
  environment:
    - DATA_SOURCE_NAME=postgresql://user:password@host:5432/dbname?sslmode=disable
  ports:
    - "9187:9187"

# In prometheus.yml
- job_name: 'postgres'
  static_configs:
    - targets: ['postgres-exporter:9187']
```

#### Redis Exporter

```yaml
# In docker-compose-grafana.yml
redis-exporter:
  image: oliver006/redis_exporter
  environment:
    - REDIS_ADDR=redis:6379
  ports:
    - "9121:9121"

# In prometheus.yml
- job_name: 'redis'
  static_configs:
    - targets: ['redis-exporter:9121']
```

## AlertManager Configuration

### Email Alerts

Edit `grafana/alertmanager.yml`:

```yaml
global:
  smtp_from: 'alerts@regami.com'
  smtp_smarthost: 'smtp.gmail.com:587'
  smtp_auth_username: 'your-email@gmail.com'
  smtp_auth_password: 'your-app-password'
  smtp_require_tls: true

receivers:
  - name: 'critical'
    email_configs:
      - to: 'oncall@regami.com'
        headers:
          Subject: '[CRITICAL] {{ .GroupLabels.alertname }}'
```

### Slack Alerts

```yaml
receivers:
  - name: 'critical'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'
        channel: '#alerts-critical'
        title: '[CRITICAL] {{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
```

## Custom Metrics

### Adding Metrics to Dashboards

1. Create a new panel in Grafana UI
2. Write a PromQL query, e.g.:
   ```promql
   rate(regami_user_registrations_total[1h])
   ```
3. Export the dashboard as JSON
4. Save to `dashboards/` directory

### Available Regami Metrics

See `backend/app/metrics.py` for all available metrics:

- `regami_user_registrations_total` - User registrations by role
- `regami_matches_created_total` - Matches created by type
- `regami_messages_sent_total` - Messages sent
- `regami_fcm_notifications_sent_total` - FCM notifications by type
- `regami_db_query_duration_seconds` - Database query duration
- `regami_photo_uploads_total` - Photo uploads
- And many more...

## Production Deployment

### Security Considerations

1. **Enable Authentication**: Set strong credentials in environment variables
   ```bash
   export GRAFANA_ADMIN_USER=admin
   export GRAFANA_ADMIN_PASSWORD=strong-password-here
   ```

2. **Use HTTPS**: Configure reverse proxy (nginx, Traefik) with SSL
   ```nginx
   server {
       listen 443 ssl;
       server_name grafana.regami.com;

       location / {
           proxy_pass http://localhost:3000;
       }
   }
   ```

3. **Network Isolation**: Use Docker networks to isolate monitoring stack
   ```yaml
   networks:
     monitoring:
       internal: true  # No external access
   ```

4. **Restrict Access**: Use firewall rules to limit access to monitoring ports

### Data Retention

Prometheus retains metrics for 30 days by default. To change:

```yaml
# In docker-compose-grafana.yml
command:
  - '--storage.tsdb.retention.time=90d'  # 90 days
```

### Backup

Backup these directories regularly:
- `grafana-data` - Grafana configuration and dashboards
- `prometheus-data` - Time-series metrics data
- `alertmanager-data` - Alert state

```bash
# Backup script example
docker-compose -f docker-compose-grafana.yml stop
tar -czf monitoring-backup-$(date +%Y%m%d).tar.gz \
    /var/lib/docker/volumes/regami-grafana-data \
    /var/lib/docker/volumes/regami-prometheus-data
docker-compose -f docker-compose-grafana.yml start
```

## Troubleshooting

### Grafana Can't Connect to Prometheus

Check Prometheus is running:
```bash
docker ps | grep prometheus
curl http://localhost:9090/-/healthy
```

### No Metrics from API

Verify the API metrics endpoint:
```bash
curl http://your-api:8000/metrics
```

Check Prometheus targets:
```bash
# Visit http://localhost:9090/targets
# Ensure regami-api target is UP
```

### Dashboard Shows "No Data"

1. Check time range (top right in Grafana)
2. Verify metrics exist in Prometheus:
   ```
   # Visit http://localhost:9090/graph
   # Run query: regami_user_registrations_total
   ```
3. Check Prometheus scrape interval hasn't changed

## References

- [Grafana Documentation](https://grafana.com/docs/)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [PromQL Query Language](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [AlertManager Documentation](https://prometheus.io/docs/alerting/latest/alertmanager/)

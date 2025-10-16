# Regami Grafana Dashboards

Pre-built Grafana dashboards for monitoring the Regami platform.

## Available Dashboards

### 1. API Metrics (`api-metrics.json`)
Monitors backend API performance and health.

**Panels:**
- Request Rate (requests/sec by endpoint and method)
- Response Time (p95 latency)
- Error Rate (4xx and 5xx errors)
- Active WebSocket Connections
- Database Connection Pool Status
- Cache Hit Rate
- Top Endpoints by Request Count

**Refresh Rate:** 30 seconds

### 2. Infrastructure (`infrastructure.json`)
Monitors system resources and infrastructure health.

**Panels:**
- CPU Usage (per container)
- Memory Usage (per container)
- Disk Usage
- Network I/O (RX/TX)
- Database Connections
- Redis Memory Usage
- S3 Storage Used
- Container Restarts (24h)

**Refresh Rate:** 1 minute

### 3. Business Metrics (`business-metrics.json`)
Tracks key business KPIs and user engagement.

**Panels:**
- Total Users
- Active Users (7 days)
- Total Dogs
- Active Matches
- User Registrations (daily trend)
- Matches Created (daily trend)
- Messages Sent (rate)
- Match Status Distribution
- User Engagement Rate
- Average Matches per User
- Match Success Rate

**Refresh Rate:** 5 minutes

## Installation

### Option 1: Grafana UI Import

1. Open Grafana at http://localhost:3000 (or your Grafana URL)
2. Navigate to **Dashboards** → **Import**
3. Upload JSON file or paste JSON content
4. Select Prometheus data source
5. Click **Import**

### Option 2: Provisioning (Recommended for Production)

1. Copy dashboard files to Grafana provisioning directory:
```bash
cp infra/grafana/dashboards/*.json /etc/grafana/provisioning/dashboards/
```

2. Create provisioning config in `/etc/grafana/provisioning/dashboards/regami.yml`:
```yaml
apiVersion: 1

providers:
  - name: 'Regami'
    orgId: 1
    folder: 'Regami'
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /etc/grafana/provisioning/dashboards
      foldersFromFilesStructure: true
```

3. Restart Grafana:
```bash
systemctl restart grafana-server
```

### Option 3: Docker Compose

Add to your `docker-compose-grafana.yml`:

```yaml
services:
  grafana:
    image: grafana/grafana:latest
    volumes:
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./grafana/provisioning:/etc/grafana/provisioning
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
```

## Data Sources Required

Dashboards expect the following Prometheus metrics:

### API Metrics
- `http_requests_total` - HTTP request counter with labels: method, endpoint, status
- `http_request_duration_seconds` - Request duration histogram
- `websocket_connections_active` - Active WebSocket gauge
- `db_pool_connections_active` - Database pool gauge
- `redis_cache_hits` - Cache hit counter
- `redis_cache_requests` - Cache request counter

### Infrastructure Metrics
- `container_cpu_usage_seconds_total` - Container CPU (from cAdvisor)
- `container_memory_usage_bytes` - Container memory
- `node_filesystem_*` - Filesystem metrics (from Node Exporter)
- `container_network_*_bytes_total` - Network metrics
- `pg_stat_database_numbackends` - PostgreSQL connections (from postgres_exporter)
- `redis_memory_*_bytes` - Redis memory (from redis_exporter)

### Business Metrics
- `regami_users_total` - Total users gauge
- `regami_users_active_7d` - Active users gauge
- `regami_dogs_total` - Total dogs gauge
- `regami_matches_*` - Match counters and gauges
- `regami_messages_sent_total` - Message counter

## Implementing Custom Metrics

Add Prometheus instrumentation to your FastAPI app:

```python
from prometheus_client import Counter, Gauge, Histogram

# Business metrics
users_total = Gauge('regami_users_total', 'Total number of users')
users_active_7d = Gauge('regami_users_active_7d', 'Active users in last 7 days')
dogs_total = Gauge('regami_dogs_total', 'Total number of dogs')
matches_created = Counter('regami_matches_created_total', 'Total matches created')
messages_sent = Counter('regami_messages_sent_total', 'Total messages sent')

# Update metrics periodically
@app.on_event("startup")
async def update_business_metrics():
    while True:
        users_total.set(await db.count_users())
        users_active_7d.set(await db.count_active_users(days=7))
        dogs_total.set(await db.count_dogs())
        await asyncio.sleep(300)  # Update every 5 minutes
```

## Customization

All dashboards are in JSON format and can be customized:

1. Edit panel queries to match your metrics
2. Adjust thresholds and alert rules
3. Add/remove panels as needed
4. Change colors and visualizations
5. Modify refresh rates

## Alerting

Configure alerts in Grafana for critical metrics:

- **High Error Rate:** > 1% 5xx errors for 5 minutes
- **Slow Response Time:** p95 > 1000ms for 10 minutes
- **Low Cache Hit Rate:** < 80% for 15 minutes
- **High CPU Usage:** > 80% for 5 minutes
- **Low Disk Space:** < 10% available
- **Container Restarts:** > 5 in 1 hour

## Support

For issues or questions about dashboards:
- Check Grafana logs: `journalctl -u grafana-server`
- Verify Prometheus data source connectivity
- Ensure metrics are being collected
- See [Grafana Documentation](https://grafana.com/docs/)

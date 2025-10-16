# Load Testing

Load tests for the Regami API using [k6](https://k6.io/).

## Prerequisites

Install k6:

**macOS:**
```bash
brew install k6
```

**Linux:**
```bash
sudo gpg -k
sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
sudo apt-get update
sudo apt-get install k6
```

**Docker:**
```bash
docker pull grafana/k6:latest
```

## Available Tests

### 1. Basic Load Test (`basic-load-test.js`)

Simulates realistic user behavior with gradual load increase.

**Stages:**
- Ramp up to 10 users over 2 minutes
- Maintain 10 users for 5 minutes
- Ramp up to 50 users over 2 minutes
- Maintain 50 users for 5 minutes
- Ramp up to 100 users over 2 minutes
- Maintain 100 users for 5 minutes
- Ramp down to 0 users over 5 minutes

**Tested Endpoints:**
- `POST /auth/login`
- `GET /users/me`
- `GET /dogs/`
- `GET /availability/offers`
- `GET /matches/`
- `GET /messages/`
- `GET /notifications/`

**Thresholds:**
- 95th percentile response time < 500ms
- 99th percentile response time < 1000ms
- Error rate < 1%

**Run:**
```bash
k6 run tests/load/basic-load-test.js
```

### 2. Spike Test (`spike-test.js`)

Tests system behavior under sudden traffic spikes.

**Configuration:**
- 100 virtual users
- 30 seconds duration
- High request rate
- Very low tolerance for errors

**Thresholds:**
- 95th percentile response time < 200ms
- Error rate < 1%

**Run:**
```bash
k6 run tests/load/spike-test.js
```

### 3. Stress Test (`stress-test.js`)

Long-running test to identify memory leaks and performance degradation.

**Stages:**
- Ramp up to 200 users over 10 minutes
- Maintain 200 users for 1 hour
- Ramp down to 0 users over 10 minutes

**User Behavior:**
- 70% browse dogs
- 50% check messages
- 40% search availability
- Random 5-15 second delays between actions

**Thresholds:**
- 95th percentile response time < 1000ms
- Error rate < 5%

**Run:**
```bash
k6 run tests/load/stress-test.js
```

## Usage

### Basic Usage

Run against local development server:
```bash
k6 run tests/load/basic-load-test.js
```

Run against custom URL:
```bash
k6 run -e BASE_URL=https://api.regami.com tests/load/basic-load-test.js
```

### Output Options

**JSON output for analysis:**
```bash
k6 run --out json=results.json tests/load/basic-load-test.js
```

**InfluxDB for real-time monitoring:**
```bash
k6 run --out influxdb=http://localhost:8086/k6 tests/load/basic-load-test.js
```

**Cloud output (requires k6 Cloud account):**
```bash
k6 cloud tests/load/basic-load-test.js
```

### Custom Options

Override VUs and duration:
```bash
k6 run --vus 50 --duration 5m tests/load/basic-load-test.js
```

### CI/CD Integration

Run in GitHub Actions:
```yaml
- name: Run Load Tests
  run: |
    k6 run --quiet --out json=load-test-results.json tests/load/basic-load-test.js
```

## Interpreting Results

### Key Metrics

**http_req_duration**: Time from request start to response end
- `p(90)`: 90th percentile (90% of requests faster than this)
- `p(95)`: 95th percentile
- `p(99)`: 99th percentile

**http_req_failed**: Percentage of failed requests (non-2xx/3xx responses)

**http_reqs**: Total number of requests per second

**vus**: Number of active virtual users

**iterations**: Number of complete test iterations

### Example Output

```
     ✓ login successful
     ✓ get user profile successful
     ✓ list dogs successful

     checks.........................: 100.00% ✓ 15000 ✗ 0
     data_received..................: 45 MB   1.5 MB/s
     data_sent......................: 15 MB   500 kB/s
     http_req_blocked...............: avg=1.2ms    min=0s     med=0s     max=50ms
     http_req_connecting............: avg=800µs    min=0s     med=0s     max=30ms
   ✓ http_req_duration..............: avg=120ms    min=50ms   med=100ms  max=800ms
       { expected_response:true }...: avg=120ms    min=50ms   med=100ms  max=800ms
   ✓ http_req_failed................: 0.00%   ✓ 0     ✗ 5000
     http_req_receiving.............: avg=2ms      min=0s     med=1ms    max=50ms
     http_req_sending...............: avg=500µs    min=0s     med=0s     max=10ms
     http_req_tls_handshaking.......: avg=0s       min=0s     med=0s     max=0s
     http_req_waiting...............: avg=117.5ms  min=48ms   med=98ms   max=795ms
     http_reqs......................: 5000    166.666667/s
     iteration_duration.............: avg=10s      min=8s     med=9.5s   max=15s
     iterations.....................: 500     16.666667/s
     vus............................: 100     min=10  max=100
     vus_max........................: 100     min=100 max=100
```

### Performance Targets

**Excellent:**
- p95 < 200ms
- p99 < 500ms
- Error rate < 0.1%

**Good:**
- p95 < 500ms
- p99 < 1000ms
- Error rate < 1%

**Acceptable:**
- p95 < 1000ms
- p99 < 2000ms
- Error rate < 5%

**Needs Optimization:**
- p95 > 1000ms
- p99 > 2000ms
- Error rate > 5%

## Troubleshooting

### High Error Rates

**Cause:** Database connection pool exhausted, rate limiting triggered, or server overload.

**Solutions:**
- Increase database connection pool size
- Adjust rate limits
- Scale horizontally (add more API instances)
- Optimize slow queries

### High Response Times

**Cause:** Slow database queries, missing indexes, or inefficient code.

**Solutions:**
- Add database indexes
- Enable query caching (if needed)
- Optimize N+1 queries
- Profile slow endpoints with APM tools

### Connection Errors

**Cause:** Too many concurrent connections, firewall limits, or network issues.

**Solutions:**
- Adjust ulimit on server
- Increase max connections in nginx/load balancer
- Use connection pooling

## Best Practices

1. **Always run tests on staging environment first**
2. **Start with low load and gradually increase**
3. **Monitor server resources (CPU, memory, disk) during tests**
4. **Run tests from geographically distributed locations**
5. **Seed database with realistic data volume**
6. **Test one change at a time for accurate comparison**
7. **Establish baseline metrics before optimization**
8. **Schedule regular load tests in CI/CD pipeline**

## Further Reading

- [k6 Documentation](https://k6.io/docs/)
- [k6 Best Practices](https://k6.io/docs/testing-guides/automated-performance-testing/)
- [Load Testing Best Practices](https://k6.io/docs/testing-guides/test-types/)

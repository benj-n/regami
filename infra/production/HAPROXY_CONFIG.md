# HAProxy Configuration for Regami Production

This document provides the HAProxy configuration for the external load balancer
that sits in front of the Regami production VMs.

> **Note**: The HAProxy is managed externally (not by the application team).
> This document is provided for the infrastructure team to configure the load balancer.

## Architecture

```
Internet
    │
    ▼
┌─────────────┐
│  HAProxy    │  (External - your infrastructure)
│  (TCP/HTTPS)│
└──────┬──────┘
       │
       ├────────────────────────┐
       │                        │
       ▼                        ▼
┌─────────────┐          ┌─────────────┐
│  VM1-PROD   │          │  VM2-PROD   │
│  (Active)   │          │  (Standby)  │
│  10.x.x.1   │          │  10.x.x.2   │
└─────────────┘          └─────────────┘
```

## Configuration

### Frontend Configuration

```haproxy
frontend regami_https
    bind *:443 ssl crt /etc/haproxy/certs/regami.com.pem
    bind *:80

    # Redirect HTTP to HTTPS
    http-request redirect scheme https unless { ssl_fc }

    # Route to backend based on hostname
    acl is_api hdr(host) -i api.regami.com
    acl is_web hdr(host) -i regami.com www.regami.com

    use_backend regami_api if is_api
    use_backend regami_web if is_web
    default_backend regami_web
```

### Backend Configuration (Active-Passive)

```haproxy
backend regami_web
    balance roundrobin
    option httpchk GET /health
    http-check expect status 200

    # Active-passive: VM2 is backup
    server vm1-prod 10.x.x.1:443 ssl verify none check inter 5s fall 3 rise 2
    server vm2-prod 10.x.x.2:443 ssl verify none check inter 5s fall 3 rise 2 backup

backend regami_api
    balance roundrobin
    option httpchk GET /health
    http-check expect status 200

    # Active-passive: VM2 is backup
    server vm1-prod 10.x.x.1:443 ssl verify none check inter 5s fall 3 rise 2
    server vm2-prod 10.x.x.2:443 ssl verify none check inter 5s fall 3 rise 2 backup
```

### WebSocket Support

For WebSocket connections, ensure proper upgrade handling:

```haproxy
frontend regami_https
    # ... existing config ...

    # WebSocket detection
    acl is_websocket hdr(Upgrade) -i websocket
    acl is_ws_path path_beg /ws

    use_backend regami_websocket if is_websocket is_ws_path

backend regami_websocket
    balance source  # Sticky sessions for WebSocket
    option httpchk GET /health
    timeout server 3600s  # 1 hour for WebSocket connections
    timeout tunnel 3600s

    server vm1-prod 10.x.x.1:443 ssl verify none check inter 5s fall 3 rise 2
    server vm2-prod 10.x.x.2:443 ssl verify none check inter 5s fall 3 rise 2 backup
```

## Health Check Endpoints

Each VM exposes health check endpoints:

| Endpoint | Port | Description |
|----------|------|-------------|
| `/health` | 443 | Application health |
| `/health?check=db` | 443 | Database connectivity |

## Monitoring

### HAProxy Stats

Enable the stats page for monitoring:

```haproxy
listen stats
    bind *:8404
    stats enable
    stats uri /haproxy-stats
    stats auth admin:your-secure-password
    stats refresh 10s
```

### Recommended Alerts

- Backend server down (fall count exceeded)
- High response time (> 500ms p95)
- High 5xx error rate (> 1%)
- SSL certificate expiry (< 30 days)

## Failover Behavior

1. **Normal operation**: All traffic goes to VM1 (active)
2. **VM1 fails health check**: HAProxy automatically routes to VM2 (backup)
3. **VM1 recovers**: Traffic returns to VM1

The `inter 5s fall 3 rise 2` settings mean:
- Health check every 5 seconds
- Mark down after 3 consecutive failures (15 seconds)
- Mark up after 2 consecutive successes (10 seconds)

## SSL Certificate

The HAProxy SSL certificate should be a PEM file containing:
1. The certificate for regami.com
2. Any intermediate certificates
3. The private key

```bash
cat regami.com.crt intermediate.crt regami.com.key > regami.com.pem
```

Place at: `/etc/haproxy/certs/regami.com.pem`

## DNS Configuration

Configure DNS records:

| Record | Type | Value |
|--------|------|-------|
| regami.com | A | [HAProxy IP] |
| www.regami.com | CNAME | regami.com |
| api.regami.com | CNAME | regami.com |
| storage.regami.com | CNAME | regami.com |

## Contacts

For application-level issues: support@regami.com

---
name: Performance Issue
about: Report performance problems or optimization opportunities
title: '[PERF] '
labels: performance
assignees: ''
---

## Description
A clear and concise description of the performance issue.

## Affected Area
- [ ] API Response Time
- [ ] Database Query
- [ ] Frontend Rendering
- [ ] Build Time
- [ ] Memory Usage
- [ ] Network/WebSocket
- [ ] Other: _______

## Current Behavior
**Metric:** (e.g., p95 response time, load time, memory footprint)
- Current: _______
- Expected: _______

**Steps to Reproduce:**
1.
2.
3.

## Performance Data
<!-- Include metrics, profiling data, or screenshots -->

**Backend:**
```
# Example: API timing logs, database slow query logs
```

**Frontend:**
```
# Example: Chrome DevTools Performance profile, Lighthouse scores
```

**Load Testing:**
```
# Example: k6/Locust results showing requests/sec, error rate
```

## Environment
- Deployment: [dev/staging/production]
- Load: [concurrent users, requests/sec]
- Database size: [row counts, table sizes]
- Infrastructure: [instance types, resources]

## Proposed Solution
<!-- Optional: Describe optimization approach -->

## Acceptance Criteria
- [ ] Metric improves to acceptable level
- [ ] No regression in functionality
- [ ] Changes validated with load testing

## Additional Context
<!-- Links to profiling data, related issues, etc. -->

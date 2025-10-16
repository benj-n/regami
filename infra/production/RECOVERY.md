# Regami Production Recovery Runbook

This document covers recovery procedures for the Regami production environment,
including the 2-node etcd/Patroni cluster split-brain recovery.

## Architecture Overview

```
External HAProxy
      │
      ├── VM1-PROD (active)
      │   ├── Caddy
      │   ├── regami-api
      │   ├── regami-web
      │   ├── Patroni (PostgreSQL leader)
      │   ├── etcd (node 1)
      │   └── MinIO
      │
      └── VM2-PROD (standby)
          ├── Caddy
          ├── regami-api
          ├── regami-web
          ├── Patroni (PostgreSQL replica)
          ├── etcd (node 2)
          └── MinIO
```

## 2-Node etcd Split-Brain Recovery

With only 2 etcd nodes, quorum cannot be achieved if one node fails.
This is a known limitation we accept in exchange for simplicity.

### Symptoms of Split-Brain

- Both VMs think they are the leader
- Patroni shows "no quorum" errors
- API returns database connection errors
- etcd logs show: `raft: stopped leader election`

### Recovery Procedure

**Step 1: Identify the healthy node**

```bash
# Check on VM1
ssh regami-prod-1 "docker exec regami-etcd etcdctl endpoint health"
ssh regami-prod-1 "docker exec regami-patroni patronictl list"

# Check on VM2
ssh regami-prod-2 "docker exec regami-etcd etcdctl endpoint health"
ssh regami-prod-2 "docker exec regami-patroni patronictl list"
```

Choose the node with the most recent data (check PostgreSQL WAL position).

**Step 2: Stop services on the unhealthy node**

```bash
# On the unhealthy node (e.g., VM2)
ssh regami-prod-2 "cd /opt/regami && docker compose down"
```

**Step 3: Reset etcd on the unhealthy node**

```bash
# Remove etcd data
ssh regami-prod-2 "docker volume rm regami_etcd_data"
```

**Step 4: Update etcd cluster configuration**

On VM1 (healthy node), add VM2 back to the cluster:

```bash
ssh regami-prod-1 "docker exec regami-etcd etcdctl member add vm2-prod --peer-urls=http://10.0.0.2:2380"
```

**Step 5: Restart the recovered node**

On VM2, update `.env` to join existing cluster:

```bash
# Edit /opt/regami/.env
ETCD_CLUSTER_STATE=existing
```

Then start services:

```bash
ssh regami-prod-2 "cd /opt/regami && docker compose up -d"
```

**Step 6: Verify recovery**

```bash
# Check etcd cluster health
ssh regami-prod-1 "docker exec regami-etcd etcdctl member list"
ssh regami-prod-1 "docker exec regami-etcd etcdctl endpoint health --cluster"

# Check Patroni cluster
ssh regami-prod-1 "docker exec regami-patroni patronictl list"
```

### PostgreSQL Failover

If the PostgreSQL leader fails, Patroni will automatically promote the replica.

**Manual failover (if needed):**

```bash
# Force failover to specific node
ssh regami-prod-1 "docker exec regami-patroni patronictl switchover --master vm1-prod --candidate vm2-prod"
```

## Single Node Failure Recovery

### VM1 (Active) Fails

1. HAProxy automatically routes traffic to VM2
2. VM2 becomes the new leader (if Patroni has quorum)
3. Restore VM1 when ready:
   ```bash
   ssh regami-prod-1 "cd /opt/regami && docker compose up -d"
   ```

### VM2 (Standby) Fails

1. Traffic continues on VM1
2. Fix VM2 and rejoin:
   ```bash
   ssh regami-prod-2 "cd /opt/regami && docker compose up -d"
   ```

## Database Recovery from Backup

If both nodes have corrupted data:

**Step 1: Stop all services**

```bash
ssh regami-prod-1 "cd /opt/regami && docker compose down"
ssh regami-prod-2 "cd /opt/regami && docker compose down"
```

**Step 2: Remove corrupted data**

```bash
ssh regami-prod-1 "docker volume rm regami_postgres_data regami_etcd_data"
ssh regami-prod-2 "docker volume rm regami_postgres_data regami_etcd_data"
```

**Step 3: Restore from backup**

```bash
# Start only PostgreSQL on VM1
ssh regami-prod-1 "cd /opt/regami && docker compose up -d postgres"

# Wait for PostgreSQL to start
sleep 10

# Restore backup
ssh regami-prod-1 "gunzip -c /opt/regami/backups/regami-postgres-YYYYMMDD.sql.gz | docker exec -i regami-postgres psql -U regami regami"
```

**Step 4: Restart full stack**

```bash
ssh regami-prod-1 "cd /opt/regami && docker compose up -d"
ssh regami-prod-2 "cd /opt/regami && docker compose up -d"
```

## Contact

For critical issues, contact the on-call engineer via:
- Email: support@regami.com
- PagerDuty: [link]

## Appendix: Useful Commands

```bash
# Check Patroni cluster status
docker exec regami-patroni patronictl list

# Check etcd cluster status
docker exec regami-etcd etcdctl member list
docker exec regami-etcd etcdctl endpoint status --cluster -w table

# Check PostgreSQL replication lag
docker exec regami-patroni psql -U regami -c "SELECT pg_last_wal_receive_lsn(), pg_last_wal_replay_lsn(), pg_last_xact_replay_timestamp();"

# Force Patroni reinit (last resort)
docker exec regami-patroni patronictl reinit regami-cluster vm2-prod
```

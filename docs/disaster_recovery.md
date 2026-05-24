## ፋይል #302: `docs/disaster_recovery.md`

```markdown
# Wolloyewa Store Bot - Disaster Recovery Plan

## 📋 Plan Overview

| Attribute | Value |
|-----------|-------|
| Plan Version | 1.0 |
| Last Updated | 2024-01-15 |
| Owner | DevOps Team |
| RTO | 4 hours |
| RPO | 15 minutes |
| Classification | Critical |

---

## 🎯 Recovery Objectives

### Recovery Time Objectives (RTO)

| Service | RTO | Priority |
|---------|-----|----------|
| Telegram Bot | 1 hour | Critical |
| API Gateway | 2 hours | High |
| Payment Processing | 2 hours | High |
| Database | 4 hours | Medium |
| Analytics | 8 hours | Low |

### Recovery Point Objectives (RPO)

| Data Type | RPO | Backup Frequency |
|-----------|-----|------------------|
| User Data | 15 min | Continuous |
| Orders | 15 min | Continuous |
| Payments | 1 hour | Hourly |
| Products | 1 day | Daily |
| Logs | 1 day | Daily |

---

## 🚨 Disaster Scenarios

### Scenario 1: Database Failure

#### Detection
```bash
# Monitoring alert triggers when:
- PostgreSQL service down
- Connection pool exhausted
- Replication lag > 60 seconds
```

#### Response Procedure

**Step 1: Assess (0-5 min)**
```bash
# Check database status
sudo systemctl status postgresql

# Check replication
psql -c "SELECT * FROM pg_stat_replication;"

# Check disk space
df -h /var/lib/postgresql/
```

**Step 2: Attempt Recovery (5-15 min)**
```bash
# Try to restart
sudo systemctl restart postgresql

# Check logs
sudo tail -100 /var/log/postgresql/postgresql.log

# If failed, check for corruption
sudo -u postgres pg_check -d welloyewadb
```

**Step 3: Failover (15-30 min)**
```bash
# Promote replica to primary
sudo -u postgres pg_ctl promote -D /var/lib/postgresql/15/main

# Update application configuration
aws rds modify-db-instance --db-instance-identifier wolloyewa --apply-immediately

# Verify connectivity
psql -h new-primary-host -U wolloyewa_user -d welloyewadb -c "SELECT 1"
```

**Step 4: Restore (30-60 min)**
```bash
# If no replica available
./scripts/restore.sh --latest

# Verify data integrity
./scripts/verify_backup.sh
```

### Scenario 2: Redis Failure

#### Detection
```bash
# Check Redis status
redis-cli ping

# Monitor memory
redis-cli INFO memory
```

#### Response Procedure

**Step 1: Restart (0-5 min)**
```bash
sudo systemctl restart redis-server
```

**Step 2: Rebuild Cache (5-15 min)**
```bash
# Clear corrupted cache
redis-cli FLUSHALL

# Rebuild from database
python scripts/rebuild_cache.py
```

**Step 3: Failover (15-30 min)**
```bash
# If using Redis Sentinel
redis-cli -p 26379 SENTINEL failover mymaster

# Update application config
kubectl set env deployment/wolloyewa REDIS_HOST=new-redis-host
```

### Scenario 3: Application Failure

#### Detection
```bash
# Health check fails
curl http://localhost:8000/health

# High error rate in logs
grep "ERROR" /var/log/wolloyewa/app.log | wc -l
```

#### Response Procedure

**Step 1: Restart (0-5 min)**
```bash
# Docker deployment
docker-compose restart app

# Kubernetes
kubectl rollout restart deployment/wolloyewa-app

# Systemd
sudo systemctl restart wolloyewa
```

**Step 2: Rollback (5-15 min)**
```bash
# Docker rollback
docker-compose down
docker-compose up -d

# Kubernetes rollback
kubectl rollout undo deployment/wolloyewa-app

# Git rollback
git revert HEAD --no-edit
git push origin main
```

**Step 3: Scale (15-30 min)**
```bash
# Increase replicas
kubectl scale deployment/wolloyewa-app --replicas=5

# Auto-scaling
kubectl autoscale deployment wolloyewa-app --cpu-percent=70 --min=3 --max=10
```

### Scenario 4: Region/AZ Failure

#### Detection
```bash
# Multi-region health check
curl https://api.wolloyewa.com/health
curl https://backup-api.wolloyewa.com/health
```

#### Response Procedure

**Step 1: DNS Failover (0-10 min)**
```bash
# Update Route53
aws route53 change-resource-record-sets --hosted-zone-id ZONE_ID --change-batch file://failover.json

# Or update CloudFlare
curl -X PUT "https://api.cloudflare.com/client/v4/zones/ZONE_ID/dns_records/RECORD_ID" \
     -H "Authorization: Bearer TOKEN" \
     -H "Content-Type: application/json" \
     --data '{"content":"backup-api.wolloyewa.com"}'
```

**Step 2: Activate DR Site (10-30 min)**
```bash
# Scale up DR environment
kubectl scale deployment/wolloyewa-app --replicas=5 --namespace=dr

# Promote DR database
./scripts/promote_dr_database.sh

# Verify DR site
curl https://dr-api.wolloyewa.com/health
```

---

## 💾 Backup Procedures

### Database Backup

#### Full Backup (Daily)
```bash
# Automated backup at 2 AM
0 2 * * * /opt/wolloyewa/scripts/backup.sh

# Manual backup
./scripts/backup.sh --type=full

# Verify backup
./scripts/verify_backup.sh --backup-file=/backups/latest.sql.gz
```

#### Continuous Backup (WAL Archiving)
```bash
# Enable WAL archiving
ALTER SYSTEM SET wal_level = 'replica';
ALTER SYSTEM SET archive_mode = 'on';
ALTER SYSTEM SET archive_command = 'cp %p /backups/wal/%f';

# Reload configuration
SELECT pg_reload_conf();
```

### Redis Backup

#### RDB Snapshots
```bash
# Manual snapshot
redis-cli SAVE

# Automatic (configured in redis.conf)
save 900 1
save 300 10
save 60 10000
```

#### AOF Persistence
```bash
# Enable AOF
redis-cli CONFIG SET appendonly yes

# Rewrite AOF
redis-cli BGREWRITEAOF
```

### Media Files Backup

```bash
# S3 sync
aws s3 sync /var/www/media s3://wolloyewa-backups/media/ --delete

# Versioning enabled
aws s3api put-bucket-versioning --bucket wolloyewa-backups --versioning-configuration Status=Enabled
```

---

## 🔄 Recovery Procedures

### Full System Recovery

```bash
# Step 1: Provision new infrastructure
cd devops/terraform/aws
terraform apply -auto-approve

# Step 2: Restore database
./scripts/restore.sh --latest

# Step 3: Restore Redis
redis-cli --rdb /backups/dump.rdb

# Step 4: Restore media files
aws s3 sync s3://wolloyewa-backups/media/ /var/www/media/

# Step 5: Deploy application
kubectl apply -f devops/kubernetes/

# Step 6: Verify system
./scripts/healthcheck.sh
```

### Point-in-Time Recovery

```bash
# List available recovery points
./scripts/list_recovery_points.sh

# Restore to specific time
./scripts/restore_to_time.sh --timestamp "2024-01-15 14:30:00"

# Verify recovery
./scripts/verify_recovery.sh
```

### Table-Level Recovery

```bash
# Extract specific table from backup
pg_restore -t orders /backups/full_backup.sql > orders_restore.sql

# Restore table
psql -d welloyewadb -f orders_restore.sql
```

---

## 📋 Runbooks

### Database Failover Runbook

```bash
#!/bin/bash
# database_failover.sh

set -e

echo "Starting database failover..."

# 1. Check replica status
REPLICA_LAG=$(psql -h replica-host -c "SELECT pg_wal_lsn_diff(pg_last_wal_receive_lsn(), pg_last_wal_replay_lsn());" -t)

if [ $REPLICA_LAG -gt 1048576 ]; then
    echo "Replica lag too high: $REPLICA_LAG bytes"
    exit 1
fi

# 2. Promote replica
ssh replica-host "sudo -u postgres pg_ctl promote -D /var/lib/postgresql/15/main"

# 3. Update application
kubectl set env deployment/wolloyewa-app DATABASE_HOST=replica-host

# 4. Verify
if curl -f http://localhost:8000/health; then
    echo "Failover successful"
else
    echo "Failover failed"
    exit 1
fi
```

### Cache Recovery Runbook

```bash
#!/bin/bash
# cache_recovery.sh

set -e

echo "Starting cache recovery..."

# 1. Clear old cache
redis-cli FLUSHALL

# 2. Warm up cache
python scripts/warm_cache.py --concurrency=10

# 3. Verify cache hit rate
HIT_RATE=$(redis-cli INFO stats | grep keyspace_hits | cut -d: -f2)

if [ $HIT_RATE -gt 80 ]; then
    echo "Cache recovery successful"
else
    echo "Cache hit rate low: $HIT_RATE%"
fi
```

---

## 📊 Testing Schedule

| Test Type | Frequency | Last Test | Status |
|-----------|-----------|-----------|--------|
| Backup Restore | Weekly | 2024-01-10 | ✅ Pass |
| Failover | Monthly | 2024-01-05 | ✅ Pass |
| DR Simulation | Quarterly | 2023-12-15 | ✅ Pass |
| Full Recovery | Bi-annually | 2023-11-20 | ✅ Pass |
| Chaos Testing | Monthly | 2024-01-12 | ⚠️ Partial |

### Test Procedures

#### Backup Restore Test
```bash
# 1. Restore to test environment
./scripts/restore.sh --latest --target=test_db

# 2. Verify data integrity
./scripts/verify_data.sh --source=prod --target=test

# 3. Clean up
./scripts/cleanup_test.sh
```

#### Failover Test
```bash
# 1. Simulate primary failure
./scripts/simulate_failure.sh --component=database

# 2. Monitor failover
./scripts/monitor_failover.sh --timeout=300

# 3. Verify recovery
./scripts/verify_recovery.sh

# 4. Failback
./scripts/failback.sh
```

---

## 📞 Emergency Contacts

| Role | Primary | Secondary | Escalation |
|------|---------|-----------|------------|
| Incident Commander | DevOps Lead | CTO | CEO |
| Database Admin | DBA Team Lead | On-call DBA | DevOps Lead |
| Network Engineer | Network Lead | Security Lead | CTO |
| Security Analyst | Security Lead | CSIRT | CISO |

### Contact Tree

```
Incident Detection
        │
        ▼
   [L1 Support]
        │
        ▼
   [On-call Engineer] (15 min)
        │
        ▼
   [DevOps Lead] (30 min)
        │
        ▼
   [CTO] (1 hour)
        │
        ▼
   [CEO] (2 hours)
```

---

## 📈 Post-Incident Review

### Review Template

```markdown
# Post-Incident Report

## Incident Details
- Date: 
- Duration: 
- Impact: 
- Root Cause: 

## Timeline
- T+0: Detection
- T+5: Response initiated
- T+15: Containment
- T+30: Recovery started
- T+60: Service restored

## Lessons Learned
- What went well:
- What went wrong:
- What to improve:

## Action Items
- [ ] Action 1
- [ ] Action 2
```

---

## 🛠️ Recovery Tools

### Essential Tools

| Tool | Purpose | Installation |
|------|---------|--------------|
| pg_basebackup | PostgreSQL backup | `apt install postgresql-client` |
| redis-cli | Redis management | `apt install redis-tools` |
| awscli | S3 operations | `pip install awscli` |
| kubectl | K8s management | `curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"` |

### Custom Scripts

| Script | Purpose | Location |
|--------|---------|----------|
| backup.sh | Automated backup | `/scripts/backup.sh` |
| restore.sh | Database restore | `/scripts/restore.sh` |
| failover.sh | Automated failover | `/scripts/failover.sh` |
| verify.sh | Recovery verification | `/scripts/verify_recovery.sh` |

---

## 📚 Appendix

### Disaster Recovery Checklist

#### Pre-Disaster
- [x] Backups configured
- [x] Replication set up
- [x] Monitoring active
- [x] Runbooks documented
- [x] Team trained

#### During Disaster
- [ ] Incident declared
- [ ] Team notified
- [ ] Runbook followed
- [ ] Stakeholders updated
- [ ] Recovery attempted

#### Post-Disaster
- [ ] Service verified
- [ ] Root cause identified
- [ ] Post-mortem completed
- [ ] Improvements implemented
- [ ] Documentation updated

### SLA Commitments

| Service | Uptime | Penalty |
|---------|--------|---------|
| API | 99.9% | 10% credit |
| Bot | 99.5% | 5% credit |
| Payments | 99.95% | 20% credit |

---

**Next:** [Development Guide](development_guide.md)
```

**ቀጣይ ፋይል #303 ልስጥህ?** "ቀጣይ" በል።
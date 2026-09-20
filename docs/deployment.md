ደስ ብሎኛል! በጣም ጥሩ ውሳኔ ነው። መጀመሪያ በኮምፒውተርህ ላይ ሥራውን መሥራት ከዚያ በኋላ ወደ GitHub መግፋት።

## ቀጣይ ፋይል #299: `docs/deployment.md`

ይህ ፋይል ፕሮጀክቱን ወደ ምርት አካባቢ (production) እንዴት ማሰማራት እንደሚቻል የሚገልጽ ሰነድ ነው።

```markdown
# Wolloyewa Store Bot - Deployment Guide

## 📋 ይዘቶች

1. [System Requirements](#system-requirements)
2. [Production Environment Setup](#production-environment-setup)
3. [Docker Deployment](#docker-deployment)
4. [Kubernetes Deployment](#kubernetes-deployment)
5. [AWS Deployment](#aws-deployment)
6. [DigitalOcean Deployment](#digitalocean-deployment)
7. [Monitoring & Logging](#monitoring--logging)
8. [Backup & Recovery](#backup--recovery)
9. [Security Checklist](#security-checklist)
10. [Troubleshooting](#troubleshooting)

---

## System Requirements

### Minimum Requirements
| Resource | Requirement |
|----------|-------------|
| CPU | 2 vCPUs |
| RAM | 4 GB |
| Storage | 20 GB SSD |
| OS | Ubuntu 22.04 LTS / Debian 11 |

### Recommended Requirements
| Resource | Requirement |
|----------|-------------|
| CPU | 4 vCPUs |
| RAM | 8 GB |
| Storage | 50 GB SSD |
| OS | Ubuntu 22.04 LTS |

### Software Dependencies
- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Nginx 1.24+
- Docker 24+ (optional)
- Kubernetes 1.28+ (optional)

---

## Production Environment Setup

### 1. Server Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3.11 python3.11-venv python3-pip \
    postgresql-15 postgresql-contrib redis-server nginx \
    git curl wget htop

# Configure timezone
sudo timedatectl set-timezone Africa/Addis_Ababa
```

### 2. Database Setup

```bash
# Create database and user
sudo -u postgres psql << EOF
CREATE DATABASE welloyewadb;
CREATE USER wolloyewa_user WITH PASSWORD 'strong_password';
ALTER ROLE wolloyewa_user SET client_encoding TO 'utf8';
ALTER ROLE wolloyewa_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE wolloyewa_user SET timezone TO 'Africa/Addis_Ababa';
GRANT ALL PRIVILEGES ON DATABASE welloyewadb TO wolloyewa_user;
EOF

# Optimize PostgreSQL
sudo tee -a /etc/postgresql/15/main/postgresql.conf << EOF
shared_buffers = '1GB'
effective_cache_size = '3GB'
maintenance_work_mem = '256MB'
work_mem = '16MB'
max_connections = 200
EOF

sudo systemctl restart postgresql
```

### 3. Redis Setup

```bash
# Configure Redis
sudo tee -a /etc/redis/redis.conf << EOF
maxmemory 2gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
EOF

sudo systemctl restart redis-server
```

### 4. Application Setup

```bash
# Clone repository
git clone https://github.com/seidmekuriaw3-oss/welloyewa.git
cd welloyewa

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
nano .env  # Edit with production values

# Run migrations
alembic upgrade head

# Seed initial data (optional)
python scripts/seed_db.py

# Create systemd service
sudo tee /etc/systemd/system/wolloyewa.service << EOF
[Unit]
Description=Wolloyewa Store Bot
After=network.target postgresql.service redis-server.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/home/ubuntu/welloyewa
Environment="PATH=/home/ubuntu/welloyewa/venv/bin"
ExecStart=/home/ubuntu/welloyewa/venv/bin/gunicorn main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Start service
sudo systemctl daemon-reload
sudo systemctl enable wolloyewa
sudo systemctl start wolloyewa
```

---

## Docker Deployment

### 1. Build and Run with Docker Compose

```bash
# Clone repository
git clone https://github.com/seidmekuriaw3-oss/welloyewa.git
cd welloyewa

# Create .env file
cp .env.example .env
nano .env

# Build and start containers
docker-compose -f docker-compose.yml up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

### 2. Production Docker Compose

Create `docker-compose.prod.yml`:

```yaml
version: '3.9'

services:
  postgres:
    image: postgres:15-alpine
    restart: always
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - wolloyewa_network

  redis:
    image: redis:7-alpine
    restart: always
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    networks:
      - wolloyewa_network

  app:
    build:
      context: .
      target: production
    restart: always
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - ADMIN_IDS=${ADMIN_IDS}
    depends_on:
      - postgres
      - redis
    networks:
      - wolloyewa_network

  nginx:
    image: nginx:alpine
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./devops/nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./devops/nginx/ssl:/etc/nginx/ssl:ro
    depends_on:
      - app
    networks:
      - wolloyewa_network

volumes:
  postgres_data:
  redis_data:

networks:
  wolloyewa_network:
    driver: bridge
```

---

## Kubernetes Deployment

### 1. Create Namespace

```bash
kubectl create namespace wolloyewa
```

### 2. Create Secrets

```bash
kubectl create secret generic wolloyewa-secrets \
  --from-literal=postgres-password='your_password' \
  --from-literal=redis-password='your_redis_password' \
  --from-literal=telegram-token='your_telegram_token' \
  --namespace=wolloyewa
```

### 3. Apply Configurations

```bash
kubectl apply -f devops/kubernetes/configmap.yaml
kubectl apply -f devops/kubernetes/secrets.yaml
kubectl apply -f devops/kubernetes/deployment.yaml
kubectl apply -f devops/kubernetes/service.yaml
kubectl apply -f devops/kubernetes/ingress.yaml
kubectl apply -f devops/kubernetes/hpa.yaml
```

### 4. Check Status

```bash
kubectl get pods -n wolloyewa
kubectl get svc -n wolloyewa
kubectl get ingress -n wolloyewa
```

---

## AWS Deployment

### 1. Prerequisites

```bash
# Install AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Configure AWS
aws configure
```

### 2. Deploy with Terraform

```bash
cd devops/terraform/aws

# Initialize Terraform
terraform init

# Review plan
terraform plan

# Apply
terraform apply -auto-approve
```

### 3. ECS Deployment

```bash
# Build and push Docker image
aws ecr create-repository --repository-name wolloyewa
docker build -t wolloyewa .
docker tag wolloyewa:latest <account-id>.dkr.ecr.<region>.amazonaws.com/wolloyewa:latest
docker push <account-id>.dkr.ecr.<region>.amazonaws.com/wolloyewa:latest

# Deploy to ECS
aws ecs update-service --cluster wolloyewa --service wolloyewa-app --force-new-deployment
```

---

## DigitalOcean Deployment

### 1. Install doctl

```bash
# Install doctl
snap install doctl

# Authenticate
doctl auth init
```

### 2. Deploy with Terraform

```bash
cd devops/terraform/digitalocean

# Initialize
terraform init

# Apply
terraform apply -auto-approve
```

### 3. App Platform Deployment

```bash
# Create app spec
doctl apps create --spec .do/app.yaml
```

---

## Monitoring & Logging

### Prometheus Setup

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'wolloyewa'
    static_configs:
      - targets: ['localhost:8000']
```

### Grafana Dashboard

```bash
# Access Grafana
http://localhost:3000
# Default credentials: admin/admin
```

### Log Aggregation

```bash
# Install Vector for log shipping
curl --proto '=https' --tlsv1.2 -sSfL https://sh.vector.dev | bash

# Configure Vector
cat > /etc/vector/vector.toml << EOF
[sources.app]
type = "file"
include = ["/var/log/wolloyewa/*.log"]

[sinks.loki]
type = "loki"
inputs = ["app"]
endpoint = "http://loki:3100"
EOF
```

---

## Backup & Recovery

### Automated Backups

```bash
# Add to crontab
0 2 * * * /home/ubuntu/welloyewa/scripts/backup.sh

# Manual backup
./scripts/backup.sh

# Restore from backup
./scripts/restore.sh --latest
```

### Point-in-Time Recovery

```bash
# Create recovery point
python scripts/create_recovery_point.py

# Restore to timestamp
python scripts/restore_to_time.py --timestamp "2024-01-01 00:00:00"
```

---

## Security Checklist

### ✅ Pre-deployment
- [ ] Change all default passwords
- [ ] Generate new SECRET_KEY
- [ ] Enable HTTPS with Let's Encrypt
- [ ] Configure firewall (UFW)
- [ ] Set up fail2ban
- [ ] Enable audit logging

### ✅ Database Security
- [ ] Use strong passwords
- [ ] Enable SSL connections
- [ ] Restrict network access
- [ ] Regular backup verification

### ✅ Application Security
- [ ] Set DEBUG=False
- [ ] Configure CORS properly
- [ ] Enable rate limiting
- [ ] Set up security headers
- [ ] Use environment variables

### ✅ Monitoring
- [ ] Set up uptime monitoring
- [ ] Configure alerts
- [ ] Enable error tracking (Sentry)
- [ ] Set up log aggregation

---

## Troubleshooting

### Common Issues

#### Issue 1: Database Connection Failed
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Test connection
psql -h localhost -U wolloyewa_user -d welloyewadb -c "SELECT 1"
```

#### Issue 2: Redis Connection Failed
```bash
# Check Redis status
sudo systemctl status redis-server

# Test connection
redis-cli ping
```

#### Issue 3: Application Won't Start
```bash
# Check logs
journalctl -u wolloyewa -f

# Check port
sudo netstat -tlnp | grep 8000
```

#### Issue 4: Telegram Webhook Fails
```bash
# Check webhook status
curl https://api.telegram.org/bot<YOUR_TOKEN>/getWebhookInfo

# Reset webhook
curl https://api.telegram.org/bot<YOUR_TOKEN>/deleteWebhook

# Set webhook again
curl -F "url=https://your-domain.com/webhook/telegram" \
     https://api.telegram.org/bot<YOUR_TOKEN>/setWebhook
```

---

## Performance Tuning

### PostgreSQL Tuning
```sql
-- Enable query logging for slow queries
ALTER SYSTEM SET log_min_duration_statement = 1000;
SELECT pg_reload_conf();

-- Create indexes for frequent queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_created_at ON orders(created_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_products_vendor_status ON products(vendor_id, status);
```

### Redis Tuning
```bash
# Check memory usage
redis-cli INFO memory

# Monitor slow commands
redis-cli SLOWLOG GET 10
```

### Application Tuning
```python
# Adjust worker count based on CPU
workers = multiprocessing.cpu_count() * 2 + 1

# Adjust rate limits based on traffic
RATE_LIMIT_PER_MINUTE = 120  # Increase for production
```

---

## Support

For deployment support:
- 📧 Email: deployment@wolloyewa.com
- 💬 Telegram: @wolloyewa_support
- 📚 Documentation: https://docs.wolloyewa.com

---

**Next:** [User Manual](user_manual.md)
```


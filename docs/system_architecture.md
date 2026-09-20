## ፋይል #300: `docs/system_architecture.md`

```markdown
# Wolloyewa Store Bot - System Architecture

## 📐 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Clients Layer                                   │
├─────────────┬─────────────┬─────────────┬─────────────┬───────────────────┤
│  Telegram   │  Web App    │  Mobile App │   API       │   Webhooks        │
│    Bot      │   (React)   │  (Flutter)  │   Clients   │   (Payments)      │
└──────┬──────┴──────┬──────┴──────┬──────┴──────┬──────┴───────┬───────────┘
       │             │             │             │              │
       ▼             ▼             ▼             ▼              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Gateway Layer                                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │  Nginx   │ │   API    │ │   Auth   │ │  Rate    │ │    Circuit       │ │
│  │  Proxy   │ │ Gateway  │ │  Middle- │ │ Limiter  │ │    Breaker       │ │
│  │          │ │          │ │   ware   │ │          │ │                  │ │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Application Layer                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         FastAPI Application                          │   │
│  ├──────────┬──────────┬──────────┬──────────┬──────────┬────────────┤   │
│  │  Users   │ Products │  Orders  │Payment   │Inventory │ Marketing  │   │
│  │  Module  │  Module  │  Module  │ Module   │  Module  │  Module    │   │
│  ├──────────┼──────────┼──────────┼──────────┼──────────┼────────────┤   │
│  │Analytics │ Support  │  Vendor  │  Admin   │  Common  │   Bot      │   │
│  │  Module  │  Module  │  Module  │  Module  │  Module  │  Handlers  │   │
│  └──────────┴──────────┴──────────┴──────────┴──────────┴────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Service Layer                                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │ Business │ │  Cache   │ │   Task   │ │  Search  │ │   Notification   │ │
│  │  Logic   │ │ Service  │ │  Queue   │ │  Engine  │ │    Service       │ │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Data Layer                                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │PostgreSQL│ │  Redis   │ │    S3    │ │ClickHouse│ │   ElasticSearch  │ │
│  │ (Primary)│ │ (Cache)  │ │(Storage) │ │(Analytics│ │    (Search)      │ │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🏗️ Component Details

### 1. Gateway Layer

#### Nginx Reverse Proxy
```nginx
upstream wolloyewa_backend {
    least_conn;
    server app1:8000 weight=1;
    server app2:8000 weight=1;
    server app3:8000 weight=1;
}

server {
    listen 443 ssl http2;
    server_name api.wolloyewa.com;
    
    location / {
        proxy_pass http://wolloyewa_backend;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

#### API Gateway Features
| Feature | Implementation |
|---------|----------------|
| Rate Limiting | 60 req/min per IP |
| Authentication | JWT with refresh tokens |
| Request Validation | Pydantic schemas |
| Response Caching | Redis (5 min TTL) |
| Circuit Breaker | 5 failures = open |

### 2. Application Layer

#### Module Structure

```
apps/
├── common/          # Shared utilities
├── users/           # User management
├── products/        # Product catalog
├── orders/          # Order processing
├── payments/        # Payment integration
├── inventory/       # Stock management
├── marketing/       # Promotions, coupons
├── analytics/       # Reporting
└── support/         # Tickets, FAQs
```

#### Core Module

```
core/
├── config.py        # Settings management
├── security/        # Auth, encryption, security utilities
│   ├── __init__.py
│   ├── audit_trail.py
│   ├── encryption.py
│   ├── fraud_detection.py
│   ├── gdpr_compliance.py
│   ├── middleware.py
│   ├── pii_masker.py
│   ├── rate_limiter_advanced.py
│   ├── sql_injection_detector.py
├── events.py        # Event bus
├── exceptions.py    # Custom exceptions
├── logger.py        # Structured logging
├── circuit_breaker.py
├── rate_limiter.py
└── dependencies.py  # FastAPI deps
```

### 3. Service Layer

#### Task Queue (Celery)

```python
# Task definition
@celery_app.task
def process_order(order_id: int):
    order = get_order(order_id)
    process_payment(order)
    update_inventory(order)
    send_notification(order)
```

#### Queue Configuration
| Queue Name | Purpose | Concurrency |
|------------|---------|-------------|
| default | General tasks | 4 |
| high_priority | Payments, orders | 2 |
| email | Email sending | 2 |
| sms | SMS sending | 1 |
| analytics | Data processing | 2 |

#### Cache Strategy

```python
# Cache aside pattern
async def get_product(product_id):
    cached = await redis.get(f"product:{product_id}")
    if cached:
        return cached
    
    product = await db.get(Product, product_id)
    await redis.setex(f"product:{product_id}", 3600, product)
    return product
```

### 4. Data Layer

#### Database Schema

```sql
-- Core tables
users           -- User accounts
vendors         -- Vendor profiles
products        -- Product catalog
orders          -- Order headers
order_items     -- Order details
inventory       -- Stock levels
payments        -- Payment records
reviews         -- Product reviews
```

#### Index Strategy

```sql
-- High traffic queries
CREATE INDEX CONCURRENTLY idx_products_status ON products(status);
CREATE INDEX CONCURRENTLY idx_orders_user_status ON orders(user_id, status);
CREATE INDEX CONCURRENTLY idx_inventory_product ON inventory(product_id);
```

#### Redis Data Structures

| Key Pattern | Type | Purpose | TTL |
|-------------|------|---------|-----|
| `user:{id}` | Hash | User session | 1 day |
| `cart:{user_id}` | JSON | Shopping cart | 7 days |
| `rate_limit:{ip}` | String | Rate limiting | 1 min |
| `cache:{endpoint}` | JSON | API cache | 5 min |

---

## 🔄 Data Flow

### Order Creation Flow

```
┌────────┐     ┌────────┐     ┌────────┐     ┌────────┐     ┌────────┐
│ Client │────▶│  API   │────▶│ Order  │────▶│Payment │────▶│Inventory│
│        │     │Gateway │     │Service │     │Service │     │Service │
└────────┘     └────────┘     └────────┘     └────────┘     └────────┘
                                    │              │              │
                                    ▼              ▼              ▼
                               ┌────────┐     ┌────────┐     ┌────────┐
                               │  DB    │     │Chapa/  │     │ Redis  │
                               │(Order) │     │Telebirr│     │(Stock) │
                               └────────┘     └────────┘     └────────┘
```

### Payment Processing Flow

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  User    │────▶│ Payment  │────▶│ Gateway  │────▶│ Webhook  │
│  Request │     │ Initiate │     │  (Chapa) │     │ Endpoint │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
                                                          │
                                                          ▼
                                                    ┌──────────┐
                                                    │  Order   │
                                                    │  Update  │
                                                    └──────────┘
```

---

## 🔒 Security Architecture

### Authentication Flow

```
┌────────┐     ┌────────┐     ┌────────┐     ┌────────┐
│ User   │────▶│ JWT    │────▶│ Token  │────▶│ Access │
│ Login  │     │ Create │     │ Store  │     │ Resource│
└────────┘     └────────┘     └────────┘     └────────┘
                                    │
                                    ▼
                              ┌────────┐
                              │ Redis  │
                              │(Blacklist)│
                              └────────┘
```

### Security Measures

| Layer | Measures |
|-------|----------|
| Network | HTTPS, CORS, Rate limiting |
| Application | JWT, Input validation, SQL injection prevention |
| Data | Encryption at rest, PII masking |
| Infrastructure | Firewall, Fail2ban, Regular updates |

---

## 📊 Monitoring Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Metrics Collection                        │
├─────────────┬─────────────┬─────────────┬───────────────────────┤
│ Prometheus  │  Grafana    │  Sentry     │    ELK Stack          │
│ (Metrics)   │(Dashboard)  │ (Errors)    │    (Logs)             │
└──────┬──────┴──────┬──────┴──────┬──────┴───────────┬───────────┘
       │             │             │                  │
       ▼             ▼             ▼                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                          Alert Manager                           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────────┐ │
│  │Telegram  │ │  Email   │ │   SMS    │ │   PagerDuty        │ │
│  │Alerts    │ │ Alerts   │ │ Alerts   │ │   Integration      │ │
│  └──────────┘ └──────────┘ └──────────┘ └────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Key Metrics

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| API Response Time | < 200ms | > 500ms |
| Error Rate | < 0.1% | > 1% |
| CPU Usage | < 50% | > 80% |
| Memory Usage | < 60% | > 85% |
| Database Connections | < 50 | > 80 |

---

## 🚀 Deployment Architecture

### Production Setup

```
                    ┌─────────────────────────────┐
                    │      Load Balancer (Nginx)   │
                    │        (SSL Termination)     │
                    └─────────────┬───────────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              │                   │                   │
              ▼                   ▼                   ▼
        ┌──────────┐        ┌──────────┐        ┌──────────┐
        │  App #1  │        │  App #2  │        │  App #3  │
        │ (API/Bot)│        │ (API/Bot)│        │ (API/Bot)│
        └────┬─────┘        └────┬─────┘        └────┬─────┘
             │                   │                   │
             └───────────────────┼───────────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                  │
              ▼                  ▼                  ▼
        ┌──────────┐        ┌──────────┐        ┌──────────┐
        │PostgreSQL│        │  Redis   │        │  Celery  │
        │ (Primary)│        │ (Primary)│        │  Worker  │
        └────┬─────┘        └──────────┘        └──────────┘
             │
             ▼
        ┌──────────┐
        │PostgreSQL│
        │(Replica) │
        └──────────┘
```

### Auto-scaling Rules

```yaml
scaling_rules:
  - metric: cpu_utilization
    threshold: 70%
    adjustment: +1
    cooldown: 300s
  
  - metric: memory_usage
    threshold: 80%
    adjustment: +1
    cooldown: 300s
  
  - metric: requests_per_second
    threshold: 1000
    adjustment: +2
    cooldown: 180s
```

---

## 🔄 CI/CD Pipeline

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  GitHub  │────▶│  GitHub  │────▶│  Docker  │────▶│   AWS    │
│  Push    │     │ Actions  │     │  Build   │     │  ECS     │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
                       │
                       ▼
                 ┌──────────┐
                 │  Tests   │
                 │ (Pytest) │
                 └──────────┘
```

### Pipeline Stages

| Stage | Actions | Duration |
|-------|---------|----------|
| Test | Unit tests, Linting | 2 min |
| Build | Docker image | 3 min |
| Deploy | ECS deployment | 5 min |
| Verify | Health checks | 1 min |

---

## 📈 Performance Metrics

### Target KPIs

| Metric | Target | Current |
|--------|--------|---------|
| API Response (p95) | < 200ms | 150ms |
| Concurrent Users | 10,000 | 8,500 |
| Orders Per Second | 100 | 75 |
| Database Query Time | < 50ms | 35ms |
| Cache Hit Rate | > 80% | 85% |
| System Uptime | 99.9% | 99.95% |

### Scalability Limits

| Component | Current | Max | Scale Method |
|-----------|---------|-----|--------------|
| API Servers | 3 | 10 | Horizontal |
| Database | 1 primary + 1 replica | 1 primary + 3 replicas | Read replicas |
| Redis | 1 | 3 | Cluster mode |
| Celery Workers | 4 | 20 | Horizontal |

---

## 🛡️ Disaster Recovery

### RTO/RPO Targets

| Metric | Target |
|--------|--------|
| Recovery Time Objective (RTO) | 4 hours |
| Recovery Point Objective (RPO) | 15 minutes |

### Backup Strategy

```yaml
backup:
  database:
    frequency: daily
    retention: 30 days
    type: full + WAL
  
  redis:
    frequency: daily
    retention: 7 days
    type: RDB snapshot
  
  media:
    frequency: continuous
    retention: indefinite
    type: S3 replication
```

### Failover Procedure

1. Detect primary failure (3 failed health checks)
2. Promote replica to primary
3. Update DNS/load balancer
4. Verify system health
5. Notify admins

---

## 📚 Technology Stack

### Backend
| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.11 | Core language |
| FastAPI | 0.108 | Web framework |
| SQLAlchemy | 2.0 | ORM |
| Alembic | 1.13 | Migrations |
| Celery | 5.3 | Task queue |
| Pydantic | 2.5 | Data validation |

### Database & Cache
| Technology | Version | Purpose |
|------------|---------|---------|
| PostgreSQL | 15 | Primary database |
| Redis | 7 | Cache & queue broker |
| ClickHouse | 23.6 | Analytics |
| S3 | - | File storage |

### Monitoring
| Technology | Purpose |
|------------|---------|
| Prometheus | Metrics collection |
| Grafana | Visualization |
| Sentry | Error tracking |
| ELK Stack | Log aggregation |

### DevOps
| Technology | Purpose |
|------------|---------|
| Docker | Containerization |
| Kubernetes | Orchestration |
| GitHub Actions | CI/CD |
| Terraform | Infrastructure as code |

---

## 🔗 Related Documentation

- [API Documentation](api_docs.md)
- [Deployment Guide](deployment.md)
- [Security Audit](security_audit.md)
- [Development Guide](development_guide.md)

---

**Next:** [Security Audit](security_audit.md)
```

**ቀጣይ ፋይል #301 ልስጥህ?** "ቀጣይ" በል።
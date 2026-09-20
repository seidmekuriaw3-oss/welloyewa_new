# ============================
# WOLLOYEWA STORE BOT - DIGITALOCEAN TERRAFORM CONFIGURATION
# ============================

terraform {
  required_version = ">= 1.0"
  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
  backend "s3" {
    bucket = "wolloyewa-terraform-state"
    key    = "digitalocean/prod/terraform.tfstate"
    region = "nyc3"
  }
}

provider "digitalocean" {
  token = var.do_token
}

# ============================
# Kubernetes Cluster
# ============================

resource "digitalocean_kubernetes_cluster" "main" {
  name   = "wolloyewa-cluster"
  region = var.region
  version = var.k8s_version

  node_pool {
    name       = "worker-pool"
    size       = var.node_size
    node_count = var.node_count
    auto_scale = true
    min_nodes  = var.min_nodes
    max_nodes  = var.max_nodes

    tags = ["wolloyewa", "production"]
  }

  maintenance_policy {
    day        = "sunday"
    start_time = "02:00"
  }

  lifecycle {
    ignore_changes = [
      node_pool[0].node_count,
    ]
  }
}

# ============================
# Managed Database (PostgreSQL)
# ============================

resource "digitalocean_database_cluster" "postgres" {
  name       = "wolloyewa-db"
  engine     = "pg"
  version    = "15"
  size       = var.db_size
  region     = var.region
  node_count = var.db_node_count

  maintenance_window {
    day  = "sunday"
    hour = "03:00"
  }

  tags = ["wolloyewa", "database", "production"]
}

resource "digitalocean_database_user" "app_user" {
  cluster_id = digitalocean_database_cluster.postgres.id
  name       = "wolloyewa_user"
}

resource "random_password" "db_password" {
  length  = 24
  special = false
}

resource "digitalocean_database_db" "main" {
  cluster_id = digitalocean_database_cluster.postgres.id
  name       = "welloyewadb"
}

# ============================
# Managed Redis
# ============================

resource "digitalocean_database_cluster" "redis" {
  name       = "wolloyewa-redis"
  engine     = "redis"
  version    = "7"
  size       = var.redis_size
  region     = var.region
  node_count = var.redis_node_count

  tags = ["wolloyewa", "cache", "production"]
}

# ============================
# Container Registry
# ============================

resource "digitalocean_container_registry" "main" {
  name                   = "wolloyewa"
  subscription_tier_slug = "basic"
}

# ============================
# Spaces (Object Storage)
# ============================

resource "digitalocean_spaces_bucket" "media" {
  name   = "wolloyewa-media"
  region = var.region
  acl    = "private"

  versioning {
    enabled = true
  }

  lifecycle_rule {
    enabled = true
    expiration {
      days = 30
    }
  }

  tags = {
    Environment = "production"
    Project     = "Wolloyewa"
  }
}

resource "digitalocean_spaces_bucket" "backups" {
  name   = "wolloyewa-backups"
  region = var.region
  acl    = "private"

  versioning {
    enabled = true
  }

  lifecycle_rule {
    enabled = true
    expiration {
      days = 90
    }
  }
}

# ============================
# Load Balancer
# ============================

resource "digitalocean_loadbalancer" "public" {
  name   = "wolloyewa-lb"
  region = var.region

  forwarding_rule {
    entry_port     = 80
    entry_protocol = "http"
    target_port    = 80
    target_protocol = "http"
  }

  forwarding_rule {
    entry_port     = 443
    entry_protocol = "https"
    target_port    = 80
    target_protocol = "http"
    certificate_id = digitalocean_certificate.ssl.id
  }

  healthcheck {
    port     = 8000
    protocol = "http"
    path     = "/health"
  }

  droplet_ids = []
  enable_proxy_protocol = false
  enable_backend_keepalive = true

  sticky_sessions {
    type = "none"
  }
}

# ============================
# SSL Certificate
# ============================

resource "digitalocean_certificate" "ssl" {
  name    = "wolloyewa-ssl"
  type    = "lets_encrypt"
  domains = var.domains
}

# ============================
# DNS Records
# ============================

resource "digitalocean_domain" "main" {
  name = var.domain_name
}

resource "digitalocean_record" "api" {
  domain = digitalocean_domain.main.name
  type   = "A"
  name   = "api"
  value  = digitalocean_loadbalancer.public.ip
  ttl    = 300
}

resource "digitalocean_record" "www" {
  domain = digitalocean_domain.main.name
  type   = "A"
  name   = "www"
  value  = digitalocean_loadbalancer.public.ip
  ttl    = 300
}

resource "digitalocean_record" "cdn" {
  domain = digitalocean_domain.main.name
  type   = "CNAME"
  name   = "cdn"
  value  = digitalocean_spaces_bucket.media.bucket_domain_name
  ttl    = 300
}

# ============================
# Firewall
# ============================

resource "digitalocean_firewall" "k8s" {
  name  = "wolloyewa-firewall"
  tags  = ["wolloyewa"]

  inbound_rule {
    protocol         = "tcp"
    port_range       = "80"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  inbound_rule {
    protocol         = "tcp"
    port_range       = "443"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  inbound_rule {
    protocol         = "tcp"
    port_range       = "22"
    source_addresses = var.admin_cidrs
  }

  inbound_rule {
    protocol         = "tcp"
    port_range       = "6443"
    source_addresses = var.admin_cidrs
  }

  outbound_rule {
    protocol                = "tcp"
    port_range              = "1-65535"
    destination_addresses   = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
    protocol                = "udp"
    port_range              = "1-65535"
    destination_addresses   = ["0.0.0.0/0", "::/0"]
  }
}

# ============================
# Monitoring (Uptime Checks)
# ============================

resource "digitalocean_cdn" "cdn" {
  origin = digitalocean_spaces_bucket.media.bucket_domain_name
  ttl    = 3600
}

resource "digitalocean_monitor_alert" "cpu_high" {
  name        = "CPU High Alert"
  type        = "v1/insights/droplet/cpu"
  entities    = digitalocean_kubernetes_cluster.main.node_pool[0].nodes[*].id
  window      = "5m"
  compare     = "GreaterThan"
  value       = 80
  enabled     = true

  alerts {
    email = ["alerts@wolloyewa.com"]
  }
}

resource "digitalocean_monitor_alert" "memory_high" {
  name        = "Memory High Alert"
  type        = "v1/insights/droplet/memory"
  entities    = digitalocean_kubernetes_cluster.main.node_pool[0].nodes[*].id
  window      = "5m"
  compare     = "GreaterThan"
  value       = 85
  enabled     = true

  alerts {
    email = ["alerts@wolloyewa.com"]
  }
}
# ============================
# WOLLOYEWA STORE BOT - DIGITALOCEAN TERRAFORM VARIABLES
# ============================

variable "do_token" {
  description = "DigitalOcean API token"
  type        = string
  sensitive   = true
}

variable "region" {
  description = "DigitalOcean region"
  type        = string
  default     = "fra1"  # Frankfurt (closest to Ethiopia)
}

variable "domain_name" {
  description = "Domain name"
  type        = string
  default     = "wolloyewa.com"
}

variable "domains" {
  description = "Domains for SSL certificate"
  type        = list(string)
  default     = ["wolloyewa.com", "*.wolloyewa.com", "api.wolloyewa.com", "cdn.wolloyewa.com"]
}

variable "k8s_version" {
  description = "Kubernetes version"
  type        = string
  default     = "1.28.2-do.0"
}

variable "node_size" {
  description = "Node size for Kubernetes worker pool"
  type        = string
  default     = "s-2vcpu-4gb"
}

variable "node_count" {
  description = "Initial node count"
  type        = number
  default     = 3
}

variable "min_nodes" {
  description = "Minimum nodes for autoscaling"
  type        = number
  default     = 2
}

variable "max_nodes" {
  description = "Maximum nodes for autoscaling"
  type        = number
  default     = 10
}

variable "db_size" {
  description = "Database node size"
  type        = string
  default     = "db-s-2vcpu-4gb"
}

variable "db_node_count" {
  description = "Number of database nodes"
  type        = number
  default     = 2
}

variable "redis_size" {
  description = "Redis node size"
  type        = string
  default     = "db-s-2vcpu-4gb"
}

variable "redis_node_count" {
  description = "Number of Redis nodes"
  type        = number
  default     = 2
}

variable "admin_cidrs" {
  description = "CIDR blocks for admin access"
  type        = list(string)
  default     = ["192.168.0.0/16", "10.0.0.0/8"]
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default = {
    Project     = "WolloyewaStoreBot"
    Environment = "Production"
    ManagedBy   = "Terraform"
  }
}

variable "enable_monitoring" {
  description = "Enable monitoring alerts"
  type        = bool
  default     = true
}

variable "backup_retention_days" {
  description = "Backup retention in days"
  type        = number
  default     = 30
}

variable "alert_email" {
  description = "Email for alerts"
  type        = string
  default     = "alerts@wolloyewa.com"
}
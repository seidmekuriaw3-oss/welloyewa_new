# ============================
# WOLLOYEWA STORE BOT - AWS TERRAFORM VARIABLES
# ============================

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "eu-north-1"
}

variable "availability_zones" {
  description = "Availability zones"
  type        = list(string)
  default     = ["eu-north-1a", "eu-north-1b", "eu-north-1c"]
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.0.0.0/16"
}

variable "private_subnets" {
  description = "Private subnet CIDRs"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
}

variable "public_subnets" {
  description = "Public subnet CIDRs"
  type        = list(string)
  default     = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.large"
}

variable "db_allocated_storage" {
  description = "RDS allocated storage in GB"
  type        = number
  default     = 100
}

variable "db_username" {
  description = "Database username"
  type        = string
  default     = "wolloyewa_user"
  sensitive   = true
}

variable "db_multi_az" {
  description = "Enable multi-AZ for RDS"
  type        = bool
  default     = true
}

variable "redis_node_type" {
  description = "Redis node type"
  type        = string
  default     = "cache.t3.medium"
}

variable "redis_num_nodes" {
  description = "Number of Redis nodes"
  type        = number
  default     = 2
}

variable "app_desired_count" {
  description = "Desired number of app instances"
  type        = number
  default     = 3
}

variable "app_min_count" {
  description = "Minimum number of app instances"
  type        = number
  default     = 2
}

variable "app_max_count" {
  description = "Maximum number of app instances"
  type        = number
  default     = 10
}

variable "worker_desired_count" {
  description = "Desired number of worker instances"
  type        = number
  default     = 2
}

variable "worker_min_count" {
  description = "Minimum number of worker instances"
  type        = number
  default     = 1
}

variable "worker_max_count" {
  description = "Maximum number of worker instances"
  type        = number
  default     = 5
}

variable "domain_name" {
  description = "Domain name"
  type        = string
  default     = "wolloyewa.com"
}

variable "tags" {
  description = "Default tags"
  type        = map(string)
  default = {
    Project     = "WolloyewaStoreBot"
    Environment = "Production"
    ManagedBy   = "Terraform"
  }
}

variable "enable_waf" {
  description = "Enable WAF protection"
  type        = bool
  default     = true
}

variable "enable_backup" {
  description = "Enable automated backups"
  type        = bool
  default     = true
}

variable "backup_retention_days" {
  description = "Backup retention period in days"
  type        = number
  default     = 30
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 90
}

variable "alert_email" {
  description = "Email address for alerts"
  type        = string
  default     = "alerts@wolloyewa.com"
}

variable "sns_topic_name" {
  description = "SNS topic name for alerts"
  type        = string
  default     = "wolloyewa-alerts"
}
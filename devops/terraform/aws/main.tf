# ============================
# WOLLOYEWA STORE BOT - AWS TERRAFORM CONFIGURATION
# ============================

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
  backend "s3" {
    bucket = "wolloyewa-terraform-state"
    key    = "prod/terraform.tfstate"
    region = "eu-north-1"
  }
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      Environment = var.environment
      Project     = "WolloyewaStoreBot"
      ManagedBy   = "Terraform"
    }
  }
}

# ============================
# VPC Module
# ============================

module "vpc" {
  source = "terraform-aws-modules/vpc/aws"
  version = "5.0.0"

  name = "wolloyewa-vpc"
  cidr = var.vpc_cidr

  azs             = var.availability_zones
  private_subnets = var.private_subnets
  public_subnets  = var.public_subnets

  enable_nat_gateway     = true
  enable_vpn_gateway     = false
  single_nat_gateway     = true
  enable_dns_hostnames   = true
  enable_dns_support     = true

  tags = {
    Name = "wolloyewa-vpc"
  }
}

# ============================
# RDS PostgreSQL Module
# ============================

module "rds" {
  source = "terraform-aws-modules/rds/aws"
  version = "6.0.0"

  identifier = "wolloyewa-postgres"

  engine               = "postgres"
  engine_version       = "15.3"
  instance_class       = var.db_instance_class
  allocated_storage    = var.db_allocated_storage
  storage_encrypted    = true
  storage_type         = "gp3"

  db_name  = "welloyewadb"
  username = var.db_username
  password = random_password.db_password.result
  port     = 5432

  multi_az               = var.db_multi_az
  publicly_accessible    = false
  backup_retention_period = 30
  backup_window          = "03:00-04:00"
  maintenance_window     = "Mon:04:00-Mon:05:00"

  deletion_protection = true
  skip_final_snapshot = false
  final_snapshot_identifier_prefix = "wolloyewa-final"

  performance_insights_enabled = true
  performance_insights_retention_period = 7

  enabled_cloudwatch_logs_exports = ["postgresql"]

  vpc_security_group_ids = [module.db_security_group.security_group_id]

  db_subnet_group_name   = module.db_subnet_group.name
  subnet_ids             = module.vpc.private_subnets

  tags = {
    Name = "wolloyewa-postgres"
  }
}

resource "random_password" "db_password" {
  length  = 20
  special = false
}

module "db_security_group" {
  source = "terraform-aws-modules/security-group/aws"

  name        = "wolloyewa-db-sg"
  description = "Security group for PostgreSQL"
  vpc_id      = module.vpc.vpc_id

  ingress_with_cidr_blocks = [
    {
      from_port   = 5432
      to_port     = 5432
      protocol    = "tcp"
      description = "PostgreSQL from VPC"
      cidr_blocks = var.vpc_cidr
    }
  ]

  egress_rules = ["all-all"]
}

module "db_subnet_group" {
  source = "terraform-aws-modules/rds/aws//modules/db_subnet_group"

  name       = "wolloyewa-db-subnet-group"
  subnet_ids = module.vpc.private_subnets
}

# ============================
# Elasticache Redis Module
# ============================

module "redis" {
  source = "terraform-aws-modules/elasticache/aws"

  cluster_id           = "wolloyewa-redis"
  engine               = "redis"
  engine_version       = "7.0"
  node_type            = var.redis_node_type
  num_cache_nodes      = var.redis_num_nodes
  parameter_group_name = "default.redis7"
  port                 = 6379

  subnet_ids = module.vpc.private_subnets
  security_group_ids = [module.redis_security_group.security_group_id]

  automatic_failover_enabled = true
  multi_az_enabled          = true

  at_rest_encryption_enabled = true
  transit_encryption_enabled = true

  tags = {
    Name = "wolloyewa-redis"
  }
}

module "redis_security_group" {
  source = "terraform-aws-modules/security-group/aws"

  name        = "wolloyewa-redis-sg"
  description = "Security group for Redis"
  vpc_id      = module.vpc.vpc_id

  ingress_with_cidr_blocks = [
    {
      from_port   = 6379
      to_port     = 6379
      protocol    = "tcp"
      description = "Redis from VPC"
      cidr_blocks = var.vpc_cidr
    }
  ]

  egress_rules = ["all-all"]
}

# ============================
# ECS Cluster
# ============================

resource "aws_ecs_cluster" "main" {
  name = "wolloyewa-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

# ============================
# ECR Repository
# ============================

resource "aws_ecr_repository" "app" {
  name = "wolloyewa-app"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "KMS"
  }
}

# ============================
# S3 Buckets
# ============================

resource "aws_s3_bucket" "media" {
  bucket = "wolloyewa-media-${var.environment}"
  force_destroy = false

  tags = {
    Name = "Wolloyewa Media Storage"
  }
}

resource "aws_s3_bucket_versioning" "media" {
  bucket = aws_s3_bucket.media.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "media" {
  bucket = aws_s3_bucket.media.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "media" {
  bucket = aws_s3_bucket.media.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ============================
# CloudFront Distribution
# ============================

resource "aws_cloudfront_distribution" "cdn" {
  origin {
    domain_name = aws_s3_bucket.media.bucket_regional_domain_name
    origin_id   = "media-origin"
    
    s3_origin_config {
      origin_access_identity = aws_cloudfront_origin_access_identity.media.cloudfront_access_identity_path
    }
  }

  enabled             = true
  is_ipv6_enabled     = true
  comment             = "Wolloyewa CDN"
  default_root_object = "index.html"

  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD", "OPTIONS"]
    target_origin_id = "media-origin"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 3600
    max_ttl                = 86400
    compress               = true
  }

  price_class = "PriceClass_100"

  restrictions {
    geo_restriction {
      restriction_type = "whitelist"
      locations        = ["ET"]
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = false
    acm_certificate_arn            = aws_acm_certificate.cert.arn
    ssl_support_method             = "sni-only"
    minimum_protocol_version       = "TLSv1.2_2021"
  }

  tags = {
    Name = "Wolloyewa CDN"
  }
}

resource "aws_cloudfront_origin_access_identity" "media" {
  comment = "Media OAI"
}

# ============================
# ACM Certificate
# ============================

resource "aws_acm_certificate" "cert" {
  domain_name       = "*.wolloyewa.com"
  validation_method = "DNS"

  tags = {
    Name = "Wolloyewa Certificate"
  }

  lifecycle {
    create_before_destroy = true
  }
}

# ============================
# Route53 Zone
# ============================

data "aws_route53_zone" "main" {
  name         = "wolloyewa.com"
  private_zone = false
}

resource "aws_route53_record" "cert_validation" {
  for_each = {
    for dvo in aws_acm_certificate.cert.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }

  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = data.aws_route53_zone.main.zone_id
}

resource "aws_acm_certificate_validation" "cert" {
  certificate_arn         = aws_acm_certificate.cert.arn
  validation_record_fqdns = [for record in aws_route53_record.cert_validation : record.fqdn]
}

# ============================
# CloudWatch Alarms
# ============================

resource "aws_cloudwatch_metric_alarm" "high_cpu" {
  alarm_name          = "wolloyewa-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name        = "CPUUtilization"
  namespace          = "AWS/ECS"
  period             = 300
  statistic          = "Average"
  threshold          = 80
  alarm_description  = "High CPU usage on ECS cluster"
  
  dimensions = {
    ClusterName = aws_ecs_cluster.main.name
  }
}

resource "aws_cloudwatch_metric_alarm" "high_memory" {
  alarm_name          = "wolloyewa-high-memory"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name        = "MemoryUtilization"
  namespace          = "AWS/ECS"
  period             = 300
  statistic          = "Average"
  threshold          = 85
  alarm_description  = "High memory usage on ECS cluster"
  
  dimensions = {
    ClusterName = aws_ecs_cluster.main.name
  }
}
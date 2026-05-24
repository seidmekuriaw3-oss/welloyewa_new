# ============================
# WOLLOYEWA STORE BOT - METRICS COLLECTION
# ============================
"""Prometheus metrics collection and monitoring."""

import time
from typing import Dict, Any, Optional, Callable
from functools import wraps
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Summary,
    Info,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

from core.config import settings
from core.logger import logger


# ============================
# HTTP Metrics
# ============================

http_requests_total = Counter(
    'http_requests_total',
    'Total number of HTTP requests',
    ['method', 'endpoint', 'status_code']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]
)

http_requests_in_progress = Gauge(
    'http_requests_in_progress',
    'Number of HTTP requests in progress',
    ['method']
)


# ============================
# Business Metrics
# ============================

orders_total = Counter(
    'orders_total',
    'Total number of orders created',
    ['status', 'payment_method']
)

orders_value_total = Counter(
    'orders_value_total',
    'Total value of orders in Birr',
    ['status']
)

products_total = Gauge(
    'products_total',
    'Total number of products',
    ['status', 'category']
)

users_total = Gauge(
    'users_total',
    'Total number of users',
    ['role', 'status']
)

vendors_total = Gauge(
    'vendors_total',
    'Total number of vendors',
    ['status']
)

cart_value = Histogram(
    'cart_value_birr',
    'Cart value in Birr',
    buckets=[100, 500, 1000, 2500, 5000, 10000, 25000, 50000]
)


# ============================
# Payment Metrics
# ============================

payments_total = Counter(
    'payments_total',
    'Total number of payment attempts',
    ['method', 'status']
)

payments_value_total = Counter(
    'payments_value_total',
    'Total value of payments in Birr',
    ['method', 'status']
)

payment_duration_seconds = Histogram(
    'payment_duration_seconds',
    'Payment processing duration in seconds',
    ['method'],
    buckets=[0.5, 1, 2, 5, 10, 20, 30]
)


# ============================
# Database Metrics
# ============================

db_connections = Gauge(
    'db_connections',
    'Number of active database connections',
    ['pool']
)

db_query_duration_seconds = Histogram(
    'db_query_duration_seconds',
    'Database query duration in seconds',
    ['operation', 'table'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1]
)

db_errors_total = Counter(
    'db_errors_total',
    'Total number of database errors',
    ['error_type']
)


# ============================
# Cache Metrics
# ============================

cache_hits_total = Counter(
    'cache_hits_total',
    'Total number of cache hits',
    ['cache_name']
)

cache_misses_total = Counter(
    'cache_misses_total',
    'Total number of cache misses',
    ['cache_name']
)

cache_operations_duration_seconds = Histogram(
    'cache_operations_duration_seconds',
    'Cache operation duration in seconds',
    ['operation', 'cache_name']
)


# ============================
# Message Queue Metrics
# ============================

queue_messages_total = Counter(
    'queue_messages_total',
    'Total number of messages processed',
    ['queue', 'status']
)

queue_message_duration_seconds = Histogram(
    'queue_message_duration_seconds',
    'Message processing duration in seconds',
    ['queue', 'task']
)

queue_size = Gauge(
    'queue_size',
    'Current size of message queue',
    ['queue']
)


# ============================
# External Service Metrics
# ============================

external_requests_total = Counter(
    'external_requests_total',
    'Total number of external service requests',
    ['service', 'method', 'status_code']
)

external_request_duration_seconds = Histogram(
    'external_request_duration_seconds',
    'External service request duration in seconds',
    ['service']
)


# ============================
# System Metrics
# ============================

system_cpu_usage = Gauge(
    'system_cpu_usage',
    'System CPU usage percentage'
)

system_memory_usage = Gauge(
    'system_memory_usage',
    'System memory usage in bytes'
)

system_uptime_seconds = Gauge(
    'system_uptime_seconds',
    'System uptime in seconds'
)

goroutines = Gauge(
    'goroutines',
    'Number of active goroutines'
)


# ============================
# Bot Specific Metrics
# ============================

bot_messages_total = Counter(
    'bot_messages_total',
    'Total number of bot messages processed',
    ['command', 'status']
)

bot_active_users = Gauge(
    'bot_active_users',
    'Number of active bot users',
    ['period']
)

bot_command_duration_seconds = Histogram(
    'bot_command_duration_seconds',
    'Bot command processing duration in seconds',
    ['command']
)


class MetricsCollector:
    """Collector for application metrics."""
    
    @staticmethod
    def record_order_created(order_value: float, payment_method: str):
        """Record order creation metric."""
        orders_total.labels(status='created', payment_method=payment_method).inc()
        orders_value_total.labels(status='created').inc(order_value)
        logger.debug(f"Recorded order creation: {order_value} ETB via {payment_method}")
    
    @staticmethod
    def record_order_completed(order_value: float, payment_method: str):
        """Record order completion metric."""
        orders_total.labels(status='completed', payment_method=payment_method).inc()
        orders_value_total.labels(status='completed').inc(order_value)
    
    @staticmethod
    def record_payment_attempt(method: str, status: str, amount: float = 0):
        """Record payment attempt metric."""
        payments_total.labels(method=method, status=status).inc()
        if amount > 0:
            payments_value_total.labels(method=method, status=status).inc(amount)
    
    @staticmethod
    def record_cache_hit(cache_name: str):
        """Record cache hit."""
        cache_hits_total.labels(cache_name=cache_name).inc()
    
    @staticmethod
    def record_cache_miss(cache_name: str):
        """Record cache miss."""
        cache_misses_total.labels(cache_name=cache_name).inc()
    
    @staticmethod
    def record_db_query(duration: float, operation: str, table: str):
        """Record database query metric."""
        db_query_duration_seconds.labels(operation=operation, table=table).observe(duration)
    
    @staticmethod
    def record_external_request(service: str, duration: float, status_code: int):
        """Record external service request metric."""
        external_requests_total.labels(
            service=service,
            method='request',
            status_code=status_code
        ).inc()
        external_request_duration_seconds.labels(service=service).observe(duration)
    
    @staticmethod
    def update_products_count(status: str, category: str, count: int):
        """Update products gauge metric."""
        products_total.labels(status=status, category=category).set(count)
    
    @staticmethod
    def update_users_count(role: str, status: str, count: int):
        """Update users gauge metric."""
        users_total.labels(role=role, status=status).set(count)
    
    @staticmethod
    def record_bot_command(command: str, duration: float, success: bool):
        """Record bot command metric."""
        status = 'success' if success else 'error'
        bot_messages_total.labels(command=command, status=status).inc()
        bot_command_duration_seconds.labels(command=command).observe(duration)
    
    @staticmethod
    def update_active_users(count: int, period: str = 'daily'):
        """Update active users metric."""
        bot_active_users.labels(period=period).set(count)


# Global metrics collector instance
metrics_collector = MetricsCollector()


def track_request_metrics(endpoint: str):
    """Decorator to track HTTP request metrics."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            method = kwargs.get('method', 'GET')
            http_requests_in_progress.labels(method=method).inc()
            
            start_time = time.time()
            try:
                response = await func(*args, **kwargs)
                status_code = getattr(response, 'status_code', 200)
                http_requests_total.labels(
                    method=method,
                    endpoint=endpoint,
                    status_code=status_code
                ).inc()
                return response
            except Exception as e:
                http_requests_total.labels(
                    method=method,
                    endpoint=endpoint,
                    status_code=500
                ).inc()
                raise
            finally:
                duration = time.time() - start_time
                http_request_duration_seconds.labels(
                    method=method,
                    endpoint=endpoint
                ).observe(duration)
                http_requests_in_progress.labels(method=method).dec()
        
        return wrapper
    return decorator


def track_request(endpoint: str, method: str, duration: float, status_code: int):
    """Track request metrics."""
    http_requests_total.labels(method=method, endpoint=endpoint, status_code=status_code).inc()
    http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)


def track_error(error_type: str, endpoint: str = None):
    """Track error metric."""
    db_errors_total.labels(error_type=error_type).inc()
    logger.warning(f"Error tracked: {error_type} at {endpoint}")


def track_order_created(order_value: float, payment_method: str):
    """Track order created metric."""
    metrics_collector.record_order_created(order_value, payment_method)


def track_payment_success(method: str, amount: float):
    """Track successful payment metric."""
    metrics_collector.record_payment_attempt(method, 'success', amount)


def get_metrics() -> bytes:
    """Get Prometheus metrics in text format."""
    return generate_latest()


__all__ = [
    "MetricsCollector",
    "metrics_collector",
    "track_request",
    "track_request_metrics",
    "track_error",
    "track_order_created",
    "track_payment_success",
    "get_metrics",
    # Individual metrics for direct access
    "http_requests_total",
    "http_request_duration_seconds",
    "orders_total",
    "payments_total",
    "db_query_duration_seconds",
    "cache_hits_total",
    "bot_messages_total",
]
# ============================
# WOLLOYEWA STORE BOT - ANALYTICS SCHEMAS
# ============================
"""Pydantic schemas for analytics request/response validation."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from decimal import Decimal
from pydantic import Field

from apps.common.schemas import BaseSchema


# ============================
# Sales Report Schemas
# ============================

class SalesReportRequest(BaseSchema):
    """Schema for sales report request."""
    
    start_date: datetime = Field(..., description="Report start date")
    end_date: datetime = Field(..., description="Report end date")
    vendor_id: Optional[int] = Field(None, description="Filter by vendor ID")
    group_by: Optional[str] = Field("day", description="Group by (day, week, month)")


class DailySalesData(BaseSchema):
    """Schema for daily sales data."""
    
    date: str = Field(..., description="Date")
    order_count: int = Field(0, description="Number of orders")
    total_sales: float = Field(0.0, description="Total sales amount")
    average_order: float = Field(0.0, description="Average order value")


class WeeklySalesData(BaseSchema):
    """Schema for weekly sales data."""
    
    year: int = Field(..., description="Year")
    week: int = Field(..., description="Week number")
    order_count: int = Field(0, description="Number of orders")
    total_sales: float = Field(0.0, description="Total sales amount")


class MonthlySalesData(BaseSchema):
    """Schema for monthly sales data."""
    
    month: str = Field(..., description="Month (YYYY-MM)")
    order_count: int = Field(0, description="Number of orders")
    total_sales: float = Field(0.0, description="Total sales amount")


class TopProductData(BaseSchema):
    """Schema for top product data."""
    
    product_id: int = Field(..., description="Product ID")
    product_name: str = Field(..., description="Product name")
    quantity_sold: int = Field(0, description="Quantity sold")
    revenue: float = Field(0.0, description="Revenue generated")


class SalesSummaryResponse(BaseSchema):
    """Schema for sales summary response."""
    
    total_orders: int = Field(0, description="Total number of orders")
    total_revenue: float = Field(0.0, description="Total revenue")
    avg_order_value: float = Field(0.0, description="Average order value")
    total_discount: float = Field(0.0, description="Total discount given")
    total_shipping: float = Field(0.0, description="Total shipping collected")
    total_tax: float = Field(0.0, description="Total tax collected")


class SalesReportResponse(BaseSchema):
    """Schema for sales report response."""
    
    period: Dict[str, str] = Field(..., description="Report period")
    summary: SalesSummaryResponse = Field(..., description="Sales summary")
    daily_breakdown: List[DailySalesData] = Field(default_factory=list, description="Daily breakdown")
    weekly_breakdown: List[WeeklySalesData] = Field(default_factory=list, description="Weekly breakdown")
    monthly_breakdown: List[MonthlySalesData] = Field(default_factory=list, description="Monthly breakdown")
    top_products: List[TopProductData] = Field(default_factory=list, description="Top selling products")
    top_categories: List[Dict[str, Any]] = Field(default_factory=list, description="Top selling categories")
    revenue_by_payment: List[Dict[str, Any]] = Field(default_factory=list, description="Revenue by payment method")


# ============================
# User Analytics Schemas
# ============================

class UserGrowthData(BaseSchema):
    """Schema for user growth data."""
    
    date: str = Field(..., description="Date")
    new_users: int = Field(0, description="New users registered")


class UserRetentionData(BaseSchema):
    """Schema for user retention data."""
    
    cohort_size: int = Field(0, description="Number of users in cohort")
    returning_users: int = Field(0, description="Users who returned")
    retention_rate: float = Field(0.0, description="Retention rate percentage")


class UserActivityReport(BaseSchema):
    """Schema for user activity report."""
    
    active_users: int = Field(0, description="Active users in period")
    new_users: int = Field(0, description="New users in period")
    user_growth: List[UserGrowthData] = Field(default_factory=list, description="User growth over time")
    retention: UserRetentionData = Field(..., description="User retention metrics")
    user_segments: Dict[str, int] = Field(default_factory=dict, description="User segmentation counts")
    conversion_funnel: Dict[str, float] = Field(default_factory=dict, description="Conversion funnel metrics")


# ============================
# Product Analytics Schemas
# ============================

class ProductPerformanceData(BaseSchema):
    """Schema for product performance data."""
    
    product_id: int = Field(..., description="Product ID")
    product_name: str = Field(..., description="Product name")
    views: int = Field(0, description="Number of views")
    sales: int = Field(0, description="Number of sales")
    revenue: float = Field(0.0, description="Revenue generated")
    conversion_rate: float = Field(0.0, description="Conversion rate percentage")
    average_rating: float = Field(0.0, description="Average rating")
    stock_quantity: int = Field(0, description="Current stock quantity")
    status: str = Field(..., description="Product status")


class InventoryAnalyticsData(BaseSchema):
    """Schema for inventory analytics data."""
    
    total_products: int = Field(0, description="Total products in inventory")
    total_units: int = Field(0, description="Total units in stock")
    total_value: float = Field(0.0, description="Total inventory value")
    out_of_stock_count: int = Field(0, description="Out of stock products")
    low_stock_count: int = Field(0, description="Low stock products")
    in_stock_count: int = Field(0, description="In stock products")


class ProductPerformanceReport(BaseSchema):
    """Schema for product performance report."""
    
    products: List[ProductPerformanceData] = Field(default_factory=list, description="Product performance list")
    inventory: InventoryAnalyticsData = Field(..., description="Inventory analytics")
    low_stock_products: List[Dict[str, Any]] = Field(default_factory=list, description="Low stock products")


# ============================
# Dashboard Schemas
# ============================

class RevenueStats(BaseSchema):
    """Schema for revenue statistics."""
    
    revenue: float = Field(0.0, description="Revenue amount")
    orders: int = Field(0, description="Number of orders")
    average_order_value: float = Field(0.0, description="Average order value")


class OrderStats(BaseSchema):
    """Schema for order statistics."""
    
    pending: int = Field(0, description="Pending orders")
    processing: int = Field(0, description="Processing orders")
    shipped: int = Field(0, description="Shipped orders")
    delivered: int = Field(0, description="Delivered orders")
    cancelled: int = Field(0, description="Cancelled orders")


class UserStats(BaseSchema):
    """Schema for user statistics."""
    
    total_users: int = Field(0, description="Total users")
    active_users: int = Field(0, description="Active users")
    new_users_today: int = Field(0, description="New users today")
    vendors: int = Field(0, description="Number of vendors")


class RecentOrder(BaseSchema):
    """Schema for recent order data."""
    
    order_id: int = Field(..., description="Order ID")
    order_number: str = Field(..., description="Order number")
    total: float = Field(..., description="Order total")
    status: str = Field(..., description="Order status")
    created_at: str = Field(..., description="Creation timestamp")
    customer_name: Optional[str] = Field(None, description="Customer name")


class DashboardSummary(BaseSchema):
    """Schema for dashboard summary response."""
    
    today: RevenueStats = Field(..., description="Today's stats")
    weekly: RevenueStats = Field(..., description="Weekly stats")
    monthly: RevenueStats = Field(..., description="Monthly stats")
    recent_orders: List[RecentOrder] = Field(default_factory=list, description="Recent orders")
    top_products: List[TopProductData] = Field(default_factory=list, description="Top products")
    active_users: int = Field(0, description="Active users")
    low_stock_count: int = Field(0, description="Low stock products count")
    low_stock_products: List[Dict[str, Any]] = Field(default_factory=list, description="Low stock products")


# ============================
# Custom Report Schemas
# ============================

class CustomReportRequest(BaseSchema):
    """Schema for custom report request."""
    
    report_type: str = Field(..., description="Report type (sales, users, products)")
    start_date: datetime = Field(..., description="Start date")
    end_date: datetime = Field(..., description="End date")
    dimensions: List[str] = Field(default_factory=list, description="Group by dimensions")
    metrics: List[str] = Field(default_factory=list, description="Metrics to include")
    filters: Optional[Dict[str, Any]] = Field(None, description="Additional filters")
    format: str = Field("json", description="Export format (json, csv, excel)")


__all__ = [
    "SalesReportRequest",
    "SalesReportResponse",
    "DailySalesData",
    "WeeklySalesData",
    "MonthlySalesData",
    "TopProductData",
    "SalesSummaryResponse",
    "UserGrowthData",
    "UserRetentionData",
    "UserActivityReport",
    "ProductPerformanceData",
    "InventoryAnalyticsData",
    "ProductPerformanceReport",
    "RevenueStats",
    "OrderStats",
    "UserStats",
    "RecentOrder",
    "DashboardSummary",
    "CustomReportRequest",
]
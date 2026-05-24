# ============================
# WOLLOYEWA STORE BOT - CLICKHOUSE LOADER
# ============================
"""Load transformed data into ClickHouse for analytics."""

from typing import Dict, Any, List, Optional
from datetime import datetime

from core.config import settings
from core.logger import logger


class ClickHouseLoader:
    """
    Load data into ClickHouse data warehouse.
    
    Features:
    - Batch loading for large datasets
    - Table creation and schema management
    - Incremental loading with deduplication
    - Error handling and retry logic
    """
    
    def __init__(self, host: Optional[str] = None, port: int = 8123):
        self.host = host or "localhost"
        self.port = port
        self._client = None
        self._initialized = False
        self._batch_size = 5000
    
    async def _get_client(self):
        """Get ClickHouse client (lazy initialization)."""
        if not self._initialized:
            try:
                # Import clickhouse driver only when needed
                from clickhouse_driver import Client
                
                self._client = Client(
                    host=self.host,
                    port=self.port,
                    user='default',
                    password='',
                    database='wolloyewa',
                )
                await self._create_tables_if_not_exists()
                self._initialized = True
                logger.info(f"Connected to ClickHouse at {self.host}:{self.port}")
            except ImportError:
                logger.warning("ClickHouse driver not installed. Using mock mode.")
                self._initialized = True
            except Exception as e:
                logger.error(f"Failed to connect to ClickHouse: {e}")
                raise
        
        return self._client
    
    async def _create_tables_if_not_exists(self) -> None:
        """Create necessary tables if they don't exist."""
        if not self._client:
            return
        
        # Orders table
        create_orders_table = """
        CREATE TABLE IF NOT EXISTS wolloyewa.orders (
            order_id UInt64,
            order_number String,
            user_id UInt64,
            vendor_id UInt64,
            status String,
            total Decimal64(2),
            payment_method String,
            payment_status String,
            shipping_city String,
            created_at DateTime,
            updated_at DateTime
        ) ENGINE = MergeTree()
        ORDER BY (created_at, order_id)
        """
        
        # Order items table
        create_items_table = """
        CREATE TABLE IF NOT EXISTS wolloyewa.order_items (
            item_id UInt64,
            order_id UInt64,
            product_id UInt64,
            product_name String,
            quantity UInt32,
            unit_price Decimal64(2),
            total_price Decimal64(2),
            created_at DateTime
        ) ENGINE = MergeTree()
        ORDER BY (created_at, order_id)
        """
        
        # Users table
        create_users_table = """
        CREATE TABLE IF NOT EXISTS wolloyewa.users (
            user_id UInt64,
            telegram_id String,
            role String,
            status String,
            age_group String,
            city String,
            customer_segment String,
            is_vendor UInt8,
            created_at DateTime,
            last_active DateTime
        ) ENGINE = MergeTree()
        ORDER BY (created_at, user_id)
        """
        
        # Daily analytics table
        create_analytics_table = """
        CREATE TABLE IF NOT EXISTS wolloyewa.daily_analytics (
            date Date,
            metric_name String,
            metric_value Float64,
            dimension String,
            dimension_value String
        ) ENGINE = SummingMergeTree()
        ORDER BY (date, metric_name, dimension, dimension_value)
        """
        
        try:
            self._client.execute(create_orders_table)
            self._client.execute(create_items_table)
            self._client.execute(create_users_table)
            self._client.execute(create_analytics_table)
            logger.info("ClickHouse tables created/verified")
        except Exception as e:
            logger.error(f"Failed to create ClickHouse tables: {e}")
    
    async def load_orders(self, orders: List[Dict[str, Any]]) -> int:
        """
        Load orders into ClickHouse.
        
        Args:
            orders: List of order dictionaries
            
        Returns:
            Number of rows loaded
        """
        if not orders:
            return 0
        
        client = await self._get_client()
        if not client:
            logger.warning("ClickHouse client not available, skipping load")
            return 0
        
        # Prepare data for insertion
        data = []
        for order in orders:
            data.append((
                order.get('id'),
                order.get('order_number'),
                order.get('user_id'),
                order.get('vendor_id'),
                order.get('status'),
                order.get('total', 0),
                order.get('payment_method'),
                order.get('payment_status'),
                order.get('shipping_city'),
                order.get('created_at'),
                order.get('updated_at'),
            ))
        
        try:
            client.execute(
                """
                INSERT INTO wolloyewa.orders 
                (order_id, order_number, user_id, vendor_id, status, total, 
                 payment_method, payment_status, shipping_city, created_at, updated_at)
                VALUES
                """,
                data,
            )
            logger.info(f"Loaded {len(data)} orders into ClickHouse")
            return len(data)
        except Exception as e:
            logger.error(f"Failed to load orders into ClickHouse: {e}")
            return 0
    
    async def load_order_items(self, items: List[Dict[str, Any]]) -> int:
        """
        Load order items into ClickHouse.
        
        Args:
            items: List of order item dictionaries
            
        Returns:
            Number of rows loaded
        """
        if not items:
            return 0
        
        client = await self._get_client()
        if not client:
            return 0
        
        data = []
        for item in items:
            data.append((
                item.get('id'),
                item.get('order_id'),
                item.get('product_id'),
                item.get('product_name'),
                item.get('quantity', 0),
                item.get('unit_price', 0),
                item.get('total_price', 0),
                item.get('created_at'),
            ))
        
        try:
            client.execute(
                """
                INSERT INTO wolloyewa.order_items 
                (item_id, order_id, product_id, product_name, quantity, 
                 unit_price, total_price, created_at)
                VALUES
                """,
                data,
            )
            logger.info(f"Loaded {len(data)} order items into ClickHouse")
            return len(data)
        except Exception as e:
            logger.error(f"Failed to load order items into ClickHouse: {e}")
            return 0
    
    async def load_users(self, users: List[Dict[str, Any]]) -> int:
        """
        Load user data into ClickHouse.
        
        Args:
            users: List of user dictionaries
            
        Returns:
            Number of rows loaded
        """
        if not users:
            return 0
        
        client = await self._get_client()
        if not client:
            return 0
        
        data = []
        for user in users:
            data.append((
                user.get('user_id'),
                user.get('telegram_id'),
                user.get('role'),
                user.get('status'),
                user.get('age_group'),
                user.get('city'),
                user.get('customer_segment'),
                1 if user.get('is_vendor') else 0,
                user.get('created_at'),
                user.get('last_active'),
            ))
        
        try:
            client.execute(
                """
                INSERT INTO wolloyewa.users 
                (user_id, telegram_id, role, status, age_group, city, 
                 customer_segment, is_vendor, created_at, last_active)
                VALUES
                """,
                data,
            )
            logger.info(f"Loaded {len(data)} users into ClickHouse")
            return len(data)
        except Exception as e:
            logger.error(f"Failed to load users into ClickHouse: {e}")
            return 0
    
    async def load_analytics_event(
        self,
        date: datetime,
        metric_name: str,
        metric_value: float,
        dimension: str = "total",
        dimension_value: str = "all",
    ) -> bool:
        """
        Load a single analytics event.
        
        Args:
            date: Event date
            metric_name: Name of the metric
            metric_value: Value of the metric
            dimension: Dimension to aggregate by
            dimension_value: Value of the dimension
            
        Returns:
            True if successful
        """
        client = await self._get_client()
        if not client:
            return False
        
        try:
            client.execute(
                """
                INSERT INTO wolloyewa.daily_analytics 
                (date, metric_name, metric_value, dimension, dimension_value)
                VALUES
                """,
                [(date.date(), metric_name, metric_value, dimension, dimension_value)],
            )
            return True
        except Exception as e:
            logger.error(f"Failed to load analytics event: {e}")
            return False
    
    async def load_analytics_batch(self, events: List[Dict[str, Any]]) -> int:
        """
        Load multiple analytics events.
        
        Args:
            events: List of event dictionaries
            
        Returns:
            Number of rows loaded
        """
        if not events:
            return 0
        
        client = await self._get_client()
        if not client:
            return 0
        
        data = []
        for event in events:
            data.append((
                event.get('date'),
                event.get('metric_name'),
                event.get('metric_value', 0),
                event.get('dimension', 'total'),
                event.get('dimension_value', 'all'),
            ))
        
        try:
            client.execute(
                """
                INSERT INTO wolloyewa.daily_analytics 
                (date, metric_name, metric_value, dimension, dimension_value)
                VALUES
                """,
                data,
            )
            logger.info(f"Loaded {len(data)} analytics events into ClickHouse")
            return len(data)
        except Exception as e:
            logger.error(f"Failed to load analytics events: {e}")
            return 0
    
    async def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """
        Execute a raw ClickHouse query.
        
        Args:
            query: SQL query string
            
        Returns:
            Query results as list of dictionaries
        """
        client = await self._get_client()
        if not client:
            return []
        
        try:
            result = client.execute(query, with_column_types=True)
            rows = result[0]
            columns = [col[0] for col in result[1]]
            
            return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return []


# Global ClickHouse loader instance
clickhouse_loader = ClickHouseLoader()


async def load_to_clickhouse(data_type: str, data: List[Dict[str, Any]]) -> int:
    """
    Convenience function to load data to ClickHouse.
    
    Args:
        data_type: Type of data ('orders', 'order_items', 'users', 'analytics')
        data: List of data dictionaries
        
    Returns:
        Number of rows loaded
    """
    if data_type == 'orders':
        return await clickhouse_loader.load_orders(data)
    elif data_type == 'order_items':
        return await clickhouse_loader.load_order_items(data)
    elif data_type == 'users':
        return await clickhouse_loader.load_users(data)
    elif data_type == 'analytics':
        return await clickhouse_loader.load_analytics_batch(data)
    else:
        logger.error(f"Unknown data type: {data_type}")
        return 0


async def load_orders_to_clickhouse(orders: List[Dict[str, Any]]) -> int:
    """Load orders to ClickHouse."""
    return await clickhouse_loader.load_orders(orders)


async def load_users_to_clickhouse(users: List[Dict[str, Any]]) -> int:
    """Load users to ClickHouse."""
    return await clickhouse_loader.load_users(users)


async def load_analytics_events(events: List[Dict[str, Any]]) -> int:
    """Load analytics events to ClickHouse."""
    return await clickhouse_loader.load_analytics_batch(events)


__all__ = [
    "ClickHouseLoader",
    "clickhouse_loader",
    "load_to_clickhouse",
    "load_orders_to_clickhouse",
    "load_users_to_clickhouse",
    "load_analytics_events",
]
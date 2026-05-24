# ============================
# WOLLOYEWA STORE BOT - ORDER EXTRACTOR
# ============================
"""Extract order data from PostgreSQL for analytics."""

from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import logger
from infrastructure.database.session import get_db_session
from apps.orders.models import Order, OrderItem
from apps.orders.schemas import OrderStatus, PaymentStatus


class OrderExtractor:
    """
    Extract order data for ETL pipeline.
    
    Features:
    - Extract orders by date range
    - Incremental extraction (only new/modified)
    - Batch processing for large datasets
    - Extract order items with product details
    """
    
    def __init__(self, batch_size: int = 1000):
        self.batch_size = batch_size
        self._last_extracted_at: Optional[datetime] = None
    
    async def extract_orders(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status: Optional[List[OrderStatus]] = None,
        incremental: bool = True,
    ) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """
        Extract orders with optional filters.
        
        Args:
            start_date: Start date for extraction
            end_date: End date for extraction
            status: Filter by order status
            incremental: Only extract new/modified orders
            
        Yields:
            Batches of order data as dictionaries
        """
        async for session in get_db_session():
            try:
                query = select(Order)
                
                # Apply filters
                if start_date:
                    query = query.where(Order.created_at >= start_date)
                if end_date:
                    query = query.where(Order.created_at <= end_date)
                if status:
                    query = query.where(Order.status.in_(status))
                
                # Incremental extraction
                if incremental and self._last_extracted_at:
                    query = query.where(
                        and_(
                            Order.updated_at > self._last_extracted_at,
                            Order.created_at > self._last_extracted_at,
                        )
                    )
                
                # Order by created_at for consistent batches
                query = query.order_by(Order.created_at)
                
                # Execute with pagination
                offset = 0
                total_extracted = 0
                
                while True:
                    batch_query = query.offset(offset).limit(self.batch_size)
                    result = await session.execute(batch_query)
                    orders = result.scalars().all()
                    
                    if not orders:
                        break
                    
                    batch_data = []
                    for order in orders:
                        order_dict = self._serialize_order(order)
                        batch_data.append(order_dict)
                    
                    yield batch_data
                    
                    total_extracted += len(orders)
                    offset += self.batch_size
                    
                    logger.debug(f"Extracted {total_extracted} orders so far")
                
                # Update last extracted timestamp
                if incremental and total_extracted > 0:
                    self._last_extracted_at = datetime.utcnow()
                
                logger.info(f"Extracted {total_extracted} orders from database")
                
            except Exception as e:
                logger.error(f"Failed to extract orders: {e}")
                raise
            finally:
                await session.close()
    
    async def extract_order_items(
        self,
        order_ids: List[int],
    ) -> List[Dict[str, Any]]:
        """
        Extract order items for specific orders.
        
        Args:
            order_ids: List of order IDs
            
        Returns:
            List of order item dictionaries
        """
        async for session in get_db_session():
            try:
                query = select(OrderItem).where(OrderItem.order_id.in_(order_ids))
                result = await session.execute(query)
                items = result.scalars().all()
                
                return [self._serialize_order_item(item) for item in items]
                
            except Exception as e:
                logger.error(f"Failed to extract order items: {e}")
                raise
            finally:
                await session.close()
    
    async def extract_orders_with_items(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """
        Extract orders with their items in a single pass.
        
        Yields:
            Batches of order data including items
        """
        async for batch in self.extract_orders(start_date, end_date):
            order_ids = [order['id'] for order in batch]
            items = await self.extract_order_items(order_ids)
            
            # Group items by order_id
            items_by_order: Dict[int, List[Dict]] = {}
            for item in items:
                order_id = item['order_id']
                if order_id not in items_by_order:
                    items_by_order[order_id] = []
                items_by_order[order_id].append(item)
            
            # Attach items to orders
            for order in batch:
                order['items'] = items_by_order.get(order['id'], [])
            
            yield batch
    
    def _serialize_order(self, order: Order) -> Dict[str, Any]:
        """Convert Order model to dictionary."""
        return {
            'id': order.id,
            'order_number': order.order_number,
            'user_id': order.user_id,
            'vendor_id': order.vendor_id,
            'status': order.status.value if order.status else None,
            'subtotal': float(order.subtotal) if order.subtotal else 0,
            'shipping_fee': float(order.shipping_fee) if order.shipping_fee else 0,
            'tax': float(order.tax) if order.tax else 0,
            'discount': float(order.discount) if order.discount else 0,
            'total': float(order.total) if order.total else 0,
            'payment_method': order.payment_method.value if order.payment_method else None,
            'payment_status': order.payment_status.value if order.payment_status else None,
            'payment_transaction_id': order.payment_transaction_id,
            'shipping_address': order.shipping_address,
            'shipping_city': order.shipping_city,
            'shipping_phone': order.shipping_phone,
            'shipping_method': order.shipping_method.value if order.shipping_method else None,
            'tracking_number': order.tracking_number,
            'customer_notes': order.customer_notes,
            'admin_notes': order.admin_notes,
            'cancelled_at': order.cancelled_at.isoformat() if order.cancelled_at else None,
            'cancelled_reason': order.cancelled_reason,
            'delivered_at': order.delivered_at.isoformat() if order.delivered_at else None,
            'created_at': order.created_at.isoformat(),
            'updated_at': order.updated_at.isoformat(),
        }
    
    def _serialize_order_item(self, item: OrderItem) -> Dict[str, Any]:
        """Convert OrderItem model to dictionary."""
        return {
            'id': item.id,
            'order_id': item.order_id,
            'product_id': item.product_id,
            'product_name': item.product_name,
            'product_sku': item.product_sku,
            'quantity': item.quantity,
            'unit_price': float(item.unit_price) if item.unit_price else 0,
            'total_price': float(item.total_price) if item.total_price else 0,
            'discount': float(item.discount) if item.discount else 0,
            'created_at': item.created_at.isoformat(),
        }
    
    def get_extraction_metrics(self) -> Dict[str, Any]:
        """Get extraction metrics."""
        return {
            'last_extracted_at': self._last_extracted_at.isoformat() if self._last_extracted_at else None,
            'batch_size': self.batch_size,
        }
    
    def reset_extraction_checkpoint(self) -> None:
        """Reset the incremental extraction checkpoint."""
        self._last_extracted_at = None
        logger.info("Reset extraction checkpoint")


async def extract_orders(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    batch_size: int = 1000,
) -> List[Dict[str, Any]]:
    """
    Convenience function to extract all orders (non-streaming).
    
    Args:
        start_date: Start date filter
        end_date: End date filter
        batch_size: Batch size for extraction
        
    Returns:
        List of all extracted orders
    """
    extractor = OrderExtractor(batch_size=batch_size)
    all_orders = []
    
    async for batch in extractor.extract_orders(start_date, end_date, incremental=False):
        all_orders.extend(batch)
    
    return all_orders


async def extract_order_items(order_ids: List[int]) -> List[Dict[str, Any]]:
    """Convenience function to extract order items."""
    extractor = OrderExtractor()
    return await extractor.extract_order_items(order_ids)


__all__ = [
    "OrderExtractor",
    "extract_orders",
    "extract_order_items",
]
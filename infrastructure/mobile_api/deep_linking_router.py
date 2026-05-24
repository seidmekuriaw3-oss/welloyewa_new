# ============================
# WOLLOYEWA STORE BOT - DEEP LINKING ROUTER
# ============================
"""Deep linking router for mobile app navigation."""

from enum import Enum
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from urllib.parse import urlparse, parse_qs

from core.logger import logger


class DeepLinkType(str, Enum):
    """Deep link types."""
    PRODUCT = "product"
    ORDER = "order"
    STORE = "store"
    PROMOTION = "promotion"
    CHECKOUT = "checkout"
    PROFILE = "profile"
    SUPPORT = "support"
    CATEGORY = "category"


@dataclass
class DeepLinkData:
    """Deep link parsed data."""
    
    link_type: DeepLinkType
    params: Dict[str, Any]
    raw_url: str
    screen: str  # Target screen in app


@dataclass
class DeepLinkHandler:
    """Deep link handler registration."""
    
    link_type: DeepLinkType
    handler: Callable
    priority: int = 0


class DeepLinkRouter:
    """
    Deep linking router for mobile apps.
    
    Features:
    - Parse deep links from URLs
    - Route to appropriate screens
    - Generate deep links for sharing
    - Custom handler registration
    """
    
    def __init__(self):
        self._handlers: Dict[DeepLinkType, List[DeepLinkHandler]] = {}
        self._scheme = "wolloyewa"
        self._host = "app.wolloyewa.com"
    
    def register_handler(
        self,
        link_type: DeepLinkType,
        handler: Callable,
        priority: int = 0,
    ) -> None:
        """
        Register a deep link handler.
        
        Args:
            link_type: Type of deep link
            handler: Handler function
            priority: Handler priority (higher = more important)
        """
        if link_type not in self._handlers:
            self._handlers[link_type] = []
        
        self._handlers[link_type].append(DeepLinkHandler(
            link_type=link_type,
            handler=handler,
            priority=priority,
        ))
        
        # Sort by priority
        self._handlers[link_type].sort(key=lambda h: h.priority, reverse=True)
        
        logger.info(f"Registered deep link handler for type: {link_type.value}")
    
    async def handle_deep_link(self, url: str) -> Optional[Any]:
        """
        Handle a deep link URL.
        
        Args:
            url: Deep link URL
            
        Returns:
            Handler response
        """
        # Parse the deep link
        link_data = self.parse_deep_link(url)
        
        if not link_data:
            logger.warning(f"Could not parse deep link: {url}")
            return None
        
        # Find handler
        handlers = self._handlers.get(link_data.link_type, [])
        
        if not handlers:
            logger.warning(f"No handler for deep link type: {link_data.link_type.value}")
            return None
        
        # Execute handler
        for handler in handlers:
            try:
                if handler.handler:
                    result = await handler.handler(link_data)
                    if result:
                        logger.info(f"Deep link handled: {link_data.link_type.value}")
                        return result
            except Exception as e:
                logger.error(f"Deep link handler error: {e}")
        
        return None
    
    def parse_deep_link(self, url: str) -> Optional[DeepLinkData]:
        """
        Parse a deep link URL.
        
        Args:
            url: Deep link URL
            
        Returns:
            Parsed deep link data
        """
        try:
            parsed = urlparse(url)
            
            # Check scheme
            if parsed.scheme != self._scheme:
                return None
            
            # Extract path components
            path_parts = parsed.path.strip('/').split('/')
            
            if not path_parts:
                return None
            
            # Determine link type from path
            link_type_str = path_parts[0]
            try:
                link_type = DeepLinkType(link_type_str)
            except ValueError:
                logger.warning(f"Unknown deep link type: {link_type_str}")
                return None
            
            # Parse query parameters
            params = parse_qs(parsed.query)
            # Convert lists to single values where appropriate
            params = {k: v[0] if len(v) == 1 else v for k, v in params.items()}
            
            # Add path parameters
            if len(path_parts) > 1:
                params["path_id"] = path_parts[1] if len(path_parts) > 1 else None
                params["path_action"] = path_parts[2] if len(path_parts) > 2 else None
            
            # Determine target screen
            screen = self._get_target_screen(link_type, params)
            
            return DeepLinkData(
                link_type=link_type,
                params=params,
                raw_url=url,
                screen=screen,
            )
            
        except Exception as e:
            logger.error(f"Failed to parse deep link: {e}")
            return None
    
    def _get_target_screen(self, link_type: DeepLinkType, params: Dict) -> str:
        """Get target screen name for deep link."""
        screen_map = {
            DeepLinkType.PRODUCT: "ProductDetail",
            DeepLinkType.ORDER: "OrderDetail",
            DeepLinkType.STORE: "StoreHome",
            DeepLinkType.PROMOTION: "PromotionDetail",
            DeepLinkType.CHECKOUT: "Checkout",
            DeepLinkType.PROFILE: "Profile",
            DeepLinkType.SUPPORT: "Support",
            DeepLinkType.CATEGORY: "CategoryProducts",
        }
        
        return screen_map.get(link_type, "Home")
    
    def generate_deep_link(
        self,
        link_type: DeepLinkType,
        params: Dict[str, Any],
    ) -> str:
        """
        Generate a deep link URL.
        
        Args:
            link_type: Type of deep link
            params: Parameters
            
        Returns:
            Deep link URL
        """
        # Build path
        path = f"/{link_type.value}"
        
        if "id" in params:
            path += f"/{params['id']}"
        
        # Build query string
        query_parts = []
        for key, value in params.items():
            if key == "id":
                continue
            if isinstance(value, list):
                for v in value:
                    query_parts.append(f"{key}={v}")
            else:
                query_parts.append(f"{key}={value}")
        
        query_string = "&".join(query_parts)
        
        url = f"{self._scheme}://{self._host}{path}"
        if query_string:
            url += f"?{query_string}"
        
        return url
    
    async def generate_shareable_link(
        self,
        link_type: DeepLinkType,
        params: Dict[str, Any],
    ) -> str:
        """
        Generate a shareable deep link for social media/web.
        
        Args:
            link_type: Type of deep link
            params: Parameters
            
        Returns:
            Web URL that redirects to deep link
        """
        # Generate the actual deep link
        deep_link = self.generate_deep_link(link_type, params)
        
        # In production, return a web URL that redirects to the deep link
        # https://share.wolloyewa.com/link?url={encoded_deep_link}
        
        import urllib.parse
        encoded_link = urllib.parse.quote(deep_link)
        
        return f"https://share.wolloyewa.com/link?url={encoded_link}"


# Global deep link router
deep_link_router = DeepLinkRouter()


def register_deep_link_handler(
    link_type: str,
    handler: Callable,
    priority: int = 0,
) -> None:
    """Register a deep link handler."""
    deep_link_router.register_handler(DeepLinkType(link_type), handler, priority)


async def handle_deep_link(url: str) -> Optional[Any]:
    """Handle a deep link URL."""
    return await deep_link_router.handle_deep_link(url)


def generate_deep_link(link_type: str, params: Dict[str, Any]) -> str:
    """Generate a deep link URL."""
    return deep_link_router.generate_deep_link(DeepLinkType(link_type), params)


def parse_deep_link(url: str) -> Optional[DeepLinkData]:
    """Parse a deep link URL."""
    return deep_link_router.parse_deep_link(url)


__all__ = [
    "DeepLinkRouter",
    "DeepLinkHandler",
    "DeepLinkData",
    "DeepLinkType",
    "deep_link_router",
    "register_deep_link_handler",
    "handle_deep_link",
    "generate_deep_link",
    "parse_deep_link",
]
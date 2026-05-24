# ============================
# WOLLOYEWA STORE BOT - CANNED RESPONSES
# ============================
"""Pre-defined response templates for common support scenarios."""

from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime

from core.logger import logger


class ResponseCategory(str, Enum):
    """Categories of canned responses."""
    GREETING = "greeting"
    ORDER = "order"
    PAYMENT = "payment"
    SHIPPING = "shipping"
    RETURN = "return"
    ACCOUNT = "account"
    TECHNICAL = "technical"
    CLOSING = "closing"
    GENERAL = "general"


@dataclass
class CannedResponse:
    """Canned response template."""
    
    id: str
    title: str
    category: ResponseCategory
    content: str
    content_am: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    usage_count: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_used: Optional[datetime] = None
    is_active: bool = True


class CannedResponseManager:
    """
    Manager for canned response templates.
    
    Features:
    - Pre-defined response templates
    - Multi-language support
    - Usage tracking
    - Search by keyword
    """
    
    def __init__(self):
        self._responses: Dict[str, CannedResponse] = {}
        self._init_default_responses()
    
    def _init_default_responses(self) -> None:
        """Initialize default canned responses."""
        default_responses = [
            CannedResponse(
                id="greeting_1",
                title="Welcome Message",
                category=ResponseCategory.GREETING,
                content="Welcome to Wolloyewa Store! How can I assist you today?",
                content_am="እንኳን ወደ ዎሎየዋ ስቶር በደህና መጡ! ዛሬ እንዴት ልረዳዎት እችላለሁ?",
                tags=["welcome", "hello", "hi"],
            ),
            CannedResponse(
                id="order_status_1",
                title="Order Status Check",
                category=ResponseCategory.ORDER,
                content="I can help you check your order status. Please provide your order number.",
                content_am="የትዕዛዝ ሁኔታዎን ለማየት እረዳዎታለሁ። እባክዎ የትዕዛዝ ቁጥርዎን ይስጡን።",
                tags=["status", "track", "where is my order"],
            ),
            CannedResponse(
                id="payment_failed",
                title="Payment Failed",
                category=ResponseCategory.PAYMENT,
                content="I'm sorry your payment didn't go through. Please try again with a different payment method or contact your bank. If the issue persists, please contact our payment support team.",
                content_am="ክፍያዎ ባለመሳካቱ ይቅርታ። እባክዎ በሌላ የክፍያ መንገድ ይሞክሩ ወይም ባንክዎን ያግኙ። ችግሩ ከቀጠለ እባክዎ የክፍያ ድጋፍ ቡድናችንን ያግኙ።",
                tags=["payment", "failed", "declined", "error"],
            ),
            CannedResponse(
                id="shipping_delay",
                title="Shipping Delay",
                category=ResponseCategory.SHIPPING,
                content="I apologize for the delay in shipping your order. Due to high demand, deliveries may take 2-3 extra business days. Your order will be delivered soon.",
                content_am="የማድረስ መዘግየት ይቅርታ። በከፍተኛ ፍላጎት ምክንያት፣ ማድረስ 2-3 ተጨማሪ የስራ ቀናት ሊወስድ ይችላል። ትዕዛዝዎ በቅርቡ ይደርስዎታል።",
                tags=["delay", "late", "shipping", "delivery"],
            ),
            CannedResponse(
                id="return_policy",
                title="Return Policy",
                category=ResponseCategory.RETURN,
                content="You can return items within 14 days of delivery. Items must be unused and in original packaging. To start a return, please go to Orders > Select Order > Request Return.",
                content_am="ምርቶችን ከደረሱ በኋላ በ14 ቀናት ውስጥ መመለስ ይችላሉ። ምርቶች ባልተጠቀሙበት ሁኔታ እና በዋና ማሸጊያው መሆን አለባቸው። መመለስ ለመጀመር፣ እባክዎ ትዕዛዞች > ትዕዛዝ ምረጥ > መመለስ ጠይቅ የሚለውን ይጫኑ።",
                tags=["return", "refund", "exchange"],
            ),
            CannedResponse(
                id="account_locked",
                title="Account Locked",
                category=ResponseCategory.ACCOUNT,
                content="Your account may be locked due to multiple failed login attempts. Please use the 'Forgot Password' feature or contact support to unlock your account.",
                content_am="መለያዎ በብዙ ያልተሳኩ የመግቢያ ሙከራዎች ምክንያት ተቆልፏል። እባክዎ 'የይለፍ ቃል ረሳሁ' ባህሪን ይጠቀሙ ወይም መለያዎን ለመክፈት ድጋፍ ያግኙ።",
                tags=["locked", "blocked", "account"],
            ),
            CannedResponse(
                id="technical_issue",
                title="Technical Issue",
                category=ResponseCategory.TECHNICAL,
                content="I'm sorry you're experiencing a technical issue. Please try clearing your cache or using a different browser. If the problem continues, our technical team will investigate.",
                tags=["error", "bug", "not working", "issue"],
            ),
            CannedResponse(
                id="closing_1",
                title="Closing Message",
                category=ResponseCategory.CLOSING,
                content="Thank you for contacting Wolloyewa Support. Is there anything else I can help you with?",
                content_am="ዎሎየዋ ድጋፍን ስላገኙ እናመሰግናለን። ሌላ ልረዳዎት የምችልበት ነገር አለ?",
                tags=["bye", "thanks", "closing", "end"],
            ),
        ]
        
        for response in default_responses:
            self._responses[response.id] = response
    
    def add_response(self, response: CannedResponse) -> None:
        """Add a canned response."""
        self._responses[response.id] = response
        logger.info(f"Added canned response: {response.title}")
    
    def get_response(self, response_id: str) -> Optional[CannedResponse]:
        """Get a canned response by ID."""
        return self._responses.get(response_id)
    
    def get_response_by_tags(self, query: str) -> List[CannedResponse]:
        """
        Find responses matching tags.
        
        Args:
            query: Search query
            
        Returns:
            List of matching responses
        """
        query_lower = query.lower()
        matches = []
        
        for response in self._responses.values():
            if not response.is_active:
                continue
            
            # Check tags
            for tag in response.tags:
                if query_lower in tag.lower():
                    matches.append(response)
                    break
            
            # Check title
            if query_lower in response.title.lower():
                if response not in matches:
                    matches.append(response)
        
        # Sort by usage count
        matches.sort(key=lambda r: r.usage_count, reverse=True)
        return matches
    
    def get_responses_by_category(self, category: ResponseCategory) -> List[CannedResponse]:
        """Get responses by category."""
        return [
            r for r in self._responses.values()
            if r.category == category and r.is_active
        ]
    
    def search_responses(self, keyword: str) -> List[CannedResponse]:
        """Search responses by keyword in title or content."""
        keyword_lower = keyword.lower()
        matches = []
        
        for response in self._responses.values():
            if not response.is_active:
                continue
            
            if (keyword_lower in response.title.lower() or
                keyword_lower in response.content.lower() or
                (response.content_am and keyword_lower in response.content_am.lower())):
                matches.append(response)
        
        return matches
    
    def increment_usage(self, response_id: str) -> None:
        """Increment usage count for a response."""
        response = self._responses.get(response_id)
        if response:
            response.usage_count += 1
            response.last_used = datetime.utcnow()


# Global canned response manager
canned_response_manager = CannedResponseManager()


async def get_canned_response(response_id: str) -> Optional[CannedResponse]:
    """Get a canned response by ID."""
    return canned_response_manager.get_response(response_id)


async def search_canned_responses(query: str) -> List[CannedResponse]:
    """Search canned responses."""
    return canned_response_manager.get_response_by_tags(query)


async def get_responses_by_category(category: ResponseCategory) -> List[CannedResponse]:
    """Get responses by category."""
    return canned_response_manager.get_responses_by_category(category)


__all__ = [
    "CannedResponseManager",
    "CannedResponse",
    "ResponseCategory",
    "canned_response_manager",
    "get_canned_response",
    "search_canned_responses",
    "get_responses_by_category",
]
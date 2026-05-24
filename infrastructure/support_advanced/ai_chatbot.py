# ============================
# WOLLOYEWA STORE BOT - AI CHATBOT
# ============================
"""AI-powered chatbot for automated customer support."""

import uuid
from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime

from core.logger import logger


class IntentType(str, Enum):
    """Chatbot intent types."""
    GREETING = "greeting"
    ORDER_STATUS = "order_status"
    TRACKING = "tracking"
    RETURN_POLICY = "return_policy"
    PAYMENT_ISSUE = "payment_issue"
    PRODUCT_INFO = "product_info"
    SHIPPING = "shipping"
    ACCOUNT_ISSUE = "account_issue"
    COMPLAINT = "complaint"
    GENERAL = "general"
    FAREWELL = "farewell"


@dataclass
class ChatMessage:
    """Chat message."""
    
    message_id: str
    user_id: int
    content: str
    is_bot: bool
    intent: Optional[IntentType] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChatSession:
    """Chat session."""
    
    session_id: str
    user_id: int
    messages: List[ChatMessage] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_active: datetime = field(default_factory=datetime.utcnow)
    resolved: bool = False


@dataclass
class ChatResponse:
    """Chatbot response."""
    
    content: str
    intent: IntentType
    confidence: float
    suggested_actions: List[str] = field(default_factory=list)
    requires_human: bool = False


class AIChatbot:
    """
    AI-powered chatbot for customer support.
    
    Features:
    - Intent recognition
    - Context-aware responses
    - Multi-language support (English, Amharic)
    - Escalation to human agents
    """
    
    def __init__(self):
        self._sessions: Dict[str, ChatSession] = {}
        self._intent_responses = self._init_intent_responses()
    
    def _init_intent_responses(self) -> Dict[IntentType, Dict[str, str]]:
        """Initialize intent responses."""
        return {
            IntentType.GREETING: {
                "en": "Hello! How can I help you today?",
                "am": "ሰላም! እንዴት ልረዳዎት እችላለሁ?",
            },
            IntentType.ORDER_STATUS: {
                "en": "To check your order status, please provide your order number.",
                "am": "የትዕዛዝ ሁኔታዎን ለማየት፣ እባክዎ የትዕዛዝ ቁጥርዎን ይስጡን።",
            },
            IntentType.TRACKING: {
                "en": "You can track your order using the tracking number sent to your phone.",
                "am": "ትዕዛዝዎን በስልክዎ በተላከው የክትትል ቁጥር መከታተል ይችላሉ።",
            },
            IntentType.RETURN_POLICY: {
                "en": "Items can be returned within 14 days of delivery in original condition.",
                "am": "ምርቶች ከደረሱ በኋላ በ14 ቀናት ውስጥ ባልተጠቀሙበት ሁኔታ መመለስ ይቻላል።",
            },
            IntentType.PAYMENT_ISSUE: {
                "en": "I can help with payment issues. Please describe the problem you're experiencing.",
                "am": "በክፍያ ችግሮች ልረዳዎት እችላለሁ። እባክዎ ያጋጠመዎትን ችግር ይግለጹ።",
            },
            IntentType.PRODUCT_INFO: {
                "en": "Please provide the product name or ID so I can help you with information.",
                "am": "እባክዎ የምርት ስም ወይም መለያ ቁጥር ይስጡን።",
            },
            IntentType.SHIPPING: {
                "en": "Delivery usually takes 2-5 business days within Addis Ababa, and 5-10 days for other cities.",
                "am": "ማድረስ በአዲስ አበባ ውስጥ 2-5 የስራ ቀናት፣ ለሌሎች ከተሞች ደግሞ 5-10 ቀናት ይወስዳል።",
            },
            IntentType.ACCOUNT_ISSUE: {
                "en": "I can help with account issues. Please describe the problem with your account.",
                "am": "በአካውንት ችግሮች ልረዳዎት እችላለሁ። እባክዎ ችግሩን ይግለጹ።",
            },
            IntentType.COMPLAINT: {
                "en": "I'm sorry to hear that. I'll connect you with a support agent who can help.",
                "am": "ይህን በመስማቴ አዝናለሁ። እርስዎን ሊረዳዎ ከሚችል የድጋፍ ባለሙያ ጋር አገናኛለሁ።",
            },
            IntentType.FAREWELL: {
                "en": "Thank you for chatting with us! Have a great day!",
                "am": "ከእኛ ጋር ስለተወያዩ እናመሰግናለን! መልካም ቀን ይሁንላችሁ!",
            },
            IntentType.GENERAL: {
                "en": "I'm here to help. Could you please provide more details about your question?",
                "am": "ለመርዳት እዚህ አለሁ። እባክዎ ስለጥያቄዎ ተጨማሪ መረጃ ይስጡን።",
            },
        }
    
    def _detect_intent(self, message: str) -> tuple[IntentType, float]:
        """
        Detect intent from user message.
        
        Args:
            message: User message
            
        Returns:
            Tuple of (intent, confidence)
        """
        message_lower = message.lower()
        
        intent_keywords = {
            IntentType.GREETING: ["hello", "hi", "hey", "ሰላም", "ታዲያስ"],
            IntentType.ORDER_STATUS: ["order", "status", "ትዕዛዝ", "ሁኔታ"],
            IntentType.TRACKING: ["track", "tracking", "ክትትል", "የት ደረሰ"],
            IntentType.RETURN_POLICY: ["return", "refund", "መመለስ", "ተመላሽ"],
            IntentType.PAYMENT_ISSUE: ["payment", "pay", "chapa", "telebirr", "ክፍያ"],
            IntentType.PRODUCT_INFO: ["product", "item", "ምርት", "እቃ"],
            IntentType.SHIPPING: ["shipping", "delivery", "ማድረስ", "ማጓጓዝ"],
            IntentType.ACCOUNT_ISSUE: ["account", "login", "password", "አካውንት", "መግቢያ"],
            IntentType.COMPLAINT: ["complaint", "issue", "problem", "ቅሬታ", "ችግር", "አልወደድኩትም"],
            IntentType.FAREWELL: ["bye", "goodbye", "ቻው", "ደህና ሁን"],
        }
        
        best_intent = IntentType.GENERAL
        best_score = 0
        
        for intent, keywords in intent_keywords.items():
            score = sum(1 for kw in keywords if kw in message_lower)
            if score > best_score:
                best_score = score
                best_intent = intent
        
        confidence = min(best_score / 3, 0.95) if best_score > 0 else 0.3
        
        return best_intent, confidence
    
    async def get_response(
        self,
        user_id: int,
        message: str,
        language: str = "en",
        session_id: Optional[str] = None,
    ) -> ChatResponse:
        """
        Get chatbot response.
        
        Args:
            user_id: User ID
            message: User message
            language: Language code (en, am)
            session_id: Existing session ID
        
        Returns:
            ChatResponse
        """
        # Detect intent
        intent, confidence = self._detect_intent(message)
        
        # Get response content
        responses = self._intent_responses.get(intent, self._intent_responses[IntentType.GENERAL])
        content = responses.get(language, responses["en"])
        
        # Check if human intervention needed
        requires_human = intent == IntentType.COMPLAINT or confidence < 0.4
        
        # Get or create session
        if not session_id:
            session_id = str(uuid.uuid4())
            session = ChatSession(session_id=session_id, user_id=user_id)
            self._sessions[session_id] = session
        else:
            session = self._sessions.get(session_id)
            if not session:
                session = ChatSession(session_id=session_id, user_id=user_id)
                self._sessions[session_id] = session
        
        # Add messages to session
        user_message = ChatMessage(
            message_id=str(uuid.uuid4()),
            user_id=user_id,
            content=message,
            is_bot=False,
            intent=intent,
        )
        session.messages.append(user_message)
        
        bot_message = ChatMessage(
            message_id=str(uuid.uuid4()),
            user_id=user_id,
            content=content,
            is_bot=True,
            intent=intent,
        )
        session.messages.append(bot_message)
        session.last_active = datetime.utcnow()
        
        # Determine suggested actions
        suggested_actions = []
        if intent == IntentType.ORDER_STATUS:
            suggested_actions = ["Provide order number"]
        elif intent == IntentType.RETURN_POLICY:
            suggested_actions = ["Start return process", "View policy details"]
        elif intent == IntentType.PAYMENT_ISSUE:
            suggested_actions = ["Contact payment support", "Try alternative payment"]
        
        return ChatResponse(
            content=content,
            intent=intent,
            confidence=confidence,
            suggested_actions=suggested_actions,
            requires_human=requires_human,
        )
    
    async def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get chat session by ID."""
        return self._sessions.get(session_id)
    
    async def resolve_session(self, session_id: str) -> bool:
        """Mark a session as resolved."""
        session = self._sessions.get(session_id)
        if session:
            session.resolved = True
            logger.info(f"Chat session {session_id} resolved")
            return True
        return False


# Global chatbot instance
ai_chatbot = AIChatbot()


async def get_chatbot_response(
    user_id: int,
    message: str,
    language: str = "en",
    session_id: Optional[str] = None,
) -> ChatResponse:
    """Get chatbot response."""
    return await ai_chatbot.get_response(user_id, message, language, session_id)


async def create_chat_session(user_id: int) -> str:
    """Create a new chat session."""
    session_id = str(uuid.uuid4())
    session = ChatSession(session_id=session_id, user_id=user_id)
    ai_chatbot._sessions[session_id] = session
    return session_id


async def get_chat_history(session_id: str) -> List[ChatMessage]:
    """Get chat history for a session."""
    session = await ai_chatbot.get_session(session_id)
    return session.messages if session else []


__all__ = [
    "AIChatbot",
    "ChatMessage",
    "ChatSession",
    "ChatResponse",
    "IntentType",
    "ai_chatbot",
    "get_chatbot_response",
    "create_chat_session",
    "get_chat_history",
]
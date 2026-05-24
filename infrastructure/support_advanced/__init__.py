# ============================
# WOLLOYEWA STORE BOT - ADVANCED SUPPORT MODULE
# ============================
"""Advanced customer support features including AI chatbot and sentiment analysis."""

from infrastructure.support_advanced.ai_chatbot import (
    AIChatbot,
    ChatMessage,
    ChatSession,
    ChatResponse,
    get_chatbot_response,
    create_chat_session,
    get_chat_history,
    IntentType,
)
from infrastructure.support_advanced.sentiment_analyzer import (
    SentimentAnalyzer,
    SentimentResult,
    SentimentScore,
    analyze_sentiment,
    analyze_ticket_sentiment,
    get_sentiment_stats,
)
from infrastructure.support_advanced.auto_ticket_routing import (
    AutoTicketRouter,
    RoutingRule,
    TicketRouter,
    route_ticket,
    get_routing_stats,
    assign_best_agent,
    RoutingStrategy,
)
from infrastructure.support_advanced.canned_responses import (
    CannedResponseManager,
    CannedResponse,
    ResponseCategory,
    get_canned_response,
    search_canned_responses,
    get_responses_by_category,
)
from infrastructure.support_advanced.sla_monitor import (
    SLAMonitor,
    SLAMetric,
    SLAViolation,
    monitor_sla,
    check_sla_compliance,
    get_sla_report,
    SLATracker,
)
from infrastructure.support_advanced.customer_satisfaction import (
    CustomerSatisfaction,
    SatisfactionSurvey,
    SurveyResponse,
    send_satisfaction_survey,
    collect_feedback,
    get_csat_score,
    get_satisfaction_stats,
)

__all__ = [
    # AI Chatbot
    "AIChatbot",
    "ChatMessage",
    "ChatSession",
    "ChatResponse",
    "get_chatbot_response",
    "create_chat_session",
    "get_chat_history",
    "IntentType",
    # Sentiment Analysis
    "SentimentAnalyzer",
    "SentimentResult",
    "SentimentScore",
    "analyze_sentiment",
    "analyze_ticket_sentiment",
    "get_sentiment_stats",
    # Auto Ticket Routing
    "AutoTicketRouter",
    "RoutingRule",
    "TicketRouter",
    "route_ticket",
    "get_routing_stats",
    "assign_best_agent",
    "RoutingStrategy",
    # Canned Responses
    "CannedResponseManager",
    "CannedResponse",
    "ResponseCategory",
    "get_canned_response",
    "search_canned_responses",
    "get_responses_by_category",
    # SLA Monitor
    "SLAMonitor",
    "SLAMetric",
    "SLAViolation",
    "monitor_sla",
    "check_sla_compliance",
    "get_sla_report",
    "SLATracker",
    # Customer Satisfaction
    "CustomerSatisfaction",
    "SatisfactionSurvey",
    "SurveyResponse",
    "send_satisfaction_survey",
    "collect_feedback",
    "get_csat_score",
    "get_satisfaction_stats",
]
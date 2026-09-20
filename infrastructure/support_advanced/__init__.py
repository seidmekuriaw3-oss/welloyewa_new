# ============================
# WOLLOYEWA STORE BOT - ADVANCED SUPPORT MODULE
# ============================
"""Advanced customer support features including AI chatbot and sentiment analysis."""

from infrastructure.support_advanced.ai_chatbot import (
    AIChatbot,
    ChatMessage,
    ChatResponse,
    ChatSession,
    IntentType,
    create_chat_session,
    get_chat_history,
    get_chatbot_response,
)
from infrastructure.support_advanced.auto_ticket_routing import (
    AutoTicketRouter,
    RoutingRule,
    RoutingStrategy,
    TicketRouter,
    assign_best_agent,
    get_routing_stats,
    route_ticket,
)
from infrastructure.support_advanced.canned_responses import (
    CannedResponse,
    CannedResponseManager,
    ResponseCategory,
    get_canned_response,
    get_responses_by_category,
    search_canned_responses,
)
from infrastructure.support_advanced.customer_satisfaction import (
    CustomerSatisfaction,
    SatisfactionSurvey,
    SurveyResponse,
    collect_feedback,
    get_csat_score,
    get_satisfaction_stats,
    send_satisfaction_survey,
)
from infrastructure.support_advanced.sentiment_analyzer import (
    SentimentAnalyzer,
    SentimentResult,
    SentimentScore,
    analyze_sentiment,
    analyze_ticket_sentiment,
    get_sentiment_stats,
)
from infrastructure.support_advanced.sla_monitor import (
    SLAMetric,
    SLAMonitor,
    SLATracker,
    SLAViolation,
    check_sla_compliance,
    get_sla_report,
    monitor_sla,
)

__all__ = [
    # AI Chatbot
    "AIChatbot",
    # Auto Ticket Routing
    "AutoTicketRouter",
    "CannedResponse",
    # Canned Responses
    "CannedResponseManager",
    "ChatMessage",
    "ChatResponse",
    "ChatSession",
    # Customer Satisfaction
    "CustomerSatisfaction",
    "IntentType",
    "ResponseCategory",
    "RoutingRule",
    "RoutingStrategy",
    "SLAMetric",
    # SLA Monitor
    "SLAMonitor",
    "SLATracker",
    "SLAViolation",
    "SatisfactionSurvey",
    # Sentiment Analysis
    "SentimentAnalyzer",
    "SentimentResult",
    "SentimentScore",
    "SurveyResponse",
    "TicketRouter",
    "analyze_sentiment",
    "analyze_ticket_sentiment",
    "assign_best_agent",
    "check_sla_compliance",
    "collect_feedback",
    "create_chat_session",
    "get_canned_response",
    "get_chat_history",
    "get_chatbot_response",
    "get_csat_score",
    "get_responses_by_category",
    "get_routing_stats",
    "get_satisfaction_stats",
    "get_sentiment_stats",
    "get_sla_report",
    "monitor_sla",
    "route_ticket",
    "search_canned_responses",
    "send_satisfaction_survey",
]

# ============================
# WOLLOYEWA STORE BOT - CUSTOMER SATISFACTION
# ============================
"""Customer satisfaction tracking and survey management."""

from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from core.logger import logger


class SatisfactionRating(str, Enum):
    """Customer satisfaction ratings."""
    VERY_UNSATISFIED = "very_unsatisfied"
    UNSATISFIED = "unsatisfied"
    NEUTRAL = "neutral"
    SATISFIED = "satisfied"
    VERY_SATISFIED = "very_satisfied"


@dataclass
class SurveyResponse:
    """Customer survey response."""
    
    response_id: str
    user_id: int
    ticket_id: Optional[int] = None
    order_id: Optional[int] = None
    rating: Optional[SatisfactionRating] = None
    rating_value: int = 0  # 1-5
    feedback: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SatisfactionSurvey:
    """Survey definition."""
    
    survey_id: str
    name: str
    questions: List[str]
    is_active: bool = True
    target_type: str = "ticket"  # ticket, order, general


class CustomerSatisfaction:
    """
    Customer satisfaction tracking.
    
    Features:
    - Post-resolution surveys
    - CSAT score calculation
    - Feedback collection
    - Trend analysis
    """
    
    def __init__(self):
        self._responses: List[SurveyResponse] = []
        self._surveys: Dict[str, SatisfactionSurvey] = {}
        self._init_default_surveys()
    
    def _init_default_surveys(self) -> None:
        """Initialize default surveys."""
        ticket_survey = SatisfactionSurvey(
            survey_id="ticket_satisfaction",
            name="Ticket Resolution Satisfaction",
            questions=[
                "How satisfied are you with the resolution of your issue?",
                "How would you rate the response time?",
                "How likely are you to use our support again?",
            ],
            target_type="ticket",
        )
        self._surveys[ticket_survey.survey_id] = ticket_survey
        
        order_survey = SatisfactionSurvey(
            survey_id="order_satisfaction",
            name="Order Experience",
            questions=[
                "How satisfied are you with your purchase?",
                "How would you rate the delivery experience?",
                "Would you recommend this seller to others?",
            ],
            target_type="order",
        )
        self._surveys[order_survey.survey_id] = order_survey
    
    def create_survey(self, survey: SatisfactionSurvey) -> None:
        """Create a new survey."""
        self._surveys[survey.survey_id] = survey
        logger.info(f"Created survey: {survey.name}")
    
    def add_response(self, response: SurveyResponse) -> None:
        """Add a survey response."""
        self._responses.append(response)
        logger.info(f"Added survey response from user {response.user_id}: rating {response.rating_value}/5")
    
    async def send_satisfaction_survey(
        self,
        user_id: int,
        target_type: str,
        target_id: int,
        survey_id: str = "ticket_satisfaction",
    ) -> str:
        """
        Send a satisfaction survey to a user.
        
        Args:
            user_id: User ID
            target_type: Type of target (ticket, order)
            target_id: Target ID
            survey_id: Survey ID
            
        Returns:
            Response ID
        """
        import uuid
        
        survey = self._surveys.get(survey_id)
        if not survey:
            raise ValueError(f"Survey not found: {survey_id}")
        
        response_id = str(uuid.uuid4())
        
        # Create placeholder response
        response = SurveyResponse(
            response_id=response_id,
            user_id=user_id,
            ticket_id=target_id if target_type == "ticket" else None,
            order_id=target_id if target_type == "order" else None,
        )
        
        self._responses.append(response)
        
        # In production, send survey via Telegram or email
        logger.info(f"Sent survey {survey_id} to user {user_id} for {target_type} {target_id}")
        
        return response_id
    
    async def collect_feedback(
        self,
        response_id: str,
        rating: int,
        feedback: Optional[str] = None,
    ) -> bool:
        """
        Collect feedback from user.
        
        Args:
            response_id: Survey response ID
            rating: Rating (1-5)
            feedback: Optional feedback text
            
        Returns:
            True if feedback recorded
        """
        for response in self._responses:
            if response.response_id == response_id:
                response.rating_value = rating
                response.feedback = feedback
                response.resolved_at = datetime.utcnow()
                
                # Map numeric rating to enum
                if rating >= 4:
                    response.rating = SatisfactionRating.VERY_SATISFIED
                elif rating >= 3:
                    response.rating = SatisfactionRating.SATISFIED
                elif rating == 3:
                    response.rating = SatisfactionRating.NEUTRAL
                elif rating == 2:
                    response.rating = SatisfactionRating.UNSATISFIED
                else:
                    response.rating = SatisfactionRating.VERY_UNSATISFIED
                
                logger.info(f"Collected feedback for response {response_id}: rating {rating}/5")
                return True
        
        logger.warning(f"Response not found: {response_id}")
        return False
    
    def get_csat_score(
        self,
        days: int = 30,
        target_type: Optional[str] = None,
    ) -> float:
        """
        Calculate CSAT score (percentage of satisfied customers).
        
        Args:
            days: Number of days to look back
            target_type: Filter by target type
            
        Returns:
            CSAT score (0-100)
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        responses = [
            r for r in self._responses
            if r.created_at >= cutoff and r.rating_value > 0
        ]
        
        if target_type:
            if target_type == "ticket":
                responses = [r for r in responses if r.ticket_id]
            elif target_type == "order":
                responses = [r for r in responses if r.order_id]
        
        if not responses:
            return 0.0
        
        # Count satisfied responses (rating 4 or 5)
        satisfied = sum(1 for r in responses if r.rating_value >= 4)
        
        return round((satisfied / len(responses)) * 100, 1)
    
    def get_satisfaction_stats(self, days: int = 30) -> Dict[str, Any]:
        """
        Get satisfaction statistics.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Satisfaction statistics
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        responses = [r for r in self._responses if r.created_at >= cutoff]
        
        if not responses:
            return {
                "total_responses": 0,
                "average_rating": 0,
                "csat_score": 0,
                "rating_distribution": {},
            }
        
        rating_distribution = {
            "5": 0,
            "4": 0,
            "3": 0,
            "2": 0,
            "1": 0,
        }
        
        total_rating = 0
        for r in responses:
            rating_distribution[str(r.rating_value)] = rating_distribution.get(str(r.rating_value), 0) + 1
            total_rating += r.rating_value
        
        average_rating = total_rating / len(responses)
        csat_score = self.get_csat_score(days)
        
        return {
            "total_responses": len(responses),
            "average_rating": round(average_rating, 2),
            "csat_score": csat_score,
            "rating_distribution": rating_distribution,
            "ticket_satisfaction": self.get_csat_score(days, "ticket"),
            "order_satisfaction": self.get_csat_score(days, "order"),
        }
    
    def get_recent_feedback(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get recent feedback with low ratings.
        
        Args:
            limit: Maximum number of feedback items
            
        Returns:
            List of feedback
        """
        feedback_items = [
            {
                "user_id": r.user_id,
                "rating": r.rating_value,
                "feedback": r.feedback,
                "created_at": r.created_at.isoformat(),
                "ticket_id": r.ticket_id,
                "order_id": r.order_id,
            }
            for r in self._responses
            if r.feedback and r.rating_value <= 3
        ]
        
        # Sort by created_at descending
        feedback_items.sort(key=lambda x: x["created_at"], reverse=True)
        
        return feedback_items[:limit]


# Global customer satisfaction manager
customer_satisfaction = CustomerSatisfaction()


async def send_satisfaction_survey(
    user_id: int,
    target_type: str,
    target_id: int,
) -> str:
    """Send satisfaction survey to user."""
    return await customer_satisfaction.send_satisfaction_survey(user_id, target_type, target_id)


async def collect_feedback(response_id: str, rating: int, feedback: Optional[str] = None) -> bool:
    """Collect feedback from user."""
    return await customer_satisfaction.collect_feedback(response_id, rating, feedback)


async def get_csat_score(days: int = 30) -> float:
    """Get CSAT score."""
    return customer_satisfaction.get_csat_score(days)


async def get_satisfaction_stats(days: int = 30) -> Dict[str, Any]:
    """Get satisfaction statistics."""
    return customer_satisfaction.get_satisfaction_stats(days)


__all__ = [
    "CustomerSatisfaction",
    "SatisfactionSurvey",
    "SurveyResponse",
    "SatisfactionRating",
    "customer_satisfaction",
    "send_satisfaction_survey",
    "collect_feedback",
    "get_csat_score",
    "get_satisfaction_stats",
]
# ============================
# WOLLOYEWA STORE BOT - CHURN PREDICTOR
# ============================
"""User churn prediction and at-risk user identification."""

import math
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict

from core.logger import logger
from infrastructure.redis.client import get_redis_client


class ChurnRiskLevel(str, Enum):
    """Churn risk levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ChurnPrediction:
    """Churn prediction result for a user."""
    
    user_id: int
    risk_level: ChurnRiskLevel
    churn_probability: float  # 0-1
    factors: List[str]
    recommended_actions: List[str]
    predicted_churn_date: Optional[datetime] = None


class ChurnPredictor:
    """
    User churn prediction engine.
    
    Features:
    - Predict user churn probability
    - Identify at-risk users
    - Provide retention recommendations
    - Track churn metrics
    """
    
    def __init__(self):
        self._redis = None
        self._user_activity: Dict[int, Dict[str, Any]] = {}
        self._churn_history: List[Dict[str, Any]] = []
        
        # Weights for different factors
        self._weights = {
            'last_active_days': 0.25,
            'purchase_frequency': 0.20,
            'avg_order_value': 0.10,
            'support_tickets': 0.15,
            'product_returns': 0.15,
            'engagement_score': 0.15,
        }
    
    async def _get_redis(self):
        """Get Redis client lazily."""
        if self._redis is None:
            self._redis = await get_redis_client()
        return self._redis
    
    async def update_user_activity(self, user_id: int, activity: Dict[str, Any]) -> None:
        """
        Update user activity data for churn prediction.
        
        Args:
            user_id: User ID
            activity: Activity data (last_active, purchases, etc.)
        """
        if user_id not in self._user_activity:
            self._user_activity[user_id] = {}
        
        self._user_activity[user_id].update(activity)
        self._user_activity[user_id]['last_updated'] = datetime.utcnow()
    
    async def calculate_churn_probability(self, user_id: int) -> Tuple[float, List[str]]:
        """
        Calculate churn probability for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Tuple of (probability, list_of_contributing_factors)
        """
        activity = self._user_activity.get(user_id, {})
        
        if not activity:
            return 0.5, ["No activity data available"]
        
        factors = []
        weighted_score = 0.0
        
        # Factor 1: Days since last active
        last_active = activity.get('last_active')
        if last_active:
            if isinstance(last_active, str):
                last_active = datetime.fromisoformat(last_active)
            days_inactive = (datetime.utcnow() - last_active).days
            days_score = min(1.0, days_inactive / 30)  # 30 days = 100% risk
            weighted_score += days_score * self._weights['last_active_days']
            if days_inactive > 7:
                factors.append(f"Inactive for {days_inactive} days")
        
        # Factor 2: Purchase frequency
        purchase_count = activity.get('purchase_count', 0)
        last_purchase = activity.get('last_purchase')
        
        if purchase_count == 0:
            purchase_score = 0.8
            factors.append("No purchase history")
        elif last_purchase:
            if isinstance(last_purchase, str):
                last_purchase = datetime.fromisoformat(last_purchase)
            days_since_purchase = (datetime.utcnow() - last_purchase).days
            if days_since_purchase > 60:
                purchase_score = 0.7
                factors.append(f"No purchase in {days_since_purchase} days")
            else:
                purchase_score = max(0, 1 - (days_since_purchase / 60))
        else:
            purchase_score = 0.5
        
        weighted_score += purchase_score * self._weights['purchase_frequency']
        
        # Factor 3: Average order value
        avg_order_value = activity.get('avg_order_value', 0)
        if avg_order_value > 0:
            if avg_order_value < 100:  # Low value customers more likely to churn
                order_score = 0.6
                factors.append("Low average order value")
            else:
                order_score = 0.3
        else:
            order_score = 0.5
        
        weighted_score += order_score * self._weights['avg_order_value']
        
        # Factor 4: Support tickets
        support_tickets = activity.get('support_tickets', 0)
        if support_tickets > 3:
            ticket_score = min(1.0, support_tickets / 10)
            factors.append(f"Multiple support tickets ({support_tickets})")
        else:
            ticket_score = support_tickets * 0.1
        
        weighted_score += ticket_score * self._weights['support_tickets']
        
        # Factor 5: Product returns
        return_count = activity.get('return_count', 0)
        if return_count > 0:
            return_score = min(0.8, return_count * 0.2)
            factors.append(f"Product returns ({return_count})")
        else:
            return_score = 0.0
        
        weighted_score += return_score * self._weights['product_returns']
        
        # Factor 6: Engagement score (email opens, notifications clicks)
        engagement = activity.get('engagement_score', 0.5)
        engagement_score = 1 - engagement  # Lower engagement = higher churn risk
        if engagement < 0.3:
            factors.append("Low engagement with notifications")
        weighted_score += engagement_score * self._weights['engagement_score']
        
        # Ensure probability is between 0 and 1
        probability = min(1.0, max(0.0, weighted_score))
        
        return probability, factors
    
    async def predict_churn(self, user_id: int) -> ChurnPrediction:
        """
        Predict churn for a specific user.
        
        Args:
            user_id: User ID
            
        Returns:
            ChurnPrediction object
        """
        probability, factors = await self.calculate_churn_probability(user_id)
        
        # Determine risk level
        if probability >= 0.7:
            risk_level = ChurnRiskLevel.CRITICAL
        elif probability >= 0.5:
            risk_level = ChurnRiskLevel.HIGH
        elif probability >= 0.3:
            risk_level = ChurnRiskLevel.MEDIUM
        else:
            risk_level = ChurnRiskLevel.LOW
        
        # Generate recommended actions
        recommended_actions = []
        
        if risk_level in [ChurnRiskLevel.HIGH, ChurnRiskLevel.CRITICAL]:
            if "Inactive" in str(factors):
                recommended_actions.append("Send re-engagement campaign with discount")
            if "No purchase history" in str(factors):
                recommended_actions.append("Offer first-purchase discount")
            if "Low average order value" in str(factors):
                recommended_actions.append("Recommend higher-value products with bundle deals")
            if "Multiple support tickets" in str(factors):
                recommended_actions.append("Proactive customer support outreach")
            if "Low engagement" in str(factors):
                recommended_actions.append("Personalized notification preferences survey")
        
        # Predict potential churn date (if probability > 0.5)
        predicted_date = None
        if probability > 0.5:
            days_to_churn = int((1 - probability) * 60) + 7
            predicted_date = datetime.utcnow() + timedelta(days=days_to_churn)
        
        return ChurnPrediction(
            user_id=user_id,
            risk_level=risk_level,
            churn_probability=round(probability, 3),
            factors=factors,
            recommended_actions=recommended_actions,
            predicted_churn_date=predicted_date,
        )
    
    async def get_at_risk_users(
        self,
        min_probability: float = 0.5,
        limit: int = 100,
    ) -> List[ChurnPrediction]:
        """
        Get users at risk of churning.
        
        Args:
            min_probability: Minimum churn probability threshold
            limit: Maximum number of users to return
            
        Returns:
            List of churn predictions for at-risk users
        """
        predictions = []
        
        for user_id in self._user_activity:
            prediction = await self.predict_churn(user_id)
            if prediction.churn_probability >= min_probability:
                predictions.append(prediction)
        
        # Sort by probability (highest first)
        predictions.sort(key=lambda x: x.churn_probability, reverse=True)
        
        return predictions[:limit]
    
    async def get_churn_metrics(self) -> Dict[str, Any]:
        """
        Get overall churn metrics.
        
        Returns:
            Dictionary with churn statistics
        """
        predictions = []
        for user_id in self._user_activity:
            prediction = await self.predict_churn(user_id)
            predictions.append(prediction)
        
        if not predictions:
            return {"total_users": 0, "at_risk_count": 0, "avg_churn_probability": 0}
        
        at_risk = [p for p in predictions if p.churn_probability >= 0.5]
        high_risk = [p for p in predictions if p.risk_level == ChurnRiskLevel.HIGH]
        critical_risk = [p for p in predictions if p.risk_level == ChurnRiskLevel.CRITICAL]
        
        avg_probability = sum(p.churn_probability for p in predictions) / len(predictions)
        
        return {
            "total_users": len(predictions),
            "at_risk_count": len(at_risk),
            "high_risk_count": len(high_risk),
            "critical_risk_count": len(critical_risk),
            "avg_churn_probability": round(avg_probability, 3),
            "risk_distribution": {
                "low": len([p for p in predictions if p.risk_level == ChurnRiskLevel.LOW]),
                "medium": len([p for p in predictions if p.risk_level == ChurnRiskLevel.MEDIUM]),
                "high": len(high_risk),
                "critical": len(critical_risk),
            },
        }
    
    async def record_churn(self, user_id: int, reason: Optional[str] = None) -> None:
        """
        Record that a user has churned.
        
        Args:
            user_id: User ID
            reason: Reason for churn (if known)
        """
        self._churn_history.append({
            "user_id": user_id,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        # Remove from active users
        if user_id in self._user_activity:
            del self._user_activity[user_id]
        
        logger.info(f"Recorded churn for user {user_id}: {reason or 'No reason provided'}")
    
    async def get_churn_rate(self, days: int = 30) -> float:
        """
        Calculate churn rate over a period.
        
        Args:
            days: Number of days to look back
            
        Returns:
            Churn rate as percentage
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        recent_churns = [
            c for c in self._churn_history
            if datetime.fromisoformat(c["timestamp"]) >= cutoff
        ]
        
        total_active = len(self._user_activity)
        churned_count = len(recent_churns)
        
        if total_active + churned_count == 0:
            return 0.0
        
        return (churned_count / (total_active + churned_count)) * 100


# Global churn predictor instance
churn_predictor = ChurnPredictor()


async def predict_user_churn(user_id: int) -> ChurnPrediction:
    """Convenience function to predict user churn."""
    return await churn_predictor.predict_churn(user_id)


async def get_at_risk_users(limit: int = 100) -> List[ChurnPrediction]:
    """Convenience function to get at-risk users."""
    return await churn_predictor.get_at_risk_users(limit=limit)


__all__ = [
    "ChurnPredictor",
    "ChurnPrediction",
    "ChurnRiskLevel",
    "churn_predictor",
    "predict_user_churn",
    "get_at_risk_users",
]
# ============================
# WOLLOYEWA STORE BOT - A/B TESTING FRAMEWORK
# ============================
"""A/B testing framework for experimenting with features and UI changes."""

import hashlib
import math
from enum import Enum
from typing import Dict, Any, List, Optional, Union, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict

from core.logger import logger
from infrastructure.redis.client import get_redis_client


class ExperimentStatus(str, Enum):
    """Status of an A/B test experiment."""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ExperimentVariant(str, Enum):
    """Variants in an A/B test."""
    CONTROL = "control"
    VARIANT_A = "variant_a"
    VARIANT_B = "variant_b"
    VARIANT_C = "variant_c"
    VARIANT_D = "variant_d"


@dataclass
class Experiment:
    """A/B test experiment configuration."""
    
    id: str
    name: str
    description: str
    variants: List[ExperimentVariant]
    traffic_allocation: Dict[ExperimentVariant, float]  # Percentage of users
    status: ExperimentStatus = ExperimentStatus.DRAFT
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    target_metric: str = "conversion_rate"  # conversion_rate, revenue, click_through, etc.
    minimum_sample_size: int = 1000
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        # Ensure traffic allocation sums to 100%
        if self.variants:
            total = sum(self.traffic_allocation.values())
            if abs(total - 100) > 0.01:
                raise ValueError(f"Traffic allocation must sum to 100%, got {total}%")


@dataclass
class ExperimentConversion:
    """Conversion event for an experiment."""
    
    experiment_id: str
    user_id: int
    variant: ExperimentVariant
    metric_name: str
    value: float = 1.0
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ExperimentResult:
    """Statistical results of an experiment."""
    
    experiment_id: str
    variant: ExperimentVariant
    sample_size: int
    conversions: int
    conversion_rate: float
    lift_vs_control: Optional[float] = None
    is_significant: bool = False
    p_value: Optional[float] = None
    confidence_interval: Optional[Tuple[float, float]] = None


class ABTestingFramework:
    """
    A/B testing framework for running experiments.
    
    Features:
    - User segmentation and assignment
    - Conversion tracking
    - Statistical significance calculation
    - Experiment management
    """
    
    def __init__(self):
        self._redis = None
        self._experiments: Dict[str, Experiment] = {}
        self._user_assignments: Dict[str, Dict[int, ExperimentVariant]] = defaultdict(dict)
        self._conversions: List[ExperimentConversion] = []
        
        # Default experiments
        self._init_default_experiments()
    
    def _init_default_experiments(self) -> None:
        """Initialize default A/B tests."""
        # Example: Checkout button color test
        checkout_button_test = Experiment(
            id="checkout_button_color",
            name="Checkout Button Color Test",
            description="Testing green vs blue checkout button",
            variants=[ExperimentVariant.CONTROL, ExperimentVariant.VARIANT_A],
            traffic_allocation={
                ExperimentVariant.CONTROL: 50,
                ExperimentVariant.VARIANT_A: 50,
            },
            target_metric="conversion_rate",
        )
        self._experiments[checkout_button_test.id] = checkout_button_test
        
        # Example: Free shipping threshold test
        shipping_test = Experiment(
            id="shipping_threshold",
            name="Free Shipping Threshold Test",
            description="Testing different free shipping thresholds",
            variants=[ExperimentVariant.CONTROL, ExperimentVariant.VARIANT_A, ExperimentVariant.VARIANT_B],
            traffic_allocation={
                ExperimentVariant.CONTROL: 34,
                ExperimentVariant.VARIANT_A: 33,
                ExperimentVariant.VARIANT_B: 33,
            },
            target_metric="average_order_value",
        )
        self._experiments[shipping_test.id] = shipping_test
    
    async def _get_redis(self):
        """Get Redis client lazily."""
        if self._redis is None:
            self._redis = await get_redis_client()
        return self._redis
    
    def create_experiment(self, experiment: Experiment) -> None:
        """Create a new A/B test experiment."""
        self._experiments[experiment.id] = experiment
        logger.info(f"Created experiment: {experiment.name} (ID: {experiment.id})")
    
    def get_experiment(self, experiment_id: str) -> Optional[Experiment]:
        """Get experiment by ID."""
        return self._experiments.get(experiment_id)
    
    def update_experiment_status(self, experiment_id: str, status: ExperimentStatus) -> bool:
        """Update experiment status."""
        if experiment_id in self._experiments:
            self._experiments[experiment_id].status = status
            logger.info(f"Experiment {experiment_id} status updated to {status.value}")
            return True
        return False
    
    def assign_variant(self, experiment_id: str, user_id: int) -> Optional[ExperimentVariant]:
        """
        Assign a user to a variant for an experiment.
        
        Uses consistent hashing to ensure same user always gets same variant.
        
        Args:
            experiment_id: Experiment ID
            user_id: User ID
            
        Returns:
            Assigned variant
        """
        experiment = self._experiments.get(experiment_id)
        
        if not experiment or experiment.status != ExperimentStatus.ACTIVE:
            return None
        
        # Check if user already assigned
        if user_id in self._user_assignments[experiment_id]:
            return self._user_assignments[experiment_id][user_id]
        
        # Consistent hashing for user assignment
        hash_key = f"{experiment_id}:{user_id}"
        hash_value = int(hashlib.md5(hash_key.encode()).hexdigest()[:8], 16)
        hash_percent = hash_value % 100
        
        # Determine variant based on traffic allocation
        cumulative = 0
        for variant, allocation in experiment.traffic_allocation.items():
            cumulative += allocation
            if hash_percent < cumulative:
                self._user_assignments[experiment_id][user_id] = variant
                logger.debug(f"Assigned user {user_id} to {variant.value} for experiment {experiment_id}")
                return variant
        
        # Fallback to control
        return ExperimentVariant.CONTROL
    
    async def track_conversion(
        self,
        experiment_id: str,
        user_id: int,
        metric_name: str,
        value: float = 1.0,
    ) -> None:
        """
        Track a conversion for an experiment.
        
        Args:
            experiment_id: Experiment ID
            user_id: User ID
            metric_name: Name of the metric (e.g., 'purchase', 'click')
            value: Value of the conversion (default 1.0)
        """
        experiment = self._experiments.get(experiment_id)
        if not experiment or experiment.status != ExperimentStatus.ACTIVE:
            return
        
        variant = self.assign_variant(experiment_id, user_id)
        if not variant:
            return
        
        conversion = ExperimentConversion(
            experiment_id=experiment_id,
            user_id=user_id,
            variant=variant,
            metric_name=metric_name,
            value=value,
        )
        
        self._conversions.append(conversion)
        
        # Store in Redis for persistence
        try:
            redis = await self._get_redis()
            key = f"ab_test:conv:{experiment_id}:{variant.value}"
            await redis.hincrby(key, metric_name, int(value))
            await redis.hincrby(f"{key}:users", str(user_id), 1)
        except Exception as e:
            logger.error(f"Failed to store conversion in Redis: {e}")
        
        logger.debug(f"Tracked conversion for experiment {experiment_id}, user {user_id}, variant {variant.value}")
    
    async def get_experiment_results(self, experiment_id: str) -> List[ExperimentResult]:
        """
        Calculate statistical results for an experiment.
        
        Args:
            experiment_id: Experiment ID
            
        Returns:
            List of results per variant
        """
        experiment = self._experiments.get(experiment_id)
        if not experiment:
            return []
        
        # Get conversions for this experiment
        experiment_conversions = [
            c for c in self._conversions
            if c.experiment_id == experiment_id
        ]
        
        # Group by variant
        variant_data: Dict[ExperimentVariant, Dict[str, Any]] = {}
        for variant in experiment.variants:
            variant_data[variant] = {
                "users": set(),
                "conversions": 0,
                "total_value": 0.0,
            }
        
        for conv in experiment_conversions:
            data = variant_data[conv.variant]
            data["users"].add(conv.user_id)
            data["conversions"] += 1
            data["total_value"] += conv.value
        
        # Calculate results
        results = []
        control_data = variant_data.get(ExperimentVariant.CONTROL)
        
        for variant, data in variant_data.items():
            sample_size = len(data["users"])
            conversions = data["conversions"]
            conversion_rate = (conversions / sample_size) if sample_size > 0 else 0
            
            result = ExperimentResult(
                experiment_id=experiment_id,
                variant=variant,
                sample_size=sample_size,
                conversions=conversions,
                conversion_rate=round(conversion_rate * 100, 2),
            )
            
            # Calculate lift vs control
            if control_data and variant != ExperimentVariant.CONTROL:
                control_rate = (control_data["conversions"] / len(control_data["users"])) if len(control_data["users"]) > 0 else 0
                if control_rate > 0:
                    lift = ((conversion_rate - control_rate) / control_rate) * 100
                    result.lift_vs_control = round(lift, 2)
            
            # Calculate statistical significance if sample size is sufficient
            if sample_size >= experiment.minimum_sample_size:
                result.is_significant = self._calculate_significance(
                    conversions, sample_size,
                    control_data["conversions"] if control_data else 0,
                    len(control_data["users"]) if control_data else 0,
                )
            
            results.append(result)
        
        return results
    
    def _calculate_significance(
        self,
        conversions_a: int,
        sample_a: int,
        conversions_b: int,
        sample_b: int,
    ) -> bool:
        """
        Calculate statistical significance using z-test.
        
        Returns:
            True if result is statistically significant (p < 0.05)
        """
        if sample_a == 0 or sample_b == 0:
            return False
        
        rate_a = conversions_a / sample_a
        rate_b = conversions_b / sample_b
        
        # Pooled proportion
        pooled = (conversions_a + conversions_b) / (sample_a + sample_b)
        
        # Standard error
        se = math.sqrt(pooled * (1 - pooled) * (1/sample_a + 1/sample_b))
        
        if se == 0:
            return False
        
        # Z-score
        z_score = abs(rate_a - rate_b) / se
        
        # Check if z-score > 1.96 (95% confidence)
        return z_score > 1.96
    
    async def get_experiment_summary(self, experiment_id: str) -> Dict[str, Any]:
        """
        Get a summary of experiment results.
        
        Args:
            experiment_id: Experiment ID
            
        Returns:
            Dictionary with experiment summary
        """
        experiment = self._experiments.get(experiment_id)
        if not experiment:
            return {"error": "Experiment not found"}
        
        results = await self.get_experiment_results(experiment_id)
        
        return {
            "experiment_id": experiment.id,
            "name": experiment.name,
            "status": experiment.status.value,
            "start_date": experiment.start_date.isoformat() if experiment.start_date else None,
            "end_date": experiment.end_date.isoformat() if experiment.end_date else None,
            "target_metric": experiment.target_metric,
            "results": [
                {
                    "variant": r.variant.value,
                    "sample_size": r.sample_size,
                    "conversions": r.conversions,
                    "conversion_rate": r.conversion_rate,
                    "lift_vs_control": r.lift_vs_control,
                    "is_significant": r.is_significant,
                }
                for r in results
            ],
        }
    
    async def get_winning_variant(self, experiment_id: str) -> Optional[ExperimentVariant]:
        """
        Determine the winning variant for an experiment.
        
        Args:
            experiment_id: Experiment ID
            
        Returns:
            Winning variant or None
        """
        results = await self.get_experiment_results(experiment_id)
        
        if not results:
            return None
        
        # Find variant with highest conversion rate
        best = max(results, key=lambda r: r.conversion_rate)
        
        # Only declare winner if significant
        if best.is_significant:
            return best.variant
        
        return None


# Global A/B testing framework instance
ab_testing_framework = ABTestingFramework()


def get_experiment(experiment_id: str) -> Optional[Experiment]:
    """Get experiment by ID."""
    return ab_testing_framework.get_experiment(experiment_id)


async def track_conversion(
    experiment_id: str,
    user_id: int,
    metric_name: str = "conversion",
    value: float = 1.0,
) -> None:
    """Convenience function to track conversion."""
    await ab_testing_framework.track_conversion(experiment_id, user_id, metric_name, value)


async def get_experiment_results(experiment_id: str) -> List[ExperimentResult]:
    """Convenience function to get experiment results."""
    return await ab_testing_framework.get_experiment_results(experiment_id)


__all__ = [
    "ABTestingFramework",
    "Experiment",
    "ExperimentStatus",
    "ExperimentVariant",
    "ExperimentConversion",
    "ExperimentResult",
    "ab_testing_framework",
    "get_experiment",
    "track_conversion",
    "get_experiment_results",
]
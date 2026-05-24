# ============================
# WOLLOYEWA STORE BOT - DATA PIPELINE MODULE
# ============================
"""Data pipeline for real-time analytics, recommendations, and ETL."""

from core.data_pipeline.real_time_analytics import (
    RealTimeAnalytics,
    real_time_analytics,
    track_user_action,
    track_product_view,
    track_search_query,
    get_hot_products,
    get_user_activity_stats,
)
from core.data_pipeline.recommendation_engine import (
    RecommendationEngine,
    recommendation_engine,
    get_product_recommendations,
    get_personalized_recommendations,
    get_similar_products,
    get_frequently_bought_together,
)
from core.data_pipeline.churn_predictor import (
    ChurnPredictor,
    churn_predictor,
    predict_user_churn,
    get_at_risk_users,
    ChurnRiskLevel,
)
from core.data_pipeline.ab_testing_framework import (
    ABTestingFramework,
    ab_testing_framework,
    Experiment,
    ExperimentVariant,
    get_experiment,
    track_conversion,
    get_experiment_results,
)
from core.data_pipeline.cohort_analysis import (
    CohortAnalysis,
    cohort_analysis,
    CohortType,
    perform_cohort_analysis,
    get_user_retention,
    get_lifetime_value,
)
from core.data_pipeline.etl.order_extractor import (
    OrderExtractor,
    extract_orders,
)
from core.data_pipeline.etl.user_transformer import (
    UserTransformer,
    transform_user_data,
)
from core.data_pipeline.etl.clickhouse_loader import (
    ClickHouseLoader,
    clickhouse_loader,
    load_to_clickhouse,
)

__all__ = [
    # Real-time Analytics
    "RealTimeAnalytics",
    "real_time_analytics",
    "track_user_action",
    "track_product_view",
    "track_search_query",
    "get_hot_products",
    "get_user_activity_stats",
    # Recommendation Engine
    "RecommendationEngine",
    "recommendation_engine",
    "get_product_recommendations",
    "get_personalized_recommendations",
    "get_similar_products",
    "get_frequently_bought_together",
    # Churn Prediction
    "ChurnPredictor",
    "churn_predictor",
    "predict_user_churn",
    "get_at_risk_users",
    "ChurnRiskLevel",
    # A/B Testing
    "ABTestingFramework",
    "ab_testing_framework",
    "Experiment",
    "ExperimentVariant",
    "get_experiment",
    "track_conversion",
    "get_experiment_results",
    # Cohort Analysis
    "CohortAnalysis",
    "cohort_analysis",
    "CohortType",
    "perform_cohort_analysis",
    "get_user_retention",
    "get_lifetime_value",
    # ETL
    "OrderExtractor",
    "extract_orders",
    "UserTransformer",
    "transform_user_data",
    "ClickHouseLoader",
    "clickhouse_loader",
    "load_to_clickhouse",
]
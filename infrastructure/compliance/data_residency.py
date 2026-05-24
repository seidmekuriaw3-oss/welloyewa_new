# ============================
# WOLLOYEWA STORE BOT - DATA RESIDENCY
# ============================
"""Data residency compliance for Ethiopian data protection laws."""

from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime

from core.config import settings
from core.logger import logger


class DataRegion(str, Enum):
    """Data storage regions."""
    ETHIOPIA = "ethiopia"
    EU = "eu"
    US = "us"
    ASIA = "asia"
    AUTO = "auto"


class DataClassification(str, Enum):
    """Data classification levels."""
    PUBLIC = "public"           # Publicly available data
    INTERNAL = "internal"       # Internal business data
    CONFIDENTIAL = "confidential"  # Customer data, PII
    RESTRICTED = "restricted"   # Financial, payment data


@dataclass
class DataLocation:
    """Data location information."""
    
    region: DataRegion
    data_type: str
    classification: DataClassification
    stored_at: datetime
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class DataResidencyManager:
    """
    Data residency compliance manager.
    
    Features:
    - Ensure data is stored in compliant regions
    - Track data location
    - Data classification
    - Cross-border transfer controls
    """
    
    def __init__(self):
        self._data_locations: Dict[str, DataLocation] = {}
        self._restricted_regions = [DataRegion.ETHIOPIA]  # Ethiopian data must stay in Ethiopia
        
        # Classification rules
        self._classification_rules = {
            DataClassification.PUBLIC: [DataRegion.ETHIOPIA, DataRegion.EU, DataRegion.US, DataRegion.ASIA],
            DataClassification.INTERNAL: [DataRegion.ETHIOPIA, DataRegion.EU],
            DataClassification.CONFIDENTIAL: [DataRegion.ETHIOPIA],
            DataClassification.RESTRICTED: [DataRegion.ETHIOPIA],
        }
    
    def classify_data(self, data_type: str, contains_pii: bool = False, is_financial: bool = False) -> DataClassification:
        """
        Classify data based on type and sensitivity.
        
        Args:
            data_type: Type of data
            contains_pii: Whether data contains PII
            is_financial: Whether data is financial
            
        Returns:
            DataClassification level
        """
        if is_financial:
            return DataClassification.RESTRICTED
        elif contains_pii:
            return DataClassification.CONFIDENTIAL
        elif data_type in ["user_profile", "order_history", "customer_data"]:
            return DataClassification.CONFIDENTIAL
        elif data_type in ["analytics", "logs", "metrics"]:
            return DataClassification.INTERNAL
        else:
            return DataClassification.PUBLIC
    
    def get_allowed_regions(self, classification: DataClassification) -> List[DataRegion]:
        """Get allowed regions for a data classification."""
        return self._classification_rules.get(classification, [DataRegion.ETHIOPIA])
    
    def is_region_allowed(self, classification: DataClassification, region: DataRegion) -> bool:
        """Check if a region is allowed for a data classification."""
        allowed = self.get_allowed_regions(classification)
        return region in allowed
    
    async def ensure_data_residency(
        self,
        data_id: str,
        data_type: str,
        classification: DataClassification,
        target_region: Optional[DataRegion] = None,
    ) -> bool:
        """
        Ensure data is stored in a compliant region.
        
        Args:
            data_id: Data identifier
            data_type: Type of data
            classification: Data classification
            target_region: Desired storage region
            
        Returns:
            True if compliant region found
        """
        allowed_regions = self.get_allowed_regions(classification)
        
        if target_region and target_region in allowed_regions:
            region = target_region
        elif allowed_regions:
            region = allowed_regions[0]
        else:
            logger.error(f"No allowed region for classification {classification.value}")
            return False
        
        # Record data location
        location = DataLocation(
            region=region,
            data_type=data_type,
            classification=classification,
            stored_at=datetime.utcnow(),
        )
        
        self._data_locations[data_id] = location
        
        logger.info(f"Data {data_id} stored in {region.value} (classification: {classification.value})")
        return True
    
    async def get_data_location(self, data_id: str) -> Optional[DataLocation]:
        """Get the storage location of data."""
        return self._data_locations.get(data_id)
    
    async def migrate_data(
        self,
        data_id: str,
        target_region: DataRegion,
    ) -> bool:
        """
        Migrate data to a different region.
        
        Args:
            data_id: Data identifier
            target_region: Target region
            
        Returns:
            True if migration successful
        """
        location = await self.get_data_location(data_id)
        
        if not location:
            logger.warning(f"Data {data_id} not found")
            return False
        
        if not self.is_region_allowed(location.classification, target_region):
            logger.warning(f"Region {target_region.value} not allowed for classification {location.classification.value}")
            return False
        
        # Update location
        location.region = target_region
        location.stored_at = datetime.utcnow()
        self._data_locations[data_id] = location
        
        logger.info(f"Data {data_id} migrated to {target_region.value}")
        return True
    
    async def get_compliance_report(self) -> Dict[str, Any]:
        """Get data residency compliance report."""
        regions_count = {}
        classifications_count = {}
        
        for location in self._data_locations.values():
            regions_count[location.region.value] = regions_count.get(location.region.value, 0) + 1
            classifications_count[location.classification.value] = classifications_count.get(location.classification.value, 0) + 1
        
        return {
            "total_data_objects": len(self._data_locations),
            "data_by_region": regions_count,
            "data_by_classification": classifications_count,
            "restricted_regions": [r.value for r in self._restricted_regions],
        }


# Global data residency manager
data_residency_manager = DataResidencyManager()


async def ensure_data_residency(
    data_id: str,
    data_type: str,
    contains_pii: bool = False,
    is_financial: bool = False,
) -> bool:
    """Ensure data is stored in a compliant region."""
    classification = data_residency_manager.classify_data(data_type, contains_pii, is_financial)
    return await data_residency_manager.ensure_data_residency(data_id, data_type, classification)


async def get_data_location(data_id: str) -> Optional[DataLocation]:
    """Get data location."""
    return await data_residency_manager.get_data_location(data_id)


class DataResidencyCompliance:
    """Singleton data residency manager."""
    
    _instance: Optional[DataResidencyManager] = None
    
    @classmethod
    def get_instance(cls) -> DataResidencyManager:
        if cls._instance is None:
            cls._instance = DataResidencyManager()
        return cls._instance


__all__ = [
    "DataResidencyManager",
    "DataRegion",
    "DataClassification",
    "DataLocation",
    "data_residency_manager",
    "ensure_data_residency",
    "get_data_location",
    "DataResidencyCompliance",
]
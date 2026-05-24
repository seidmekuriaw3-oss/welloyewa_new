# ============================
# WOLLOYEWA STORE BOT - GDPR COMPLIANCE
# ============================
"""GDPR compliance utilities for data privacy and user rights."""

import json
from enum import Enum
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from core.config import settings
from core.logger import logger
from core.security.encryption import encrypt_data, decrypt_data
from core.security.pii_masker import pii_masker


class ConsentPurpose(str, Enum):
    """Purposes for which user consent is required."""
    MARKETING = "marketing"
    ANALYTICS = "analytics"
    PERSONALIZATION = "personalization"
    THIRD_PARTY_SHARING = "third_party_sharing"
    LOCATION = "location"
    NOTIFICATIONS = "notifications"


class ConsentStatus(str, Enum):
    """Status of user consent."""
    GRANTED = "granted"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"
    NOT_GIVEN = "not_given"


@dataclass
class ConsentRecord:
    """Record of user consent."""
    
    user_id: int
    purpose: ConsentPurpose
    status: ConsentStatus
    granted_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


@dataclass
class DataSubjectRequest:
    """GDPR data subject request."""
    
    request_id: str
    user_id: int
    request_type: str  # 'access', 'rectification', 'erasure', 'portability'
    status: str  # 'pending', 'processing', 'completed', 'rejected'
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    data: Optional[Dict[str, Any]] = None
    reason: Optional[str] = None


class ConsentManager:
    """
    Manage user consent for data processing.
    
    Features:
    - Consent tracking and storage
    - Consent expiration
    - Audit trail for consent changes
    """
    
    def __init__(self):
        self._consents: Dict[str, List[ConsentRecord]] = {}
        self._consent_expiry_days = 365  # Consent expires after 1 year
    
    def get_consent(self, user_id: int, purpose: ConsentPurpose) -> Optional[ConsentRecord]:
        """Get current consent for a user and purpose."""
        key = f"{user_id}:{purpose.value}"
        consents = self._consents.get(key, [])
        
        if not consents:
            return None
        
        # Return most recent consent
        latest = max(consents, key=lambda c: c.updated_at)
        
        # Check if expired
        if latest.status == ConsentStatus.GRANTED:
            expiry = latest.granted_at + timedelta(days=self._consent_expiry_days)
            if datetime.utcnow() > expiry:
                latest.status = ConsentStatus.EXPIRED
                self.update_consent(user_id, purpose, ConsentStatus.EXPIRED)
        
        return latest
    
    def grant_consent(
        self,
        user_id: int,
        purpose: ConsentPurpose,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> ConsentRecord:
        """Grant consent for a purpose."""
        record = ConsentRecord(
            user_id=user_id,
            purpose=purpose,
            status=ConsentStatus.GRANTED,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        key = f"{user_id}:{purpose.value}"
        if key not in self._consents:
            self._consents[key] = []
        self._consents[key].append(record)
        
        logger.info(f"Consent granted: user {user_id} for {purpose.value}")
        return record
    
    def withdraw_consent(self, user_id: int, purpose: ConsentPurpose) -> bool:
        """Withdraw consent for a purpose."""
        key = f"{user_id}:{purpose.value}"
        
        if key in self._consents and self._consents[key]:
            record = ConsentRecord(
                user_id=user_id,
                purpose=purpose,
                status=ConsentStatus.WITHDRAWN,
            )
            self._consents[key].append(record)
            logger.info(f"Consent withdrawn: user {user_id} for {purpose.value}")
            return True
        
        return False
    
    def update_consent(self, user_id: int, purpose: ConsentPurpose, status: ConsentStatus) -> bool:
        """Update consent status."""
        key = f"{user_id}:{purpose.value}"
        
        if key in self._consents and self._consents[key]:
            record = ConsentRecord(
                user_id=user_id,
                purpose=purpose,
                status=status,
            )
            self._consents[key].append(record)
            return True
        
        return False
    
    def has_consent(self, user_id: int, purpose: ConsentPurpose) -> bool:
        """Check if user has given consent for a purpose."""
        consent = self.get_consent(user_id, purpose)
        return consent is not None and consent.status == ConsentStatus.GRANTED
    
    def get_all_consents(self, user_id: int) -> Dict[str, str]:
        """Get all consents for a user."""
        result = {}
        for purpose in ConsentPurpose:
            consent = self.get_consent(user_id, purpose)
            result[purpose.value] = consent.status.value if consent else ConsentStatus.NOT_GIVEN.value
        return result


class GDPRCompliance:
    """
    GDPR compliance manager for user data rights.
    
    Handles:
    - Right to access (data export)
    - Right to rectification (data correction)
    - Right to erasure (right to be forgotten)
    - Right to data portability
    - Consent management
    """
    
    def __init__(self):
        self._requests: List[DataSubjectRequest] = []
        self._consent_manager = ConsentManager()
        self._data_retention_days = settings.DATA_RETENTION_DAYS
        self._data_store: Dict[str, Dict[str, Any]] = {}  # Simulated data store
    
    def request_data_access(self, user_id: int) -> DataSubjectRequest:
        """Handle right to access request (GDPR Article 15)."""
        request = DataSubjectRequest(
            request_id=f"DSR-{user_id}-{int(datetime.utcnow().timestamp())}",
            user_id=user_id,
            request_type="access",
            status="pending",
        )
        self._requests.append(request)
        logger.info(f"Data access request created for user {user_id}")
        return request
    
    def request_data_rectification(self, user_id: int, corrections: Dict[str, Any]) -> DataSubjectRequest:
        """Handle right to rectification request (GDPR Article 16)."""
        request = DataSubjectRequest(
            request_id=f"DSR-{user_id}-{int(datetime.utcnow().timestamp())}",
            user_id=user_id,
            request_type="rectification",
            status="pending",
            data=corrections,
        )
        self._requests.append(request)
        logger.info(f"Data rectification request created for user {user_id}")
        return request
    
    def request_data_erasure(self, user_id: int, reason: Optional[str] = None) -> DataSubjectRequest:
        """Handle right to erasure request (GDPR Article 17)."""
        request = DataSubjectRequest(
            request_id=f"DSR-{user_id}-{int(datetime.utcnow().timestamp())}",
            user_id=user_id,
            request_type="erasure",
            status="pending",
            reason=reason,
        )
        self._requests.append(request)
        logger.info(f"Data erasure request created for user {user_id}")
        return request
    
    def request_data_portability(self, user_id: int) -> DataSubjectRequest:
        """Handle right to data portability request (GDPR Article 20)."""
        request = DataSubjectRequest(
            request_id=f"DSR-{user_id}-{int(datetime.utcnow().timestamp())}",
            user_id=user_id,
            request_type="portability",
            status="pending",
        )
        self._requests.append(request)
        logger.info(f"Data portability request created for user {user_id}")
        return request
    
    def process_request(self, request_id: str) -> Dict[str, Any]:
        """Process a data subject request."""
        request = next((r for r in self._requests if r.request_id == request_id), None)
        
        if not request:
            raise ValueError(f"Request not found: {request_id}")
        
        request.status = "processing"
        
        if request.request_type == "access":
            result = self._process_access_request(request.user_id)
        elif request.request_type == "rectification":
            result = self._process_rectification_request(request.user_id, request.data or {})
        elif request.request_type == "erasure":
            result = self._process_erasure_request(request.user_id)
        elif request.request_type == "portability":
            result = self._process_portability_request(request.user_id)
        else:
            result = {"error": "Unknown request type"}
        
        request.status = "completed"
        request.completed_at = datetime.utcnow()
        request.data = result
        
        return result
    
    def _process_access_request(self, user_id: int) -> Dict[str, Any]:
        """Process data access request."""
        # In production, fetch actual user data from database
        user_data = self._data_store.get(str(user_id), {})
        
        # Mask sensitive data
        masked_data = {}
        for key, value in user_data.items():
            if isinstance(value, str):
                masked_data[key] = pii_masker.mask(value, keep_ends=1)
            else:
                masked_data[key] = value
        
        return {
            "user_id": user_id,
            "data": masked_data,
            "export_date": datetime.utcnow().isoformat(),
            "data_retention_days": self._data_retention_days,
        }
    
    def _process_rectification_request(self, user_id: int, corrections: Dict[str, Any]) -> Dict[str, Any]:
        """Process data rectification request."""
        # In production, update database with corrections
        if str(user_id) not in self._data_store:
            self._data_store[str(user_id)] = {}
        
        self._data_store[str(user_id)].update(corrections)
        
        return {
            "user_id": user_id,
            "corrections_applied": corrections,
            "updated_at": datetime.utcnow().isoformat(),
        }
    
    def _process_erasure_request(self, user_id: int) -> Dict[str, Any]:
        """Process data erasure request (right to be forgotten)."""
        # In production, anonymize or delete user data
        if str(user_id) in self._data_store:
            # Anonymize instead of delete for audit purposes
            self._data_store[str(user_id)] = {
                "anonymized": True,
                "original_user_id": f"anon_{user_id}",
            }
        
        return {
            "user_id": user_id,
            "erasure_completed": True,
            "completed_at": datetime.utcnow().isoformat(),
        }
    
    def _process_portability_request(self, user_id: int) -> Dict[str, Any]:
        """Process data portability request."""
        user_data = self._data_store.get(str(user_id), {})
        
        return {
            "user_id": user_id,
            "data": user_data,
            "format": "json",
            "export_date": datetime.utcnow().isoformat(),
        }
    
    def get_pending_requests(self) -> List[DataSubjectRequest]:
        """Get all pending requests."""
        return [r for r in self._requests if r.status == "pending"]
    
    def get_consent_manager(self) -> ConsentManager:
        """Get consent manager instance."""
        return self._consent_manager
    
    def is_compliant(self) -> Dict[str, Any]:
        """Check GDPR compliance status."""
        return {
            "consent_management": True,
            "data_retention_enabled": self._data_retention_days > 0,
            "data_retention_days": self._data_retention_days,
            "right_to_access_enabled": True,
            "right_to_erasure_enabled": True,
            "right_to_portability_enabled": True,
            "pending_requests": len(self.get_pending_requests()),
        }
    
    def anonymize_user_data(self, user_id: int) -> bool:
        """Anonymize user data for compliance."""
        # In production, implement proper anonymization
        logger.info(f"Anonymizing data for user {user_id}")
        return True


# Global GDPR compliance instance
gdpr_compliance = GDPRCompliance()


def handle_data_request(
    user_id: int,
    request_type: str,
    data: Optional[Dict[str, Any]] = None,
) -> DataSubjectRequest:
    """Convenience function to handle GDPR data requests."""
    if request_type == "access":
        return gdpr_compliance.request_data_access(user_id)
    elif request_type == "rectification":
        return gdpr_compliance.request_data_rectification(user_id, data or {})
    elif request_type == "erasure":
        return gdpr_compliance.request_data_erasure(user_id)
    elif request_type == "portability":
        return gdpr_compliance.request_data_portability(user_id)
    else:
        raise ValueError(f"Unknown request type: {request_type}")


__all__ = [
    "GDPRCompliance",
    "ConsentManager",
    "ConsentPurpose",
    "ConsentStatus",
    "ConsentRecord",
    "DataSubjectRequest",
    "gdpr_compliance",
    "handle_data_request",
]
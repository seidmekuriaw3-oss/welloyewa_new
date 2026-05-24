# ============================
# WOLLOYEWA STORE BOT - PRIVACY POLICY GENERATOR
# ============================
"""Privacy policy generation and management for GDPR compliance."""

from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime

from core.config import settings
from core.logger import logger


class ConsentType(str, Enum):
    """Types of user consent."""
    MARKETING = "marketing"
    ANALYTICS = "analytics"
    PERSONALIZATION = "personalization"
    THIRD_PARTY = "third_party"
    COOKIES = "cookies"


@dataclass
class PrivacyPolicy:
    """Privacy policy data."""
    
    version: str
    effective_date: datetime
    content: str
    content_am: Optional[str] = None
    changes: Optional[List[str]] = None
    previous_version: Optional[str] = None


@dataclass
class UserConsent:
    """User consent record."""
    
    user_id: int
    consent_type: ConsentType
    granted: bool
    granted_at: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    expires_at: Optional[datetime] = None


class PrivacyPolicyGenerator:
    """
    Privacy policy generator.
    
    Features:
    - Generate GDPR-compliant privacy policy
    - Multi-language support (English, Amharic)
    - Version management
    - Consent tracking
    """
    
    def __init__(self):
        self._policies: Dict[str, PrivacyPolicy] = {}
        self._user_consents: Dict[str, List[UserConsent]] = {}
        self._current_version = "1.0"
        
        # Initialize with default policy
        self._init_default_policy()
    
    def _init_default_policy(self) -> None:
        """Initialize default privacy policy."""
        default_policy = PrivacyPolicy(
            version="1.0",
            effective_date=datetime.utcnow(),
            content=self._generate_policy_content("en"),
            content_am=self._generate_policy_content("am"),
        )
        self._policies["1.0"] = default_policy
    
    def _generate_policy_content(self, language: str = "en") -> str:
        """Generate privacy policy content."""
        company_name = "Wolloyewa Technologies PLC"
        company_address = "Addis Ababa, Ethiopia"
        
        if language == "am":
            return f"""
# የግላዊነት ፖሊሲ

**ውጤታማ ቀን:** {datetime.utcnow().strftime('%B %d, %Y')}

## መግቢያ
እንኳን ወደ {company_name} በደህና መጡ። የእርስዎን ግላዊነት መጠበቅ ቅድሚያ የምንሰጠው ጉዳይ ነው።

## የምንሰበስበው መረጃ
- ስም፣ ስልክ ቁጥር፣ ኢሜይል አድራሻ
- የማድረሻ አድራሻ
- የክፍያ መረጃ
- የትዕዛዝ ታሪክ

## መረጃዎን እንዴት እንጠቀማለን
- ትዕዛዞትን ለማስኬድ
- የደንበኛ ድጋፍ ለመስጠት
- አገልግሎታችንን ለማሻሻል
- ህጋዊ መስፈርቶችን ለማሟላት

## መረጃዎን ከማን ጋር እንጋራለን
መረጃዎን ያለፈቃድዎ ከሶስተኛ ወገኖች አንጋራም።

## መብቶችዎ
- መረጃዎን የማግኘት መብት
- መረጃዎን የማስተካከል መብት
- መረጃዎን የማጥፋት መብት
- ፈቃድዎን የመሻር መብት

## እንዴት እንደምናገኙ
ኢሜይል: privacy@wolloyewa.com
አድራሻ: {company_address}
"""
        else:
            return f"""
# Privacy Policy

**Effective Date:** {datetime.utcnow().strftime('%B %d, %Y')}

## Introduction
Welcome to {company_name}. Protecting your privacy is our top priority.

## Information We Collect
- Name, phone number, email address
- Shipping address
- Payment information
- Order history

## How We Use Your Information
- Process your orders
- Provide customer support
- Improve our services
- Comply with legal requirements

## Information Sharing
We do not share your information with third parties without your consent.

## Your Rights
- Right to access your data
- Right to rectify your data
- Right to erasure (right to be forgotten)
- Right to withdraw consent

## Contact Us
Email: privacy@wolloyewa.com
Address: {company_address}
"""
    
    async def get_current_policy(self) -> PrivacyPolicy:
        """Get current privacy policy."""
        return self._policies.get(self._current_version)
    
    async def update_privacy_policy(
        self,
        new_version: str,
        changes: List[str],
        effective_date: Optional[datetime] = None,
    ) -> PrivacyPolicy:
        """
        Update privacy policy to new version.
        
        Args:
            new_version: New version number
            changes: List of changes
            effective_date: Effective date (defaults to now)
            
        Returns:
            New PrivacyPolicy
        """
        current = await self.get_current_policy()
        
        new_policy = PrivacyPolicy(
            version=new_version,
            effective_date=effective_date or datetime.utcnow(),
            content=self._generate_policy_content("en"),
            content_am=self._generate_policy_content("am"),
            changes=changes,
            previous_version=current.version if current else None,
        )
        
        self._policies[new_version] = new_policy
        self._current_version = new_version
        
        logger.info(f"Privacy policy updated to version {new_version}")
        return new_policy
    
    async def record_consent(
        self,
        user_id: int,
        consent_type: ConsentType,
        granted: bool,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> UserConsent:
        """
        Record user consent.
        
        Args:
            user_id: User ID
            consent_type: Type of consent
            granted: Whether consent is granted
            ip_address: User's IP address
            user_agent: User's browser agent
            
        Returns:
            UserConsent record
        """
        consent = UserConsent(
            user_id=user_id,
            consent_type=consent_type,
            granted=granted,
            granted_at=datetime.utcnow(),
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        key = f"{user_id}:{consent_type.value}"
        if key not in self._user_consents:
            self._user_consents[key] = []
        self._user_consents[key].append(consent)
        
        logger.info(f"Consent recorded for user {user_id}: {consent_type.value} = {granted}")
        return consent
    
    async def get_user_consents(
        self,
        user_id: int,
        consent_type: Optional[ConsentType] = None,
    ) -> List[UserConsent]:
        """Get user consent records."""
        consents = []
        
        for key, records in self._user_consents.items():
            if key.startswith(str(user_id)):
                if consent_type is None or consent_type.value in key:
                    consents.extend(records)
        
        # Sort by timestamp descending
        consents.sort(key=lambda x: x.granted_at, reverse=True)
        return consents
    
    async def has_consent(
        self,
        user_id: int,
        consent_type: ConsentType,
    ) -> bool:
        """Check if user has given consent."""
        consents = await self.get_user_consents(user_id, consent_type)
        
        if not consents:
            return False
        
        # Most recent consent
        latest = consents[0]
        return latest.granted
    
    async def withdraw_consent(
        self,
        user_id: int,
        consent_type: ConsentType,
        ip_address: Optional[str] = None,
    ) -> UserConsent:
        """Withdraw previously granted consent."""
        return await self.record_consent(user_id, consent_type, False, ip_address)


# Global privacy policy generator
privacy_policy_gen = PrivacyPolicyGenerator()


async def generate_privacy_policy(language: str = "en") -> str:
    """Generate privacy policy content."""
    policy = await privacy_policy_gen.get_current_policy()
    return policy.content_am if language == "am" else policy.content


async def update_privacy_policy(
    new_version: str,
    changes: List[str],
) -> PrivacyPolicy:
    """Update privacy policy to new version."""
    return await privacy_policy_gen.update_privacy_policy(new_version, changes)


class PrivacyCompliance:
    """Singleton privacy compliance manager."""
    
    _instance: Optional[PrivacyPolicyGenerator] = None
    
    @classmethod
    def get_instance(cls) -> PrivacyPolicyGenerator:
        if cls._instance is None:
            cls._instance = PrivacyPolicyGenerator()
        return cls._instance


__all__ = [
    "PrivacyPolicyGenerator",
    "PrivacyPolicy",
    "ConsentType",
    "UserConsent",
    "privacy_policy_gen",
    "generate_privacy_policy",
    "update_privacy_policy",
    "PrivacyCompliance",
]
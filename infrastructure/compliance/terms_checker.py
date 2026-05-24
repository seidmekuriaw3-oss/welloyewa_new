# ============================
# WOLLOYEWA STORE BOT - TERMS CHECKER
# ============================
"""Terms of service acceptance tracking and compliance."""

from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime

from core.logger import logger


@dataclass
class TermsVersion:
    """Terms of service version."""
    
    version: str
    effective_date: datetime
    content: str
    content_am: Optional[str] = None
    changes: Optional[List[str]] = None
    is_current: bool = False


@dataclass
class TermsAcceptance:
    """User terms acceptance record."""
    
    user_id: int
    version: str
    accepted_at: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    is_withdrawn: bool = False
    withdrawn_at: Optional[datetime] = None


class TermsChecker:
    """
    Terms of service compliance checker.
    
    Features:
    - Version management
    - User acceptance tracking
    - Forced acceptance for new versions
    - Audit trail for acceptances
    """
    
    def __init__(self):
        self._versions: Dict[str, TermsVersion] = {}
        self._acceptances: Dict[int, List[TermsAcceptance]] = {}
        self._current_version = "1.0"
        
        # Initialize default terms
        self._init_default_terms()
    
    def _init_default_terms(self) -> None:
        """Initialize default terms of service."""
        default_terms = TermsVersion(
            version="1.0",
            effective_date=datetime.utcnow(),
            content=self._generate_terms_content("en"),
            content_am=self._generate_terms_content("am"),
            is_current=True,
        )
        self._versions["1.0"] = default_terms
    
    def _generate_terms_content(self, language: str = "en") -> str:
        """Generate terms of service content."""
        company_name = "Wolloyewa Technologies PLC"
        
        if language == "am":
            return f"""
# የአገልግሎት ውሎች

**ውጤታማ ቀን:** {datetime.utcnow().strftime('%B %d, %Y')}

## 1. የአገልግሎት መግለጫ
Wolloyewa የኢትዮጵያ የኢ-ኮሜርስ መድረክ ሲሆን ገዢዎችን ከሻጮች ጋር የሚያገናኝ ነው።

## 2. መለያ መመዝገብ
- አገልግሎቱን ለመጠቀም መለያ መፍጠር አለብዎት
- ትክክለኛ እና ወቅታዊ መረጃ መስጠት አለብዎት
- ለመለያዎ ደህንነት እርስዎ ኃላፊ ነዎት

## 3. ግዢዎች እና ክፍያዎች
- ሁሉም ግዢዎች በዚህ ውል ይተዳደራሉ
- ዋጋዎች በብር ነው
- ክፍያዎች በሚገኙ የክፍያ መግብሮች ይከናወናሉ

## 4. ማድረስ
- የማድረሻ ጊዜዎች ግምታዊ ናቸው
- ለማድረስ ኃላፊነቱ በሻጩ ላይ ነው

## 5. መመለስ እና ተመላሽ
- ምርቶች በ14 ቀናት ውስጥ መመለስ ይቻላል
- ምርቶች ባልተጠቀሙበት ሁኔታ መሆን አለባቸው

## 6. የአጠቃቀም ገደቦች
- ህገ-ወጥ እንቅስቃሴዎችን መጠቀም አይቻልም
- የሌሎችን መብቶች ማክበር አለብዎት
- ጎጂ ይዘቶችን መለጠፍ አይፈቀድም

## 7. ውል ማቋረጥ
- ውሎቹን ባለማክበር መለያዎ ሊቋረጥ ይችላል
- በማንኛውም ጊዜ መለያዎን መሰረዝ ይችላሉ

## 8. ኃላፊነት
- ኩባንያው ለቀጥታ ጉዳቶች ብቻ ኃላፊ ነው
- ከፍተኛው ኃላፊነት የክፍያ መጠን ነው

## 9. ለውጦች
- ውሎቹን በማንኛውም ጊዜ ማሻሻል እንችላለን
- ለውጦች በዚህ ገጽ ላይ ይታተማሉ

## 10. እንዴት እንደምናገኙ
ኢሜይል: legal@wolloyewa.com
አድራሻ: Addis Ababa, Ethiopia
"""
        else:
            return f"""
# Terms of Service

**Effective Date:** {datetime.utcnow().strftime('%B %d, %Y')}

## 1. Service Description
Wolloyewa is an Ethiopian e-commerce platform connecting buyers with sellers.

## 2. Account Registration
- You must create an account to use the service
- You must provide accurate and current information
- You are responsible for your account security

## 3. Purchases and Payments
- All purchases are governed by these terms
- Prices are in Ethiopian Birr (ETB)
- Payments are processed through available payment gateways

## 4. Delivery
- Delivery times are estimates
- Delivery responsibility lies with the seller

## 5. Returns and Refunds
- Products can be returned within 14 days
- Products must be in unused condition

## 6. Prohibited Activities
- Illegal activities are prohibited
- You must respect others' rights
- Harmful content is not allowed

## 7. Termination
- Violation of terms may result in termination
- You may delete your account at any time

## 8. Limitation of Liability
- Company is only liable for direct damages
- Maximum liability equals payment amount

## 9. Changes to Terms
- We may modify terms at any time
- Changes will be posted on this page

## 10. Contact Us
Email: legal@wolloyewa.com
Address: Addis Ababa, Ethiopia
"""
    
    async def get_current_terms(self) -> TermsVersion:
        """Get current terms of service."""
        return self._versions.get(self._current_version)
    
    async def update_terms(
        self,
        new_version: str,
        changes: List[str],
        effective_date: Optional[datetime] = None,
    ) -> TermsVersion:
        """
        Update terms of service to new version.
        
        Args:
            new_version: New version number
            changes: List of changes
            effective_date: Effective date (defaults to now)
            
        Returns:
            New TermsVersion
        """
        # Update current version to not current
        if self._current_version in self._versions:
            self._versions[self._current_version].is_current = False
        
        new_terms = TermsVersion(
            version=new_version,
            effective_date=effective_date or datetime.utcnow(),
            content=self._generate_terms_content("en"),
            content_am=self._generate_terms_content("am"),
            changes=changes,
            is_current=True,
        )
        
        self._versions[new_version] = new_terms
        self._current_version = new_version
        
        logger.info(f"Terms of service updated to version {new_version}")
        return new_terms
    
    async def record_acceptance(
        self,
        user_id: int,
        version: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> TermsAcceptance:
        """
        Record user acceptance of terms.
        
        Args:
            user_id: User ID
            version: Terms version accepted
            ip_address: User's IP address
            user_agent: User's browser agent
            
        Returns:
            TermsAcceptance record
        """
        # Check if user already accepted this version
        if await self.has_accepted_version(user_id, version):
            logger.warning(f"User {user_id} already accepted version {version}")
        
        acceptance = TermsAcceptance(
            user_id=user_id,
            version=version,
            accepted_at=datetime.utcnow(),
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        if user_id not in self._acceptances:
            self._acceptances[user_id] = []
        self._acceptances[user_id].append(acceptance)
        
        logger.info(f"User {user_id} accepted terms version {version}")
        return acceptance
    
    async def has_accepted_version(
        self,
        user_id: int,
        version: str,
    ) -> bool:
        """Check if user has accepted a specific version."""
        if user_id not in self._acceptances:
            return False
        
        for acceptance in self._acceptances[user_id]:
            if acceptance.version == version and not acceptance.is_withdrawn:
                return True
        
        return False
    
    async def needs_new_acceptance(self, user_id: int) -> bool:
        """Check if user needs to accept new terms version."""
        current_version = await self.get_current_terms()
        
        if not current_version:
            return True
        
        return not await self.has_accepted_version(user_id, current_version.version)
    
    async def withdraw_acceptance(
        self,
        user_id: int,
        version: Optional[str] = None,
    ) -> bool:
        """
        Withdraw acceptance of terms.
        
        Args:
            user_id: User ID
            version: Specific version to withdraw (defaults to all)
            
        Returns:
            True if withdrawn
        """
        if user_id not in self._acceptances:
            return False
        
        withdrawn = False
        for acceptance in self._acceptances[user_id]:
            if (version is None or acceptance.version == version) and not acceptance.is_withdrawn:
                acceptance.is_withdrawn = True
                acceptance.withdrawn_at = datetime.utcnow()
                withdrawn = True
        
        if withdrawn:
            logger.info(f"User {user_id} withdrew acceptance of terms{ ' version ' + version if version else ''}")
        
        return withdrawn
    
    async def get_user_acceptance_history(
        self,
        user_id: int,
    ) -> List[TermsAcceptance]:
        """Get user's terms acceptance history."""
        return self._acceptances.get(user_id, [])


# Global terms checker
terms_checker = TermsChecker()


async def check_terms_acceptance(user_id: int) -> bool:
    """Check if user has accepted current terms."""
    return not await terms_checker.needs_new_acceptance(user_id)


async def record_terms_acceptance(
    user_id: int,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> TermsAcceptance:
    """Record user acceptance of current terms."""
    current = await terms_checker.get_current_terms()
    return await terms_checker.record_acceptance(user_id, current.version, ip_address, user_agent)


async def get_current_terms(language: str = "en") -> str:
    """Get current terms of service content."""
    current = await terms_checker.get_current_terms()
    return current.content_am if language == "am" else current.content


class TermsCompliance:
    """Singleton terms compliance manager."""
    
    _instance: Optional[TermsChecker] = None
    
    @classmethod
    def get_instance(cls) -> TermsChecker:
        if cls._instance is None:
            cls._instance = TermsChecker()
        return cls._instance


__all__ = [
    "TermsChecker",
    "TermsVersion",
    "TermsAcceptance",
    "terms_checker",
    "check_terms_acceptance",
    "record_terms_acceptance",
    "get_current_terms",
    "TermsCompliance",
]
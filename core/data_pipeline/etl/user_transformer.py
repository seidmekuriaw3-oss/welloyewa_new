# ============================
# WOLLOYEWA STORE BOT - USER TRANSFORMER
# ============================
"""Transform user data for analytics and warehousing."""

import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime, date

from core.logger import logger
from core.security.pii_masker import pii_masker


class UserTransformer:
    """
    Transform user data for ETL pipeline.
    
    Features:
    - Data cleansing and normalization
    - PII anonymization for analytics
    - Feature engineering for ML
    - Data enrichment with derived fields
    """
    
    def __init__(self, anonymize_pii: bool = True):
        self.anonymize_pii = anonymize_pii
    
    def transform_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform a single user record.
        
        Args:
            user_data: Raw user data from database
            
        Returns:
            Transformed user data ready for warehouse
        """
        transformed = {}
        
        # Basic info (anonymized if needed)
        if self.anonymize_pii:
            transformed['user_id'] = self._anonymize_id(user_data.get('id'))
            transformed['telegram_id'] = self._anonymize_id(user_data.get('telegram_id'))
            transformed['username'] = self._anonymize_username(user_data.get('username'))
            transformed['first_name'] = self._mask_name(user_data.get('first_name'))
            transformed['last_name'] = self._mask_name(user_data.get('last_name'))
            transformed['phone_number'] = pii_masker.mask(user_data.get('phone_number', ''), keep_ends=2)
            transformed['email'] = self._mask_email(user_data.get('email'))
            transformed['city'] = user_data.get('city')  # City is not PII
            transformed['subcity'] = user_data.get('subcity')
        else:
            transformed['user_id'] = user_data.get('id')
            transformed['telegram_id'] = user_data.get('telegram_id')
            transformed['username'] = user_data.get('username')
            transformed['first_name'] = user_data.get('first_name')
            transformed['last_name'] = user_data.get('last_name')
            transformed['phone_number'] = user_data.get('phone_number')
            transformed['email'] = user_data.get('email')
            transformed['city'] = user_data.get('city')
            transformed['subcity'] = user_data.get('subcity')
        
        # Role and status
        transformed['role'] = user_data.get('role')
        transformed['status'] = user_data.get('status')
        
        # Demographics
        transformed['gender'] = user_data.get('gender')
        transformed['age'] = self._calculate_age(user_data.get('date_of_birth'))
        transformed['age_group'] = self._get_age_group(transformed.get('age'))
        
        # Location (city-level only for privacy)
        transformed['city'] = user_data.get('city')
        transformed['city_encoded'] = self._encode_city(user_data.get('city'))
        
        # Time-based features
        created_at = user_data.get('created_at')
        if created_at:
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at)
            transformed['created_at'] = created_at.isoformat()
            transformed['created_year'] = created_at.year
            transformed['created_month'] = created_at.month
            transformed['created_week'] = created_at.isocalendar()[1]
            transformed['days_since_registration'] = (datetime.utcnow() - created_at).days
        else:
            transformed['created_at'] = None
            transformed['created_year'] = None
            transformed['created_month'] = None
            transformed['created_week'] = None
            transformed['days_since_registration'] = None
        
        # Activity flags
        last_active = user_data.get('last_active')
        if last_active:
            if isinstance(last_active, str):
                last_active = datetime.fromisoformat(last_active)
            transformed['last_active'] = last_active.isoformat()
            transformed['days_since_last_active'] = (datetime.utcnow() - last_active).days
            transformed['is_active_recent'] = transformed['days_since_last_active'] <= 7
        else:
            transformed['last_active'] = None
            transformed['days_since_last_active'] = None
            transformed['is_active_recent'] = False
        
        # Verification status
        transformed['is_verified'] = user_data.get('is_verified', False)
        
        # Vendor specific fields
        if user_data.get('vendor_id'):
            transformed['is_vendor'] = True
            transformed['vendor_id'] = user_data.get('vendor_id')
            transformed['business_name'] = user_data.get('business_name')
            transformed['is_vendor_approved'] = user_data.get('is_approved', False)
            transformed['vendor_rating'] = float(user_data.get('rating', 0))
            transformed['vendor_total_sales'] = user_data.get('total_sales', 0)
        else:
            transformed['is_vendor'] = False
            transformed['vendor_id'] = None
            transformed['business_name'] = None
            transformed['is_vendor_approved'] = False
            transformed['vendor_rating'] = 0
            transformed['vendor_total_sales'] = 0
        
        # Customer segment
        transformed['customer_segment'] = self._determine_segment(transformed)
        
        return transformed
    
    def transform_users_batch(self, users_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform a batch of user records."""
        return [self.transform_user(user) for user in users_data]
    
    def _anonymize_id(self, id_value: Optional[int]) -> Optional[str]:
        """Anonymize user ID for analytics."""
        if not id_value:
            return None
        hash_obj = hashlib.blake2b(str(id_value).encode(), digest_size=16)
        return hash_obj.hexdigest()
    
    def _anonymize_username(self, username: Optional[str]) -> Optional[str]:
        """Anonymize username."""
        if not username:
            return None
        return hashlib.md5(username.encode()).hexdigest()[:16]
    
    def _mask_name(self, name: Optional[str]) -> Optional[str]:
        """Mask user name."""
        if not name:
            return None
        if len(name) <= 2:
            return name[0] + "*"
        return name[0] + "*" * (len(name) - 2) + name[-1]
    
    def _mask_email(self, email: Optional[str]) -> Optional[str]:
        """Mask email address."""
        if not email or "@" not in email:
            return email
        
        local, domain = email.split("@", 1)
        if len(local) <= 2:
            masked_local = "*" * len(local)
        else:
            masked_local = local[0] + "*" * (len(local) - 2) + local[-1]
        
        return f"{masked_local}@{domain}"
    
    def _calculate_age(self, dob: Optional[date]) -> Optional[int]:
        """Calculate age from date of birth."""
        if not dob:
            return None
        
        if isinstance(dob, str):
            dob = datetime.fromisoformat(dob).date()
        
        today = datetime.utcnow().date()
        age = today.year - dob.year
        if (today.month, today.day) < (dob.month, dob.day):
            age -= 1
        
        return age if age >= 0 else None
    
    def _get_age_group(self, age: Optional[int]) -> Optional[str]:
        """Get age group from age."""
        if age is None:
            return None
        
        if age < 18:
            return "Under 18"
        elif age < 25:
            return "18-24"
        elif age < 35:
            return "25-34"
        elif age < 45:
            return "35-44"
        elif age < 55:
            return "45-54"
        else:
            return "55+"
    
    def _encode_city(self, city: Optional[str]) -> Optional[int]:
        """Encode city name to integer for ML models."""
        if not city:
            return None
        
        # Simple hash-based encoding
        city_map = {
            'Addis Ababa': 1,
            'Dire Dawa': 2,
            'Mekelle': 3,
            'Gondar': 4,
            'Bahir Dar': 5,
            'Hawassa': 6,
            'Adama': 7,
            'Jimma': 8,
            'Harar': 9,
            'Dessie': 10,
        }
        
        return city_map.get(city, 0)
    
    def _determine_segment(self, transformed: Dict[str, Any]) -> str:
        """
        Determine customer segment based on behavior.
        
        Segments:
        - New: Registered within last 30 days
        - Active: Active within last 7 days
        - At Risk: Inactive 8-30 days
        - Dormant: Inactive 31-90 days
        - Churned: Inactive > 90 days
        """
        days_since_registration = transformed.get('days_since_registration')
        days_since_last_active = transformed.get('days_since_last_active')
        
        if days_since_registration is not None and days_since_registration <= 30:
            return "New"
        
        if days_since_last_active is not None:
            if days_since_last_active <= 7:
                return "Active"
            elif days_since_last_active <= 30:
                return "At Risk"
            elif days_since_last_active <= 90:
                return "Dormant"
            else:
                return "Churned"
        
        return "Unknown"
    
    def enrich_with_order_history(
        self,
        user_data: Dict[str, Any],
        order_history: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Enrich user data with order history.
        
        Args:
            user_data: Transformed user data
            order_history: List of user's orders
            
        Returns:
            Enriched user data
        """
        enriched = user_data.copy()
        
        if not order_history:
            enriched['total_orders'] = 0
            enriched['total_spent'] = 0
            enriched['avg_order_value'] = 0
            enriched['last_order_date'] = None
            enriched['first_order_date'] = None
            enriched['order_frequency_days'] = None
            return enriched
        
        total_orders = len(order_history)
        total_spent = sum(o.get('total', 0) for o in order_history)
        avg_order_value = total_spent / total_orders if total_orders > 0 else 0
        
        order_dates = [o.get('created_at') for o in order_history if o.get('created_at')]
        if order_dates:
            if isinstance(order_dates[0], str):
                order_dates = [datetime.fromisoformat(d) for d in order_dates]
            order_dates.sort()
            first_order = order_dates[0]
            last_order = order_dates[-1]
            
            # Calculate average days between orders
            if len(order_dates) > 1:
                date_diffs = [(order_dates[i] - order_dates[i-1]).days for i in range(1, len(order_dates))]
                order_frequency = sum(date_diffs) / len(date_diffs)
            else:
                order_frequency = None
        else:
            first_order = None
            last_order = None
            order_frequency = None
        
        enriched['total_orders'] = total_orders
        enriched['total_spent'] = round(total_spent, 2)
        enriched['avg_order_value'] = round(avg_order_value, 2)
        enriched['last_order_date'] = last_order.isoformat() if last_order else None
        enriched['first_order_date'] = first_order.isoformat() if first_order else None
        enriched['order_frequency_days'] = round(order_frequency, 1) if order_frequency else None
        
        # Update segment based on order history
        if total_orders > 10:
            enriched['customer_segment'] = "Loyal"
        elif total_orders > 3:
            enriched['customer_segment'] = "Regular"
        elif total_orders > 0:
            enriched['customer_segment'] = "Occasional"
        
        return enriched


async def transform_user_data(
    user_data: Dict[str, Any],
    anonymize: bool = True,
) -> Dict[str, Any]:
    """Convenience function to transform user data."""
    transformer = UserTransformer(anonymize_pii=anonymize)
    return transformer.transform_user(user_data)


async def anonymize_user_data(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience function to anonymize user data."""
    transformer = UserTransformer(anonymize_pii=True)
    return transformer.transform_user(user_data)


async def enrich_user_data(
    user_data: Dict[str, Any],
    order_history: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Convenience function to enrich user data with order history."""
    transformer = UserTransformer(anonymize_pii=True)
    return transformer.enrich_with_order_history(user_data, order_history)


__all__ = [
    "UserTransformer",
    "transform_user_data",
    "anonymize_user_data",
    "enrich_user_data",
]
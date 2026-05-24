# ============================
# WOLLOYEWA STORE BOT - DATE HELPERS
# ============================
"""Date and time utility functions with Ethiopian calendar support."""

from datetime import datetime, date, time, timedelta
from typing import Optional, Union
import pytz

from core.config import settings
from core.constants import ETHIOPIAN_MONTHS, ETHIOPIAN_WEEKDAYS


DateType = Union[datetime, date, str, int]


class DateHelper:
    """Comprehensive date and time utilities."""
    
    # Ethiopian timezone
    ADDIS_ABABA_TZ = pytz.timezone('Africa/Addis_Ababa')
    
    @classmethod
    def now(cls) -> datetime:
        """Get current datetime in Addis Ababa timezone."""
        return datetime.now(cls.ADDIS_ABABA_TZ)
    
    @classmethod
    def today(cls) -> date:
        """Get current date in Addis Ababa timezone."""
        return cls.now().date()
    
    @classmethod
    def utc_now(cls) -> datetime:
        """Get current UTC datetime."""
        return datetime.utcnow()
    
    @classmethod
    def to_addis(cls, dt: datetime) -> datetime:
        """Convert datetime to Addis Ababa timezone."""
        if dt.tzinfo is None:
            dt = pytz.utc.localize(dt)
        return dt.astimezone(cls.ADDIS_ABABA_TZ)
    
    @classmethod
    def to_utc(cls, dt: datetime) -> datetime:
        """Convert datetime to UTC."""
        if dt.tzinfo is None:
            dt = cls.ADDIS_ABABA_TZ.localize(dt)
        return dt.astimezone(pytz.UTC)
    
    @classmethod
    def format_date(
        cls,
        dt: Optional[DateType] = None,
        format_str: str = "%Y-%m-%d",
        locale: str = "am",
    ) -> str:
        """
        Format date for display.
        
        Args:
            dt: Date to format (defaults to current date)
            format_str: Python datetime format string
            locale: Language locale ('am', 'en', 'om')
            
        Returns:
            Formatted date string
        """
        if dt is None:
            dt = cls.today()
        
        if isinstance(dt, (int, str)):
            dt = cls.parse_date(dt)
        
        if locale == "am":
            return cls._format_ethiopian_date(dt)
        
        if isinstance(dt, datetime):
            return dt.strftime(format_str)
        return dt.strftime(format_str)
    
    @classmethod
    def _format_ethiopian_date(cls, dt: Union[datetime, date]) -> str:
        """Format date in Ethiopian calendar."""
        from core.utils.ethiopian_calendar import convert_to_ethiopian
        et_date = convert_to_ethiopian(dt)
        return f"{et_date.day} {et_date.month_name} {et_date.year}"
    
    @classmethod
    def parse_date(
        cls,
        date_str: str,
        formats: Optional[list] = None,
    ) -> Optional[date]:
        """
        Parse date string to date object.
        
        Args:
            date_str: Date string to parse
            formats: List of formats to try (defaults to common formats)
            
        Returns:
            Date object or None if parsing fails
        """
        if formats is None:
            formats = [
                "%Y-%m-%d",
                "%d/%m/%Y",
                "%m/%d/%Y",
                "%Y%m%d",
                "%d-%m-%Y",
                "%m-%d-%Y",
            ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        
        return None
    
    @classmethod
    def parse_datetime(
        cls,
        dt_str: str,
        formats: Optional[list] = None,
    ) -> Optional[datetime]:
        """
        Parse datetime string to datetime object.
        
        Args:
            dt_str: Datetime string to parse
            formats: List of formats to try
            
        Returns:
            Datetime object or None if parsing fails
        """
        if formats is None:
            formats = [
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M:%S.%f",
                "%d/%m/%Y %H:%M:%S",
                "%Y%m%d%H%M%S",
            ]
        
        for fmt in formats:
            try:
                return datetime.strptime(dt_str, fmt)
            except ValueError:
                continue
        
        return None
    
    @classmethod
    def format_timedelta(cls, delta: timedelta, locale: str = "am") -> str:
        """
        Format timedelta for human-readable display.
        
        Args:
            delta: Timedelta object
            locale: Language locale
            
        Returns:
            Human-readable time difference string
        """
        seconds = int(delta.total_seconds())
        
        if seconds < 60:
            return f"{seconds} ሰከንድ" if locale == "am" else f"{seconds} seconds"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes} ደቂቃ" if locale == "am" else f"{minutes} minutes"
        elif seconds < 86400:
            hours = seconds // 3600
            return f"{hours} ሰዓት" if locale == "am" else f"{hours} hours"
        else:
            days = seconds // 86400
            return f"{days} ቀን" if locale == "am" else f"{days} days"
    
    @classmethod
    def time_ago(cls, dt: datetime, locale: str = "am") -> str:
        """
        Get human-readable time ago string.
        
        Args:
            dt: Past datetime
            locale: Language locale
            
        Returns:
            String like "2 hours ago"
        """
        now = cls.now()
        delta = now - cls.to_addis(dt)
        
        seconds = int(delta.total_seconds())
        
        if seconds < 60:
            return f"ከ{seconds} ሰከንድ በፊት" if locale == "am" else f"{seconds} seconds ago"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"ከ{minutes} ደቂቃ በፊት" if locale == "am" else f"{minutes} minutes ago"
        elif seconds < 86400:
            hours = seconds // 3600
            return f"ከ{hours} ሰዓት በፊት" if locale == "am" else f"{hours} hours ago"
        elif seconds < 604800:
            days = seconds // 86400
            return f"ከ{days} ቀን በፊት" if locale == "am" else f"{days} days ago"
        elif seconds < 2592000:
            weeks = seconds // 604800
            return f"ከ{weeks} ሳምንት በፊት" if locale == "am" else f"{weeks} weeks ago"
        else:
            return cls.format_date(dt, locale=locale)
    
    @classmethod
    def days_between(cls, start: DateType, end: DateType) -> int:
        """Calculate number of days between two dates."""
        start_date = cls._to_date(start)
        end_date = cls._to_date(end)
        return (end_date - start_date).days
    
    @classmethod
    def add_days(cls, dt: DateType, days: int) -> date:
        """Add days to a date."""
        date_obj = cls._to_date(dt)
        return date_obj + timedelta(days=days)
    
    @classmethod
    def start_of_day(cls, dt: Optional[DateType] = None) -> datetime:
        """Get start of day (00:00:00)."""
        if dt is None:
            dt = cls.today()
        date_obj = cls._to_date(dt)
        return datetime.combine(date_obj, time.min).replace(tzinfo=cls.ADDIS_ABABA_TZ)
    
    @classmethod
    def end_of_day(cls, dt: Optional[DateType] = None) -> datetime:
        """Get end of day (23:59:59)."""
        if dt is None:
            dt = cls.today()
        date_obj = cls._to_date(dt)
        return datetime.combine(date_obj, time.max).replace(tzinfo=cls.ADDIS_ABABA_TZ)
    
    @classmethod
    def start_of_week(cls, dt: Optional[DateType] = None) -> datetime:
        """Get start of week (Monday)."""
        if dt is None:
            dt = cls.today()
        date_obj = cls._to_date(dt)
        start = date_obj - timedelta(days=date_obj.weekday())
        return cls.start_of_day(start)
    
    @classmethod
    def start_of_month(cls, dt: Optional[DateType] = None) -> datetime:
        """Get start of month."""
        if dt is None:
            dt = cls.today()
        date_obj = cls._to_date(dt)
        start = date_obj.replace(day=1)
        return cls.start_of_day(start)
    
    @classmethod
    def start_of_year(cls, dt: Optional[DateType] = None) -> datetime:
        """Get start of year."""
        if dt is None:
            dt = cls.today()
        date_obj = cls._to_date(dt)
        start = date_obj.replace(month=1, day=1)
        return cls.start_of_day(start)
    
    @classmethod
    def _to_date(cls, dt: DateType) -> date:
        """Convert various types to date."""
        if isinstance(dt, datetime):
            return dt.date()
        elif isinstance(dt, date):
            return dt
        elif isinstance(dt, str):
            parsed = cls.parse_date(dt)
            if parsed:
                return parsed
            raise ValueError(f"Cannot parse date: {dt}")
        elif isinstance(dt, int):
            return datetime.fromtimestamp(dt).date()
        else:
            raise ValueError(f"Unsupported date type: {type(dt)}")
    
    @classmethod
    def is_today(cls, dt: DateType) -> bool:
        """Check if date is today."""
        return cls._to_date(dt) == cls.today()
    
    @classmethod
    def is_this_week(cls, dt: DateType) -> bool:
        """Check if date is within current week."""
        date_obj = cls._to_date(dt)
        today = cls.today()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        return week_start <= date_obj <= week_end
    
    @classmethod
    def is_this_month(cls, dt: DateType) -> bool:
        """Check if date is within current month."""
        date_obj = cls._to_date(dt)
        today = cls.today()
        return date_obj.year == today.year and date_obj.month == today.month
    
    @classmethod
    def age(cls, birth_date: DateType) -> int:
        """Calculate age from birth date."""
        birth = cls._to_date(birth_date)
        today = cls.today()
        age = today.year - birth.year
        if (today.month, today.day) < (birth.month, birth.day):
            age -= 1
        return age


def format_date(dt: Optional[DateType] = None, locale: str = "am") -> str:
    """Convenience function to format date."""
    return DateHelper.format_date(dt, locale=locale)


def time_ago(dt: datetime, locale: str = "am") -> str:
    """Convenience function to get time ago string."""
    return DateHelper.time_ago(dt, locale)


def get_current_ethiopian_date() -> tuple:
    """Get current Ethiopian date (year, month, day)."""
    from core.utils.ethiopian_calendar import get_current_ethiopian_date
    return get_current_ethiopian_date()


def convert_to_ethiopian_calendar(gregorian_date: DateType) -> tuple:
    """Convert Gregorian date to Ethiopian calendar."""
    from core.utils.ethiopian_calendar import convert_to_ethiopian
    et_date = convert_to_ethiopian(gregorian_date)
    return (et_date.year, et_date.month, et_date.day)


__all__ = [
    "DateHelper",
    "format_date",
    "time_ago",
    "get_current_ethiopian_date",
    "convert_to_ethiopian_calendar",
]
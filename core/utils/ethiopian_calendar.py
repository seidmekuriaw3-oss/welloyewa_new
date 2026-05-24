# ============================
# WOLLOYEWA STORE BOT - ETHIOPIAN CALENDAR
# ============================
"""Ethiopian calendar conversion and date utilities."""

from datetime import date, datetime, timedelta
from typing import Optional, Tuple, Union
from dataclasses import dataclass

from core.constants import ETHIOPIAN_MONTHS, ETHIOPIAN_WEEKDAYS
from core.logger import logger


@dataclass
class EthiopianDate:
    """Represents a date in the Ethiopian calendar."""
    
    year: int
    month: int
    day: int
    
    @property
    def month_name(self) -> str:
        """Get name of the month in Amharic."""
        if 1 <= self.month <= 13:
            return ETHIOPIAN_MONTHS[self.month - 1]
        return "የማይታወቅ"
    
    @property
    def is_pagume(self) -> bool:
        """Check if date is in Pagume (13th month)."""
        return self.month == 13
    
    def to_gregorian(self) -> date:
        """Convert Ethiopian date to Gregorian date."""
        return convert_to_gregorian(self.year, self.month, self.day)
    
    def __str__(self) -> str:
        return f"{self.day} {self.month_name} {self.year} (ኢትዮጵያ)"
    
    def __repr__(self) -> str:
        return f"EthiopianDate(year={self.year}, month={self.month}, day={self.day})"


class EthiopianCalendar:
    """
    Ethiopian calendar utilities.
    
    The Ethiopian calendar has 12 months of 30 days each and a 13th month
    called Pagume which has 5 days (6 in leap years).
    
    Ethiopian year is approximately 7-8 years behind Gregorian calendar.
    """
    
    # Ethiopian calendar epoch (Gregorian date for Ethiopian New Year)
    # Ethiopian year 1 starts on August 29, 8 AD (Julian) / August 26, 8 AD (Gregorian)
    # For simplicity, we use known reference point
    
    # Reference: Ethiopian year 2000 started on September 11, 2007 (Gregorian)
    REFERENCE_ETHIOPIAN_YEAR = 2000
    REFERENCE_GREGORIAN_DATE = date(2007, 9, 11)
    
    # Days in each month
    MONTH_DAYS = [30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 5]
    LEAP_MONTH_DAYS = [30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 6]
    
    @classmethod
    def is_ethiopian_leap_year(cls, ethiopian_year: int) -> bool:
        """
        Check if Ethiopian year is a leap year.
        
        Ethiopian leap years occur every 4 years.
        """
        return ethiopian_year % 4 == 0
    
    @classmethod
    def get_month_days(cls, ethiopian_year: int, month: int) -> int:
        """Get number of days in an Ethiopian month."""
        if month < 1 or month > 13:
            raise ValueError(f"Invalid month: {month}. Must be 1-13")
        
        if month == 13:
            return cls.LEAP_MONTH_DAYS[12] if cls.is_ethiopian_leap_year(ethiopian_year) else cls.MONTH_DAYS[12]
        
        return cls.MONTH_DAYS[month - 1]
    
    @classmethod
    def days_since_reference(cls, ethiopian_year: int, ethiopian_month: int, ethiopian_day: int) -> int:
        """Calculate days since reference Ethiopian date."""
        days = 0
        
        # Add days from years
        for year in range(cls.REFERENCE_ETHIOPIAN_YEAR, ethiopian_year):
            days += 365 + (1 if cls.is_ethiopian_leap_year(year) else 0)
        
        # Add days from months
        for month in range(1, ethiopian_month):
            days += cls.get_month_days(ethiopian_year, month)
        
        # Add days
        days += ethiopian_day - 1
        
        return days
    
    @classmethod
    def from_gregorian(cls, gregorian_date: date) -> EthiopianDate:
        """
        Convert Gregorian date to Ethiopian date.
        
        Args:
            gregorian_date: Gregorian date to convert
            
        Returns:
            EthiopianDate object
        """
        # Calculate days difference from reference
        delta_days = (gregorian_date - cls.REFERENCE_GREGORIAN_DATE).days
        
        if delta_days < 0:
            # Handle dates before reference (fallback)
            return cls._approximate_conversion(gregorian_date)
        
        # Find Ethiopian year
        ethiopian_year = cls.REFERENCE_ETHIOPIAN_YEAR
        days_remaining = delta_days
        
        while days_remaining >= 0:
            year_days = 365 + (1 if cls.is_ethiopian_leap_year(ethiopian_year) else 0)
            if days_remaining < year_days:
                break
            days_remaining -= year_days
            ethiopian_year += 1
        
        # Find month
        for month in range(1, 14):
            month_days = cls.get_month_days(ethiopian_year, month)
            if days_remaining < month_days:
                return EthiopianDate(
                    year=ethiopian_year,
                    month=month,
                    day=days_remaining + 1
                )
            days_remaining -= month_days
        
        # Should not reach here
        return EthiopianDate(year=ethiopian_year, month=1, day=1)
    
    @classmethod
    def _approximate_conversion(cls, gregorian_date: date) -> EthiopianDate:
        """Approximate conversion for dates before reference point."""
        # Simplified conversion: Ethiopian year = Gregorian year - 7 or -8
        greg_year = gregorian_date.year
        greg_month = gregorian_date.month
        
        # Ethiopian year is 7-8 years behind
        if greg_month < 9:
            eth_year = greg_year - 8
        else:
            eth_year = greg_year - 7
        
        # Rough month conversion
        if greg_month >= 9:
            eth_month = greg_month - 8
        else:
            eth_month = greg_month + 4
        
        # Day (simplified)
        eth_day = gregorian_date.day
        
        return EthiopianDate(year=eth_year, month=eth_month, day=eth_day)
    
    @classmethod
    def to_gregorian(cls, ethiopian_year: int, ethiopian_month: int, ethiopian_day: int) -> date:
        """
        Convert Ethiopian date to Gregorian date.
        
        Args:
            ethiopian_year: Ethiopian year
            ethiopian_month: Ethiopian month (1-13)
            ethiopian_day: Ethiopian day
            
        Returns:
            Gregorian date
        """
        # Validate inputs
        if ethiopian_month < 1 or ethiopian_month > 13:
            raise ValueError(f"Invalid month: {ethiopian_month}. Must be 1-13")
        
        max_day = cls.get_month_days(ethiopian_year, ethiopian_month)
        if ethiopian_day < 1 or ethiopian_day > max_day:
            raise ValueError(f"Invalid day: {ethiopian_day} for month {ethiopian_month}. Max: {max_day}")
        
        # Calculate days from reference
        days_offset = cls.days_since_reference(ethiopian_year, ethiopian_month, ethiopian_day)
        
        # Add to reference Gregorian date
        gregorian_date = cls.REFERENCE_GREGORIAN_DATE + timedelta(days=days_offset)
        
        return gregorian_date
    
    @classmethod
    def get_current_ethiopian_date(cls) -> EthiopianDate:
        """Get current Ethiopian date."""
        return cls.from_gregorian(date.today())
    
    @classmethod
    def format_ethiopian_date(cls, eth_date: EthiopianDate, include_weekday: bool = False) -> str:
        """Format Ethiopian date as string."""
        if include_weekday:
            weekday = cls.get_ethiopian_weekday(eth_date)
            return f"{weekday}፣ {eth_date.day} {eth_date.month_name} {eth_date.year}"
        return f"{eth_date.day} {eth_date.month_name} {eth_date.year}"
    
    @classmethod
    def get_ethiopian_weekday(cls, eth_date: EthiopianDate) -> str:
        """Get Ethiopian weekday name."""
        # Convert to Gregorian to get weekday
        greg_date = cls.to_gregorian(eth_date.year, eth_date.month, eth_date.day)
        weekday_index = greg_date.weekday()
        # Adjust for Monday as first day (Ethiopian: Monday = 1)
        return ETHIOPIAN_WEEKDAYS[weekday_index]
    
    @classmethod
    def get_ethiopian_holidays(cls, year: int) -> dict:
        """
        Get major Ethiopian holidays for a given year.
        
        Args:
            year: Ethiopian year
            
        Returns:
            Dictionary of holiday names and Ethiopian dates
        """
        holidays = {
            "Enkutatash (New Year)": EthiopianDate(year=year, month=1, day=1),
            "Meskel": EthiopianDate(year=year, month=1, day=17),
            "Genna (Christmas)": EthiopianDate(year=year, month=4, day=29),
            "Timkat (Epiphany)": EthiopianDate(year=year, month=5, day=11),
            "Adwa Victory Day": EthiopianDate(year=year, month=1, day=23),
            "Ethiopian Patriots Day": EthiopianDate(year=year, month=2, day=20),
            "International Workers' Day": EthiopianDate(year=year, month=8, day=23),
            "Derg Downfall Day": EthiopianDate(year=year, month=11, day=4),
            "Fasika (Easter)": cls._calculate_easter_ethiopian(year),
            "Kidus Yohannes": EthiopianDate(year=year, month=6, day=1),
            "Birthday of Prophet Muhammad": EthiopianDate(year=year, month=4, day=12),
        }
        return holidays
    
    @classmethod
    def _calculate_easter_ethiopian(cls, year: int) -> EthiopianDate:
        """Calculate Ethiopian Easter (Fasika) date for a given year."""
        # Simplified: Easter is usually in month 10 (Miazia)
        # In Ethiopian calendar, Easter falls on 10th month (Miazia)
        return EthiopianDate(year=year, month=10, day=15)
    
    @classmethod
    def add_days(cls, eth_date: EthiopianDate, days: int) -> EthiopianDate:
        """Add days to an Ethiopian date."""
        greg_date = cls.to_gregorian(eth_date.year, eth_date.month, eth_date.day)
        new_greg_date = greg_date + timedelta(days=days)
        return cls.from_gregorian(new_greg_date)
    
    @classmethod
    def add_months(cls, eth_date: EthiopianDate, months: int) -> EthiopianDate:
        """Add months to an Ethiopian date."""
        new_month = eth_date.month + months
        new_year = eth_date.year + (new_month - 1) // 13
        new_month = ((new_month - 1) % 13) + 1
        
        # Adjust day if necessary
        max_day = cls.get_month_days(new_year, new_month)
        new_day = min(eth_date.day, max_day)
        
        return EthiopianDate(year=new_year, month=new_month, day=new_day)
    
    @classmethod
    def add_years(cls, eth_date: EthiopianDate, years: int) -> EthiopianDate:
        """Add years to an Ethiopian date."""
        new_year = eth_date.year + years
        # Handle Pagume edge case
        if eth_date.month == 13 and not cls.is_ethiopian_leap_year(new_year):
            return EthiopianDate(year=new_year, month=13, day=5)
        return EthiopianDate(year=new_year, month=eth_date.month, day=eth_date.day)


def convert_to_ethiopian(gregorian_date: Union[date, datetime, str]) -> EthiopianDate:
    """Convert Gregorian date to Ethiopian date (convenience function)."""
    if isinstance(gregorian_date, datetime):
        gregorian_date = gregorian_date.date()
    elif isinstance(gregorian_date, str):
        gregorian_date = date.fromisoformat(gregorian_date)
    
    return EthiopianCalendar.from_gregorian(gregorian_date)


def convert_to_gregorian(
    ethiopian_year: int,
    ethiopian_month: int,
    ethiopian_day: int,
) -> date:
    """Convert Ethiopian date to Gregorian date (convenience function)."""
    return EthiopianCalendar.to_gregorian(ethiopian_year, ethiopian_month, ethiopian_day)


def get_current_ethiopian_date() -> EthiopianDate:
    """Get current Ethiopian date (convenience function)."""
    return EthiopianCalendar.get_current_ethiopian_date()


def get_ethiopian_holidays(year: int) -> dict:
    """Get Ethiopian holidays for a given year."""
    return EthiopianCalendar.get_ethiopian_holidays(year)


def format_ethiopian_date(date_obj: Union[EthiopianDate, date, datetime], include_weekday: bool = False) -> str:
    """Format date as Ethiopian date string."""
    if isinstance(date_obj, (date, datetime)):
        eth_date = convert_to_ethiopian(date_obj)
    else:
        eth_date = date_obj
    
    return EthiopianCalendar.format_ethiopian_date(eth_date, include_weekday)


__all__ = [
    "EthiopianDate",
    "EthiopianCalendar",
    "convert_to_ethiopian",
    "convert_to_gregorian",
    "get_current_ethiopian_date",
    "get_ethiopian_holidays",
    "format_ethiopian_date",
]
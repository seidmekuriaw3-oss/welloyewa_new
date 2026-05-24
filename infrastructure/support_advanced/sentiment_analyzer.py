# ============================
# WOLLOYEWA STORE BOT - SENTIMENT ANALYZER
# ============================
"""Sentiment analysis for customer messages and feedback."""

import re
from enum import Enum
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from core.logger import logger


class SentimentScore(str, Enum):
    """Sentiment classification."""
    VERY_POSITIVE = "very_positive"
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    VERY_NEGATIVE = "very_negative"


@dataclass
class SentimentResult:
    """Sentiment analysis result."""
    
    score: SentimentScore
    confidence: float
    positive_words: List[str] = field(default_factory=list)
    negative_words: List[str] = field(default_factory=list)
    neutral_words: List[str] = field(default_factory=list)
    numeric_score: float = 0.0  # -1 to +1


class SentimentAnalyzer:
    """
    Sentiment analyzer for customer messages.
    
    Features:
    - Multi-language support (English, Amharic)
    - Word-based sentiment scoring
    - Confidence calculation
    - Trend analysis
    """
    
    def __init__(self):
        self._positive_words = self._init_positive_words()
        self._negative_words = self._init_negative_words()
        self._intensifiers = ["very", "really", "extremely", "so", "too", "በጣም", "እጅግ"]
        self._negations = ["not", "no", "never", "isn't", "wasn't", "አል", "ኣል", "ኣይ"]
    
    def _init_positive_words(self) -> Dict[str, List[str]]:
        """Initialize positive word lists by language."""
        return {
            "en": ["good", "great", "excellent", "amazing", "wonderful", "fantastic", "awesome",
                   "love", "like", "happy", "pleased", "satisfied", "perfect", "best", "nice",
                   "helpful", "quick", "fast", "reliable", "recommend", "thank", "thanks"],
            "am": ["ጥሩ", "በጣም ጥሩ", "ደስ ያለኝ", "አመሰግናለሁ", "እናመሰግናለን", "ደስተኛ", "ረክቻለሁ"],
        }
    
    def _init_negative_words(self) -> Dict[str, List[str]]:
        """Initialize negative word lists by language."""
        return {
            "en": ["bad", "poor", "terrible", "awful", "horrible", "disappointed", "frustrated",
                   "hate", "dislike", "angry", "upset", "worst", "slow", "broken", "damaged",
                   "wrong", "issue", "problem", "complaint", "unhappy", "unsatisfied"],
            "am": ["መጥፎ", "አልወደድኩትም", "ተበሳጨሁ", "ችግር", "ስህተት", "ተሰበረ", "ተበላሸ"],
        }
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into words."""
        # Convert to lowercase
        text = text.lower()
        # Remove punctuation
        text = re.sub(r'[^\w\s]', ' ', text)
        # Split into words
        return text.split()
    
    def analyze(
        self,
        text: str,
        language: str = "en",
    ) -> SentimentResult:
        """
        Analyze sentiment of text.
        
        Args:
            text: Text to analyze
            language: Language code (en, am)
            
        Returns:
            SentimentResult
        """
        tokens = self._tokenize(text)
        
        positive_words = self._positive_words.get(language, [])
        negative_words = self._negative_words.get(language, [])
        
        found_positive = []
        found_negative = []
        found_neutral = []
        
        score = 0
        negation_active = False
        
        for i, token in enumerate(tokens):
            # Check for negations
            if token in self._negations:
                negation_active = True
                continue
            
            # Check for intensifiers
            intensity = 1.5 if token in self._intensifiers else 1.0
            
            # Check sentiment
            if token in positive_words:
                word_score = intensity if not negation_active else -intensity
                score += word_score
                found_positive.append(token)
            elif token in negative_words:
                word_score = -intensity if not negation_active else intensity
                score += word_score
                found_negative.append(token)
            else:
                found_neutral.append(token)
            
            # Reset negation after processing a word
            negation_active = False
        
        # Normalize score to -1 to +1 range
        max_score = len(tokens) * 1.5
        if max_score > 0:
            normalized_score = max(-1, min(1, score / max_score))
        else:
            normalized_score = 0
        
        # Determine sentiment score
        if normalized_score >= 0.6:
            sentiment = SentimentScore.VERY_POSITIVE
        elif normalized_score >= 0.2:
            sentiment = SentimentScore.POSITIVE
        elif normalized_score >= -0.2:
            sentiment = SentimentScore.NEUTRAL
        elif normalized_score >= -0.6:
            sentiment = SentimentScore.NEGATIVE
        else:
            sentiment = SentimentScore.VERY_NEGATIVE
        
        # Calculate confidence based on number of sentiment words found
        total_sentiment_words = len(found_positive) + len(found_negative)
        confidence = min(0.95, total_sentiment_words / (len(tokens) / 2 + 1)) if tokens else 0.5
        
        return SentimentResult(
            score=sentiment,
            confidence=confidence,
            positive_words=found_positive[:5],
            negative_words=found_negative[:5],
            neutral_words=found_neutral[:5],
            numeric_score=normalized_score,
        )
    
    def analyze_ticket(
        self,
        ticket_subject: str,
        ticket_message: str,
        language: str = "en",
    ) -> SentimentResult:
        """
        Analyze sentiment of a support ticket.
        
        Args:
            ticket_subject: Ticket subject
            ticket_message: Ticket message
            language: Language code
            
        Returns:
            SentimentResult
        """
        combined = f"{ticket_subject} {ticket_message}"
        return self.analyze(combined, language)
    
    def get_trend(
        self,
        results: List[SentimentResult],
    ) -> Dict[str, Any]:
        """
        Analyze sentiment trend over time.
        
        Args:
            results: List of sentiment results
            
        Returns:
            Trend analysis
        """
        if not results:
            return {"trend": "stable", "change": 0}
        
        recent = results[-7:] if len(results) > 7 else results
        older = results[:7] if len(results) > 14 else []
        
        recent_avg = sum(r.numeric_score for r in recent) / len(recent)
        older_avg = sum(r.numeric_score for r in older) / len(older) if older else recent_avg
        
        change = recent_avg - older_avg
        
        if change > 0.1:
            trend = "improving"
        elif change < -0.1:
            trend = "declining"
        else:
            trend = "stable"
        
        return {
            "trend": trend,
            "change": round(change, 3),
            "recent_score": round(recent_avg, 3),
            "period_average": round(recent_avg, 3),
        }


# Global sentiment analyzer
sentiment_analyzer = SentimentAnalyzer()


def analyze_sentiment(text: str, language: str = "en") -> SentimentResult:
    """Analyze sentiment of text."""
    return sentiment_analyzer.analyze(text, language)


def analyze_ticket_sentiment(subject: str, message: str) -> SentimentResult:
    """Analyze sentiment of a support ticket."""
    return sentiment_analyzer.analyze_ticket(subject, message)


def get_sentiment_stats(results: List[SentimentResult]) -> Dict[str, Any]:
    """Get sentiment statistics."""
    if not results:
        return {
            "total": 0,
            "distribution": {},
            "average_score": 0,
            "positive_rate": 0,
            "negative_rate": 0,
        }
    
    distribution = {
        SentimentScore.VERY_POSITIVE.value: 0,
        SentimentScore.POSITIVE.value: 0,
        SentimentScore.NEUTRAL.value: 0,
        SentimentScore.NEGATIVE.value: 0,
        SentimentScore.VERY_NEGATIVE.value: 0,
    }
    
    for r in results:
        distribution[r.score.value] = distribution.get(r.score.value, 0) + 1
    
    total = len(results)
    positive_count = distribution[SentimentScore.VERY_POSITIVE.value] + distribution[SentimentScore.POSITIVE.value]
    negative_count = distribution[SentimentScore.VERY_NEGATIVE.value] + distribution[SentimentScore.NEGATIVE.value]
    
    avg_score = sum(r.numeric_score for r in results) / total if total > 0 else 0
    
    return {
        "total": total,
        "distribution": distribution,
        "average_score": round(avg_score, 3),
        "positive_rate": round(positive_count / total * 100, 2),
        "negative_rate": round(negative_count / total * 100, 2),
        "neutral_rate": round(distribution[SentimentScore.NEUTRAL.value] / total * 100, 2),
    }


__all__ = [
    "SentimentAnalyzer",
    "SentimentResult",
    "SentimentScore",
    "sentiment_analyzer",
    "analyze_sentiment",
    "analyze_ticket_sentiment",
    "get_sentiment_stats",
]
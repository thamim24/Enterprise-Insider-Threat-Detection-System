"""
ML-based Document Sensitivity Classifier

This module provides automatic classification of document sensitivity levels
based on content analysis. It uses keyword matching, pattern recognition,
and confidence scoring to predict sensitivity.

The hybrid approach compares user-declared sensitivity with ML-predicted
sensitivity to detect potential data exfiltration attempts.
"""

import re
from typing import Tuple, Dict, List
from dataclasses import dataclass
from enum import Enum


class PredictedSensitivity(Enum):
    """Predicted sensitivity levels"""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"


@dataclass
class SensitivityPrediction:
    """Result of sensitivity classification"""
    predicted_level: str
    confidence: float
    risk_indicators: List[str]
    keyword_matches: Dict[str, List[str]]
    is_mismatch: bool = False
    mismatch_risk_score: float = 0.0
    explanation: str = ""


# Keyword patterns for each sensitivity level
CONFIDENTIAL_KEYWORDS = {
    # Financial
    "financial": ["salary", "compensation", "bonus", "revenue", "profit", "loss", 
                  "budget", "forecast", "quarterly", "annual report", "earnings",
                  "financial statement", "balance sheet", "income statement",
                  "tax", "audit", "fiscal", "dividend", "stock option", "equity"],
    
    # Personal/HR
    "personal": ["ssn", "social security", "employee id", "date of birth", "dob",
                 "home address", "personal phone", "medical", "health record",
                 "performance review", "disciplinary", "termination", "resignation",
                 "salary history", "background check", "drug test"],
    
    # Security
    "security": ["password", "credential", "secret key", "api key", "private key",
                 "access token", "authentication", "authorization", "encryption key",
                 "security protocol", "firewall", "vulnerability", "penetration test",
                 "security audit", "incident report", "breach"],
    
    # Legal
    "legal": ["contract", "agreement", "nda", "non-disclosure", "lawsuit", "litigation",
              "settlement", "confidential agreement", "proprietary", "trade secret",
              "intellectual property", "patent", "trademark", "copyright"],
    
    # Strategic
    "strategic": ["merger", "acquisition", "restructuring", "layoff", "downsizing",
                  "strategic plan", "competitive analysis", "market strategy",
                  "product roadmap", "unreleased", "pre-announcement", "insider"],
}

INTERNAL_KEYWORDS = {
    # Operations
    "operations": ["internal memo", "staff meeting", "department update", "policy",
                   "procedure", "guideline", "workflow", "process document",
                   "training material", "onboarding", "handbook"],
    
    # Project
    "project": ["project plan", "timeline", "milestone", "deliverable", "sprint",
                "backlog", "requirements", "specification", "design document",
                "architecture", "technical document"],
    
    # Communication
    "communication": ["internal communication", "team update", "all-hands",
                      "newsletter", "announcement", "notice", "reminder"],
}

PUBLIC_KEYWORDS = {
    # Marketing
    "marketing": ["press release", "public announcement", "marketing material",
                  "brochure", "advertisement", "promotional", "campaign",
                  "public statement", "media kit"],
    
    # General
    "general": ["public information", "general knowledge", "open source",
                "publicly available", "external communication", "customer facing"],
}

# Regex patterns for sensitive data
SENSITIVE_PATTERNS = {
    "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
    "credit_card": r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b",
    "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    "phone": r"\b\d{3}[- .]?\d{3}[- .]?\d{4}\b",
    "money": r"\$[\d,]+(?:\.\d{2})?|\b\d+(?:,\d{3})*(?:\.\d{2})?\s*(?:USD|dollars?|EUR|euros?)\b",
    "percentage": r"\b\d+(?:\.\d+)?%\b",
    "api_key": r"\b[A-Za-z0-9]{32,}\b",
    "password_field": r"(?i)password\s*[:=]\s*\S+",
}


def classify_document_sensitivity(content: str) -> SensitivityPrediction:
    """
    Classify document sensitivity based on content analysis.
    
    Args:
        content: The document content to analyze
        
    Returns:
        SensitivityPrediction with predicted level and confidence
    """
    content_lower = content.lower()
    
    # Track matches for each category
    confidential_matches = {}
    internal_matches = {}
    public_matches = {}
    
    confidential_score = 0.0
    internal_score = 0.0
    public_score = 0.0
    
    risk_indicators = []
    
    # Check confidential keywords
    for category, keywords in CONFIDENTIAL_KEYWORDS.items():
        matches = []
        for keyword in keywords:
            if keyword.lower() in content_lower:
                matches.append(keyword)
                confidential_score += 0.15  # Higher weight for confidential
        if matches:
            confidential_matches[category] = matches
            
    # Check internal keywords
    for category, keywords in INTERNAL_KEYWORDS.items():
        matches = []
        for keyword in keywords:
            if keyword.lower() in content_lower:
                matches.append(keyword)
                internal_score += 0.1
        if matches:
            internal_matches[category] = matches
            
    # Check public keywords
    for category, keywords in PUBLIC_KEYWORDS.items():
        matches = []
        for keyword in keywords:
            if keyword.lower() in content_lower:
                matches.append(keyword)
                public_score += 0.1
        if matches:
            public_matches[category] = matches
    
    # Check sensitive patterns (high risk indicators)
    for pattern_name, pattern in SENSITIVE_PATTERNS.items():
        if re.search(pattern, content, re.IGNORECASE):
            confidential_score += 0.25  # Patterns are strong indicators
            risk_indicators.append(f"Detected {pattern_name} pattern")
    
    # Normalize scores
    total_score = confidential_score + internal_score + public_score
    if total_score > 0:
        confidential_score /= total_score
        internal_score /= total_score
        public_score /= total_score
    else:
        # Default to internal if no keywords found
        internal_score = 0.6
        confidential_score = 0.2
        public_score = 0.2
    
    # Determine predicted level
    all_matches = {}
    if confidential_score >= internal_score and confidential_score >= public_score:
        predicted_level = "confidential"
        confidence = min(confidential_score + 0.2, 1.0)  # Boost confidence
        all_matches = confidential_matches
    elif internal_score >= public_score:
        predicted_level = "internal"
        confidence = min(internal_score + 0.1, 1.0)
        all_matches = internal_matches
    else:
        predicted_level = "public"
        confidence = min(public_score + 0.1, 1.0)
        all_matches = public_matches
    
    # Build explanation
    if all_matches:
        match_summary = ", ".join([f"{cat}: {', '.join(kws[:3])}" 
                                   for cat, kws in list(all_matches.items())[:3]])
        explanation = f"ML detected {predicted_level} content based on: {match_summary}"
    else:
        explanation = f"ML classified as {predicted_level} (default classification, no strong indicators)"
    
    if risk_indicators:
        explanation += f". Risk indicators: {', '.join(risk_indicators[:3])}"
    
    return SensitivityPrediction(
        predicted_level=predicted_level,
        confidence=round(confidence, 2),
        risk_indicators=risk_indicators,
        keyword_matches=all_matches,
        explanation=explanation
    )


def compare_sensitivity(
    user_declared: str, 
    ml_predicted: str, 
    ml_confidence: float
) -> Tuple[bool, float, str]:
    """
    Compare user-declared sensitivity with ML prediction.
    
    Returns:
        Tuple of (is_mismatch, risk_score_modifier, explanation)
    """
    # Sensitivity hierarchy (higher = more sensitive)
    hierarchy = {"public": 1, "internal": 2, "confidential": 3}
    
    user_level = hierarchy.get(user_declared.lower(), 2)
    ml_level = hierarchy.get(ml_predicted.lower(), 2)
    
    if user_level == ml_level:
        return False, 0.0, "Sensitivity levels match"
    
    # User declares LOWER sensitivity than ML predicts - SUSPICIOUS
    if user_level < ml_level:
        severity = ml_level - user_level  # 1 or 2 levels difference
        risk_modifier = 0.3 * severity * ml_confidence
        explanation = (
            f"⚠️ SENSITIVITY MISMATCH: User declared '{user_declared}' but "
            f"ML detected '{ml_predicted}' (confidence: {ml_confidence:.0%}). "
            f"Potential attempt to bypass security controls!"
        )
        return True, risk_modifier, explanation
    
    # User declares HIGHER sensitivity than ML predicts - Less suspicious
    # Could be overly cautious (acceptable) or trying to restrict access
    risk_modifier = 0.05 * ml_confidence
    explanation = (
        f"User declared '{user_declared}' but ML suggests '{ml_predicted}' "
        f"(confidence: {ml_confidence:.0%}). User may be overly cautious."
    )
    return False, risk_modifier, explanation


def analyze_document_for_upload(
    content: str, 
    user_declared_sensitivity: str
) -> Dict:
    """
    Full analysis of document for upload, comparing user declaration with ML prediction.
    
    Args:
        content: Document content
        user_declared_sensitivity: User's declared sensitivity level
        
    Returns:
        Dictionary with analysis results
    """
    # Get ML prediction
    prediction = classify_document_sensitivity(content)
    
    # Compare with user declaration
    is_mismatch, risk_modifier, mismatch_explanation = compare_sensitivity(
        user_declared_sensitivity,
        prediction.predicted_level,
        prediction.confidence
    )
    
    # Update prediction with mismatch info
    prediction.is_mismatch = is_mismatch
    prediction.mismatch_risk_score = risk_modifier
    
    return {
        "ml_predicted_sensitivity": prediction.predicted_level,
        "ml_confidence": prediction.confidence,
        "user_declared_sensitivity": user_declared_sensitivity.lower(),
        "is_mismatch": is_mismatch,
        "mismatch_risk_modifier": risk_modifier,
        "risk_indicators": prediction.risk_indicators,
        "keyword_matches": prediction.keyword_matches,
        "ml_explanation": prediction.explanation,
        "mismatch_explanation": mismatch_explanation if is_mismatch else None,
        "should_alert": is_mismatch and risk_modifier > 0.2,
    }

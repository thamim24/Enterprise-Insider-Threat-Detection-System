"""
Risk Fusion Engine
Combines behavioral anomaly, document sensitivity, and integrity signals
into unified risk scores
Extracted and refactored from notebook prototype
"""
import numpy as np
from typing import Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class RiskLevel(str, Enum):
    """Risk level classifications"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class RiskComponents:
    """Individual risk components before fusion"""
    behavior_score: float = 0.0
    classification_score: float = 0.0
    integrity_score: float = 0.0
    
    # Additional context scores
    cross_department_multiplier: float = 1.0
    action_multiplier: float = 1.0
    temporal_multiplier: float = 1.0


@dataclass
class RiskAssessment:
    """Complete risk assessment result"""
    # Final scores
    risk_score: float
    risk_level: RiskLevel
    severity_label: str
    
    # Components
    components: RiskComponents
    weighted_components: Dict[str, float]
    
    # Context
    is_anomalous: bool
    is_cross_department: bool
    requires_alert: bool
    
    # Explanation
    primary_risk_factor: str
    risk_factors: list
    
    # Metadata
    assessed_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'risk_score': self.risk_score,
            'risk_level': self.risk_level.value,
            'severity_label': self.severity_label,
            'components': {
                'behavior': self.components.behavior_score,
                'classification': self.components.classification_score,
                'integrity': self.components.integrity_score,
                'cross_dept_multiplier': self.components.cross_department_multiplier,
                'action_multiplier': self.components.action_multiplier,
                'temporal_multiplier': self.components.temporal_multiplier
            },
            'weighted_components': self.weighted_components,
            'is_anomalous': self.is_anomalous,
            'is_cross_department': self.is_cross_department,
            'requires_alert': self.requires_alert,
            'primary_risk_factor': self.primary_risk_factor,
            'risk_factors': self.risk_factors,
            'assessed_at': self.assessed_at.isoformat()
        }


class RiskFusionEngine:
    """
    Fuses multiple risk signals into unified risk assessment
    This is the core decision engine for the threat detection platform
    """
    
    # Default fusion weights
    DEFAULT_WEIGHTS = {
        'behavior': 0.4,
        'classification': 0.3,
        'integrity': 0.3
    }
    
    # Risk level thresholds
    RISK_THRESHOLDS = {
        RiskLevel.CRITICAL: 0.8,
        RiskLevel.HIGH: 0.6,
        RiskLevel.MEDIUM: 0.4,
        RiskLevel.LOW: 0.0
    }
    
    # Action risk multipliers
    ACTION_MULTIPLIERS = {
        'view': 1.0,
        'download': 1.8,
        'upload': 1.4,
        'modify': 2.5,  # Increased - modification is high risk
        'delete': 3.0,  # Increased - deletion is highest risk
        'share': 2.0
    }
    
    # Cross-department multipliers by action type (different actions have different cross-dept risk)
    CROSS_DEPT_ACTION_MULTIPLIERS = {
        'view': 1.3,      # Viewing other dept docs is minor risk
        'download': 2.0,   # Downloading other dept docs is risky
        'upload': 1.5,     # Uploading to other dept
        'modify': 2.8,     # CRITICAL: Modifying other dept docs is very high risk
        'delete': 3.5,     # CRITICAL: Deleting other dept docs is highest risk
        'share': 2.2       # Sharing other dept docs is risky
    }
    
    # Temporal risk multipliers
    TEMPORAL_MULTIPLIERS = {
        'business_hours': 1.0,
        'after_hours': 1.3,
        'weekend': 1.5,
        'holiday': 1.7
    }
    
    def __init__(self, weights: Optional[Dict[str, float]] = None):
        """
        Initialize risk fusion engine
        
        Args:
            weights: Custom fusion weights (must sum to 1.0)
        """
        if weights:
            # Normalize weights
            total = sum(weights.values())
            self.weights = {k: v/total for k, v in weights.items()}
        else:
            self.weights = self.DEFAULT_WEIGHTS.copy()
        
        # Alert threshold
        self.alert_threshold = self.RISK_THRESHOLDS[RiskLevel.MEDIUM]
    
    def compute_risk(
        self,
        behavior_score: float = 0.0,
        classification_score: float = 0.0,
        integrity_score: float = 0.0,
        action: str = "view",
        is_cross_department: bool = False,
        is_after_hours: bool = False,
        is_weekend: bool = False
    ) -> RiskAssessment:
        """
        Compute fused risk score from multiple signals
        
        Args:
            behavior_score: Anomaly detection score (0-1, higher = riskier)
            classification_score: Document sensitivity risk (0-1)
            integrity_score: Tampering risk (0-1)
            action: Type of action performed
            is_cross_department: Whether accessing other department's data
            is_after_hours: Whether action is outside business hours
            is_weekend: Whether action is on weekend
            
        Returns:
            RiskAssessment with fused score and details
        """
        # Build components
        components = RiskComponents(
            behavior_score=behavior_score,
            classification_score=classification_score,
            integrity_score=integrity_score
        )
        
        # Apply action multiplier
        components.action_multiplier = self.ACTION_MULTIPLIERS.get(action, 1.0)
        
        # Apply cross-department multiplier (action-specific for better risk differentiation)
        if is_cross_department:
            # Use action-specific cross-dept multiplier (modify/delete get much higher penalties)
            components.cross_department_multiplier = self.CROSS_DEPT_ACTION_MULTIPLIERS.get(action, 1.5)
        
        # Apply temporal multiplier
        if is_weekend:
            components.temporal_multiplier = self.TEMPORAL_MULTIPLIERS['weekend']
        elif is_after_hours:
            components.temporal_multiplier = self.TEMPORAL_MULTIPLIERS['after_hours']
        else:
            components.temporal_multiplier = self.TEMPORAL_MULTIPLIERS['business_hours']
        
        # Compute weighted base score
        weighted_components = {
            'behavior': behavior_score * self.weights['behavior'],
            'classification': classification_score * self.weights['classification'],
            'integrity': integrity_score * self.weights['integrity']
        }
        
        base_score = sum(weighted_components.values())
        
        # Add MINIMUM BASE RISK for cross-department risky actions
        # This ensures that accessing other department's documents has inherent risk
        if is_cross_department:
            # Base minimum risk for cross-department access
            cross_dept_base_risk = {
                'view': 0.15,       # Viewing other dept - low inherent risk
                'download': 0.25,   # Downloading other dept - moderate inherent risk
                'upload': 0.20,     # Uploading to other dept
                'modify': 0.45,     # CRITICAL: Modifying other dept docs - HIGH inherent risk
                'delete': 0.55,     # CRITICAL: Deleting other dept docs - HIGHEST inherent risk
                'share': 0.30       # Sharing other dept docs
            }
            min_base = cross_dept_base_risk.get(action, 0.15)
            # Use the higher of calculated base or minimum cross-dept base
            base_score = max(base_score, min_base)
        
        # Apply multipliers
        final_score = base_score * (
            components.action_multiplier *
            components.cross_department_multiplier *
            components.temporal_multiplier
        )
        
        # Cap at 1.0
        final_score = min(final_score, 1.0)
        
        # Determine risk level
        risk_level = RiskLevel.LOW
        for level, threshold in self.RISK_THRESHOLDS.items():
            if final_score >= threshold:
                risk_level = level
                break
        
        # Determine severity label
        severity_labels = {
            RiskLevel.CRITICAL: "CRITICAL - Immediate attention required",
            RiskLevel.HIGH: "HIGH - Potential security incident",
            RiskLevel.MEDIUM: "MEDIUM - Suspicious activity detected",
            RiskLevel.LOW: "LOW - Normal activity"
        }
        severity_label = severity_labels[risk_level]
        
        # Identify risk factors
        risk_factors = []
        primary_factor = "none"
        max_component_score = 0
        
        if behavior_score > 0.5:
            risk_factors.append(f"Anomalous behavior (score: {behavior_score:.2f})")
            if behavior_score > max_component_score:
                max_component_score = behavior_score
                primary_factor = "behavioral_anomaly"
        
        if classification_score > 0.5:
            risk_factors.append(f"Sensitive document accessed (score: {classification_score:.2f})")
            if classification_score > max_component_score:
                max_component_score = classification_score
                primary_factor = "document_sensitivity"
        
        if integrity_score > 0:
            risk_factors.append(f"Document tampering detected (score: {integrity_score:.2f})")
            if integrity_score > max_component_score:
                max_component_score = integrity_score
                primary_factor = "integrity_violation"
        
        if is_cross_department:
            risk_factors.append("Cross-department access")
        
        if is_after_hours or is_weekend:
            risk_factors.append(f"Off-hours activity ({'weekend' if is_weekend else 'after hours'})")
        
        if action in ['download', 'modify', 'delete']:
            risk_factors.append(f"High-risk action: {action}")
        
        return RiskAssessment(
            risk_score=final_score,
            risk_level=risk_level,
            severity_label=severity_label,
            components=components,
            weighted_components=weighted_components,
            is_anomalous=behavior_score > 0.5,
            is_cross_department=is_cross_department,
            requires_alert=final_score >= self.alert_threshold,
            primary_risk_factor=primary_factor,
            risk_factors=risk_factors
        )
    
    def should_alert(self, assessment: RiskAssessment) -> bool:
        """
        Determine if an alert should be generated
        
        Args:
            assessment: Risk assessment result
            
        Returns:
            True if alert should be generated
        """
        # Always alert on critical
        if assessment.risk_level == RiskLevel.CRITICAL:
            return True
        
        # Alert on high with multiple risk factors
        if assessment.risk_level == RiskLevel.HIGH and len(assessment.risk_factors) >= 2:
            return True
        
        # Alert on any tampering detection
        if assessment.components.integrity_score > 0:
            return True
        
        # Alert on cross-department download of confidential data
        if (assessment.is_cross_department and 
            assessment.components.classification_score > 0.7 and
            assessment.components.action_multiplier >= 1.5):
            return True
        
        return assessment.risk_score >= self.alert_threshold
    
    def generate_alert_summary(
        self,
        assessment: RiskAssessment,
        user_id: str,
        document_name: str,
        action: str
    ) -> str:
        """
        Generate human-readable alert summary
        
        Args:
            assessment: Risk assessment
            user_id: User identifier
            document_name: Document name
            action: Action performed
            
        Returns:
            Alert summary string
        """
        parts = [
            f"[{assessment.risk_level.value.upper()}]",
            f"User {user_id}",
            f"performed {action}",
            f"on {document_name}",
            f"(Risk: {assessment.risk_score:.2f})"
        ]
        
        summary = " ".join(parts)
        
        if assessment.risk_factors:
            summary += f" | Factors: {'; '.join(assessment.risk_factors[:3])}"
        
        return summary
    
    def update_weights(self, new_weights: Dict[str, float]):
        """
        Update fusion weights (e.g., based on feedback)
        
        Args:
            new_weights: New weight values
        """
        total = sum(new_weights.values())
        self.weights = {k: v/total for k, v in new_weights.items()}

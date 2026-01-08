"""
ML Engine Module
Enterprise Insider Threat Detection - Machine Learning Components
"""
from .pipeline import ThreatDetectionPipeline, UserEvent, PipelineResult
from .behavior import BehavioralAnomalyDetector, BehaviorFeatures
from .documents import (
    DocumentSensitivityClassifier,
    SensitivityLevel,
    ClassificationResult,
    IntegrityVerifier,
    IntegrityResult,
    TamperSeverity
)
from .fusion import RiskFusionEngine, RiskAssessment, RiskComponents, RiskLevel
from .explainability import (
    ShapExplainer,
    ShapExplanation,
    LimeExplainer,
    LimeExplanation
)

__all__ = [
    # Main pipeline
    "ThreatDetectionPipeline",
    "UserEvent",
    "PipelineResult",
    
    # Behavior
    "BehavioralAnomalyDetector",
    "BehaviorFeatures",
    
    # Documents
    "DocumentSensitivityClassifier",
    "SensitivityLevel",
    "ClassificationResult",
    "IntegrityVerifier",
    "IntegrityResult",
    "TamperSeverity",
    
    # Fusion
    "RiskFusionEngine",
    "RiskAssessment",
    "RiskComponents",
    "RiskLevel",
    
    # Explainability
    "ShapExplainer",
    "ShapExplanation",
    "LimeExplainer",
    "LimeExplanation"
]

"""
ML Pipeline Orchestrator
THE CROWN JEWEL - Event-driven ML processing pipeline

This is the core of the threat detection system.
Every event flows through: Event → Behavior → Sensitivity → Integrity → Risk → Explanation
"""
from typing import Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
from pydantic import BaseModel
import os

# ML Components
from .behavior import BehavioralAnomalyDetector, BehaviorFeatures
from .documents import (
    DocumentSensitivityClassifier, 
    ClassificationResult,
    SensitivityLevel,
    IntegrityVerifier,
    IntegrityResult,
    TamperSeverity
)
from .fusion import RiskFusionEngine, RiskAssessment, RiskLevel
from .explainability import ShapExplainer, LimeExplainer, ShapExplanation, LimeExplanation


class UserEvent(BaseModel):
    """
    Input event schema - THIS IS WHAT REPLACES CSV ROWS
    Every document action creates one of these
    """
    # Identity
    user_id: str
    user_department: str
    
    # Target
    document_id: str
    document_name: str
    target_department: str
    
    # Action
    action: str  # view, download, upload, modify, delete, share
    
    # Context
    bytes_transferred: int = 0
    source_ip: Optional[str] = None
    device_info: Optional[str] = None
    session_id: Optional[str] = None
    timestamp: datetime = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


@dataclass
class PipelineResult:
    """
    Complete result from ML pipeline processing
    """
    # Input event
    event: UserEvent
    
    # Risk assessment
    risk_score: float
    risk_level: str
    severity: str
    requires_alert: bool
    
    # Component scores
    behavior_score: float
    sensitivity_score: float
    integrity_score: float
    
    # Document classification
    document_sensitivity: str
    sensitivity_confidence: float
    
    # Integrity status
    is_tampered: bool
    tamper_severity: str
    
    # Context flags
    is_cross_department: bool
    is_anomalous: bool
    is_after_hours: bool
    
    # Risk factors
    risk_factors: list
    primary_risk_factor: str
    alert_summary: Optional[str]
    
    # Explainability
    shap_explanation: Optional[Dict] = None
    lime_explanation: Optional[Dict] = None
    
    # Metadata
    processed_at: datetime = field(default_factory=datetime.utcnow)
    processing_time_ms: float = 0.0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON/API response"""
        return {
            'event': self.event.dict() if hasattr(self.event, 'dict') else self.event,
            'risk': {
                'score': self.risk_score,
                'level': self.risk_level,
                'severity': self.severity,
                'requires_alert': self.requires_alert
            },
            'components': {
                'behavior': self.behavior_score,
                'sensitivity': self.sensitivity_score,
                'integrity': self.integrity_score
            },
            'document': {
                'sensitivity': self.document_sensitivity,
                'sensitivity_confidence': self.sensitivity_confidence,
                'is_tampered': self.is_tampered,
                'tamper_severity': self.tamper_severity
            },
            'context': {
                'is_cross_department': self.is_cross_department,
                'is_anomalous': self.is_anomalous,
                'is_after_hours': self.is_after_hours
            },
            'risk_factors': self.risk_factors,
            'primary_risk_factor': self.primary_risk_factor,
            'alert_summary': self.alert_summary,
            'explanations': {
                'shap': self.shap_explanation,
                'lime': self.lime_explanation
            },
            'metadata': {
                'processed_at': self.processed_at.isoformat(),
                'processing_time_ms': self.processing_time_ms
            }
        }


class ThreatDetectionPipeline:
    """
    THE MAIN ML PIPELINE
    
    Processes events through the complete detection chain:
    1. Extract behavioral features
    2. Score behavioral anomaly
    3. Classify document sensitivity  
    4. Check document integrity
    5. Fuse into final risk score
    6. Generate explanations
    7. Determine if alert needed
    
    Usage:
        pipeline = ThreatDetectionPipeline()
        pipeline.initialize()
        
        event = UserEvent(...)
        result = pipeline.run(event, document_content="...")
    """
    
    def __init__(
        self,
        contamination: float = 0.1,
        behavior_weight: float = 0.4,
        classification_weight: float = 0.3,
        integrity_weight: float = 0.3,
        use_semantic: bool = False,  # Set True if sentence-transformers available
        use_zero_shot: bool = False,  # Set True if transformers available
        enable_shap: bool = True,
        enable_lime: bool = True
    ):
        """
        Initialize pipeline components
        
        Args:
            contamination: Anomaly detection contamination rate
            behavior_weight: Weight for behavioral component
            classification_weight: Weight for sensitivity component
            integrity_weight: Weight for integrity component
            use_semantic: Use semantic similarity for integrity
            use_zero_shot: Use zero-shot NLP for classification
            enable_shap: Enable SHAP explanations
            enable_lime: Enable LIME explanations
        """
        # Configuration
        self.config = {
            'contamination': contamination,
            'weights': {
                'behavior': behavior_weight,
                'classification': classification_weight,
                'integrity': integrity_weight
            },
            'use_semantic': use_semantic,
            'use_zero_shot': use_zero_shot,
            'enable_shap': enable_shap,
            'enable_lime': enable_lime
        }
        
        # Initialize components
        self.behavior_detector = BehavioralAnomalyDetector(
            contamination=contamination
        )
        
        self.sensitivity_classifier = DocumentSensitivityClassifier(
            use_zero_shot=use_zero_shot
        )
        
        self.integrity_verifier = IntegrityVerifier(
            use_semantic=use_semantic
        )
        
        self.risk_engine = RiskFusionEngine(
            weights=self.config['weights']
        )
        
        # Explainers (initialized after model training)
        self.shap_explainer: Optional[ShapExplainer] = None
        self.lime_explainer: Optional[LimeExplainer] = None
        
        if enable_lime:
            self.lime_explainer = LimeExplainer()
        
        # Document content cache (in production, use proper storage)
        self._document_cache: Dict[str, str] = {}
        
        self._is_initialized = False
    
    def initialize(
        self,
        training_data=None,
        documents_dir: str = None
    ):
        """
        Initialize the pipeline with training data
        
        Args:
            training_data: DataFrame with behavioral features for training
            documents_dir: Directory with original documents for integrity baseline
        """
        # Train behavior model if data provided
        if training_data is not None:
            print("Training behavioral anomaly detector...")
            metrics = self.behavior_detector.train(training_data)
            print(f"Training complete: {metrics}")
            
            # Set up SHAP explainer
            if self.config['enable_shap']:
                self.shap_explainer = ShapExplainer(
                    model=self.behavior_detector.model,
                    feature_names=self.behavior_detector.feature_names
                )
                
                # Use training data as background
                feature_cols = [c for c in BehaviorFeatures.feature_names() 
                               if c in training_data.columns]
                background = training_data[feature_cols].values
                self.shap_explainer.setup_explainer(background)
        
        # Register documents for integrity checking
        if documents_dir and os.path.exists(documents_dir):
            print(f"Registering documents from {documents_dir}...")
            for filename in os.listdir(documents_dir):
                if filename.endswith('.txt'):
                    filepath = os.path.join(documents_dir, filename)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    doc_id = os.path.splitext(filename)[0]
                    self.integrity_verifier.register_document(doc_id, content, filename)
                    self._document_cache[doc_id] = content
            
            print(f"Registered {len(self._document_cache)} documents")
        
        self._is_initialized = True
        print("Pipeline initialized successfully")
    
    def run(
        self,
        event: UserEvent,
        document_content: Optional[str] = None
    ) -> PipelineResult:
        """
        RUN THE COMPLETE ML PIPELINE ON AN EVENT
        
        This is the main entry point that orchestrates all ML components.
        
        Args:
            event: UserEvent to process
            document_content: Optional document content for classification/integrity
            
        Returns:
            PipelineResult with all detection outputs
        """
        start_time = datetime.utcnow()
        
        # Ensure timestamp
        if event.timestamp is None:
            event.timestamp = datetime.utcnow()
        
        # 1. EXTRACT BEHAVIORAL FEATURES
        user_history = self.behavior_detector.get_user_history(event.user_id)
        
        behavior_features = self.behavior_detector.extract_features_from_event(
            event.dict(),
            user_history
        )
        
        # 2. SCORE BEHAVIORAL ANOMALY
        behavior_score, behavior_level, is_anomalous = self.behavior_detector.score_event(
            behavior_features
        )
        
        # Update user history
        self.behavior_detector.update_user_history(event.user_id, event.dict())
        
        # 3. CLASSIFY DOCUMENT SENSITIVITY
        sensitivity_result = ClassificationResult(
            sensitivity=SensitivityLevel.INTERNAL,
            confidence=0.5,
            method="default",
            probabilities={"public": 0.2, "internal": 0.6, "confidential": 0.2},
            keywords_found=[]
        )
        
        if document_content:
            sensitivity_result = self.sensitivity_classifier.classify(document_content)
        elif event.document_id in self._document_cache:
            content = self._document_cache[event.document_id]
            sensitivity_result = self.sensitivity_classifier.classify(content)
        
        sensitivity_score = self.sensitivity_classifier.get_risk_score(sensitivity_result)
        
        # 4. CHECK DOCUMENT INTEGRITY
        integrity_result = IntegrityResult(
            document_id=event.document_id,
            filename=event.document_name,
            original_hash="",
            current_hash="",
            hash_match=True,
            is_tampered=False,
            tamper_severity=TamperSeverity.NONE,
            semantic_similarity=None,
            size_change_bytes=0,
            size_change_percent=0.0,
            verified_at=datetime.utcnow()
        )
        
        if document_content and event.action in ['modify', 'upload']:
            original_content = self._document_cache.get(event.document_id)
            integrity_result = self.integrity_verifier.verify_content(
                event.document_id,
                document_content,
                original_content
            )
        
        integrity_score = self.integrity_verifier.get_risk_score(integrity_result)
        
        # 5. DETERMINE CONTEXT
        is_cross_department = (
            event.user_department.lower() != event.target_department.lower()
        )
        
        is_after_hours = (
            event.timestamp.hour < 8 or event.timestamp.hour > 18
        )
        
        is_weekend = event.timestamp.weekday() >= 5
        
        # 6. FUSE INTO FINAL RISK SCORE
        risk_assessment = self.risk_engine.compute_risk(
            behavior_score=behavior_score,
            classification_score=sensitivity_score,
            integrity_score=integrity_score,
            action=event.action,
            is_cross_department=is_cross_department,
            is_after_hours=is_after_hours,
            is_weekend=is_weekend
        )
        
        # 7. GENERATE EXPLANATIONS
        shap_explanation = None
        lime_explanation = None
        
        if self.shap_explainer and is_anomalous:
            shap_exp = self.shap_explainer.explain(
                behavior_features.to_array(),
                user_id=event.user_id
            )
            if shap_exp:
                shap_explanation = shap_exp.to_dict()
        
        if self.lime_explainer and document_content:
            lime_exp = self.lime_explainer.explain(
                document_content,
                document_id=event.document_id,
                filename=event.document_name
            )
            if lime_exp:
                lime_explanation = lime_exp.to_dict()
        
        # 8. GENERATE ALERT SUMMARY IF NEEDED
        alert_summary = None
        if risk_assessment.requires_alert:
            alert_summary = self.risk_engine.generate_alert_summary(
                risk_assessment,
                event.user_id,
                event.document_name,
                event.action
            )
        
        # Calculate processing time
        end_time = datetime.utcnow()
        processing_time_ms = (end_time - start_time).total_seconds() * 1000
        
        # Build result
        return PipelineResult(
            event=event,
            risk_score=risk_assessment.risk_score,
            risk_level=risk_assessment.risk_level.value,
            severity=risk_assessment.severity_label,
            requires_alert=risk_assessment.requires_alert,
            behavior_score=behavior_score,
            sensitivity_score=sensitivity_score,
            integrity_score=integrity_score,
            document_sensitivity=sensitivity_result.sensitivity.value,
            sensitivity_confidence=sensitivity_result.confidence,
            is_tampered=integrity_result.is_tampered,
            tamper_severity=integrity_result.tamper_severity.value,
            is_cross_department=is_cross_department,
            is_anomalous=is_anomalous,
            is_after_hours=is_after_hours or is_weekend,
            risk_factors=risk_assessment.risk_factors,
            primary_risk_factor=risk_assessment.primary_risk_factor,
            alert_summary=alert_summary,
            shap_explanation=shap_explanation,
            lime_explanation=lime_explanation,
            processed_at=end_time,
            processing_time_ms=processing_time_ms
        )
    
    def process_batch(self, events: list, document_contents: Dict[str, str] = None) -> list:
        """
        Process multiple events
        
        Args:
            events: List of UserEvent objects
            document_contents: Optional mapping of document_id -> content
            
        Returns:
            List of PipelineResults
        """
        results = []
        document_contents = document_contents or {}
        
        for event in events:
            content = document_contents.get(event.document_id)
            result = self.run(event, content)
            results.append(result)
        
        return results
    
    def get_statistics(self) -> Dict:
        """Get pipeline statistics"""
        return {
            'is_initialized': self._is_initialized,
            'config': self.config,
            'documents_registered': len(self._document_cache),
            'model_trained': self.behavior_detector.is_trained,
            'feature_names': self.behavior_detector.feature_names
        }

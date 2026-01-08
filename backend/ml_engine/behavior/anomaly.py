"""
Behavioral Anomaly Detection Module
Event-driven IsolationForest for detecting unusual user behavior
Extracted and refactored from notebook prototype
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import joblib
import os


@dataclass
class BehaviorFeatures:
    """Features extracted from user behavior"""
    user_id: str
    
    # Activity volume
    total_events_24h: int = 0
    total_bytes_24h: int = 0
    unique_documents_24h: int = 0
    
    # Temporal patterns
    is_after_hours: bool = False  # Activity outside 9-5
    is_weekend: bool = False
    hour_of_day: int = 0
    
    # Cross-department activity
    cross_dept_access_count: int = 0
    cross_dept_ratio: float = 0.0
    
    # Action patterns
    download_count: int = 0
    modify_count: int = 0
    view_count: int = 0
    
    # Sensitivity patterns
    confidential_access_count: int = 0
    internal_access_count: int = 0
    
    # Session patterns
    avg_session_duration: float = 0.0
    unique_ips: int = 1
    unique_devices: int = 1
    
    def to_array(self) -> np.ndarray:
        """Convert to feature array for model"""
        return np.array([
            self.total_events_24h,
            self.total_bytes_24h / 1000000,  # Normalize to MB
            self.unique_documents_24h,
            int(self.is_after_hours),
            int(self.is_weekend),
            self.hour_of_day,
            self.cross_dept_access_count,
            self.cross_dept_ratio,
            self.download_count,
            self.modify_count,
            self.view_count,
            self.confidential_access_count,
            self.internal_access_count,
            self.avg_session_duration,
            self.unique_ips,
            self.unique_devices
        ]).reshape(1, -1)
    
    @staticmethod
    def feature_names() -> List[str]:
        """Get feature names for explainability"""
        return [
            'total_events_24h',
            'total_bytes_mb_24h',
            'unique_documents_24h',
            'is_after_hours',
            'is_weekend',
            'hour_of_day',
            'cross_dept_access_count',
            'cross_dept_ratio',
            'download_count',
            'modify_count',
            'view_count',
            'confidential_access_count',
            'internal_access_count',
            'avg_session_duration',
            'unique_ips',
            'unique_devices'
        ]


class BehavioralAnomalyDetector:
    """
    Event-driven behavioral anomaly detection using IsolationForest
    
    This is the refactored version from the notebook prototype,
    designed to process individual events in real-time.
    """
    
    def __init__(
        self,
        contamination: float = 0.1,
        n_estimators: int = 100,
        random_state: int = 42
    ):
        """
        Initialize the detector
        
        Args:
            contamination: Expected proportion of anomalies (0.0 to 0.5)
            n_estimators: Number of trees in IsolationForest
            random_state: Random seed for reproducibility
        """
        self.contamination = contamination
        self.n_estimators = n_estimators
        self.random_state = random_state
        
        self.model: Optional[IsolationForest] = None
        self.scaler = StandardScaler()
        self.is_trained = False
        self.feature_names = BehaviorFeatures.feature_names()
        
        # User behavior history cache (in production, use Redis)
        self._user_history: Dict[str, List[dict]] = {}
    
    def train(self, training_data: pd.DataFrame) -> Dict:
        """
        Train the model on historical behavioral data
        
        Args:
            training_data: DataFrame with behavioral features
            
        Returns:
            Training metrics
        """
        # Ensure we have the right features
        feature_cols = [c for c in self.feature_names if c in training_data.columns]
        X = training_data[feature_cols].values
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train IsolationForest
        self.model = IsolationForest(
            n_estimators=self.n_estimators,
            contamination=self.contamination,
            random_state=self.random_state,
            n_jobs=-1,
            warm_start=False
        )
        
        self.model.fit(X_scaled)
        self.is_trained = True
        
        # Calculate training metrics
        predictions = self.model.predict(X_scaled)
        scores = self.model.score_samples(X_scaled)
        
        return {
            "samples_trained": len(X),
            "features_used": len(feature_cols),
            "anomalies_detected": int(np.sum(predictions == -1)),
            "anomaly_rate": float(np.mean(predictions == -1)),
            "score_mean": float(np.mean(scores)),
            "score_std": float(np.std(scores))
        }
    
    def score_event(self, features: BehaviorFeatures) -> Tuple[float, str, bool]:
        """
        Score a single event for anomaly detection
        
        Args:
            features: Extracted behavioral features
            
        Returns:
            Tuple of (anomaly_score, risk_level, is_anomaly)
        """
        if not self.is_trained:
            # Return neutral score if model not trained
            return 0.0, "low", False
        
        # Get feature array and scale
        X = features.to_array()
        X_scaled = self.scaler.transform(X)
        
        # Get anomaly score (more negative = more anomalous)
        raw_score = self.model.score_samples(X_scaled)[0]
        prediction = self.model.predict(X_scaled)[0]
        
        # Convert to 0-1 risk score (higher = riskier)
        # IsolationForest scores typically range from -0.5 to 0.5
        normalized_score = float((-raw_score + 0.5) / 1.0)
        normalized_score = np.clip(normalized_score, 0, 1)
        
        # Determine risk level
        if normalized_score >= 0.8:
            risk_level = "critical"
        elif normalized_score >= 0.6:
            risk_level = "high"
        elif normalized_score >= 0.4:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        is_anomaly = prediction == -1
        
        return normalized_score, risk_level, is_anomaly
    
    def extract_features_from_event(
        self,
        event: dict,
        user_history: Optional[List[dict]] = None
    ) -> BehaviorFeatures:
        """
        Extract behavioral features from an event and user history
        
        Args:
            event: Event dictionary with user_id, action, timestamp, etc.
            user_history: Recent events for this user (last 24h)
            
        Returns:
            BehaviorFeatures dataclass
        """
        user_id = event.get("user_id", "unknown")
        timestamp = event.get("timestamp", datetime.utcnow())
        
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        
        # Initialize features
        features = BehaviorFeatures(user_id=user_id)
        
        # Temporal features
        features.hour_of_day = timestamp.hour
        features.is_after_hours = timestamp.hour < 8 or timestamp.hour > 18
        features.is_weekend = timestamp.weekday() >= 5
        
        # If we have history, calculate aggregate features
        if user_history:
            cutoff = timestamp - timedelta(hours=24)
            recent = [e for e in user_history 
                     if e.get("timestamp", datetime.min) > cutoff]
            
            features.total_events_24h = len(recent) + 1
            features.total_bytes_24h = sum(
                e.get("bytes_transferred", 0) for e in recent
            ) + event.get("bytes_transferred", 0)
            
            # Unique documents
            docs = set(e.get("document_id") for e in recent)
            docs.add(event.get("document_id"))
            features.unique_documents_24h = len(docs)
            
            # Cross-department access
            user_dept = event.get("user_department", "").lower()
            cross_dept = [e for e in recent 
                         if e.get("target_department", "").lower() != user_dept]
            features.cross_dept_access_count = len(cross_dept)
            features.cross_dept_ratio = len(cross_dept) / max(len(recent), 1)
            
            # Action counts
            actions = [e.get("action", "") for e in recent]
            features.download_count = actions.count("download")
            features.modify_count = actions.count("modify")
            features.view_count = actions.count("view")
            
            # Unique IPs and devices
            ips = set(e.get("source_ip") for e in recent if e.get("source_ip"))
            devices = set(e.get("device_info") for e in recent if e.get("device_info"))
            features.unique_ips = max(len(ips), 1)
            features.unique_devices = max(len(devices), 1)
        
        # Current event action
        action = event.get("action", "view")
        if action == "download":
            features.download_count += 1
        elif action == "modify":
            features.modify_count += 1
        elif action == "view":
            features.view_count += 1
        
        # Cross-department check for current event
        if event.get("is_cross_department", False):
            features.cross_dept_access_count += 1
        
        # Sensitivity (would come from document classification)
        sensitivity = event.get("document_sensitivity", "internal")
        if sensitivity == "confidential":
            features.confidential_access_count += 1
        elif sensitivity == "internal":
            features.internal_access_count += 1
        
        return features
    
    def update_user_history(self, user_id: str, event: dict):
        """
        Update cached user history with new event
        
        Args:
            user_id: User identifier
            event: Event to add to history
        """
        if user_id not in self._user_history:
            self._user_history[user_id] = []
        
        self._user_history[user_id].append(event)
        
        # Keep only last 24h of events (limit memory)
        cutoff = datetime.utcnow() - timedelta(hours=24)
        self._user_history[user_id] = [
            e for e in self._user_history[user_id]
            if e.get("timestamp", datetime.min) > cutoff
        ]
    
    def get_user_history(self, user_id: str) -> List[dict]:
        """Get cached user history"""
        return self._user_history.get(user_id, [])
    
    def get_feature_importance(self) -> pd.DataFrame:
        """
        Get proxy feature importance based on tree depth
        
        Returns:
            DataFrame with feature importance scores
        """
        if not self.is_trained:
            return pd.DataFrame()
        
        # Use tree-based feature importance proxy
        # Average depth at which features are used
        importances = np.zeros(len(self.feature_names))
        
        for tree in self.model.estimators_:
            # Get feature importances from each tree
            tree_imp = tree.feature_importances_
            if len(tree_imp) == len(self.feature_names):
                importances += tree_imp
        
        importances /= len(self.model.estimators_)
        
        return pd.DataFrame({
            'feature': self.feature_names,
            'importance': importances
        }).sort_values('importance', ascending=False)
    
    def save(self, path: str = "models/behavior_detector.pkl"):
        """Save model to disk"""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        joblib.dump({
            'model': self.model,
            'scaler': self.scaler,
            'feature_names': self.feature_names,
            'is_trained': self.is_trained,
            'config': {
                'contamination': self.contamination,
                'n_estimators': self.n_estimators,
                'random_state': self.random_state
            }
        }, path)
    
    @classmethod
    def load(cls, path: str = "models/behavior_detector.pkl") -> "BehavioralAnomalyDetector":
        """Load model from disk"""
        data = joblib.load(path)
        
        detector = cls(
            contamination=data['config']['contamination'],
            n_estimators=data['config']['n_estimators'],
            random_state=data['config']['random_state']
        )
        
        detector.model = data['model']
        detector.scaler = data['scaler']
        detector.feature_names = data['feature_names']
        detector.is_trained = data['is_trained']
        
        return detector

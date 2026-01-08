"""
SHAP Explainability Engine for Behavioral Anomaly Detection
Provides interpretable explanations for IsolationForest predictions
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import os
import json

try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False


@dataclass
class ShapExplanation:
    """SHAP explanation result"""
    user_id: str
    
    # SHAP values
    shap_values: Dict[str, float]  # feature -> SHAP value
    base_value: float
    predicted_score: float
    
    # Feature importance ranking
    top_features: List[Tuple[str, float]]  # (feature_name, shap_value)
    
    # Natural language explanation
    explanation_text: str
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'user_id': self.user_id,
            'shap_values': self.shap_values,
            'base_value': self.base_value,
            'predicted_score': self.predicted_score,
            'top_features': [
                {'feature': f, 'shap_value': v}
                for f, v in self.top_features
            ],
            'explanation_text': self.explanation_text
        }


class ShapExplainer:
    """
    Generate SHAP explanations for behavioral anomaly detection
    """
    
    def __init__(self, model=None, feature_names: List[str] = None):
        """
        Initialize SHAP explainer
        
        Args:
            model: Trained IsolationForest model
            feature_names: List of feature names
        """
        if not SHAP_AVAILABLE:
            print("Warning: SHAP not installed. Install with: pip install shap")
        
        self.model = model
        self.feature_names = feature_names or []
        self._explainer = None
        self._background_data = None
    
    def setup_explainer(
        self,
        background_data: np.ndarray,
        method: str = 'tree'
    ):
        """
        Set up SHAP explainer with background data
        
        Args:
            background_data: Background samples for SHAP
            method: 'tree' or 'kernel'
        """
        if not SHAP_AVAILABLE:
            return
        
        self._background_data = background_data
        
        try:
            if method == 'tree' and hasattr(self.model, 'estimators_'):
                # TreeExplainer for tree-based models
                self._explainer = shap.TreeExplainer(self.model)
            else:
                # KernelExplainer for model-agnostic explanations
                background = shap.kmeans(background_data, min(100, len(background_data)))
                self._explainer = shap.KernelExplainer(
                    self.model.score_samples if hasattr(self.model, 'score_samples') 
                    else self.model.predict,
                    background
                )
        except Exception as e:
            print(f"Failed to create SHAP explainer: {e}")
            self._explainer = None
    
    def explain(
        self,
        features: np.ndarray,
        user_id: str = "unknown"
    ) -> Optional[ShapExplanation]:
        """
        Generate SHAP explanation for a single sample
        
        Args:
            features: Feature array (1, n_features)
            user_id: User identifier
            
        Returns:
            ShapExplanation or None if not available
        """
        if not SHAP_AVAILABLE or self._explainer is None:
            return None
        
        try:
            # Ensure 2D array
            if features.ndim == 1:
                features = features.reshape(1, -1)
            
            # Get SHAP values
            shap_values = self._explainer.shap_values(features)
            
            # Handle different SHAP output formats
            if isinstance(shap_values, list):
                shap_values = shap_values[0]
            if shap_values.ndim > 1:
                shap_values = shap_values[0]
            
            # Get base value
            if hasattr(self._explainer, 'expected_value'):
                base_value = self._explainer.expected_value
                if isinstance(base_value, np.ndarray):
                    base_value = float(base_value[0])
            else:
                base_value = 0.0
            
            # Create feature -> SHAP value mapping
            shap_dict = {}
            for i, name in enumerate(self.feature_names):
                if i < len(shap_values):
                    shap_dict[name] = float(shap_values[i])
            
            # Get top features (sorted by absolute value)
            sorted_features = sorted(
                shap_dict.items(),
                key=lambda x: abs(x[1]),
                reverse=True
            )
            top_features = sorted_features[:10]
            
            # Calculate predicted score
            predicted_score = base_value + sum(shap_values)
            
            # Generate natural language explanation
            explanation_text = self._generate_explanation_text(
                user_id, top_features, predicted_score
            )
            
            return ShapExplanation(
                user_id=user_id,
                shap_values=shap_dict,
                base_value=base_value,
                predicted_score=float(predicted_score),
                top_features=top_features,
                explanation_text=explanation_text
            )
            
        except Exception as e:
            print(f"SHAP explanation failed: {e}")
            return None
    
    def _generate_explanation_text(
        self,
        user_id: str,
        top_features: List[Tuple[str, float]],
        predicted_score: float
    ) -> str:
        """Generate natural language explanation"""
        
        # Determine if anomalous (negative scores indicate anomaly in IsolationForest)
        is_anomalous = predicted_score < 0
        
        lines = [
            f"Risk Analysis for User {user_id}:",
            f"Overall anomaly score: {predicted_score:.3f}",
            f"Status: {'ANOMALOUS' if is_anomalous else 'NORMAL'}",
            "",
            "Key factors contributing to this assessment:"
        ]
        
        for i, (feature, value) in enumerate(top_features[:5], 1):
            direction = "increases" if value > 0 else "decreases"
            # For IsolationForest, positive SHAP = more normal, negative = more anomalous
            impact = "risk" if value < 0 else "normalcy"
            
            # Format feature name for readability
            readable_name = feature.replace('_', ' ').title()
            
            lines.append(f"  {i}. {readable_name}: {direction} {impact} by {abs(value):.3f}")
        
        return "\n".join(lines)
    
    def explain_batch(
        self,
        features_df: pd.DataFrame,
        user_ids: List[str] = None
    ) -> List[ShapExplanation]:
        """
        Generate explanations for multiple samples
        
        Args:
            features_df: DataFrame with features
            user_ids: List of user identifiers
            
        Returns:
            List of ShapExplanations
        """
        if not SHAP_AVAILABLE or self._explainer is None:
            return []
        
        if user_ids is None:
            user_ids = [f"user_{i}" for i in range(len(features_df))]
        
        explanations = []
        
        for i, (idx, row) in enumerate(features_df.iterrows()):
            features = row.values.reshape(1, -1)
            user_id = user_ids[i] if i < len(user_ids) else f"user_{i}"
            
            exp = self.explain(features, user_id)
            if exp:
                explanations.append(exp)
        
        return explanations
    
    def get_global_importance(self) -> pd.DataFrame:
        """
        Get global feature importance from SHAP values
        
        Returns:
            DataFrame with feature importance
        """
        if self._background_data is None or self._explainer is None:
            return pd.DataFrame()
        
        try:
            shap_values = self._explainer.shap_values(self._background_data)
            
            if isinstance(shap_values, list):
                shap_values = shap_values[0]
            
            # Mean absolute SHAP value per feature
            importance = np.mean(np.abs(shap_values), axis=0)
            
            return pd.DataFrame({
                'feature': self.feature_names,
                'importance': importance
            }).sort_values('importance', ascending=False)
            
        except Exception as e:
            print(f"Failed to compute global importance: {e}")
            return pd.DataFrame()
    
    def save_explanation(
        self,
        explanation: ShapExplanation,
        output_dir: str = "xai_outputs/shap_explanations"
    ) -> str:
        """Save explanation to JSON file"""
        os.makedirs(output_dir, exist_ok=True)
        
        filepath = os.path.join(output_dir, f"{explanation.user_id}_shap.json")
        
        with open(filepath, 'w') as f:
            json.dump(explanation.to_dict(), f, indent=2)
        
        return filepath

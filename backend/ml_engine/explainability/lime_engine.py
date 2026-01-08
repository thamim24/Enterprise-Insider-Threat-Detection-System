"""
LIME Explainability Engine for Document Classification
Provides interpretable explanations for text classification predictions
"""
import numpy as np
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
import os
import json

try:
    from lime.lime_text import LimeTextExplainer
    LIME_AVAILABLE = True
except ImportError:
    LIME_AVAILABLE = False


@dataclass
class LimeExplanation:
    """LIME explanation result for document classification"""
    document_id: str
    filename: str
    
    # Classification result
    predicted_class: str
    confidence: float
    class_probabilities: Dict[str, float]
    
    # LIME explanation
    top_features: List[Dict]  # word, weight, direction
    lime_html: str  # Pre-rendered HTML explanation
    
    # Natural language explanation
    explanation_text: str
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'document_id': self.document_id,
            'filename': self.filename,
            'predicted_class': self.predicted_class,
            'confidence': self.confidence,
            'class_probabilities': self.class_probabilities,
            'top_features': self.top_features,
            'lime_html': self.lime_html,
            'explanation_text': self.explanation_text
        }


class LimeExplainer:
    """
    Generate LIME explanations for document classification
    """
    
    CLASS_NAMES = ['public', 'internal', 'confidential']
    
    def __init__(self, predictor: Optional[Callable] = None):
        """
        Initialize LIME explainer
        
        Args:
            predictor: Function that takes list of texts and returns probabilities
        """
        if not LIME_AVAILABLE:
            print("Warning: LIME not installed. Install with: pip install lime")
        
        self.predictor = predictor
        self._explainer = None
        
        if LIME_AVAILABLE:
            self._explainer = LimeTextExplainer(
                class_names=self.CLASS_NAMES,
                split_expression=r'\W+',
                bow=True
            )
    
    def set_predictor(self, predictor: Callable):
        """
        Set the predictor function
        
        Args:
            predictor: Function(texts: List[str]) -> np.ndarray of probabilities
        """
        self.predictor = predictor
    
    def _default_predictor(self, texts: List[str]) -> np.ndarray:
        """
        Default keyword-based predictor for LIME
        
        Args:
            texts: List of text samples
            
        Returns:
            Array of probability distributions
        """
        sensitivity_keywords = {
            'public': ['announcement', 'public', 'general', 'everyone', 'all employees'],
            'internal': ['internal', 'employees only', 'staff', 'company use'],
            'confidential': ['confidential', 'restricted', 'secret', 'private', 
                           'sensitive', 'financial', 'pii', 'proprietary']
        }
        
        results = []
        
        for text in texts:
            text_lower = text.lower()
            scores = {}
            
            for class_name, keywords in sensitivity_keywords.items():
                score = sum(1 for kw in keywords if kw in text_lower)
                scores[class_name] = score
            
            total = sum(scores.values())
            if total == 0:
                probs = [0.2, 0.6, 0.2]  # Default to internal
            else:
                probs = [
                    scores['public'] / total,
                    scores['internal'] / total,
                    scores['confidential'] / total
                ]
            
            results.append(probs)
        
        return np.array(results)
    
    def explain(
        self,
        text: str,
        document_id: str = "unknown",
        filename: str = "document.txt",
        num_features: int = 10,
        num_samples: int = 500
    ) -> Optional[LimeExplanation]:
        """
        Generate LIME explanation for a document
        
        Args:
            text: Document text
            document_id: Document identifier
            filename: Document filename
            num_features: Number of features to explain
            num_samples: Number of perturbations for LIME
            
        Returns:
            LimeExplanation or None if not available
        """
        if not LIME_AVAILABLE or self._explainer is None:
            return None
        
        predictor = self.predictor or self._default_predictor
        
        try:
            # Generate LIME explanation
            exp = self._explainer.explain_instance(
                text,
                predictor,
                num_features=num_features,
                num_samples=num_samples
            )
            
            # Get prediction
            probs = predictor([text])[0]
            predicted_idx = np.argmax(probs)
            predicted_class = self.CLASS_NAMES[predicted_idx]
            confidence = float(probs[predicted_idx])
            
            # Build class probabilities
            class_probabilities = {
                name: float(prob)
                for name, prob in zip(self.CLASS_NAMES, probs)
            }
            
            # Extract feature weights
            top_features = []
            for word, weight in exp.as_list():
                # Positive weight = pushes toward predicted class
                # Negative weight = pushes away from predicted class
                if weight > 0:
                    direction = f"supports '{predicted_class}'"
                else:
                    direction = f"against '{predicted_class}'"
                
                top_features.append({
                    'word': word,
                    'weight': float(weight),
                    'direction': direction,
                    'abs_weight': abs(weight)
                })
            
            # Sort by absolute weight
            top_features.sort(key=lambda x: x['abs_weight'], reverse=True)
            
            # Generate HTML
            try:
                lime_html = exp.as_html()
            except:
                lime_html = ""
            
            # Generate explanation text
            explanation_text = self._generate_explanation_text(
                filename, predicted_class, confidence, top_features
            )
            
            return LimeExplanation(
                document_id=document_id,
                filename=filename,
                predicted_class=predicted_class,
                confidence=confidence,
                class_probabilities=class_probabilities,
                top_features=top_features[:num_features],
                lime_html=lime_html,
                explanation_text=explanation_text
            )
            
        except Exception as e:
            print(f"LIME explanation failed: {e}")
            return None
    
    def _generate_explanation_text(
        self,
        filename: str,
        predicted_class: str,
        confidence: float,
        top_features: List[Dict]
    ) -> str:
        """Generate natural language explanation"""
        
        lines = [
            f"Document Classification Explanation: {filename}",
            f"",
            f"Predicted Sensitivity: {predicted_class.upper()}",
            f"Confidence: {confidence:.1%}",
            f"",
            f"Key words influencing this classification:"
        ]
        
        supporting = [f for f in top_features if f['weight'] > 0][:3]
        opposing = [f for f in top_features if f['weight'] < 0][:3]
        
        if supporting:
            lines.append(f"  Words supporting '{predicted_class}' classification:")
            for f in supporting:
                lines.append(f"    • '{f['word']}' (weight: +{f['weight']:.3f})")
        
        if opposing:
            lines.append(f"  Words suggesting different classification:")
            for f in opposing:
                lines.append(f"    • '{f['word']}' (weight: {f['weight']:.3f})")
        
        # Add recommendation based on sensitivity
        lines.append("")
        if predicted_class == "confidential":
            lines.append("⚠️ This document contains sensitive content and should be handled with care.")
        elif predicted_class == "internal":
            lines.append("ℹ️ This document is for internal use only.")
        else:
            lines.append("✓ This document can be shared publicly.")
        
        return "\n".join(lines)
    
    def explain_batch(
        self,
        documents: List[Dict],
        num_features: int = 10
    ) -> List[LimeExplanation]:
        """
        Generate explanations for multiple documents
        
        Args:
            documents: List of dicts with 'text', 'document_id', 'filename'
            num_features: Number of features per explanation
            
        Returns:
            List of LimeExplanations
        """
        explanations = []
        
        for doc in documents:
            exp = self.explain(
                text=doc.get('text', doc.get('content', '')),
                document_id=doc.get('document_id', 'unknown'),
                filename=doc.get('filename', 'document.txt'),
                num_features=num_features
            )
            if exp:
                explanations.append(exp)
        
        return explanations
    
    def save_explanation(
        self,
        explanation: LimeExplanation,
        output_dir: str = "xai_outputs/lime_explanations",
        save_html: bool = True
    ) -> Dict[str, str]:
        """
        Save explanation to files
        
        Args:
            explanation: LimeExplanation to save
            output_dir: Output directory
            save_html: Whether to save HTML file
            
        Returns:
            Dict with saved file paths
        """
        os.makedirs(output_dir, exist_ok=True)
        
        base_name = os.path.splitext(explanation.filename)[0]
        paths = {}
        
        # Save JSON
        json_path = os.path.join(output_dir, f"{base_name}_explanation.json")
        with open(json_path, 'w') as f:
            json.dump(explanation.to_dict(), f, indent=2)
        paths['json'] = json_path
        
        # Save HTML
        if save_html and explanation.lime_html:
            html_path = os.path.join(output_dir, f"{base_name}_explanation.html")
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(explanation.lime_html)
            paths['html'] = html_path
        
        return paths

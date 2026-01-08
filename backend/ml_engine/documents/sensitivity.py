"""
Document Sensitivity Classification Module
NLP-based classification for document sensitivity levels
Extracted and refactored from notebook prototype
"""
import os
import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

# Transformers will be imported lazily to avoid DLL issues at startup
TRANSFORMERS_AVAILABLE = False
_transformers_checked = False

def _check_transformers():
    """Lazy check for transformers availability"""
    global TRANSFORMERS_AVAILABLE, _transformers_checked
    if _transformers_checked:
        return TRANSFORMERS_AVAILABLE
    _transformers_checked = True
    try:
        import transformers
        TRANSFORMERS_AVAILABLE = True
    except (ImportError, OSError) as e:
        print(f"Transformers not available: {e}")
        TRANSFORMERS_AVAILABLE = False
    return TRANSFORMERS_AVAILABLE


class SensitivityLevel(str, Enum):
    """Document sensitivity levels"""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"


@dataclass
class ClassificationResult:
    """Result of document classification"""
    sensitivity: SensitivityLevel
    confidence: float
    method: str  # "keyword" or "zero_shot"
    probabilities: Dict[str, float]
    keywords_found: List[str]


class DocumentSensitivityClassifier:
    """
    Classify documents by sensitivity level using keyword matching
    and optionally zero-shot NLP classification
    """
    
    # Sensitivity keywords (from notebook prototype)
    SENSITIVITY_KEYWORDS = {
        'public': [
            'announcement', 'public', 'general', 'all employees', 'everyone',
            'press release', 'newsletter', 'company-wide', 'open', 'shared'
        ],
        'internal': [
            'internal', 'employees only', 'staff', 'not for external',
            'company use', 'internal use', 'do not share', 'internal memo',
            'team only', 'department'
        ],
        'confidential': [
            'confidential', 'restricted', 'secret', 'private', 'sensitive',
            'classified', 'proprietary', 'financial', 'pii', 'personal data',
            'gdpr', 'ccpa', 'unauthorized access', 'c-level', 'executive',
            'ssn', 'social security', 'credit card', 'salary', 'compensation',
            'merger', 'acquisition', 'trade secret', 'nda', 'legal privilege',
            'attorney-client', 'medical', 'health', 'hipaa'
        ]
    }
    
    # Risk weights for sensitivity levels
    RISK_WEIGHTS = {
        SensitivityLevel.PUBLIC: 0.1,
        SensitivityLevel.INTERNAL: 0.5,
        SensitivityLevel.CONFIDENTIAL: 0.9
    }
    
    def __init__(self, use_zero_shot: bool = False, model_name: str = "facebook/bart-large-mnli"):
        """
        Initialize classifier
        
        Args:
            use_zero_shot: Use zero-shot NLP model (slower but more accurate)
            model_name: HuggingFace model for zero-shot classification
        """
        self.use_zero_shot = use_zero_shot and _check_transformers()
        self.model_name = model_name
        self._classifier = None
        
        if self.use_zero_shot:
            self._init_zero_shot_classifier()
    
    def _init_zero_shot_classifier(self):
        """Initialize zero-shot classifier pipeline"""
        if not _check_transformers():
            print("Warning: transformers not available, falling back to keyword classification")
            self.use_zero_shot = False
            return
        
        try:
            from transformers import pipeline as tf_pipeline
            import torch
            device = 0 if torch.cuda.is_available() else -1
            self._classifier = tf_pipeline(
                "zero-shot-classification",
                model=self.model_name,
                device=device
            )
            print(f"Zero-shot classifier loaded on {'GPU' if device == 0 else 'CPU'}")
        except (ImportError, OSError, Exception) as e:
            print(f"Failed to load zero-shot classifier: {e}")
            self.use_zero_shot = False
    
    def classify_by_keywords(self, text: str) -> ClassificationResult:
        """
        Classify document using keyword matching
        
        Args:
            text: Document text content
            
        Returns:
            ClassificationResult with sensitivity and confidence
        """
        text_lower = text.lower()
        
        scores = {}
        keywords_found = {level: [] for level in self.SENSITIVITY_KEYWORDS}
        
        # Count keyword matches for each level
        for level, keywords in self.SENSITIVITY_KEYWORDS.items():
            score = 0
            for kw in keywords:
                # Check for whole word/phrase matches
                pattern = r'\b' + re.escape(kw) + r'\b'
                matches = re.findall(pattern, text_lower)
                if matches:
                    score += len(matches)
                    keywords_found[level].append(kw)
            scores[level] = score
        
        total = sum(scores.values())
        
        if total == 0:
            # Default to internal with low confidence if no keywords found
            return ClassificationResult(
                sensitivity=SensitivityLevel.INTERNAL,
                confidence=0.5,
                method="keyword",
                probabilities={
                    "public": 0.2,
                    "internal": 0.6,
                    "confidential": 0.2
                },
                keywords_found=[]
            )
        
        # Normalize to probabilities
        probabilities = {level: score / total for level, score in scores.items()}
        
        # Get predicted level
        predicted_level = max(scores, key=scores.get)
        confidence = probabilities[predicted_level]
        
        # Boost confidence if confidential keywords found (important for security)
        if predicted_level == "confidential" and confidence < 0.6:
            confidence = min(confidence * 1.5, 0.95)
        
        return ClassificationResult(
            sensitivity=SensitivityLevel(predicted_level),
            confidence=confidence,
            method="keyword",
            probabilities=probabilities,
            keywords_found=keywords_found[predicted_level]
        )
    
    def classify_zero_shot(self, text: str, max_length: int = 512) -> ClassificationResult:
        """
        Classify document using zero-shot NLP model
        
        Args:
            text: Document text content
            max_length: Maximum text length to process
            
        Returns:
            ClassificationResult with sensitivity and confidence
        """
        if not self._classifier:
            return self.classify_by_keywords(text)
        
        # Truncate text if needed
        words = text.split()
        if len(words) > max_length:
            text = ' '.join(words[:max_length])
        
        try:
            candidate_labels = [
                'public document for everyone',
                'internal document for employees only',
                'confidential restricted document'
            ]
            
            result = self._classifier(text, candidate_labels)
            
            # Map labels to sensitivity levels
            label_map = {
                'public document for everyone': SensitivityLevel.PUBLIC,
                'internal document for employees only': SensitivityLevel.INTERNAL,
                'confidential restricted document': SensitivityLevel.CONFIDENTIAL
            }
            
            predicted_label = result['labels'][0]
            confidence = result['scores'][0]
            
            probabilities = {}
            for label, score in zip(result['labels'], result['scores']):
                level = label_map[label].value
                probabilities[level] = score
            
            # Also get keywords for reference
            keyword_result = self.classify_by_keywords(text)
            
            return ClassificationResult(
                sensitivity=label_map[predicted_label],
                confidence=confidence,
                method="zero_shot",
                probabilities=probabilities,
                keywords_found=keyword_result.keywords_found
            )
            
        except Exception as e:
            print(f"Zero-shot classification failed: {e}")
            return self.classify_by_keywords(text)
    
    def classify(self, text: str) -> ClassificationResult:
        """
        Classify document sensitivity
        
        Args:
            text: Document text content
            
        Returns:
            ClassificationResult
        """
        if self.use_zero_shot:
            return self.classify_zero_shot(text)
        return self.classify_by_keywords(text)
    
    def classify_file(self, filepath: str) -> ClassificationResult:
        """
        Classify a document file
        
        Args:
            filepath: Path to document file
            
        Returns:
            ClassificationResult
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        return self.classify(content)
    
    def get_risk_score(self, result: ClassificationResult) -> float:
        """
        Convert classification result to risk score
        
        Args:
            result: ClassificationResult
            
        Returns:
            Risk score (0-1)
        """
        base_risk = self.RISK_WEIGHTS[result.sensitivity]
        # Weight by confidence
        return base_risk * result.confidence
    
    def classify_directory(
        self,
        directory: str,
        extensions: List[str] = ['.txt', '.md', '.doc', '.docx', '.pdf']
    ) -> List[Dict]:
        """
        Classify all documents in a directory
        
        Args:
            directory: Directory path
            extensions: File extensions to process
            
        Returns:
            List of classification results with filenames
        """
        results = []
        
        for filename in os.listdir(directory):
            if not any(filename.lower().endswith(ext) for ext in extensions):
                continue
            
            filepath = os.path.join(directory, filename)
            
            try:
                result = self.classify_file(filepath)
                results.append({
                    'filename': filename,
                    'filepath': filepath,
                    'sensitivity': result.sensitivity.value,
                    'confidence': result.confidence,
                    'method': result.method,
                    'risk_score': self.get_risk_score(result),
                    'keywords_found': result.keywords_found,
                    'probabilities': result.probabilities
                })
            except Exception as e:
                print(f"Error classifying {filename}: {e}")
        
        return results

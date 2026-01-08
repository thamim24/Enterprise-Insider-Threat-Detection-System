"""
Document Integrity Verification Module
Hash-based and semantic similarity verification for tampering detection
Extracted and refactored from notebook prototype
"""
import hashlib
import os
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

# Sentence transformers will be imported lazily to avoid DLL issues
SENTENCE_TRANSFORMERS_AVAILABLE = False
_sentence_transformers_checked = False

def _check_sentence_transformers():
    """Lazy check for sentence-transformers availability"""
    global SENTENCE_TRANSFORMERS_AVAILABLE, _sentence_transformers_checked
    if _sentence_transformers_checked:
        return SENTENCE_TRANSFORMERS_AVAILABLE
    _sentence_transformers_checked = True
    try:
        from sentence_transformers import SentenceTransformer
        SENTENCE_TRANSFORMERS_AVAILABLE = True
    except (ImportError, OSError) as e:
        print(f"Sentence transformers not available: {e}")
        SENTENCE_TRANSFORMERS_AVAILABLE = False
    return SENTENCE_TRANSFORMERS_AVAILABLE


class TamperSeverity(str, Enum):
    """Severity levels for document tampering"""
    NONE = "none"
    MINOR = "minor"       # Small changes, semantically similar
    MODERATE = "moderate" # Noticeable changes
    MAJOR = "major"       # Significant changes
    UNKNOWN = "unknown"   # Cannot determine (no semantic model)


@dataclass
class IntegrityResult:
    """Result of integrity verification"""
    document_id: str
    filename: str
    
    # Hash verification
    original_hash: str
    current_hash: str
    hash_match: bool
    
    # Tampering detection
    is_tampered: bool
    tamper_severity: TamperSeverity
    
    # Semantic similarity (if available)
    semantic_similarity: Optional[float]
    
    # Change details
    size_change_bytes: Optional[int]
    size_change_percent: Optional[float]
    
    # Metadata
    verified_at: datetime
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'document_id': self.document_id,
            'filename': self.filename,
            'original_hash': self.original_hash,
            'current_hash': self.current_hash,
            'hash_match': self.hash_match,
            'is_tampered': self.is_tampered,
            'tamper_severity': self.tamper_severity.value,
            'semantic_similarity': self.semantic_similarity,
            'size_change_bytes': self.size_change_bytes,
            'size_change_percent': self.size_change_percent,
            'verified_at': self.verified_at.isoformat()
        }


class IntegrityVerifier:
    """
    Verify document integrity using hash comparison and semantic similarity
    """
    
    # Semantic similarity thresholds for severity
    SEVERITY_THRESHOLDS = {
        'minor': 0.95,     # > 95% similar = minor changes
        'moderate': 0.85,  # 85-95% similar = moderate changes
        'major': 0.0       # < 85% similar = major changes
    }
    
    def __init__(self, use_semantic: bool = True, model_name: str = 'all-MiniLM-L6-v2'):
        """
        Initialize verifier
        
        Args:
            use_semantic: Use semantic similarity for severity assessment
            model_name: Sentence transformer model name
        """
        self.use_semantic = use_semantic and _check_sentence_transformers()
        self.model_name = model_name
        self._model = None
        
        # Document hash registry (in production, use database)
        self._hash_registry: Dict[str, Dict] = {}
        
        if self.use_semantic:
            self._init_semantic_model()
    
    def _init_semantic_model(self):
        """Initialize sentence transformer model"""
        if not _check_sentence_transformers():
            print("Warning: sentence-transformers not available")
            self.use_semantic = False
            return
        
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
            print(f"Semantic model loaded: {self.model_name}")
        except (ImportError, OSError, Exception) as e:
            print(f"Failed to load semantic model: {e}")
            self.use_semantic = False
    
    @staticmethod
    def compute_hash(content: str, algorithm: str = 'sha256') -> str:
        """
        Compute hash of content
        
        Args:
            content: Text content
            algorithm: Hash algorithm (sha256, md5, etc.)
            
        Returns:
            Hex hash string
        """
        if isinstance(content, str):
            content = content.encode('utf-8')
        
        hasher = hashlib.new(algorithm)
        hasher.update(content)
        return hasher.hexdigest()
    
    def compute_semantic_similarity(self, text1: str, text2: str) -> Optional[float]:
        """
        Compute semantic similarity between two texts
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score (0-1) or None if not available
        """
        if not self.use_semantic or not self._model:
            return None
        
        try:
            import numpy as np
            
            # Compute embeddings
            embeddings = self._model.encode([text1, text2])
            
            # Compute cosine similarity
            similarity = np.dot(embeddings[0], embeddings[1]) / (
                np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
            )
            
            return float(similarity)
        except Exception as e:
            print(f"Semantic similarity failed: {e}")
            return None
    
    def register_document(
        self,
        document_id: str,
        content: str,
        filename: str
    ) -> str:
        """
        Register a document's hash for future verification
        
        Args:
            document_id: Unique document identifier
            content: Document content
            filename: Document filename
            
        Returns:
            Document hash
        """
        doc_hash = self.compute_hash(content)
        
        self._hash_registry[document_id] = {
            'hash': doc_hash,
            'filename': filename,
            'size_bytes': len(content.encode('utf-8')),
            'registered_at': datetime.utcnow()
        }
        
        return doc_hash
    
    def verify_content(
        self,
        document_id: str,
        current_content: str,
        original_content: Optional[str] = None
    ) -> IntegrityResult:
        """
        Verify document content against registered hash
        
        Args:
            document_id: Document identifier
            current_content: Current content to verify
            original_content: Optional original content for semantic comparison
            
        Returns:
            IntegrityResult
        """
        current_hash = self.compute_hash(current_content)
        current_size = len(current_content.encode('utf-8'))
        
        # Get registered info
        registered = self._hash_registry.get(document_id, {})
        original_hash = registered.get('hash', current_hash)
        filename = registered.get('filename', document_id)
        original_size = registered.get('size_bytes', current_size)
        
        # Check hash match
        hash_match = (original_hash == current_hash)
        is_tampered = not hash_match
        
        # Calculate size changes
        size_change_bytes = current_size - original_size
        size_change_percent = (
            (size_change_bytes / original_size * 100)
            if original_size > 0 else 0
        )
        
        # Determine severity
        semantic_similarity = None
        tamper_severity = TamperSeverity.NONE
        
        if is_tampered:
            if self.use_semantic and original_content:
                semantic_similarity = self.compute_semantic_similarity(
                    original_content, current_content
                )
                
                if semantic_similarity is not None:
                    if semantic_similarity > self.SEVERITY_THRESHOLDS['minor']:
                        tamper_severity = TamperSeverity.MINOR
                    elif semantic_similarity > self.SEVERITY_THRESHOLDS['moderate']:
                        tamper_severity = TamperSeverity.MODERATE
                    else:
                        tamper_severity = TamperSeverity.MAJOR
                else:
                    tamper_severity = TamperSeverity.UNKNOWN
            else:
                # Without semantic similarity, use size change as proxy
                if abs(size_change_percent) < 5:
                    tamper_severity = TamperSeverity.MINOR
                elif abs(size_change_percent) < 20:
                    tamper_severity = TamperSeverity.MODERATE
                else:
                    tamper_severity = TamperSeverity.MAJOR
        
        return IntegrityResult(
            document_id=document_id,
            filename=filename,
            original_hash=original_hash,
            current_hash=current_hash,
            hash_match=hash_match,
            is_tampered=is_tampered,
            tamper_severity=tamper_severity,
            semantic_similarity=semantic_similarity,
            size_change_bytes=size_change_bytes,
            size_change_percent=size_change_percent,
            verified_at=datetime.utcnow()
        )
    
    def verify_file(
        self,
        document_id: str,
        filepath: str,
        original_filepath: Optional[str] = None
    ) -> IntegrityResult:
        """
        Verify a document file
        
        Args:
            document_id: Document identifier
            filepath: Path to current file
            original_filepath: Optional path to original file
            
        Returns:
            IntegrityResult
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            current_content = f.read()
        
        original_content = None
        if original_filepath and os.path.exists(original_filepath):
            with open(original_filepath, 'r', encoding='utf-8') as f:
                original_content = f.read()
        
        result = self.verify_content(
            document_id,
            current_content,
            original_content
        )
        result.filename = os.path.basename(filepath)
        
        return result
    
    def verify_directory(
        self,
        current_dir: str,
        original_dir: str,
        extensions: list = ['.txt']
    ) -> list:
        """
        Verify all documents in a directory against originals
        
        Args:
            current_dir: Directory with current documents
            original_dir: Directory with original documents
            extensions: File extensions to check
            
        Returns:
            List of IntegrityResults
        """
        results = []
        
        for filename in os.listdir(current_dir):
            if not any(filename.lower().endswith(ext) for ext in extensions):
                continue
            
            current_path = os.path.join(current_dir, filename)
            original_path = os.path.join(original_dir, filename)
            
            if not os.path.exists(original_path):
                continue
            
            document_id = os.path.splitext(filename)[0]
            
            # Register original if not already registered
            if document_id not in self._hash_registry:
                with open(original_path, 'r', encoding='utf-8') as f:
                    self.register_document(document_id, f.read(), filename)
            
            result = self.verify_file(document_id, current_path, original_path)
            results.append(result)
        
        return results
    
    def get_risk_score(self, result: IntegrityResult) -> float:
        """
        Convert integrity result to risk score
        
        Args:
            result: IntegrityResult
            
        Returns:
            Risk score (0-1)
        """
        if not result.is_tampered:
            return 0.0
        
        severity_scores = {
            TamperSeverity.NONE: 0.0,
            TamperSeverity.MINOR: 0.3,
            TamperSeverity.MODERATE: 0.6,
            TamperSeverity.MAJOR: 0.9,
            TamperSeverity.UNKNOWN: 0.7
        }
        
        return severity_scores.get(result.tamper_severity, 0.7)

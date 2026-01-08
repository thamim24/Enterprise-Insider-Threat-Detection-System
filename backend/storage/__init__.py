"""
Document Storage Module
Handles actual file storage and retrieval
"""
import os
from pathlib import Path

# Storage paths
STORAGE_ROOT = Path(__file__).parent
DOCUMENTS_DIR = STORAGE_ROOT / "documents"

# Ensure directories exist
DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)


def get_document_path(document_id: str, filename: str) -> Path:
    """Get the full path for a document file"""
    return DOCUMENTS_DIR / f"{document_id}_{filename}"


def save_document(document_id: str, filename: str, content: str) -> Path:
    """Save document content to file"""
    path = get_document_path(document_id, filename)
    path.write_text(content, encoding='utf-8')
    return path


def read_document(document_id: str, filename: str) -> str:
    """Read document content from file"""
    path = get_document_path(document_id, filename)
    if path.exists():
        return path.read_text(encoding='utf-8')
    return None


def document_exists(document_id: str, filename: str) -> bool:
    """Check if document file exists"""
    return get_document_path(document_id, filename).exists()


def get_document_size(document_id: str, filename: str) -> int:
    """Get document file size in bytes"""
    path = get_document_path(document_id, filename)
    if path.exists():
        return path.stat().st_size
    return 0

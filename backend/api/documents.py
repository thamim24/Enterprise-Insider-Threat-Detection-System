"""
Document API Routes
Document listing, viewing, and actions
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import PlainTextResponse, Response
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from pathlib import Path
import hashlib
import uuid

from ..db import get_db, Document, SensitivityLevel, Event, Alert, User
from ..db.models import ActionType, AlertPriority
from ..core.security import get_current_active_user, TokenData, check_department_access
from ..core.config import DEPARTMENTS
from ..ml.sensitivity_classifier import analyze_document_for_upload

router = APIRouter(prefix="/documents", tags=["Documents"])

# Document storage path
STORAGE_DIR = Path(__file__).parent.parent / "storage" / "documents"


def get_document_content(document_id: str, filename: str) -> Optional[str]:
    """Read actual document content from file storage"""
    # Try multiple file patterns
    patterns = [
        f"{document_id}_{filename}.txt",
        f"{document_id}_{filename}",
        f"{filename}.txt",
        filename
    ]
    
    for pattern in patterns:
        file_path = STORAGE_DIR / pattern
        if file_path.exists():
            try:
                return file_path.read_text(encoding='utf-8')
            except Exception:
                continue
    
    return None


class DocumentResponse(BaseModel):
    """Document response model"""
    document_id: str
    filename: str
    department: str
    sensitivity: str
    classification_confidence: float
    is_tampered: bool
    tamper_severity: str
    file_size_bytes: Optional[int]
    content_preview: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    """Document list with pagination"""
    documents: List[DocumentResponse]
    total: int
    page: int
    page_size: int
    departments: List[str]


class DocumentViewResponse(BaseModel):
    """Response when viewing a document"""
    document: DocumentResponse
    content: str
    access_info: dict  # Is cross-department, risk info


class DocumentContentUpdate(BaseModel):
    """Document content update request"""
    content: str


class DocumentUploadRequest(BaseModel):
    """Document upload request"""
    filename: str
    content: str
    department: str
    sensitivity: Optional[str] = "INTERNAL"


class DocumentUploadResponse(BaseModel):
    """Document upload response"""
    document_id: str
    filename: str
    department: str
    sensitivity: str  # User-declared sensitivity
    ml_predicted_sensitivity: str  # ML-classified sensitivity
    ml_confidence: float  # ML confidence score
    sensitivity_mismatch: bool  # True if user != ML prediction
    message: str
    is_cross_department: bool
    anomaly_triggered: bool
    warning: Optional[str] = None
    ml_explanation: Optional[str] = None  # Why ML predicted this level


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    department: Optional[str] = Query(None, description="Filter by department"),
    sensitivity: Optional[str] = Query(None, description="Filter by sensitivity"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: TokenData = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    List all documents
    
    All users can see all documents.
    Risk is calculated on ACTION, not visibility.
    """
    query = db.query(Document)
    
    # Apply filters
    if department:
        query = query.filter(Document.department == department)
    
    if sensitivity:
        query = query.filter(Document.sensitivity == SensitivityLevel(sensitivity))
    
    # Get total count
    total = query.count()
    
    # Paginate
    offset = (page - 1) * page_size
    documents = query.offset(offset).limit(page_size).all()
    
    return DocumentListResponse(
        documents=[DocumentResponse(
            document_id=doc.document_id,
            filename=doc.filename,
            department=doc.department,
            sensitivity=doc.sensitivity.value,
            classification_confidence=doc.classification_confidence,
            is_tampered=doc.is_tampered,
            tamper_severity=doc.tamper_severity,
            file_size_bytes=doc.file_size_bytes,
            content_preview=doc.content_preview[:200] if doc.content_preview else None,
            created_at=doc.created_at,
            updated_at=doc.updated_at
        ) for doc in documents],
        total=total,
        page=page,
        page_size=page_size,
        departments=DEPARTMENTS
    )


@router.get("/all", response_model=List[DocumentResponse])
async def get_all_documents(
    current_user: TokenData = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all documents (no pagination)
    """
    documents = db.query(Document).all()
    
    return [DocumentResponse(
        document_id=doc.document_id,
        filename=doc.filename,
        department=doc.department,
        sensitivity=doc.sensitivity.value,
        classification_confidence=doc.classification_confidence,
        is_tampered=doc.is_tampered,
        tamper_severity=doc.tamper_severity,
        file_size_bytes=doc.file_size_bytes,
        content_preview=doc.content_preview[:200] if doc.content_preview else None,
        created_at=doc.created_at,
        updated_at=doc.updated_at
    ) for doc in documents]


@router.get("/by-department/{department}", response_model=List[DocumentResponse])
async def get_documents_by_department(
    department: str,
    current_user: TokenData = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get documents for a specific department
    """
    if department not in DEPARTMENTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid department. Must be one of: {DEPARTMENTS}"
        )
    
    documents = db.query(Document).filter(Document.department == department).all()
    
    return [DocumentResponse(
        document_id=doc.document_id,
        filename=doc.filename,
        department=doc.department,
        sensitivity=doc.sensitivity.value,
        classification_confidence=doc.classification_confidence,
        is_tampered=doc.is_tampered,
        tamper_severity=doc.tamper_severity,
        file_size_bytes=doc.file_size_bytes,
        content_preview=doc.content_preview[:200] if doc.content_preview else None,
        created_at=doc.created_at,
        updated_at=doc.updated_at
    ) for doc in documents]


@router.get("/{document_id}/view", response_model=DocumentViewResponse)
async def view_document(
    document_id: str,
    current_user: TokenData = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    View a document
    
    This is a VIEW action - event will be ingested automatically.
    Returns document content and access information.
    """
    document = db.query(Document).filter(Document.document_id == document_id).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Check department access
    access_info = check_department_access(
        current_user.department,
        document.department,
        "view"
    )
    
    # Note: Event ingestion should be called separately via /events/ingest
    # Frontend is responsible for calling both endpoints
    
    # Use full_content from database (current state after any modifications)
    # Fall back to original_content, then file storage, then content_preview
    document_content = (
        document.full_content or 
        document.original_content or 
        get_document_content(document.document_id, document.filename) or 
        document.content_preview or 
        "No content available"
    )
    
    return DocumentViewResponse(
        document=DocumentResponse(
            document_id=document.document_id,
            filename=document.filename,
            department=document.department,
            sensitivity=document.sensitivity.value,
            classification_confidence=document.classification_confidence,
            is_tampered=document.is_tampered,
            tamper_severity=document.tamper_severity,
            file_size_bytes=document.file_size_bytes,
            content_preview=document.content_preview,
            created_at=document.created_at,
            updated_at=document.updated_at
        ),
        content=document_content,
        access_info=access_info
    )


@router.post("/{document_id}/download")
async def download_document(
    document_id: str,
    current_user: TokenData = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Download a document
    
    This is a DOWNLOAD action - higher risk than view.
    Event must be ingested separately.
    Returns actual file content for download.
    """
    document = db.query(Document).filter(Document.document_id == document_id).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Check access
    access_info = check_department_access(
        current_user.department,
        document.department,
        "download"
    )
    
    # Get actual document content - prioritize full_content from DB
    content = (
        document.full_content or
        document.original_content or
        get_document_content(document_id, document.filename) or
        document.content_preview or
        "Document content not available"
    )
    
    # Create a downloadable text file with meaningful filename
    # Since our documents are text-based, we serve as .txt
    base_filename = document.filename.rsplit('.', 1)[0] if '.' in document.filename else document.filename
    download_filename = f"{base_filename}_content.txt"
    
    return Response(
        content=content,
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{download_filename}"',
            "X-Access-Info": "cross-department" if access_info.get("is_cross_department") else "same-department",
            "X-Document-ID": document_id
        }
    )


@router.post("/{document_id}/modify")
async def modify_document(
    document_id: str,
    update: DocumentContentUpdate,
    current_user: TokenData = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Modify a document
    
    This is a MODIFY action - triggers integrity check.
    Event must be ingested with document_content for integrity verification.
    """
    document = db.query(Document).filter(Document.document_id == document_id).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Check access
    access_info = check_department_access(
        current_user.department,
        document.department,
        "modify"
    )
    
    # Warning for cross-department modification
    warning = None
    if access_info["is_cross_department"]:
        warning = "⚠️ Cross-department document modification is heavily monitored."
    
    return {
        "document_id": document_id,
        "action": "modify",
        "access_info": access_info,
        "warning": warning,
        "message": "Modification request received. Please submit via event ingestion for integrity verification."
    }


@router.get("/statistics")
async def get_document_statistics(
    current_user: TokenData = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get document statistics
    """
    total = db.query(Document).count()
    
    by_sensitivity = {}
    for level in SensitivityLevel:
        count = db.query(Document).filter(Document.sensitivity == level).count()
        by_sensitivity[level.value] = count
    
    by_department = {}
    for dept in DEPARTMENTS:
        count = db.query(Document).filter(Document.department == dept).count()
        by_department[dept] = count
    
    tampered = db.query(Document).filter(Document.is_tampered == True).count()
    
    return {
        "total_documents": total,
        "by_sensitivity": by_sensitivity,
        "by_department": by_department,
        "tampered_documents": tampered,
        "integrity_healthy": total - tampered
    }


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    request: DocumentUploadRequest,
    current_user: TokenData = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Upload a new document with HYBRID sensitivity classification.
    
    HYBRID APPROACH:
    1. User declares sensitivity level during upload
    2. ML automatically classifies document content
    3. System compares both - mismatches are flagged as potential security risks
    4. Risk score increases if user declares lower sensitivity than ML predicts
    
    Users can only upload to their own department without triggering anomaly.
    Cross-department uploads will be flagged and create an ML alert.
    """
    # Validate department (case-insensitive)
    dept_upper = request.department.upper()
    if dept_upper not in DEPARTMENTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid department. Must be one of: {DEPARTMENTS}"
        )
    normalized_department = dept_upper
    
    # Validate user-declared sensitivity (case-insensitive)
    try:
        sensitivity = SensitivityLevel(request.sensitivity.lower())
    except ValueError:
        sensitivity = SensitivityLevel.INTERNAL
    
    # ========== ML SENSITIVITY CLASSIFICATION ==========
    # Analyze document content and compare with user declaration
    ml_analysis = analyze_document_for_upload(request.content, sensitivity.value)
    
    ml_predicted = ml_analysis["ml_predicted_sensitivity"]
    ml_confidence = ml_analysis["ml_confidence"]
    sensitivity_mismatch = ml_analysis["is_mismatch"]
    mismatch_risk_modifier = ml_analysis["mismatch_risk_modifier"]
    ml_explanation = ml_analysis["ml_explanation"]
    
    # ========== CROSS-DEPARTMENT CHECK ==========
    user_dept = current_user.department.upper() if current_user.department else ""
    is_cross_department = user_dept != normalized_department
    anomaly_triggered = False
    warnings = []
    
    if is_cross_department:
        anomaly_triggered = True
        warnings.append(f"⚠️ CROSS-DEPARTMENT: User from {current_user.department} uploading to {normalized_department}")
    
    # ========== SENSITIVITY MISMATCH CHECK ==========
    if sensitivity_mismatch:
        anomaly_triggered = True
        warnings.append(ml_analysis["mismatch_explanation"])
    
    # Combine warnings
    warning = " | ".join(warnings) if warnings else None
    
    # ========== GENERATE DOCUMENT ID ==========
    max_doc = db.query(Document).order_by(Document.document_id.desc()).first()
    if max_doc:
        try:
            num = int(max_doc.document_id.replace("DOC", "")) + 1
        except:
            num = db.query(Document).count() + 1
    else:
        num = 1
    new_doc_id = f"DOC{num:03d}"
    
    # Calculate hash
    content_hash = hashlib.sha256(request.content.encode()).hexdigest()[:16]
    
    # Create preview
    content_preview = request.content[:200].replace('\n', ' ').strip()
    if len(request.content) > 200:
        content_preview += "..."
    
    # Save to file storage
    storage_dir = STORAGE_DIR / normalized_department
    storage_dir.mkdir(parents=True, exist_ok=True)
    
    safe_filename = "".join(c for c in request.filename if c.isalnum() or c in "._- ")
    file_path = storage_dir / f"{new_doc_id}_{safe_filename}.txt"
    file_path.write_text(request.content, encoding='utf-8')
    
    # ========== CREATE DOCUMENT WITH ML DATA ==========
    document = Document(
        document_id=new_doc_id,
        filename=request.filename,
        filepath=f"/documents/{normalized_department.lower()}/{request.filename}",
        department=normalized_department,
        sensitivity=sensitivity,  # User-declared
        ml_predicted_sensitivity=ml_predicted,  # ML-predicted
        ml_confidence=ml_confidence,
        sensitivity_mismatch=sensitivity_mismatch,
        classification_confidence=ml_confidence,
        original_hash=content_hash,
        current_hash=content_hash,
        file_size_bytes=len(request.content.encode('utf-8')),
        content_preview=content_preview,
        full_content=request.content,
        original_content=request.content,
    )
    db.add(document)
    db.flush()
    
    # ========== CREATE EVENT AND ALERT ==========
    user = db.query(User).filter(User.user_id == current_user.user_id).first()
    if not user:
        user = db.query(User).filter(User.username == current_user.username).first()
    
    if user:
        # Calculate risk score based on multiple factors
        base_risk = 0.15
        if is_cross_department:
            base_risk += 0.4  # Cross-department adds 0.4
        if sensitivity_mismatch:
            base_risk += mismatch_risk_modifier  # Mismatch adds variable risk
        
        risk_score = min(base_risk, 1.0)  # Cap at 1.0
        
        # Determine risk level
        if risk_score >= 0.7:
            risk_level = "critical"
        elif risk_score >= 0.5:
            risk_level = "high"
        elif risk_score >= 0.3:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        event = Event(
            event_id=f"EVT-{uuid.uuid4().hex[:8].upper()}",
            user_id=user.id,
            user_department=current_user.department,
            action=ActionType.UPLOAD,
            document_id=document.id,
            target_department=normalized_department,
            timestamp=datetime.utcnow(),
            bytes_transferred=len(request.content.encode('utf-8')),
            source_ip="0.0.0.0",
            is_cross_department=is_cross_department,
            risk_score=risk_score,
            risk_level=risk_level,
        )
        db.add(event)
        db.flush()
        
        # Create alert for anomalies (cross-dept OR sensitivity mismatch)
        if anomaly_triggered:
            # Determine priority based on risk
            if sensitivity_mismatch and is_cross_department:
                priority = AlertPriority.CRITICAL
            elif sensitivity_mismatch:
                priority = AlertPriority.HIGH
            elif is_cross_department:
                priority = AlertPriority.HIGH
            else:
                priority = AlertPriority.MEDIUM
            
            # Build detailed summary
            alert_parts = []
            if is_cross_department:
                alert_parts.append(f"Cross-department upload ({current_user.department}→{normalized_department})")
            if sensitivity_mismatch:
                alert_parts.append(f"Sensitivity mismatch (User: {sensitivity.value}, ML: {ml_predicted})")
            
            alert = Alert(
                alert_id=f"ALT-{uuid.uuid4().hex[:8].upper()}",
                event_id=event.id,
                user_id=user.id,
                priority=priority,
                risk_score=risk_score,
                summary=f"Security Alert: {' | '.join(alert_parts)} - {current_user.username}",
                details={
                    "document_id": new_doc_id,
                    "filename": request.filename,
                    "user_department": current_user.department,
                    "target_department": normalized_department,
                    "user_declared_sensitivity": sensitivity.value,
                    "ml_predicted_sensitivity": ml_predicted,
                    "ml_confidence": ml_confidence,
                    "sensitivity_mismatch": sensitivity_mismatch,
                    "is_cross_department": is_cross_department,
                    "ml_explanation": ml_explanation,
                    "risk_indicators": ml_analysis.get("risk_indicators", []),
                },
                status="open",
            )
            db.add(alert)
    
    db.commit()
    
    # Build response message
    if sensitivity_mismatch and is_cross_department:
        message = "⚠️ CRITICAL: Document uploaded with cross-department access AND sensitivity mismatch detected!"
    elif sensitivity_mismatch:
        message = f"⚠️ WARNING: You declared '{sensitivity.value}' but ML detected '{ml_predicted}' content. This has been flagged."
    elif is_cross_department:
        message = "Document uploaded with cross-department security alert"
    else:
        message = f"Document uploaded successfully (ML verified as {ml_predicted})"
    
    return DocumentUploadResponse(
        document_id=new_doc_id,
        filename=request.filename,
        department=normalized_department,
        sensitivity=sensitivity.value,
        ml_predicted_sensitivity=ml_predicted,
        ml_confidence=ml_confidence,
        sensitivity_mismatch=sensitivity_mismatch,
        message=message,
        is_cross_department=is_cross_department,
        anomaly_triggered=anomaly_triggered,
        warning=warning,
        ml_explanation=ml_explanation
    )


@router.post("/seed-demo-documents")
async def seed_demo_documents(db: Session = Depends(get_db)):
    """
    Seed demo documents for development (REMOVE IN PRODUCTION)
    """
    # Default documents for each department
    default_documents = [
        # HR Documents
        {
            "document_id": "DOC001",
            "filename": "employee_handbook.pdf",
            "filepath": "/documents/hr/employee_handbook.pdf",
            "department": "HR",
            "sensitivity": SensitivityLevel.INTERNAL,
            "original_hash": "abc123hash",
            "current_hash": "abc123hash",
            "file_size_bytes": 245000,
            "content_preview": "Employee Handbook 2026 - Company policies and guidelines for all employees.",
        },
        {
            "document_id": "DOC002",
            "filename": "salary_structure.xlsx",
            "filepath": "/documents/hr/salary_structure.xlsx",
            "department": "HR",
            "sensitivity": SensitivityLevel.CONFIDENTIAL,
            "original_hash": "def456hash",
            "current_hash": "def456hash",
            "file_size_bytes": 52000,
            "content_preview": "Salary Structure - Confidential employee compensation details including SSN data.",
        },
        {
            "document_id": "DOC003",
            "filename": "onboarding_checklist.docx",
            "filepath": "/documents/hr/onboarding_checklist.docx",
            "department": "HR",
            "sensitivity": SensitivityLevel.INTERNAL,
            "original_hash": "ghi789hash",
            "current_hash": "ghi789hash",
            "file_size_bytes": 18000,
            "content_preview": "New Employee Onboarding Checklist - Internal HR process document.",
        },
        # FINANCE Documents
        {
            "document_id": "DOC004",
            "filename": "quarterly_report_q4.pdf",
            "filepath": "/documents/finance/quarterly_report_q4.pdf",
            "department": "FINANCE",
            "sensitivity": SensitivityLevel.CONFIDENTIAL,
            "original_hash": "jkl012hash",
            "current_hash": "jkl012hash",
            "file_size_bytes": 890000,
            "content_preview": "Q4 2025 Financial Report - Confidential quarterly earnings and projections.",
        },
        {
            "document_id": "DOC005",
            "filename": "budget_2026.xlsx",
            "filepath": "/documents/finance/budget_2026.xlsx",
            "department": "FINANCE",
            "sensitivity": SensitivityLevel.CONFIDENTIAL,
            "original_hash": "mno345hash",
            "current_hash": "mno345hash",
            "file_size_bytes": 125000,
            "content_preview": "Annual Budget 2026 - Departmental budget allocations and forecasts.",
        },
        {
            "document_id": "DOC006",
            "filename": "expense_policy.pdf",
            "filepath": "/documents/finance/expense_policy.pdf",
            "department": "FINANCE",
            "sensitivity": SensitivityLevel.INTERNAL,
            "original_hash": "pqr678hash",
            "current_hash": "pqr678hash",
            "file_size_bytes": 45000,
            "content_preview": "Expense Reimbursement Policy - Guidelines for employee expense claims.",
        },
        # LEGAL Documents
        {
            "document_id": "DOC007",
            "filename": "nda_template.docx",
            "filepath": "/documents/legal/nda_template.docx",
            "department": "LEGAL",
            "sensitivity": SensitivityLevel.INTERNAL,
            "original_hash": "stu901hash",
            "current_hash": "stu901hash",
            "file_size_bytes": 32000,
            "content_preview": "Non-Disclosure Agreement Template - Standard NDA for business partners.",
        },
        {
            "document_id": "DOC008",
            "filename": "merger_acquisition_plan.pdf",
            "filepath": "/documents/legal/merger_acquisition_plan.pdf",
            "department": "LEGAL",
            "sensitivity": SensitivityLevel.CONFIDENTIAL,
            "original_hash": "vwx234hash",
            "current_hash": "vwx234hash",
            "file_size_bytes": 560000,
            "content_preview": "M&A Strategic Plan - Confidential merger and acquisition targets for 2026.",
        },
        # IT Documents
        {
            "document_id": "DOC009",
            "filename": "security_protocols.pdf",
            "filepath": "/documents/it/security_protocols.pdf",
            "department": "IT",
            "sensitivity": SensitivityLevel.CONFIDENTIAL,
            "original_hash": "yza567hash",
            "current_hash": "yza567hash",
            "file_size_bytes": 78000,
            "content_preview": "IT Security Protocols - System access controls and security procedures.",
        },
        {
            "document_id": "DOC010",
            "filename": "network_diagram.vsdx",
            "filepath": "/documents/it/network_diagram.vsdx",
            "department": "IT",
            "sensitivity": SensitivityLevel.INTERNAL,
            "original_hash": "bcd890hash",
            "current_hash": "bcd890hash",
            "file_size_bytes": 340000,
            "content_preview": "Corporate Network Architecture - Internal network topology diagram.",
        },
        # PUBLIC Documents
        {
            "document_id": "DOC011",
            "filename": "company_announcement.pdf",
            "filepath": "/documents/public/company_announcement.pdf",
            "department": "HR",
            "sensitivity": SensitivityLevel.PUBLIC,
            "original_hash": "efg123hash",
            "current_hash": "efg123hash",
            "file_size_bytes": 15000,
            "content_preview": "Company Announcement - Public press release for all employees and stakeholders.",
        },
    ]
    
    created = []
    updated = []
    
    for doc_data in default_documents:
        existing = db.query(Document).filter(Document.document_id == doc_data["document_id"]).first()
        
        if existing:
            # Update existing
            for key, value in doc_data.items():
                setattr(existing, key, value)
            updated.append(doc_data["filename"])
        else:
            # Create new
            doc = Document(**doc_data)
            db.add(doc)
            created.append(doc_data["filename"])
    
    db.commit()
    
    return {
        "message": "Demo documents seeded successfully",
        "created": created,
        "updated": updated,
        "total": len(default_documents)
    }

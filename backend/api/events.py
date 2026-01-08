"""
Event Ingestion API Routes
CRITICAL - This feeds the ML pipeline
Every document action triggers event ingestion
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import uuid

from ..db import get_db, Event, User, Document, Alert, Explanation, ActionType, AlertPriority, SessionLocal
from ..db.models import DocumentModification
from ..core.security import get_current_active_user, TokenData
from ..ml_engine import ThreatDetectionPipeline, UserEvent, PipelineResult

router = APIRouter(prefix="/events", tags=["Event Ingestion"])

# Global pipeline instance (initialized at startup)
_pipeline: Optional[ThreatDetectionPipeline] = None


def get_pipeline() -> ThreatDetectionPipeline:
    """Get ML pipeline instance"""
    global _pipeline
    if _pipeline is None:
        _pipeline = ThreatDetectionPipeline()
        _pipeline.initialize()
    return _pipeline


class EventIngest(BaseModel):
    """Event ingestion request"""
    document_id: str
    document_name: str
    target_department: str
    action: str = Field(..., description="view, download, upload, modify, delete, share")
    bytes_transferred: int = 0
    source_ip: Optional[str] = None
    device_info: Optional[str] = None
    session_id: Optional[str] = None
    document_content: Optional[str] = None  # For classification/integrity


class EventResponse(BaseModel):
    """Event response with risk assessment"""
    event_id: str
    timestamp: datetime
    
    # Risk assessment
    risk_score: float
    risk_level: str
    severity: str
    requires_alert: bool
    
    # Warning for user (displayed in UI)
    warning_message: Optional[str] = None
    
    # Component scores (for transparency)
    behavior_score: float
    sensitivity_score: float
    integrity_score: float
    
    # Status
    is_cross_department: bool
    is_anomalous: bool


class EventDetail(BaseModel):
    """Detailed event with full analysis"""
    event_id: str
    user_id: str
    username: str
    user_department: str
    
    document_id: str
    document_name: str
    target_department: str
    action: str
    
    timestamp: datetime
    bytes_transferred: int
    
    # Full risk assessment
    risk_score: float
    risk_level: str
    severity: str
    
    behavior_score: float
    sensitivity_score: float
    integrity_score: float
    
    document_sensitivity: str
    is_tampered: bool
    tamper_severity: str
    
    is_cross_department: bool
    is_anomalous: bool
    is_after_hours: bool
    
    risk_factors: List[str]
    primary_risk_factor: str
    
    # Alert info
    alert_id: Optional[str] = None
    alert_summary: Optional[str] = None


@router.post("/ingest", response_model=EventResponse)
async def ingest_event(
    event_data: EventIngest,
    background_tasks: BackgroundTasks,
    current_user: TokenData = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    CRITICAL ENDPOINT - Ingest a document action event
    
    This is the main entry point for all document actions.
    Every view, download, upload, modify triggers this endpoint.
    
    The ML pipeline processes the event and returns:
    - Risk score and level
    - Whether an alert is generated
    - Warning message to display to user
    """
    # Get pipeline
    pipeline = get_pipeline()
    
    # Create UserEvent for ML pipeline
    user_event = UserEvent(
        user_id=current_user.user_id,
        user_department=current_user.department,
        document_id=event_data.document_id,
        document_name=event_data.document_name,
        target_department=event_data.target_department,
        action=event_data.action,
        bytes_transferred=event_data.bytes_transferred,
        source_ip=event_data.source_ip,
        device_info=event_data.device_info,
        session_id=event_data.session_id,
        timestamp=datetime.utcnow()
    )
    
    # Run ML pipeline
    result = pipeline.run(user_event, event_data.document_content)
    
    # Generate event ID
    event_id = f"EVT-{uuid.uuid4().hex[:12].upper()}"
    
    # Store event in database
    db_event = Event(
        event_id=event_id,
        user_id=db.query(User).filter(User.user_id == current_user.user_id).first().id,
        user_department=current_user.department,
        action=ActionType(event_data.action),
        document_id=db.query(Document).filter(
            Document.document_id == event_data.document_id
        ).first().id if db.query(Document).filter(
            Document.document_id == event_data.document_id
        ).first() else 1,
        target_department=event_data.target_department,
        timestamp=user_event.timestamp,
        bytes_transferred=event_data.bytes_transferred,
        source_ip=event_data.source_ip,
        device_info=event_data.device_info,
        session_id=event_data.session_id,
        is_cross_department=result.is_cross_department,
        behavior_score=result.behavior_score,
        risk_score=result.risk_score,
        risk_level=result.risk_level
    )
    
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    
    # Store document modification if this is a modify action with content
    if event_data.action == "modify" and event_data.document_content:
        background_tasks.add_task(
            store_document_modification,
            current_user, event_data, result
        )
    
    # Create alert if needed (in background)
    if result.requires_alert:
        background_tasks.add_task(
            create_alert_from_result,
            db_event.id, result, current_user.user_id
        )
    
    # Store explanation (in background)
    if result.shap_explanation or result.lime_explanation:
        background_tasks.add_task(
            store_explanation,
            db_event.id, result
        )
    
    # Determine warning message for user
    warning_message = None
    if result.is_cross_department:
        warning_message = "⚠️ This action is monitored for security."
    if result.risk_level in ["high", "critical"]:
        warning_message = "⚠️ This action has been flagged for security review."
    
    return EventResponse(
        event_id=event_id,
        timestamp=user_event.timestamp,
        risk_score=result.risk_score,
        risk_level=result.risk_level,
        severity=result.severity,
        requires_alert=result.requires_alert,
        warning_message=warning_message,
        behavior_score=result.behavior_score,
        sensitivity_score=result.sensitivity_score,
        integrity_score=result.integrity_score,
        is_cross_department=result.is_cross_department,
        is_anomalous=result.is_anomalous
    )


@router.get("/all", response_model=List[EventDetail])
async def get_all_events(
    current_user: TokenData = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    limit: int = 100,
    offset: int = 0
):
    """
    Get all events (for analysts/admins)
    Returns all events across all users
    """
    events = db.query(Event).order_by(Event.timestamp.desc()).offset(offset).limit(limit).all()
    
    result = []
    for e in events:
        user = db.query(User).filter(User.id == e.user_id).first()
        if user:
            result.append(event_to_detail(e, user))
    
    return result


@router.get("/history", response_model=List[EventDetail])
async def get_user_events(
    current_user: TokenData = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    limit: int = 50,
    offset: int = 0
):
    """
    Get current user's event history
    """
    user = db.query(User).filter(User.user_id == current_user.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    events = db.query(Event).filter(
        Event.user_id == user.id
    ).order_by(Event.timestamp.desc()).offset(offset).limit(limit).all()
    
    return [event_to_detail(e, user) for e in events]


@router.get("/{event_id}", response_model=EventDetail)
async def get_event_detail(
    event_id: str,
    current_user: TokenData = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed event information
    """
    event = db.query(Event).filter(Event.event_id == event_id).first()
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    user = db.query(User).filter(User.id == event.user_id).first()
    
    return event_to_detail(event, user)


def event_to_detail(event: Event, user: User) -> EventDetail:
    """Convert DB event to EventDetail response"""
    document = event.document
    alert = event.alert
    
    # Safely compute is_anomalous - must be boolean, not None
    behavior_score = event.behavior_score or 0.0
    is_anomalous = behavior_score > 0.5
    
    return EventDetail(
        event_id=event.event_id,
        user_id=user.user_id,
        username=user.username,
        user_department=event.user_department,
        document_id=document.document_id if document else "unknown",
        document_name=document.filename if document else "unknown",
        target_department=event.target_department,
        action=event.action.value,
        timestamp=event.timestamp,
        bytes_transferred=event.bytes_transferred or 0,
        risk_score=event.risk_score or 0.0,
        risk_level=event.risk_level or "low",
        severity="",
        behavior_score=behavior_score,
        sensitivity_score=0.0,
        integrity_score=0.0,
        document_sensitivity=document.sensitivity.value if document else "internal",
        is_tampered=bool(document.is_tampered) if document else False,
        tamper_severity=document.tamper_severity if document else "none",
        is_cross_department=bool(event.is_cross_department),
        is_anomalous=is_anomalous,
        is_after_hours=False,
        risk_factors=[],
        primary_risk_factor="none",
        alert_id=alert.alert_id if alert else None,
        alert_summary=alert.summary if alert else None
    )


async def create_alert_from_result(event_id: int, result: PipelineResult, user_id: str):
    """Background task to create alert - uses own DB session"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.user_id == user_id).first()
        
        # Determine priority
        if result.risk_level == "critical":
            priority = AlertPriority.CRITICAL
        elif result.risk_level == "high":
            priority = AlertPriority.HIGH
        else:
            priority = AlertPriority.MEDIUM
        
        alert = Alert(
            alert_id=f"ALT-{uuid.uuid4().hex[:12].upper()}",
            event_id=event_id,
            user_id=user.id,
            priority=priority,
            risk_score=result.risk_score,
            summary=result.alert_summary or f"Risk alert for user {user_id}",
            details={
                'risk_factors': result.risk_factors,
                'primary_factor': result.primary_risk_factor,
                'components': {
                    'behavior': result.behavior_score,
                    'sensitivity': result.sensitivity_score,
                    'integrity': result.integrity_score
                }
            }
        )
        
        db.add(alert)
        db.commit()
        print(f"Alert created: {alert.alert_id} for event {event_id}")
    except Exception as e:
        print(f"Failed to create alert: {e}")
        db.rollback()
    finally:
        db.close()


async def store_explanation(event_id: int, result: PipelineResult):
    """Background task to store XAI explanation - uses own DB session"""
    db = SessionLocal()
    try:
        explanation = Explanation(
            explanation_id=f"EXP-{uuid.uuid4().hex[:12].upper()}",
            event_id=event_id,
            explanation_type="shap_behavior" if result.shap_explanation else "lime_text",
            shap_values=result.shap_explanation.get('shap_values') if result.shap_explanation else None,
            shap_base_value=result.shap_explanation.get('base_value') if result.shap_explanation else None,
            lime_features=result.lime_explanation.get('top_features') if result.lime_explanation else None,
            risk_components={
                'behavior': result.behavior_score,
                'classification': result.sensitivity_score,
                'integrity': result.integrity_score
            }
        )
        
        db.add(explanation)
        db.commit()
        print(f"Explanation stored: {explanation.explanation_id}")
    except Exception as e:
        print(f"Failed to store explanation: {e}")
        db.rollback()
    finally:
        db.close()


async def store_document_modification(
    current_user: TokenData, 
    event_data: 'EventIngest',
    result: PipelineResult
):
    """Background task to store document modification for integrity tracking - uses own DB session"""
    db = SessionLocal()
    try:
        # Get original document content if available
        document = db.query(Document).filter(
            Document.document_id == event_data.document_id
        ).first()
        
        # Use full_content or original_content from document (not the short preview!)
        original_content = ""
        if document:
            # Prefer original_content (preserved original), then full_content (current state)
            original_content = document.original_content or document.full_content or document.content_preview or ""
        
        modified_content = event_data.document_content or ""
        
        # Calculate diff statistics
        original_length = len(original_content)
        modified_length = len(modified_content)
        
        # Calculate characters added/removed using diff
        from difflib import SequenceMatcher
        matcher = SequenceMatcher(None, original_content, modified_content)
        chars_added = 0
        chars_removed = 0
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'replace':
                chars_removed += i2 - i1
                chars_added += j2 - j1
            elif tag == 'delete':
                chars_removed += i2 - i1
            elif tag == 'insert':
                chars_added += j2 - j1
        
        # Calculate change percentage
        change_percent = 0.0
        if original_length > 0:
            change_percent = (chars_added + chars_removed) / original_length * 100
        
        # Get user info
        user = db.query(User).filter(User.user_id == current_user.user_id).first()
        
        # Get document record
        doc_record = db.query(Document).filter(
            Document.document_id == event_data.document_id
        ).first()
        
        modification = DocumentModification(
            modification_id=f"MOD-{uuid.uuid4().hex[:12].upper()}",
            user_id=user.id if user else 1,
            username=current_user.username,
            user_department=current_user.department,
            document_id=doc_record.id if doc_record else 1,
            document_name=event_data.document_name,
            target_department=event_data.target_department,
            original_content=original_content,  # Store FULL original content
            modified_content=modified_content,  # Store FULL modified content
            original_length=original_length,
            modified_length=modified_length,
            chars_added=chars_added,
            chars_removed=chars_removed,
            change_percent=change_percent,
            is_cross_department=result.is_cross_department,
            risk_score=result.risk_score,
            risk_level=result.risk_level,
            modified_at=datetime.utcnow()
        )
        
        db.add(modification)
        
        # Also update the document's current content and mark as tampered
        if doc_record:
            doc_record.full_content = modified_content
            doc_record.is_tampered = True
            doc_record.tamper_severity = result.risk_level
            # Update hash to indicate content changed
            import hashlib
            doc_record.current_hash = hashlib.sha256(modified_content.encode()).hexdigest()[:16]
            doc_record.updated_at = datetime.utcnow()
        
        db.commit()
        print(f"Stored document modification: {modification.modification_id}")
    except Exception as e:
        print(f"Failed to store document modification: {e}")
        db.rollback()
    finally:
        db.close()

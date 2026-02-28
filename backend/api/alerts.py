"""
Alerts API Routes
Alert management for analysts and admins
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from ..db import get_db, Alert, AlertPriority, User, Event
from ..core.security import get_current_active_user, TokenData, require_analyst, UserRole

router = APIRouter(prefix="/alerts", tags=["Alerts"])


class AlertResponse(BaseModel):
    """Alert response model"""
    alert_id: str
    event_id: str
    user_id: str
    username: str
    user_department: str
    
    priority: str
    severity: str  # Alias for priority for frontend compatibility
    risk_score: float
    summary: str
    description: str  # Alias for summary for frontend compatibility
    details: Optional[dict]
    metadata: Optional[dict]  # Additional metadata including document_content
    explanation: Optional[dict]  # LIME/SHAP explanation data
    
    status: str
    assigned_to: Optional[str]
    resolution_notes: Optional[str]
    
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime]

    class Config:
        from_attributes = True


class AlertListResponse(BaseModel):
    """Alert list with pagination and stats"""
    alerts: List[AlertResponse]
    total: int
    page: int
    page_size: int
    stats: dict


class AlertUpdate(BaseModel):
    """Alert update request"""
    status: Optional[str] = None  # open, investigating, resolved, dismissed
    assigned_to: Optional[str] = None
    resolution_notes: Optional[str] = None


@router.get("/", response_model=AlertListResponse)
async def list_alerts(
    priority: Optional[str] = Query(None, description="Filter by priority"),
    status: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: TokenData = Depends(require_analyst()),
    db: Session = Depends(get_db)
):
    """
    List all alerts (ANALYST/ADMIN only)
    """
    query = db.query(Alert)
    
    # Apply filters
    if priority:
        query = query.filter(Alert.priority == AlertPriority(priority))
    
    if status:
        query = query.filter(Alert.status == status)
    
    # Get total count
    total = query.count()
    
    # Calculate stats
    stats = {
        "total": db.query(Alert).count(),
        "open": db.query(Alert).filter(Alert.status == "open").count(),
        "investigating": db.query(Alert).filter(Alert.status == "investigating").count(),
        "resolved": db.query(Alert).filter(Alert.status == "resolved").count(),
        "by_priority": {
            "critical": db.query(Alert).filter(Alert.priority == AlertPriority.CRITICAL).count(),
            "high": db.query(Alert).filter(Alert.priority == AlertPriority.HIGH).count(),
            "medium": db.query(Alert).filter(Alert.priority == AlertPriority.MEDIUM).count(),
            "low": db.query(Alert).filter(Alert.priority == AlertPriority.LOW).count()
        }
    }
    
    # Paginate
    offset = (page - 1) * page_size
    alerts = query.order_by(
        Alert.created_at.desc()  # Most recent first (all priorities mixed by time)
    ).offset(offset).limit(page_size).all()
    
    # Convert alerts to response, catching any errors
    alert_responses = []
    for a in alerts:
        try:
            alert_responses.append(alert_to_response(a, db))
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error converting alert {a.alert_id}: {e}", exc_info=True)
            # Skip this alert and continue
            continue
    
    return AlertListResponse(
        alerts=alert_responses,
        total=total,
        page=page,
        page_size=page_size,
        stats=stats
    )


@router.get("/recent", response_model=List[AlertResponse])
async def get_recent_alerts(
    limit: int = Query(10, ge=1, le=50),
    current_user: TokenData = Depends(require_analyst()),
    db: Session = Depends(get_db)
):
    """
    Get most recent alerts (ANALYST/ADMIN only)
    """
    alerts = db.query(Alert).order_by(
        Alert.created_at.desc()
    ).limit(limit).all()
    
    return [alert_to_response(a, db) for a in alerts]


@router.get("/critical", response_model=List[AlertResponse])
async def get_critical_alerts(
    current_user: TokenData = Depends(require_analyst()),
    db: Session = Depends(get_db)
):
    """
    Get all critical alerts that are not resolved
    """
    alerts = db.query(Alert).filter(
        Alert.priority == AlertPriority.CRITICAL,
        Alert.status.in_(["open", "investigating"])
    ).order_by(Alert.created_at.desc()).all()
    
    return [alert_to_response(a, db) for a in alerts]


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: str,
    current_user: TokenData = Depends(require_analyst()),
    db: Session = Depends(get_db)
):
    """
    Get alert details (ANALYST/ADMIN only)
    """
    alert = db.query(Alert).filter(Alert.alert_id == alert_id).first()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    return alert_to_response(alert, db)


@router.put("/{alert_id}", response_model=AlertResponse)
async def update_alert(
    alert_id: str,
    update: AlertUpdate,
    current_user: TokenData = Depends(require_analyst()),
    db: Session = Depends(get_db)
):
    """
    Update alert status (ANALYST/ADMIN only)
    """
    alert = db.query(Alert).filter(Alert.alert_id == alert_id).first()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    # Update fields
    if update.status:
        if update.status not in ["open", "investigating", "resolved", "dismissed"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid status"
            )
        alert.status = update.status
        
        if update.status in ["resolved", "dismissed"]:
            alert.resolved_at = datetime.utcnow()
    
    if update.assigned_to is not None:
        alert.assigned_to = update.assigned_to
    
    if update.resolution_notes is not None:
        alert.resolution_notes = update.resolution_notes
    
    alert.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(alert)
    
    return alert_to_response(alert, db)


@router.post("/{alert_id}/assign")
async def assign_alert(
    alert_id: str,
    assignee: str,
    current_user: TokenData = Depends(require_analyst()),
    db: Session = Depends(get_db)
):
    """
    Assign alert to an analyst
    """
    alert = db.query(Alert).filter(Alert.alert_id == alert_id).first()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    alert.assigned_to = assignee
    alert.status = "investigating"
    alert.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": f"Alert {alert_id} assigned to {assignee}"}


@router.post("/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str,
    notes: Optional[str] = None,
    current_user: TokenData = Depends(require_analyst()),
    db: Session = Depends(get_db)
):
    """
    Resolve an alert
    """
    alert = db.query(Alert).filter(Alert.alert_id == alert_id).first()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    alert.status = "resolved"
    alert.resolved_at = datetime.utcnow()
    alert.updated_at = datetime.utcnow()
    
    if notes:
        alert.resolution_notes = notes
    
    db.commit()
    
    return {"message": f"Alert {alert_id} resolved"}


@router.get("/user/{user_id}", response_model=List[AlertResponse])
async def get_user_alerts(
    user_id: str,
    current_user: TokenData = Depends(require_analyst()),
    db: Session = Depends(get_db)
):
    """
    Get all alerts for a specific user
    """
    user = db.query(User).filter(User.user_id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    alerts = db.query(Alert).filter(Alert.user_id == user.id).order_by(
        Alert.created_at.desc()
    ).all()
    
    return [alert_to_response(a, db) for a in alerts]


def alert_to_response(alert: Alert, db: Session) -> AlertResponse:
    """Convert DB alert to response model"""
    from ..db.models import Explanation, Document
    
    user = db.query(User).filter(User.id == alert.user_id).first()
    event = db.query(Event).filter(Event.id == alert.event_id).first()
    
    # Try to get explanation for this event
    explanation_data = None
    document_content = None
    if event:
        explanation = db.query(Explanation).filter(Explanation.event_id == event.id).first()
        if explanation:
            # Build highlights from LIME features
            highlights = []
            if explanation.lime_features:
                try:
                    # Handle both dict and list formats
                    if isinstance(explanation.lime_features, dict):
                        for word, weight in explanation.lime_features.items():
                            highlights.append({
                                "word": word,
                                "weight": weight,
                                "start": 0,
                                "end": len(word)
                            })
                    elif isinstance(explanation.lime_features, list):
                        for item in explanation.lime_features:
                            if isinstance(item, dict):
                                highlights.append({
                                    "word": item.get("word", ""),
                                    "weight": item.get("weight", 0),
                                    "start": item.get("start", 0),
                                    "end": item.get("end", 0)
                                })
                            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                                highlights.append({
                                    "word": str(item[0]),
                                    "weight": float(item[1]) if len(item) > 1 else 0,
                                    "start": 0,
                                    "end": len(str(item[0]))
                                })
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error processing LIME features for event {event.id}: {e}")
                    logger.error(f"LIME features type: {type(explanation.lime_features)}")
                    logger.error(f"LIME features content: {explanation.lime_features}")
                    highlights = []
                    
            explanation_data = {
                "type": explanation.explanation_type,
                "highlights": highlights,
                "risk_components": explanation.risk_components or {},
                "shap_values": explanation.shap_values or {}
            }
        
        # Get document content
        if event.document_id:
            document = db.query(Document).filter(Document.id == event.document_id).first()
            if document:
                document_content = document.full_content or document.content_preview
    
    # Build metadata
    metadata = {}
    if alert.details:
        if isinstance(alert.details, dict):
            metadata = alert.details.copy()
        elif isinstance(alert.details, list):
            metadata = {"items": alert.details}
    if document_content:
        metadata["document_content"] = document_content[:1000]  # Limit size
    
    return AlertResponse(
        alert_id=alert.alert_id,
        event_id=event.event_id if event else "unknown",
        user_id=user.user_id if user else "unknown",
        username=user.username if user else "unknown",
        user_department=user.department if user else "unknown",
        priority=alert.priority.value,
        severity=alert.priority.value.upper(),  # Frontend expects uppercase
        risk_score=alert.risk_score,
        summary=alert.summary,
        description=alert.summary,  # Alias
        details=alert.details if isinstance(alert.details, dict) else {"items": alert.details} if alert.details else {},
        metadata=metadata,
        explanation=explanation_data,
        status=alert.status,
        assigned_to=alert.assigned_to,
        resolution_notes=alert.resolution_notes,
        created_at=alert.created_at,
        updated_at=alert.updated_at,
        resolved_at=alert.resolved_at
    )

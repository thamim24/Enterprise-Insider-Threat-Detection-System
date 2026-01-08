"""
ML Pipeline Status API
Provides real-time statistics from the ML pipeline
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta

from ..db import get_db, User, Document, Event, Alert
from ..db.models import DocumentModification, AlertPriority

router = APIRouter(prefix="/ml", tags=["ML Pipeline"])


@router.get("/status")
async def get_pipeline_status(db: Session = Depends(get_db)):
    """
    Get real-time ML pipeline status and statistics
    This endpoint provides REAL data from the database
    """
    # Get real counts from database
    total_users = db.query(User).filter(User.is_active == True).count()
    total_documents = db.query(Document).count()
    total_events = db.query(Event).count()
    total_alerts = db.query(Alert).count()
    
    # Get today's statistics
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    events_today = db.query(Event).filter(Event.timestamp >= today_start).count()
    alerts_today = db.query(Alert).filter(Alert.created_at >= today_start).count()
    
    # Get anomalies (events with high risk scores)
    anomalies_today = db.query(Event).filter(
        Event.timestamp >= today_start,
        Event.risk_score >= 0.6
    ).count()
    
    # Get critical alerts
    critical_alerts = db.query(Alert).filter(
        Alert.priority == "CRITICAL",
        Alert.status != "RESOLVED"
    ).count()
    
    # Get recent event statistics
    last_24h = datetime.utcnow() - timedelta(hours=24)
    events_24h = db.query(Event).filter(Event.timestamp >= last_24h).count()
    
    # Calculate average risk score for today's events
    avg_risk = db.query(func.avg(Event.risk_score)).filter(
        Event.timestamp >= today_start
    ).scalar() or 0.0
    
    # Get documents by department
    docs_by_dept = {}
    dept_query = db.query(
        Document.department, 
        func.count(Document.id)
    ).group_by(Document.department).all()
    for dept, count in dept_query:
        docs_by_dept[dept] = count
    
    # Get tampered documents count
    tampered_docs = db.query(Document).filter(Document.is_tampered == True).count()
    
    return {
        "pipeline_active": True,
        "last_updated": datetime.utcnow().isoformat(),
        
        # Real statistics
        "users_monitored": total_users,
        "documents_processed": total_documents,
        "total_events": total_events,
        "total_alerts": total_alerts,
        
        # Today's stats
        "events_today": events_today,
        "alerts_today": alerts_today,
        "anomalies_today": anomalies_today,
        "critical_alerts": critical_alerts,
        
        # 24-hour stats
        "events_24h": events_24h,
        "avg_risk_score_today": round(float(avg_risk), 3),
        
        # Document integrity
        "documents_by_department": docs_by_dept,
        "tampered_documents": tampered_docs,
        "healthy_documents": total_documents - tampered_docs,
        
        # Pipeline health
        "ml_model_loaded": True,
        "behavior_model_status": "active",
        "sensitivity_model_status": "active",
        "integrity_model_status": "active"
    }


@router.get("/anomaly-timeline")
async def get_anomaly_timeline(
    hours: int = 24,
    db: Session = Depends(get_db)
):
    """
    Get anomaly score timeline for visualization
    Returns real aggregated data
    """
    now = datetime.utcnow()
    timeline = []
    
    # Get hourly aggregates
    for i in range(hours, 0, -1):
        hour_start = now - timedelta(hours=i)
        hour_end = now - timedelta(hours=i-1)
        
        # Get events in this hour
        events = db.query(Event).filter(
            Event.timestamp >= hour_start,
            Event.timestamp < hour_end
        ).all()
        
        if events:
            avg_score = sum(e.risk_score for e in events) / len(events)
            max_score = max(e.risk_score for e in events)
            event_count = len(events)
        else:
            avg_score = 0
            max_score = 0
            event_count = 0
        
        timeline.append({
            "time": hour_start.strftime("%H:%M"),
            "hour": hour_start.hour,
            "avg_score": round(avg_score, 3),
            "max_score": round(max_score, 3),
            "event_count": event_count
        })
    
    return {
        "timeline": timeline,
        "period_hours": hours,
        "generated_at": now.isoformat()
    }


@router.get("/top-risk-users")
async def get_top_risk_users(
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    Get users with highest risk scores based on recent activity
    Returns real data from events
    """
    # Get users with their event statistics
    last_24h = datetime.utcnow() - timedelta(hours=24)
    
    # Get all users
    users = db.query(User).filter(User.is_active == True).all()
    
    user_risks = []
    for user in users:
        # Get user's events in last 24h
        user_events = db.query(Event).filter(
            Event.user_id == user.id,
            Event.timestamp >= last_24h
        ).all()
        
        if user_events:
            avg_risk = sum(e.risk_score for e in user_events) / len(user_events)
            max_risk = max(e.risk_score for e in user_events)
            anomaly_count = sum(1 for e in user_events if e.risk_score >= 0.6)
            event_count = len(user_events)
        else:
            avg_risk = 0
            max_risk = 0
            anomaly_count = 0
            event_count = 0
        
        user_risks.append({
            "user_id": user.id,
            "username": user.username,
            "department": user.department,
            "risk_score": round(max_risk, 3),  # Use max for ranking
            "avg_risk_score": round(avg_risk, 3),
            "anomaly_count": anomaly_count,
            "event_count": event_count
        })
    
    # Sort by risk score descending
    user_risks.sort(key=lambda x: x["risk_score"], reverse=True)
    
    return {
        "users": user_risks[:limit],
        "total_users": len(users),
        "period": "24h"
    }


@router.get("/document-modifications")
async def get_document_modifications(
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    Get recent document modifications with diff information
    Shows what changes were made to documents - returns FULL content for proper diff display
    """
    modifications = db.query(DocumentModification).order_by(
        DocumentModification.modified_at.desc()
    ).limit(limit).all()
    
    return {
        "modifications": [
            {
                "modification_id": mod.modification_id,
                "username": mod.username,
                "user_department": mod.user_department,
                "document_name": mod.document_name,
                "target_department": mod.target_department,
                "original_content": mod.original_content or "",  # Return FULL content
                "modified_content": mod.modified_content or "",  # Return FULL content
                "original_length": mod.original_length,
                "modified_length": mod.modified_length,
                "chars_added": mod.chars_added,
                "chars_removed": mod.chars_removed,
                "change_percent": round(mod.change_percent, 1),
                "is_cross_department": mod.is_cross_department,
                "risk_score": round(mod.risk_score, 3) if mod.risk_score else 0,
                "risk_level": mod.risk_level or "low",
                "modified_at": mod.modified_at.isoformat() if mod.modified_at else None
            }
            for mod in modifications
        ],
        "total": len(modifications)
    }


@router.get("/feature-importance")
async def get_feature_importance(
    db: Session = Depends(get_db)
):
    """
    Get REAL feature importance based on actual event data
    Calculates importance by analyzing which factors correlate with high-risk events
    """
    # Get all events with their risk scores
    events = db.query(Event).all()
    
    if not events:
        return {
            "features": [],
            "total_events": 0,
            "message": "No events to analyze yet"
        }
    
    # Calculate feature importance based on actual events
    total_events = len(events)
    
    # Count high-risk events for each factor
    cross_dept_high_risk = sum(1 for e in events if e.is_cross_department and e.risk_score >= 0.6)
    cross_dept_total = sum(1 for e in events if e.is_cross_department)
    
    # Action type analysis
    action_risk = {}
    for action in ['download', 'modify', 'delete', 'view', 'upload', 'share']:
        action_events = [e for e in events if e.action.value == action]
        if action_events:
            avg_risk = sum(e.risk_score for e in action_events) / len(action_events)
            action_risk[action] = avg_risk
    
    # After-hours analysis (simplified based on timestamp)
    after_hours_events = [e for e in events if e.timestamp.hour < 8 or e.timestamp.hour > 18]
    after_hours_risk = sum(e.risk_score for e in after_hours_events) / len(after_hours_events) if after_hours_events else 0
    
    # Build feature importance list (normalized to sum to 1)
    raw_features = []
    
    # Cross-department access importance
    if cross_dept_total > 0:
        cross_dept_importance = (cross_dept_high_risk / cross_dept_total) if cross_dept_total > 0 else 0
        raw_features.append({
            "name": "Cross-department access",
            "importance": cross_dept_importance,
            "count": cross_dept_total,
            "high_risk_count": cross_dept_high_risk
        })
    
    # Action-based importance
    for action, risk in sorted(action_risk.items(), key=lambda x: x[1], reverse=True)[:3]:
        raw_features.append({
            "name": f"{action.capitalize()} actions",
            "importance": risk,
            "count": len([e for e in events if e.action.value == action])
        })
    
    # After-hours importance
    if after_hours_events:
        raw_features.append({
            "name": "After-hours activity",
            "importance": after_hours_risk,
            "count": len(after_hours_events)
        })
    
    # Normalize importances to sum to 1
    total_importance = sum(f["importance"] for f in raw_features) or 1
    for f in raw_features:
        f["importance"] = round(f["importance"] / total_importance, 3)
    
    # Sort by importance
    raw_features.sort(key=lambda x: x["importance"], reverse=True)
    
    return {
        "features": raw_features[:10],
        "total_events": total_events,
        "high_risk_events": sum(1 for e in events if e.risk_score >= 0.6),
        "generated_at": datetime.utcnow().isoformat()
    }


@router.get("/explanations")
async def get_recent_explanations(
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    Get recent XAI explanations (SHAP/LIME) from events
    Returns real explanation data stored in the database
    """
    from ..db.models import Explanation
    
    explanations = db.query(Explanation).order_by(
        Explanation.created_at.desc()
    ).limit(limit).all()
    
    return {
        "explanations": [
            {
                "explanation_id": exp.explanation_id,
                "event_id": exp.event_id,
                "document_id": exp.document_id,
                "explanation_type": exp.explanation_type,
                "shap_values": exp.shap_values,
                "shap_base_value": exp.shap_base_value,
                "lime_features": exp.lime_features,
                "risk_components": exp.risk_components,
                "created_at": exp.created_at.isoformat() if exp.created_at else None
            }
            for exp in explanations
        ],
        "total": len(explanations)
    }


@router.get("/alerts-by-day")
async def get_alerts_by_day(
    days: int = 7,
    db: Session = Depends(get_db)
):
    """
    Get alerts count by day for the last N days
    Returns REAL data for the alerts trend chart
    """
    now = datetime.utcnow()
    day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    
    alerts_by_day = []
    
    for i in range(days - 1, -1, -1):
        day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        
        # Count alerts for this day
        alert_count = db.query(Alert).filter(
            Alert.created_at >= day_start,
            Alert.created_at < day_end
        ).count()
        
        # Count events for this day  
        event_count = db.query(Event).filter(
            Event.timestamp >= day_start,
            Event.timestamp < day_end
        ).count()
        
        # Count high-risk events
        high_risk_count = db.query(Event).filter(
            Event.timestamp >= day_start,
            Event.timestamp < day_end,
            Event.risk_score >= 0.6
        ).count()
        
        alerts_by_day.append({
            "day": day_names[day_start.weekday()],
            "date": day_start.strftime("%Y-%m-%d"),
            "alerts": alert_count,
            "events": event_count,
            "high_risk": high_risk_count
        })
    
    return {
        "data": alerts_by_day,
        "period_days": days,
        "generated_at": now.isoformat()
    }


@router.get("/report-summary")
async def get_report_summary(
    db: Session = Depends(get_db)
):
    """
    Get summary data for reports page
    Returns REAL aggregated statistics
    """
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)
    week_start = today_start - timedelta(days=7)
    
    # Today's counts
    events_today = db.query(Event).filter(Event.timestamp >= today_start).count()
    alerts_today = db.query(Alert).filter(Alert.created_at >= today_start).count()
    
    # Weekly counts
    events_weekly = db.query(Event).filter(Event.timestamp >= week_start).count()
    alerts_weekly = db.query(Alert).filter(Alert.created_at >= week_start).count()
    
    # Get unique users with events this week
    users_with_events = db.query(Event.user_id).filter(
        Event.timestamp >= week_start
    ).distinct().count()
    
    # High risk events this week
    high_risk_weekly = db.query(Event).filter(
        Event.timestamp >= week_start,
        Event.risk_score >= 0.6
    ).count()
    
    # Average risk score
    avg_risk = db.query(func.avg(Event.risk_score)).filter(
        Event.timestamp >= week_start
    ).scalar() or 0.0
    
    # Critical alerts count
    critical_alerts = db.query(Alert).filter(
        Alert.created_at >= week_start,
        Alert.priority == AlertPriority.CRITICAL
    ).count()
    
    # Top risk events (join with user to get username)
    top_events = db.query(Event).filter(
        Event.timestamp >= week_start
    ).order_by(Event.risk_score.desc()).limit(10).all()
    
    return {
        "period": "weekly",
        "generated_at": now.isoformat(),
        "total_events": events_weekly,
        "alerts_generated": alerts_weekly,
        "users_analyzed": users_with_events,
        "high_risk_count": high_risk_weekly,
        "avg_risk_score": round(float(avg_risk), 3),
        "critical_count": critical_alerts,
        "top_events": [
            {
                "action": e.action.value if e.action else "unknown",
                "user": e.user.username if e.user else "unknown",
                "department": e.user_department,
                "risk_score": round(e.risk_score, 3) if e.risk_score else 0,
                "severity": e.risk_level or "low",
                "timestamp": e.timestamp.isoformat() if e.timestamp else None
            }
            for e in top_events
        ]
    }

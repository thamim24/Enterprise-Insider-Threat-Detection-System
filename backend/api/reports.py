"""
Reports API Routes
Report generation and retrieval with XAI appendix
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
import uuid
import json

from ..db import get_db, Report, Alert, Event, User
from ..core.security import get_current_active_user, TokenData, require_analyst

router = APIRouter(prefix="/reports", tags=["Reports"])


class ReportRequest(BaseModel):
    """Report generation request"""
    title: str
    report_type: str = "custom"  # daily, weekly, incident, custom
    start_date: datetime
    end_date: datetime
    include_alerts: bool = True
    include_explanations: bool = True
    description: Optional[str] = None


class ReportResponse(BaseModel):
    """Report response model"""
    report_id: str
    title: str
    report_type: str
    description: Optional[str]
    
    start_date: datetime
    end_date: datetime
    
    summary_stats: dict
    alerts_included: List[str]
    risk_trends: Optional[dict]
    top_risks: Optional[dict]
    recommendations: Optional[List[str]]
    
    pdf_path: Optional[str]
    json_path: Optional[str]
    
    generated_by: str
    generated_at: datetime

    class Config:
        from_attributes = True


class ReportListResponse(BaseModel):
    """Report list response"""
    reports: List[ReportResponse]
    total: int


@router.post("/generate", response_model=ReportResponse)
async def generate_report(
    request: ReportRequest,
    background_tasks: BackgroundTasks,
    current_user: TokenData = Depends(require_analyst()),
    db: Session = Depends(get_db)
):
    """
    Generate a new report (ANALYST/ADMIN only)
    """
    report_id = f"RPT-{uuid.uuid4().hex[:12].upper()}"
    
    # Calculate statistics for date range
    alerts = db.query(Alert).filter(
        Alert.created_at >= request.start_date,
        Alert.created_at <= request.end_date
    ).all()
    
    events = db.query(Event).filter(
        Event.timestamp >= request.start_date,
        Event.timestamp <= request.end_date
    ).all()
    
    # Summary statistics
    summary_stats = {
        "total_events": len(events),
        "total_alerts": len(alerts),
        "alerts_by_priority": {
            "critical": len([a for a in alerts if a.priority.value == "critical"]),
            "high": len([a for a in alerts if a.priority.value == "high"]),
            "medium": len([a for a in alerts if a.priority.value == "medium"]),
            "low": len([a for a in alerts if a.priority.value == "low"])
        },
        "alerts_by_status": {
            "open": len([a for a in alerts if a.status == "open"]),
            "investigating": len([a for a in alerts if a.status == "investigating"]),
            "resolved": len([a for a in alerts if a.status == "resolved"]),
            "dismissed": len([a for a in alerts if a.status == "dismissed"])
        },
        "avg_risk_score": sum(e.risk_score or 0 for e in events) / max(len(events), 1),
        "unique_users_flagged": len(set(a.user_id for a in alerts)),
        "cross_department_events": len([e for e in events if e.is_cross_department])
    }
    
    # Top risks
    users_by_alerts = {}
    for alert in alerts:
        user = db.query(User).filter(User.id == alert.user_id).first()
        if user:
            users_by_alerts[user.username] = users_by_alerts.get(user.username, 0) + 1
    
    top_risks = {
        "top_users": sorted(users_by_alerts.items(), key=lambda x: x[1], reverse=True)[:5],
        "highest_risk_events": [
            {
                "event_id": e.event_id,
                "risk_score": e.risk_score,
                "user_department": e.user_department,
                "target_department": e.target_department
            }
            for e in sorted(events, key=lambda x: x.risk_score or 0, reverse=True)[:5]
        ]
    }
    
    # Generate recommendations
    recommendations = []
    if summary_stats["alerts_by_priority"]["critical"] > 0:
        recommendations.append("Immediate review required for critical alerts")
    if summary_stats["cross_department_events"] > len(events) * 0.2:
        recommendations.append("High cross-department activity detected - review access policies")
    if summary_stats["alerts_by_status"]["open"] > 10:
        recommendations.append("Backlog of open alerts - consider additional analyst resources")
    if summary_stats["avg_risk_score"] > 0.5:
        recommendations.append("Elevated average risk score - enhanced monitoring recommended")
    
    # Create report record
    report = Report(
        report_id=report_id,
        title=request.title,
        report_type=request.report_type,
        description=request.description,
        start_date=request.start_date,
        end_date=request.end_date,
        summary_stats=summary_stats,
        alerts_included=[a.alert_id for a in alerts],
        risk_trends=None,  # Could add historical comparison
        top_risks=top_risks,
        recommendations=recommendations,
        generated_by=current_user.username
    )
    
    db.add(report)
    db.commit()
    db.refresh(report)
    
    # Generate PDF in background (placeholder)
    background_tasks.add_task(generate_pdf_report, report_id, db)
    
    return ReportResponse(
        report_id=report.report_id,
        title=report.title,
        report_type=report.report_type,
        description=report.description,
        start_date=report.start_date,
        end_date=report.end_date,
        summary_stats=report.summary_stats,
        alerts_included=report.alerts_included,
        risk_trends=report.risk_trends,
        top_risks=report.top_risks,
        recommendations=report.recommendations,
        pdf_path=report.pdf_path,
        json_path=report.json_path,
        generated_by=report.generated_by,
        generated_at=report.generated_at
    )


@router.get("/", response_model=ReportListResponse)
async def list_reports(
    report_type: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: TokenData = Depends(require_analyst()),
    db: Session = Depends(get_db)
):
    """
    List all reports (ANALYST/ADMIN only)
    """
    query = db.query(Report)
    
    if report_type:
        query = query.filter(Report.report_type == report_type)
    
    total = query.count()
    
    offset = (page - 1) * page_size
    reports = query.order_by(Report.generated_at.desc()).offset(offset).limit(page_size).all()
    
    return ReportListResponse(
        reports=[ReportResponse(
            report_id=r.report_id,
            title=r.title,
            report_type=r.report_type,
            description=r.description,
            start_date=r.start_date,
            end_date=r.end_date,
            summary_stats=r.summary_stats,
            alerts_included=r.alerts_included or [],
            risk_trends=r.risk_trends,
            top_risks=r.top_risks,
            recommendations=r.recommendations,
            pdf_path=r.pdf_path,
            json_path=r.json_path,
            generated_by=r.generated_by,
            generated_at=r.generated_at
        ) for r in reports],
        total=total
    )


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: str,
    current_user: TokenData = Depends(require_analyst()),
    db: Session = Depends(get_db)
):
    """
    Get report details (ANALYST/ADMIN only)
    """
    report = db.query(Report).filter(Report.report_id == report_id).first()
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )
    
    return ReportResponse(
        report_id=report.report_id,
        title=report.title,
        report_type=report.report_type,
        description=report.description,
        start_date=report.start_date,
        end_date=report.end_date,
        summary_stats=report.summary_stats,
        alerts_included=report.alerts_included or [],
        risk_trends=report.risk_trends,
        top_risks=report.top_risks,
        recommendations=report.recommendations,
        pdf_path=report.pdf_path,
        json_path=report.json_path,
        generated_by=report.generated_by,
        generated_at=report.generated_at
    )


@router.post("/daily")
async def generate_daily_report(
    background_tasks: BackgroundTasks,
    current_user: TokenData = Depends(require_analyst()),
    db: Session = Depends(get_db)
):
    """
    Generate daily report for yesterday
    """
    yesterday = datetime.utcnow() - timedelta(days=1)
    start_date = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    request = ReportRequest(
        title=f"Daily Security Report - {yesterday.strftime('%Y-%m-%d')}",
        report_type="daily",
        start_date=start_date,
        end_date=end_date,
        description="Automated daily security analysis report"
    )
    
    return await generate_report(request, background_tasks, current_user, db)


@router.post("/weekly")
async def generate_weekly_report(
    background_tasks: BackgroundTasks,
    current_user: TokenData = Depends(require_analyst()),
    db: Session = Depends(get_db)
):
    """
    Generate weekly report for last 7 days
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=7)
    
    request = ReportRequest(
        title=f"Weekly Security Report - {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
        report_type="weekly",
        start_date=start_date,
        end_date=end_date,
        description="Automated weekly security analysis report"
    )
    
    return await generate_report(request, background_tasks, current_user, db)


async def generate_pdf_report(report_id: str, db: Session):
    """Background task to generate PDF report"""
    # Placeholder for PDF generation
    # In production, use reportlab, weasyprint, or similar
    try:
        report = db.query(Report).filter(Report.report_id == report_id).first()
        if report:
            # Generate PDF path
            report.pdf_path = f"reports/{report_id}.pdf"
            report.json_path = f"reports/{report_id}.json"
            db.commit()
    except Exception as e:
        print(f"Failed to generate PDF: {e}")

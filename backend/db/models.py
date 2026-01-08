"""
SQLAlchemy ORM Models for Enterprise Insider Threat Detection
Tables: users, documents, events, alerts, explanations, reports
"""
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, 
    ForeignKey, JSON, Enum as SQLEnum, Index
)
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from .database import Base


class UserRole(enum.Enum):
    """User role enumeration"""
    USER = "USER"
    ANALYST = "ANALYST"
    ADMIN = "ADMIN"


class AlertPriority(enum.Enum):
    """Alert priority levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ActionType(enum.Enum):
    """Document action types"""
    VIEW = "view"
    DOWNLOAD = "download"
    UPLOAD = "upload"
    MODIFY = "modify"
    DELETE = "delete"
    SHARE = "share"


class SensitivityLevel(enum.Enum):
    """Document sensitivity levels"""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"


class User(Base):
    """User model - employees who access documents"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(50), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    department = Column(String(100), index=True, nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.USER, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    events = relationship("Event", back_populates="user")
    alerts = relationship("Alert", back_populates="user")
    
    # Behavioral metrics (updated periodically)
    risk_score = Column(Float, default=0.0)
    anomaly_count = Column(Integer, default=0)
    last_activity = Column(DateTime)
    
    def __repr__(self):
        return f"<User {self.username} ({self.department})>"


class Document(Base):
    """Document model - files being accessed and monitored"""
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(String(50), unique=True, index=True, nullable=False)
    filename = Column(String(255), nullable=False)
    filepath = Column(String(500), nullable=False)
    department = Column(String(100), index=True, nullable=False)
    
    # User-declared sensitivity
    sensitivity = Column(SQLEnum(SensitivityLevel), default=SensitivityLevel.INTERNAL)
    
    # ML-predicted sensitivity (hybrid approach)
    ml_predicted_sensitivity = Column(String(50), default="internal")
    ml_confidence = Column(Float, default=0.0)
    sensitivity_mismatch = Column(Boolean, default=False)  # True if user != ML
    classification_confidence = Column(Float, default=0.0)
    
    # Integrity tracking
    original_hash = Column(String(64), nullable=False)
    current_hash = Column(String(64), nullable=False)
    is_tampered = Column(Boolean, default=False)
    tamper_severity = Column(String(50), default="none")
    
    # Metadata
    content_preview = Column(Text)  # First 500 chars for preview
    full_content = Column(Text)  # Full document content for modification tracking
    original_content = Column(Text)  # Original content before any modifications
    file_size_bytes = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    events = relationship("Event", back_populates="document")
    explanations = relationship("Explanation", back_populates="document")
    
    def __repr__(self):
        return f"<Document {self.filename} ({self.sensitivity.value})>"


class Event(Base):
    """Event model - immutable log of all document actions"""
    __tablename__ = "events"
    
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String(50), unique=True, index=True, nullable=False)
    
    # Who
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    user_department = Column(String(100), nullable=False)
    
    # What
    action = Column(SQLEnum(ActionType), nullable=False)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    target_department = Column(String(100), nullable=False)
    
    # When
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Details
    bytes_transferred = Column(Integer, default=0)
    source_ip = Column(String(50))
    device_info = Column(String(255))
    session_id = Column(String(100))
    
    # Computed risk at event time
    is_cross_department = Column(Boolean, default=False)
    behavior_score = Column(Float)  # Raw anomaly score
    risk_score = Column(Float)      # Fused risk score
    risk_level = Column(String(20)) # critical/high/medium/low
    
    # Relationships
    user = relationship("User", back_populates="events")
    document = relationship("Document", back_populates="events")
    alert = relationship("Alert", back_populates="event", uselist=False)
    explanation = relationship("Explanation", back_populates="event", uselist=False)
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_events_user_time', 'user_id', 'timestamp'),
        Index('idx_events_risk', 'risk_score'),
    )
    
    def __repr__(self):
        return f"<Event {self.event_id}: {self.action.value} by user {self.user_id}>"


class Alert(Base):
    """Alert model - generated for high-risk events"""
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(String(50), unique=True, index=True, nullable=False)
    
    # Link to triggering event
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Alert details
    priority = Column(SQLEnum(AlertPriority), nullable=False, index=True)
    risk_score = Column(Float, nullable=False)
    summary = Column(Text, nullable=False)
    details = Column(JSON)  # Structured details
    
    # Status tracking
    status = Column(String(50), default="open", index=True)  # open, investigating, resolved, dismissed
    assigned_to = Column(String(100))  # Analyst username
    resolution_notes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = Column(DateTime)
    
    # Relationships
    event = relationship("Event", back_populates="alert")
    user = relationship("User", back_populates="alerts")
    
    def __repr__(self):
        return f"<Alert {self.alert_id} ({self.priority.value})>"


class Explanation(Base):
    """Explanation model - XAI outputs (SHAP/LIME) for events"""
    __tablename__ = "explanations"
    
    id = Column(Integer, primary_key=True, index=True)
    explanation_id = Column(String(50), unique=True, index=True, nullable=False)
    
    # Links
    event_id = Column(Integer, ForeignKey("events.id"), index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), index=True)
    
    # Explanation type
    explanation_type = Column(String(50), nullable=False)  # shap_behavior, lime_text, etc.
    
    # SHAP data
    shap_values = Column(JSON)  # Feature -> SHAP value mapping
    shap_base_value = Column(Float)
    
    # LIME data  
    lime_features = Column(JSON)  # Word -> weight mapping
    lime_html = Column(Text)  # Pre-rendered HTML
    
    # Risk components breakdown
    risk_components = Column(JSON)  # behavior, classification, integrity scores
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    event = relationship("Event", back_populates="explanation")
    document = relationship("Document", back_populates="explanations")
    
    def __repr__(self):
        return f"<Explanation {self.explanation_id} ({self.explanation_type})>"


class Report(Base):
    """Report model - generated PDF/JSON reports with XAI appendix"""
    __tablename__ = "reports"
    
    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(String(50), unique=True, index=True, nullable=False)
    
    # Report metadata
    title = Column(String(255), nullable=False)
    report_type = Column(String(50), nullable=False)  # daily, weekly, incident, custom
    description = Column(Text)
    
    # Time range covered
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    
    # Content
    summary_stats = Column(JSON)  # High-level statistics
    alerts_included = Column(JSON)  # List of alert IDs
    risk_trends = Column(JSON)  # Risk score trends
    top_risks = Column(JSON)  # Top risk entities
    recommendations = Column(JSON)  # Generated recommendations
    
    # File storage
    pdf_path = Column(String(500))
    json_path = Column(String(500))
    
    # Generation info
    generated_by = Column(String(100), nullable=False)
    generated_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Report {self.report_id}: {self.title}>"


class DocumentModification(Base):
    """DocumentModification model - tracks real document changes for integrity monitoring"""
    __tablename__ = "document_modifications"
    
    id = Column(Integer, primary_key=True, index=True)
    modification_id = Column(String(50), unique=True, index=True, nullable=False)
    
    # Who modified
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    username = Column(String(100), nullable=False)
    user_department = Column(String(100), nullable=False)
    
    # What document
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    document_name = Column(String(255), nullable=False)
    target_department = Column(String(100), nullable=False)
    
    # Change details
    original_content = Column(Text)  # Content before modification
    modified_content = Column(Text)  # Content after modification
    original_length = Column(Integer)
    modified_length = Column(Integer)
    chars_added = Column(Integer, default=0)
    chars_removed = Column(Integer, default=0)
    change_percent = Column(Float, default=0.0)
    
    # Risk assessment
    is_cross_department = Column(Boolean, default=False)
    risk_score = Column(Float, default=0.0)
    risk_level = Column(String(20))
    
    # Timestamps
    modified_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    user = relationship("User")
    document = relationship("Document")
    
    def __repr__(self):
        return f"<DocumentModification {self.modification_id}: {self.document_name} by {self.username}>"


# Helper function to create sample data
def create_sample_users(db_session):
    """Create sample users for testing"""
    from ..core.security import get_password_hash
    
    sample_users = [
        {"user_id": "U001", "username": "john.smith", "email": "john.smith@company.com", 
         "full_name": "John Smith", "department": "HR", "role": UserRole.USER},
        {"user_id": "U002", "username": "jane.doe", "email": "jane.doe@company.com",
         "full_name": "Jane Doe", "department": "Finance", "role": UserRole.USER},
        {"user_id": "U003", "username": "bob.wilson", "email": "bob.wilson@company.com",
         "full_name": "Bob Wilson", "department": "IT", "role": UserRole.USER},
        {"user_id": "U004", "username": "alice.analyst", "email": "alice.analyst@company.com",
         "full_name": "Alice Analyst", "department": "Security", "role": UserRole.ANALYST},
        {"user_id": "U005", "username": "admin", "email": "admin@company.com",
         "full_name": "System Admin", "department": "IT", "role": UserRole.ADMIN},
    ]
    
    for user_data in sample_users:
        user = User(
            **user_data,
            hashed_password=get_password_hash("password123")
        )
        db_session.add(user)
    
    db_session.commit()
    print(f"Created {len(sample_users)} sample users")

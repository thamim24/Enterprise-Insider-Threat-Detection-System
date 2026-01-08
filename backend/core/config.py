"""
Configuration settings for Enterprise Insider Threat Detection Platform
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
from functools import lru_cache
import os

class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    APP_NAME: str = "Enterprise Insider Threat Detection Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False)
    
    # Security
    SECRET_KEY: str = Field(default="your-secret-key-change-in-production-minimum-32-chars")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Database
    DATABASE_URL: str = Field(default="sqlite:///./enterprise_threat.db")
    
    # ML Engine
    ANOMALY_CONTAMINATION: float = 0.1
    ANOMALY_N_ESTIMATORS: int = 100
    RISK_BEHAVIOR_WEIGHT: float = 0.4
    RISK_CLASSIFICATION_WEIGHT: float = 0.3
    RISK_INTEGRITY_WEIGHT: float = 0.3
    
    # Alert thresholds
    ALERT_THRESHOLD_CRITICAL: float = 0.8
    ALERT_THRESHOLD_HIGH: float = 0.6
    ALERT_THRESHOLD_MEDIUM: float = 0.4
    
    # Document paths
    DOCUMENTS_DIR: str = Field(default="data/documents")
    TAMPERED_DOCS_DIR: str = Field(default="data/tampered_docs")
    XAI_OUTPUTS_DIR: str = Field(default="xai_outputs")
    
    # CORS
    CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:5173"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Risk level mappings
RISK_LEVELS = {
    "critical": {"min_score": 0.8, "color": "#dc2626", "priority": 1},
    "high": {"min_score": 0.6, "color": "#ea580c", "priority": 2},
    "medium": {"min_score": 0.4, "color": "#ca8a04", "priority": 3},
    "low": {"min_score": 0.0, "color": "#16a34a", "priority": 4}
}

# Document sensitivity levels
SENSITIVITY_LEVELS = {
    "public": {"risk_weight": 0.1, "color": "#22c55e"},
    "internal": {"risk_weight": 0.5, "color": "#eab308"},
    "confidential": {"risk_weight": 0.9, "color": "#ef4444"}
}

# User roles
ROLES = {
    "USER": {"level": 1, "can_view_own_dept": True, "can_view_other_dept": True},
    "ANALYST": {"level": 2, "can_view_alerts": True, "can_view_reports": True},
    "ADMIN": {"level": 3, "can_manage_users": True, "can_manage_system": True}
}

# Departments (UPPERCASE to match frontend and database storage)
DEPARTMENTS = ["HR", "FINANCE", "LEGAL", "IT"]

# Action types with risk multipliers
ACTION_TYPES = {
    "view": {"base_risk": 0.1, "description": "Document viewed"},
    "download": {"base_risk": 0.3, "description": "Document downloaded"},
    "upload": {"base_risk": 0.2, "description": "Document uploaded"},
    "modify": {"base_risk": 0.5, "description": "Document modified"},
    "delete": {"base_risk": 0.7, "description": "Document deleted"},
    "share": {"base_risk": 0.4, "description": "Document shared"}
}

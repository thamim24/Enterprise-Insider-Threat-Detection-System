"""
Enterprise Insider Threat Detection Platform
Main FastAPI Application Entry Point

This is the nervous system of the threat detection platform.
All requests flow through here to the ML engine.

ARCHITECTURE: Event-Driven Real-Time System
    API → Queue → ML Worker → DB → WebSocket Broadcast → Dashboard
"""
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import time
import logging
import asyncio

from .core.config import get_settings
from .db import init_db, create_sample_users, SessionLocal
from .api import (
    auth_router,
    events_router,
    documents_router,
    alerts_router,
    reports_router,
    ml_router
)
from .realtime import websocket_router
from .streaming import ml_worker

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events
    Starts background ML worker for event-driven processing
    """
    # Startup
    logger.info("🚀 Starting Enterprise Insider Threat Detection Platform...")
    
    # Initialize database
    logger.info("📊 Initializing database...")
    init_db()
    
    # Create sample users if needed
    db = SessionLocal()
    try:
        from .db import User
        if db.query(User).count() == 0:
            logger.info("👤 Creating sample users...")
            create_sample_users(db)
    finally:
        db.close()
    
    # Start background ML worker
    logger.info("⚙️ Starting background ML worker...")
    worker_task = asyncio.create_task(ml_worker())
    logger.info("✅ ML worker started - event-driven processing enabled")
    
    logger.info("✨ Platform started successfully!")
    logger.info("📡 Real-time architecture: API → Queue → Worker → ML → DB → WebSocket")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down...")
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        logger.info("ML worker stopped")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="""
    ## Enterprise Explainable Insider Threat Detection Platform
    
    A real-time, explainable ML system that detects insider data leakage 
    and document tampering using behavioral analysis, document intelligence, 
    and risk fusion.
    
    ### Features
    - **Behavioral Anomaly Detection**: IsolationForest-based user behavior analysis
    - **Document Sensitivity Classification**: NLP-based document classification
    - **Integrity Verification**: Hash and semantic similarity checking
    - **Risk Fusion**: Multi-signal risk scoring
    - **Explainability**: SHAP and LIME explanations
    
    ### API Sections
    - **Auth**: User authentication and authorization
    - **Events**: Event ingestion (feeds ML pipeline)
    - **Documents**: Document listing and access
    - **Alerts**: Alert management for analysts
    - **Reports**: Report generation with XAI appendix
    """,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time to response headers"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )


# Include routers
app.include_router(auth_router, prefix="/api")
app.include_router(events_router, prefix="/api")
app.include_router(documents_router, prefix="/api")
app.include_router(alerts_router, prefix="/api")
app.include_router(reports_router, prefix="/api")
app.include_router(ml_router, prefix="/api")
app.include_router(websocket_router)  # WebSocket real-time updates


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint
    """
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION
    }


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint with API information
    """
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "description": "Enterprise Explainable Insider Threat Detection Platform",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "auth": "/api/auth",
            "events": "/api/events",
            "documents": "/api/documents",
            "alerts": "/api/alerts",
            "reports": "/api/reports"
        }
    }


# ML Pipeline status endpoint
@app.get("/api/ml/status", tags=["ML Engine"])
async def ml_status():
    """
    Get ML pipeline status and statistics
    """
    from .api.events import get_pipeline
    
    pipeline = get_pipeline()
    stats = pipeline.get_statistics()
    
    return {
        "status": "operational" if stats["is_initialized"] else "initializing",
        "model_trained": stats["model_trained"],
        "documents_registered": stats["documents_registered"],
        "config": stats["config"]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

"""
ML Worker - Background Event Processor
Decouples API from ML processing

Flow:
    Queue → Worker → ML Pipeline → DB → WebSocket Broadcast
    
This runs forever in background, consuming events from the queue.
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any
import uuid

from .event_queue import event_queue
from ..ml_engine import ThreatDetectionPipeline, UserEvent, PipelineResult
from ..db import SessionLocal, Event, User, Document, Alert, Explanation, ActionType, AlertPriority
from ..db.models import DocumentModification
from difflib import SequenceMatcher
import hashlib

logger = logging.getLogger(__name__)

# Pipeline instance for worker
_pipeline: Optional[ThreatDetectionPipeline] = None


def get_pipeline() -> ThreatDetectionPipeline:
    """Get or initialize ML pipeline"""
    global _pipeline
    if _pipeline is None:
        logger.info("Initializing ML pipeline in worker...")
        _pipeline = ThreatDetectionPipeline()
        _pipeline.initialize()
        logger.info("ML pipeline initialized successfully")
    return _pipeline


async def process_event_from_queue(event_data: Dict[str, Any]) -> PipelineResult:
    """
    Process a single event through ML pipeline
    
    Args:
        event_data: Event payload from queue
        
    Returns:
        PipelineResult from ML pipeline
    """
    pipeline = get_pipeline()
    
    # Create UserEvent
    user_event = UserEvent(
        user_id=event_data['user_id'],
        user_department=event_data['user_department'],
        document_id=event_data['document_id'],
        document_name=event_data['document_name'],
        target_department=event_data['target_department'],
        action=event_data['action'],
        bytes_transferred=event_data.get('bytes_transferred', 0),
        source_ip=event_data.get('source_ip'),
        device_info=event_data.get('device_info'),
        session_id=event_data.get('session_id'),
        timestamp=datetime.utcnow()
    )
    
    # Run ML pipeline
    result = pipeline.run(user_event, event_data.get('document_content'))
    
    return result, user_event


async def store_event_to_db(user_event: UserEvent, result: PipelineResult, event_data: Dict[str, Any]) -> int:
    """
    Store processed event to database
    
    Returns:
        event_id (database ID)
    """
    db = SessionLocal()
    try:
        event_id = f"EVT-{uuid.uuid4().hex[:12].upper()}"
        
        # Get user and document IDs
        user = db.query(User).filter(User.user_id == user_event.user_id).first()
        document = db.query(Document).filter(Document.document_id == user_event.document_id).first()
        
        db_event = Event(
            event_id=event_id,
            user_id=user.id if user else 1,
            user_department=user_event.user_department,
            action=ActionType(user_event.action),
            document_id=document.id if document else 1,
            target_department=user_event.target_department,
            timestamp=user_event.timestamp,
            bytes_transferred=user_event.bytes_transferred,
            source_ip=user_event.source_ip,
            device_info=user_event.device_info,
            session_id=user_event.session_id,
            is_cross_department=result.is_cross_department,
            behavior_score=result.behavior_score,
            risk_score=result.risk_score,
            risk_level=result.risk_level
        )
        
        db.add(db_event)
        db.commit()
        db.refresh(db_event)
        
        logger.info(f"Stored event {event_id} to database")
        return db_event.id, event_id
        
    except Exception as e:
        logger.error(f"Failed to store event to DB: {e}")
        db.rollback()
        raise
    finally:
        db.close()


async def create_alert_if_needed(event_db_id: int, result: PipelineResult, user_id: str) -> Optional[str]:
    """
    Create alert if risk is high enough
    
    Returns:
        alert_id if created, None otherwise
    """
    if not result.requires_alert:
        logger.info(f"Skipping alert creation - requires_alert=False (risk_score={result.risk_score:.3f}, threshold=0.4)")
        return None
        
    db = SessionLocal()
    try:
        alert_id = f"ALT-{uuid.uuid4().hex[:12].upper()}"
        
        # Get user database ID from user_id string
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            logger.error(f"Cannot create alert - user {user_id} not found")
            return None
        
        # Determine priority (use correct enum values - UPPERCASE!)
        if result.risk_level == "critical":
            priority = AlertPriority.CRITICAL
        elif result.risk_level == "high":
            priority = AlertPriority.HIGH
        elif result.risk_level == "medium":
            priority = AlertPriority.MEDIUM
        else:
            priority = AlertPriority.LOW
        
        alert = Alert(
            alert_id=alert_id,
            event_id=event_db_id,
            user_id=user.id,
            priority=priority,
            status="open",
            summary=result.alert_summary or f"Suspicious activity detected - {result.risk_level.upper()} risk",
            risk_score=result.risk_score,
            details={
                'risk_level': result.risk_level,
                'severity': result.severity,
                'risk_factors': result.risk_factors,
                'risk_breakdown': {
                    'behavior': result.behavior_score,
                    'sensitivity': result.sensitivity_score,
                    'integrity': result.integrity_score
                },
                'primary_risk_factor': result.primary_risk_factor,
                'is_cross_department': result.is_cross_department,
                'is_anomalous': result.is_anomalous
            },
            created_at=datetime.utcnow()
        )
        
        db.add(alert)
        db.commit()
        db.refresh(alert)
        
        logger.info(f"✅ Created alert {alert_id} for event {event_db_id} - risk={result.risk_score:.3f}, level={result.risk_level}, priority={priority.value}")
        return alert_id
        
    except Exception as e:
        logger.error(f"❌ Failed to create alert for event {event_db_id}: {type(e).__name__}: {str(e)}", exc_info=True)
        logger.error(f"   Risk level: {result.risk_level}, requires_alert: {result.requires_alert}")
        logger.error(f"   Alert data: alert_id={alert_id}, user_id={user_id}, priority={priority if 'priority' in locals() else 'N/A'}")
        db.rollback()
        return None
    finally:
        db.close()


async def store_explanation(event_db_id: int, result: PipelineResult):
    """Store XAI explanations"""
    if not result.shap_explanation and not result.lime_explanation:
        return
        
    db = SessionLocal()
    try:
        # Ensure risk_components is always a dict
        risk_components = {
            'behavior': result.behavior_score,
            'classification': result.sensitivity_score,
            'integrity': result.integrity_score
        }
        
        explanation = Explanation(
            explanation_id=f"EXP-{uuid.uuid4().hex[:12].upper()}",
            event_id=event_db_id,
            explanation_type="shap_behavior" if result.shap_explanation else "lime_text",
            shap_values=result.shap_explanation.get('shap_values') if result.shap_explanation else None,
            shap_base_value=result.shap_explanation.get('base_value') if result.shap_explanation else None,
            lime_features=result.lime_explanation.get('top_features') if result.lime_explanation else None,
            risk_components=risk_components
        )
        
        db.add(explanation)
        db.commit()
        logger.info(f"Stored explanation for event {event_db_id}")
    except Exception as e:
        logger.error(f"Failed to store explanation: {e}")
        db.rollback()
    finally:
        db.close()


async def store_document_modification(event_data: Dict[str, Any], result: PipelineResult):
    """Store document modification for integrity tracking"""
    if event_data['action'] != 'modify' or not event_data.get('document_content'):
        return
        
    db = SessionLocal()
    try:
        # Get document
        document = db.query(Document).filter(
            Document.document_id == event_data['document_id']
        ).first()
        
        original_content = ""
        if document:
            original_content = document.original_content or document.full_content or document.content_preview or ""
        
        modified_content = event_data['document_content']
        
        # Calculate diff
        original_length = len(original_content)
        modified_length = len(modified_content)
        
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
        
        change_percent = 0.0
        if original_length > 0:
            change_percent = (chars_added + chars_removed) / original_length * 100
        
        # Get user
        user = db.query(User).filter(User.user_id == event_data['user_id']).first()
        
        modification = DocumentModification(
            modification_id=f"MOD-{uuid.uuid4().hex[:12].upper()}",
            user_id=user.id if user else 1,
            username=event_data['username'],
            user_department=event_data['user_department'],
            document_id=document.id if document else 1,
            document_name=event_data['document_name'],
            target_department=event_data['target_department'],
            original_content=original_content,
            modified_content=modified_content,
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
        
        # Update document
        if document:
            document.full_content = modified_content
            document.is_tampered = True
            document.tamper_severity = result.risk_level
            document.current_hash = hashlib.sha256(modified_content.encode()).hexdigest()[:16]
            document.updated_at = datetime.utcnow()
        
        db.commit()
        logger.info(f"Stored document modification {modification.modification_id}")
    except Exception as e:
        logger.error(f"Failed to store document modification: {e}")
        db.rollback()
    finally:
        db.close()


async def ml_worker():
    """
    Main ML worker loop
    
    Runs forever, consuming events from queue and processing them.
    This is the heart of the event-driven architecture.
    """
    logger.info("🚀 ML Worker started - listening for events...")
    
    event_count = 0
    
    while True:
        try:
            # Get event from queue (blocks until available)
            event_data = await event_queue.get()
            event_count += 1
            
            logger.info(f"Processing event #{event_count} - {event_data['action']} on {event_data['document_name']}")
            
            # Process through ML pipeline
            result, user_event = await process_event_from_queue(event_data)
            
            # Log risk assessment details
            logger.info(f"Risk Assessment: score={result.risk_score:.3f}, level={result.risk_level}, requires_alert={result.requires_alert}")
            
            # Store to database
            event_db_id, event_id = await store_event_to_db(user_event, result, event_data)
            
            # Create alert if needed
            alert_id = await create_alert_if_needed(event_db_id, result, event_data['user_id'])
            
            # Store explanations
            await store_explanation(event_db_id, result)
            
            # Store modifications
            await store_document_modification(event_data, result)
            
            # Broadcast to WebSocket (imported later to avoid circular dependency)
            try:
                from ..realtime import manager
                
                # Broadcast new event
                await manager.broadcast({
                    "type": "new_event",
                    "event_id": event_id,
                    "user_id": event_data['user_id'],
                    "action": event_data['action'],
                    "document_name": event_data['document_name'],
                    "risk_score": result.risk_score,
                    "risk_level": result.risk_level,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                # Broadcast new alert with FULL data if created
                if alert_id:
                    # Get the full alert from database
                    db = SessionLocal()
                    try:
                        from ..db.models import Alert as AlertModel
                        from ..api.alerts import alert_to_response
                        
                        alert_obj = db.query(AlertModel).filter(AlertModel.alert_id == alert_id).first()
                        if alert_obj:
                            # Convert to full response format
                            full_alert = alert_to_response(alert_obj, db)
                            
                            # Broadcast complete alert data
                            await manager.broadcast({
                                "type": "new_alert",
                                "alert": full_alert.dict()  # Full alert object
                            })
                    finally:
                        db.close()
                
                logger.info(f"✅ Event processed and broadcast - Queue: {event_queue.qsize()}")
                
            except ImportError:
                # WebSocket not set up yet, skip broadcast
                logger.debug("WebSocket manager not available, skipping broadcast")
            
            # Mark task as done
            event_queue.task_done()
            
        except asyncio.CancelledError:
            logger.info("ML Worker shutting down...")
            break
        except Exception as e:
            logger.error(f"Error processing event: {e}", exc_info=True)
            # Mark task as done even on error to prevent queue backup
            event_queue.task_done()
            # Continue processing next event
            continue

"""
WebSocket API Routes
Real-time communication endpoints
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from typing import Optional
import logging

from .connection_manager import manager
from ..core.security import verify_token_websocket

router = APIRouter()
logger = logging.getLogger(__name__)


@router.websocket("/ws/admin")
async def websocket_admin_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for admin/analyst dashboard
    
    Usage:
        ws://localhost:8000/ws/admin?token=<jwt_token>
    
    Messages sent to client:
        - connection_established: Initial connection confirmation
        - new_event: New document action event processed
        - new_alert: New security alert created
        - system_status: System health/queue status
    """
    
    # Verify authentication
    if not token:
        await websocket.close(code=1008, reason="Authentication required")
        return
    
    try:
        # Verify JWT token
        token_data = verify_token_websocket(token)
        if not token_data:
            await websocket.close(code=1008, reason="Invalid or expired token")
            return
        
        user_id = token_data.user_id
        
    except Exception as e:
        logger.error(f"WebSocket auth failed: {e}")
        await websocket.close(code=1008, reason="Authentication failed")
        return
    
    # Connect client
    await manager.connect(websocket, user_id)
    
    try:
        # Keep connection alive and handle client messages
        while True:
            # Receive messages from client (ping/pong, subscriptions, etc.)
            data = await websocket.receive_json()
            
            # Handle client commands
            if data.get("type") == "ping":
                await manager.send_personal_message({
                    "type": "pong",
                    "timestamp": data.get("timestamp")
                }, websocket)
            
            elif data.get("type") == "subscribe":
                # Could implement selective subscriptions here
                await manager.send_personal_message({
                    "type": "subscribed",
                    "channels": data.get("channels", ["all"])
                }, websocket)
            
    except WebSocketDisconnect:
        manager.disconnect(user_id)
        logger.info(f"Client {user_id} disconnected")
    except Exception as e:
        logger.error(f"WebSocket error for {user_id}: {e}")
        manager.disconnect(user_id)


@router.get("/ws/status")
async def websocket_status():
    """
    Get WebSocket connection status
    Public endpoint for monitoring
    """
    return {
        "active_connections": manager.get_connection_count(),
        "connected_users": manager.get_connected_users()
    }

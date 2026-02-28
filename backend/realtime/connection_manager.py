"""
WebSocket Connection Manager
Manages multiple analyst connections and broadcasts updates
"""
from typing import List, Dict, Any
from fastapi import WebSocket
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections for real-time updates
    
    Supports multiple analysts connected simultaneously.
    Broadcasts events, alerts, and system status updates.
    """
    
    def __init__(self):
        # Active connections: user_id -> WebSocket
        self.active_connections: Dict[str, WebSocket] = {}
        self._connection_count = 0
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """Accept and register a new connection"""
        await websocket.accept()
        self.active_connections[user_id] = websocket
        self._connection_count += 1
        
        logger.info(f"✅ WebSocket connected: {user_id} (Total: {len(self.active_connections)})")
        
        # Send welcome message
        await self.send_personal_message({
            "type": "connection_established",
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Connected to real-time threat detection stream"
        }, websocket)
    
    def disconnect(self, user_id: str):
        """Remove a connection"""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            logger.info(f"❌ WebSocket disconnected: {user_id} (Remaining: {len(self.active_connections)})")
    
    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """Send message to specific connection"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Failed to send personal message: {e}")
    
    async def broadcast(self, message: Dict[str, Any]):
        """
        Broadcast message to all connected clients
        
        This is called from ML worker after processing events.
        Non-blocking - does not wait for delivery confirmation.
        """
        if not self.active_connections:
            logger.debug("No active connections to broadcast to")
            return
        
        # Add timestamp if not present
        if "timestamp" not in message:
            message["timestamp"] = datetime.utcnow().isoformat()
        
        disconnected = []
        
        for user_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Failed to broadcast to {user_id}: {e}")
                disconnected.append(user_id)
        
        # Clean up disconnected clients
        for user_id in disconnected:
            self.disconnect(user_id)
    
    async def broadcast_alert(self, alert_data: Dict[str, Any]):
        """Broadcast new alert to all analysts"""
        await self.broadcast({
            "type": "new_alert",
            **alert_data
        })
    
    async def broadcast_event(self, event_data: Dict[str, Any]):
        """Broadcast new event to all analysts"""
        await self.broadcast({
            "type": "new_event",
            **event_data
        })
    
    async def broadcast_system_status(self, status_data: Dict[str, Any]):
        """Broadcast system status update"""
        await self.broadcast({
            "type": "system_status",
            **status_data
        })
    
    def get_connection_count(self) -> int:
        """Get number of active connections"""
        return len(self.active_connections)
    
    def get_connected_users(self) -> List[str]:
        """Get list of connected user IDs"""
        return list(self.active_connections.keys())


# Global connection manager instance
manager = ConnectionManager()

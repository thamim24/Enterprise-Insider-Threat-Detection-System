"""
Event Queue - Core of Async Architecture
Decouples API from ML processing

Flow:
    API → Queue → Worker → ML Engine → DB → WebSocket Broadcast
"""
import asyncio
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

# Global async queue for event processing
event_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)


async def get_queue_size() -> int:
    """Get current queue size for monitoring"""
    return event_queue.qsize()


async def is_queue_full() -> bool:
    """Check if queue is approaching capacity"""
    return event_queue.qsize() > 900  # 90% threshold


async def get_queue_stats() -> Dict[str, Any]:
    """Get queue statistics for monitoring dashboard"""
    size = event_queue.qsize()
    return {
        "current_size": size,
        "max_size": event_queue.maxsize,
        "utilization_percent": (size / event_queue.maxsize) * 100,
        "is_near_capacity": size > 900
    }

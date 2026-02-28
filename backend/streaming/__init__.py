"""
Real-Time Streaming Layer
Event-driven architecture for asynchronous ML processing
"""
from .event_queue import event_queue
from .ml_worker import ml_worker

__all__ = ['event_queue', 'ml_worker']

"""
Log streaming service to send backend logs to frontend in real-time
"""
import logging
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
from collections import defaultdict

# Store logs per record_id
_log_store: Dict[str, List[Dict]] = defaultdict(list)
_log_listeners: Dict[str, List[asyncio.Queue]] = defaultdict(list)


class StreamLogHandler(logging.Handler):
    """Custom logging handler that captures logs and streams them"""
    
    def __init__(self, record_id: Optional[str] = None):
        super().__init__()
        self.record_id = record_id
    
    def emit(self, record):
        """Emit a log record"""
        if not self.record_id:
            return
        
        # Format message - extract the actual log content
        message = self.format(record)
        # Remove logger name prefix (e.g., "INFO:app.services.ocr_service:")
        if ':' in message:
            parts = message.split(':', 3)
            if len(parts) >= 4:
                # Keep only the actual message part
                clean_message = parts[3].strip()
            else:
                clean_message = message
        else:
            clean_message = message
        
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": clean_message,
            "raw_message": message,
            "module": record.module,
            "funcName": record.funcName
        }
        
        # Store log
        _log_store[self.record_id].append(log_entry)
        
        # Stream to listeners
        for queue in _log_listeners.get(self.record_id, []):
            try:
                queue.put_nowait(log_entry)
            except asyncio.QueueFull:
                pass  # Skip if queue is full


def get_log_handler(record_id: str) -> StreamLogHandler:
    """Get a log handler for a specific record_id"""
    handler = StreamLogHandler(record_id=record_id)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(message)s')
    handler.setFormatter(formatter)
    return handler


async def stream_logs(record_id: str):
    """Generator that yields logs for a record_id"""
    queue = asyncio.Queue()
    _log_listeners[record_id].append(queue)
    
    try:
        # Send existing logs first
        for log in _log_store.get(record_id, []):
            yield log
        
        # Stream new logs
        while True:
            try:
                log = await asyncio.wait_for(queue.get(), timeout=30.0)
                yield log
            except asyncio.TimeoutError:
                # Send heartbeat to keep connection alive
                yield {"type": "heartbeat", "timestamp": datetime.utcnow().isoformat()}
    finally:
        # Cleanup
        if record_id in _log_listeners:
            _log_listeners[record_id].remove(queue)
            if not _log_listeners[record_id]:
                del _log_listeners[record_id]


def cleanup_logs(record_id: str):
    """Clean up logs for a record_id after processing is complete"""
    if record_id in _log_store:
        del _log_store[record_id]
    if record_id in _log_listeners:
        del _log_listeners[record_id]


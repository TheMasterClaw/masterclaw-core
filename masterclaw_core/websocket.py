"""WebSocket support for real-time MasterClaw communication

Security features:
- Rate limiting per IP and session
- Maximum connection limits per session
- Session ID validation
- Connection timeouts
- Message size limits
"""

import json
import re
import time
import logging
from typing import Dict, Set, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger("masterclaw.websocket")

# Security configuration
MAX_CONNECTIONS_PER_SESSION = 5  # Max concurrent connections per session
MAX_CONNECTIONS_PER_IP = 10  # Max concurrent connections per IP
MAX_MESSAGE_SIZE = 64 * 1024  # 64KB max message size
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX_MESSAGES = 100  # messages per window
CONNECTION_TIMEOUT_SECONDS = 3600  # 1 hour max connection duration
SESSION_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{1,64}$')  # Valid session ID format


@dataclass
class ConnectionInfo:
    """Tracks connection metadata for security enforcement"""
    websocket: WebSocket
    connected_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    message_count: int = 0
    ip_address: str = "unknown"
    
    def is_expired(self) -> bool:
        """Check if connection has exceeded max duration"""
        return datetime.utcnow() - self.connected_at > timedelta(seconds=CONNECTION_TIMEOUT_SECONDS)
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.utcnow()
        self.message_count += 1


@dataclass
class RateLimitInfo:
    """Tracks rate limiting data per client"""
    message_times: list = field(default_factory=list)
    
    def is_rate_limited(self) -> bool:
        """Check if client has exceeded rate limit"""
        now = time.time()
        window_start = now - RATE_LIMIT_WINDOW
        # Remove old entries
        self.message_times = [t for t in self.message_times if t > window_start]
        return len(self.message_times) >= RATE_LIMIT_MAX_MESSAGES
    
    def record_message(self):
        """Record a message timestamp"""
        self.message_times.append(time.time())


class ConnectionManager:
    """Manages WebSocket connections with security hardening"""
    
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.connection_info: Dict[WebSocket, ConnectionInfo] = {}
        self.connections_by_ip: Dict[str, Set[WebSocket]] = {}
        self.rate_limits: Dict[str, RateLimitInfo] = {}
    
    def _validate_session_id(self, session_id: str) -> bool:
        """Validate session ID format to prevent injection attacks"""
        if not session_id or len(session_id) > 64:
            return False
        return SESSION_ID_PATTERN.match(session_id) is not None
    
    def _get_client_ip(self, websocket: WebSocket) -> str:
        """Extract client IP from WebSocket connection"""
        # Try to get from headers first (behind proxy)
        headers = dict(websocket.headers)
        forwarded = headers.get("x-forwarded-for", headers.get("X-Forwarded-For", ""))
        if forwarded:
            # X-Forwarded-For can contain multiple IPs, take the first one
            return forwarded.split(",")[0].strip()
        # Fall back to direct connection info
        if websocket.client:
            return websocket.client.host
        return "unknown"
    
    async def connect(self, websocket: WebSocket, session_id: str) -> bool:
        """
        Accept a new WebSocket connection with security validation.
        
        Returns True if connection was accepted, False if rejected.
        """
        # Validate session ID format
        if not self._validate_session_id(session_id):
            logger.warning(f"WebSocket connection rejected: invalid session ID format")
            await websocket.close(code=4001, reason="Invalid session ID format")
            return False
        
        # Get client IP for rate limiting
        client_ip = self._get_client_ip(websocket)
        
        # Check IP-based connection limit
        current_ip_connections = len(self.connections_by_ip.get(client_ip, set()))
        if current_ip_connections >= MAX_CONNECTIONS_PER_IP:
            logger.warning(f"WebSocket connection rejected: IP {client_ip} has too many connections ({current_ip_connections})")
            await websocket.close(code=4002, reason="Too many connections from this IP")
            return False
        
        # Check session-based connection limit
        current_session_connections = len(self.active_connections.get(session_id, set()))
        if current_session_connections >= MAX_CONNECTIONS_PER_SESSION:
            logger.warning(f"WebSocket connection rejected: session {session_id} has too many connections ({current_session_connections})")
            await websocket.close(code=4003, reason="Too many connections for this session")
            return False
        
        # Accept the connection
        await websocket.accept()
        
        # Initialize connection tracking
        if session_id not in self.active_connections:
            self.active_connections[session_id] = set()
        self.active_connections[session_id].add(websocket)
        
        # Track connection info
        conn_info = ConnectionInfo(
            websocket=websocket,
            ip_address=client_ip
        )
        self.connection_info[websocket] = conn_info
        
        # Track by IP
        if client_ip not in self.connections_by_ip:
            self.connections_by_ip[client_ip] = set()
        self.connections_by_ip[client_ip].add(websocket)
        
        logger.info(f"WebSocket connected: session={session_id}, ip={client_ip}, total_session_conns={current_session_connections + 1}")
        
        # Send welcome message with connection limits
        await websocket.send_json({
            "type": "connection",
            "status": "connected",
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat(),
            "limits": {
                "max_message_size": MAX_MESSAGE_SIZE,
                "rate_limit_window": RATE_LIMIT_WINDOW,
                "rate_limit_max_messages": RATE_LIMIT_MAX_MESSAGES,
            }
        })
        
        return True
    
    def disconnect(self, websocket: WebSocket, session_id: str):
        """Remove a WebSocket connection and clean up tracking"""
        # Remove from session connections
        if session_id in self.active_connections:
            self.active_connections[session_id].discard(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
        
        # Remove from connection info and get IP for logging
        conn_info = self.connection_info.pop(websocket, None)
        client_ip = conn_info.ip_address if conn_info else "unknown"
        
        # Remove from IP tracking
        if client_ip in self.connections_by_ip:
            self.connections_by_ip[client_ip].discard(websocket)
            if not self.connections_by_ip[client_ip]:
                del self.connections_by_ip[client_ip]
        
        logger.info(f"WebSocket disconnected: session={session_id}, ip={client_ip}")
    
    async def _is_rate_limited(self, websocket: WebSocket) -> bool:
        """Check if connection is rate limited"""
        client_ip = self._get_client_ip(websocket)
        
        if client_ip not in self.rate_limits:
            self.rate_limits[client_ip] = RateLimitInfo()
        
        rate_limit = self.rate_limits[client_ip]
        
        if rate_limit.is_rate_limited():
            logger.warning(f"Rate limit exceeded for IP {client_ip}")
            return True
        
        rate_limit.record_message()
        return False
    
    async def validate_and_receive(self, websocket: WebSocket) -> Optional[dict]:
        """
        Receive and validate a WebSocket message.
        
        Returns parsed JSON or None if invalid/rate limited.
        """
        # Check connection timeout
        conn_info = self.connection_info.get(websocket)
        if conn_info and conn_info.is_expired():
            logger.info(f"Connection expired after {CONNECTION_TIMEOUT_SECONDS}s")
            await websocket.close(code=4004, reason="Connection timeout")
            return None
        
        # Check rate limiting
        if await self._is_rate_limited(websocket):
            await websocket.send_json({
                "type": "error",
                "error": "Rate limit exceeded",
                "code": "RATE_LIMIT_EXCEEDED",
                "retry_after": RATE_LIMIT_WINDOW,
            })
            return None
        
        try:
            # Receive text with size limit
            data = await websocket.receive_text()
            
            # Check message size
            if len(data) > MAX_MESSAGE_SIZE:
                logger.warning(f"Message too large: {len(data)} bytes (max {MAX_MESSAGE_SIZE})")
                await websocket.send_json({
                    "type": "error",
                    "error": f"Message too large. Max size: {MAX_MESSAGE_SIZE} bytes",
                    "code": "MESSAGE_TOO_LARGE",
                })
                return None
            
            # Parse JSON
            try:
                message = json.loads(data)
            except json.JSONDecodeError as e:
                await websocket.send_json({
                    "type": "error",
                    "error": "Invalid JSON",
                    "code": "INVALID_JSON",
                })
                return None
            
            # Update connection activity
            if conn_info:
                conn_info.update_activity()
            
            return message
            
        except WebSocketDisconnect:
            raise
        except Exception as e:
            logger.error(f"Error receiving message: {e}")
            return None
    
    def get_connection_stats(self) -> dict:
        """Get current connection statistics for monitoring"""
        total_connections = sum(len(conns) for conns in self.active_connections.values())
        return {
            "total_connections": total_connections,
            "unique_sessions": len(self.active_connections),
            "unique_ips": len(self.connections_by_ip),
            "max_connections_per_session": MAX_CONNECTIONS_PER_SESSION,
            "max_connections_per_ip": MAX_CONNECTIONS_PER_IP,
            "rate_limit_window": RATE_LIMIT_WINDOW,
            "rate_limit_max_messages": RATE_LIMIT_MAX_MESSAGES,
        }
    
    async def broadcast_to_session(self, session_id: str, message: dict):
        """Send a message to all connections in a session with dead connection cleanup"""
        if session_id not in self.active_connections:
            return
        
        disconnected = []
        
        for connection in self.active_connections[session_id]:
            try:
                await connection.send_json(message)
                # Update activity timestamp
                if connection in self.connection_info:
                    self.connection_info[connection].update_activity()
            except Exception as e:
                logger.debug(f"Failed to send to connection: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn, session_id)
    
    async def send_to_client(self, websocket: WebSocket, message: dict):
        """Send a message to a specific client"""
        try:
            await websocket.send_json(message)
            # Update activity timestamp
            if websocket in self.connection_info:
                self.connection_info[websocket].update_activity()
        except Exception as e:
            logger.debug(f"Failed to send to client: {e}")
            # Connection is likely dead, will be cleaned up on next operation


# Global connection manager
manager = ConnectionManager()


async def handle_websocket(websocket: WebSocket, session_id: str):
    """
    Handle WebSocket connection lifecycle with security hardening.
    
    Security features:
    - Session ID validation
    - Connection limits per session and IP
    - Rate limiting
    - Message size limits
    - Connection timeouts
    - Structured error responses
    """
    # Attempt connection with security validation
    connected = await manager.connect(websocket, session_id)
    if not connected:
        return  # Connection was rejected by security checks
    
    try:
        while True:
            # Receive and validate message
            message = await manager.validate_and_receive(websocket)
            
            if message is None:
                # Validation failed or connection closed
                continue
            
            # Handle different message types
            msg_type = message.get('type', 'message')
            
            if msg_type == 'ping':
                await manager.send_to_client(websocket, {
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat(),
                })
            
            elif msg_type == 'stats':
                # Return connection stats
                await manager.send_to_client(websocket, {
                    "type": "stats",
                    "data": manager.get_connection_stats(),
                })
            
            elif msg_type == 'message':
                # Echo back for now - integrate with chat handler
                content = message.get('content', '')
                
                # Validate content is not too large
                if len(content) > 10000:  # 10KB limit for chat messages
                    await manager.send_to_client(websocket, {
                        "type": "error",
                        "error": "Message content too large (max 10KB)",
                        "code": "CONTENT_TOO_LARGE",
                    })
                    continue
                
                await manager.send_to_client(websocket, {
                    "type": "message",
                    "role": "user",
                    "content": content,
                    "timestamp": datetime.utcnow().isoformat(),
                })
            
            elif msg_type == 'typing':
                # Broadcast typing indicator to session
                await manager.broadcast_to_session(session_id, {
                    "type": "typing",
                    "user": message.get('user', 'unknown'),
                })
            
            else:
                await manager.send_to_client(websocket, {
                    "type": "error",
                    "message": f"Unknown message type: {msg_type}",
                    "code": "UNKNOWN_MESSAGE_TYPE",
                })
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, session_id)
    except Exception as e:
        logger.error(f"WebSocket handler error: {e}")
        try:
            await manager.send_to_client(websocket, {
                "type": "error",
                "error": "Internal server error",
                "code": "INTERNAL_ERROR",
            })
        except:
            pass
        finally:
            manager.disconnect(websocket, session_id)

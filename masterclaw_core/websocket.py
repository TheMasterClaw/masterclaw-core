"""WebSocket support for real-time MasterClaw communication"""

import json
from typing import Dict, Set
from datetime import datetime

from fastapi import WebSocket, WebSocketDisconnect


class ConnectionManager:
    """Manages WebSocket connections for real-time updates"""
    
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        
        if session_id not in self.active_connections:
            self.active_connections[session_id] = set()
        
        self.active_connections[session_id].add(websocket)
        
        # Send welcome message
        await websocket.send_json({
            "type": "connection",
            "status": "connected",
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat(),
        })
    
    def disconnect(self, websocket: WebSocket, session_id: str):
        """Remove a WebSocket connection"""
        if session_id in self.active_connections:
            self.active_connections[session_id].discard(websocket)
            
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
    
    async def broadcast_to_session(self, session_id: str, message: dict):
        """Send a message to all connections in a session"""
        if session_id not in self.active_connections:
            return
        
        disconnected = []
        
        for connection in self.active_connections[session_id]:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.active_connections[session_id].discard(conn)
    
    async def send_to_client(self, websocket: WebSocket, message: dict):
        """Send a message to a specific client"""
        await websocket.send_json(message)


# Global connection manager
manager = ConnectionManager()


async def handle_websocket(websocket: WebSocket, session_id: str):
    """Handle WebSocket connection lifecycle"""
    await manager.connect(websocket, session_id)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                
                # Handle different message types
                msg_type = message.get('type', 'message')
                
                if msg_type == 'ping':
                    await manager.send_to_client(websocket, {
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat(),
                    })
                
                elif msg_type == 'message':
                    # Echo back for now - integrate with chat handler
                    await manager.send_to_client(websocket, {
                        "type": "message",
                        "role": "user",
                        "content": message.get('content', ''),
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
                    })
            
            except json.JSONDecodeError:
                await manager.send_to_client(websocket, {
                    "type": "error",
                    "message": "Invalid JSON",
                })
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, session_id)

"""Tests for WebSocket security features

This module tests the security hardening of the WebSocket implementation including:
- Session ID validation
- Connection limits per session and IP
- Rate limiting
- Message size limits
- Connection timeouts
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import json

from masterclaw_core.websocket import (
    ConnectionManager,
    ConnectionInfo,
    RateLimitInfo,
    MAX_CONNECTIONS_PER_SESSION,
    MAX_CONNECTIONS_PER_IP,
    MAX_MESSAGE_SIZE,
    RATE_LIMIT_WINDOW,
    RATE_LIMIT_MAX_MESSAGES,
    CONNECTION_TIMEOUT_SECONDS,
)


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket object"""
    ws = MagicMock()
    ws.accept = AsyncMock()
    ws.close = AsyncMock()
    ws.send_json = AsyncMock()
    ws.receive_text = AsyncMock()
    ws.client = MagicMock()
    ws.client.host = "127.0.0.1"
    ws.headers = {}
    return ws


@pytest.fixture
def connection_manager():
    """Create a fresh ConnectionManager instance"""
    return ConnectionManager()


class TestConnectionInfo:
    """Tests for ConnectionInfo dataclass"""
    
    def test_connection_info_creation(self):
        """Test ConnectionInfo is created with correct defaults"""
        ws = MagicMock()
        info = ConnectionInfo(websocket=ws, ip_address="192.168.1.1")
        
        assert info.websocket == ws
        assert info.ip_address == "192.168.1.1"
        assert info.message_count == 0
        assert isinstance(info.connected_at, datetime)
        assert isinstance(info.last_activity, datetime)
    
    def test_connection_info_expired(self):
        """Test is_expired returns True for old connections"""
        ws = MagicMock()
        info = ConnectionInfo(websocket=ws)
        
        # Connection should not be expired initially
        assert not info.is_expired()
        
        # Manually set connected_at to past
        info.connected_at = datetime.utcnow() - timedelta(seconds=CONNECTION_TIMEOUT_SECONDS + 1)
        assert info.is_expired()
    
    def test_update_activity(self):
        """Test update_activity increments message count and updates timestamp"""
        ws = MagicMock()
        info = ConnectionInfo(websocket=ws)
        old_activity = info.last_activity
        
        time.sleep(0.01)  # Small delay to ensure timestamp changes
        info.update_activity()
        
        assert info.message_count == 1
        assert info.last_activity > old_activity


class TestRateLimitInfo:
    """Tests for RateLimitInfo dataclass"""
    
    def test_rate_limit_not_exceeded(self):
        """Test rate limiting when under limit"""
        rl = RateLimitInfo()
        
        # Add messages under the limit
        for _ in range(RATE_LIMIT_MAX_MESSAGES - 1):
            rl.record_message()
        
        assert not rl.is_rate_limited()
    
    def test_rate_limit_exceeded(self):
        """Test rate limiting when over limit"""
        rl = RateLimitInfo()
        
        # Add messages over the limit
        for _ in range(RATE_LIMIT_MAX_MESSAGES + 1):
            rl.record_message()
        
        assert rl.is_rate_limited()
    
    def test_rate_limit_window_expiration(self):
        """Test that old messages are cleaned from window"""
        rl = RateLimitInfo()
        
        # Add a message from outside the window
        old_time = time.time() - RATE_LIMIT_WINDOW - 1
        rl.message_times.append(old_time)
        
        # Should not be rate limited with just one old message
        assert not rl.is_rate_limited()
        # Old message should be cleaned
        assert len(rl.message_times) == 0


class TestConnectionManagerValidation:
    """Tests for ConnectionManager validation methods"""
    
    def test_validate_valid_session_id(self, connection_manager):
        """Test valid session IDs pass validation"""
        valid_ids = [
            "abc123",
            "session_123",
            "test-session",
            "a" * 64,  # Max length
        ]
        
        for session_id in valid_ids:
            assert connection_manager._validate_session_id(session_id), f"Failed for {session_id}"
    
    def test_validate_invalid_session_id(self, connection_manager):
        """Test invalid session IDs fail validation"""
        invalid_ids = [
            "",  # Empty
            "a" * 65,  # Too long
            "test.session",  # Invalid chars
            "test session",  # Space
            "test<script>",  # Script tag
            "../../../etc/passwd",  # Path traversal
        ]
        
        for session_id in invalid_ids:
            assert not connection_manager._validate_session_id(session_id), f"Failed for {session_id}"
    
    def test_get_client_ip_from_x_forwarded_for(self, connection_manager, mock_websocket):
        """Test IP extraction from X-Forwarded-For header"""
        mock_websocket.headers = {"x-forwarded-for": "192.168.1.100, 10.0.0.1"}
        
        ip = connection_manager._get_client_ip(mock_websocket)
        assert ip == "192.168.1.100"
    
    def test_get_client_ip_from_client(self, connection_manager, mock_websocket):
        """Test IP extraction from client when no header"""
        mock_websocket.headers = {}
        mock_websocket.client.host = "10.0.0.5"
        
        ip = connection_manager._get_client_ip(mock_websocket)
        assert ip == "10.0.0.5"


class TestConnectionLimits:
    """Tests for connection limit enforcement"""
    
    @pytest.mark.asyncio
    async def test_connection_limit_per_session(self, connection_manager, mock_websocket):
        """Test max connections per session is enforced"""
        session_id = "test-session"
        
        # Create max connections
        websockets = []
        for i in range(MAX_CONNECTIONS_PER_SESSION):
            ws = MagicMock()
            ws.accept = AsyncMock()
            ws.headers = {}
            ws.client = MagicMock()
            ws.client.host = f"127.0.0.{i}"
            ws.close = AsyncMock()
            ws.send_json = AsyncMock()
            
            connected = await connection_manager.connect(ws, session_id)
            assert connected, f"Connection {i} should succeed"
            websockets.append(ws)
        
        # Next connection should fail
        extra_ws = MagicMock()
        extra_ws.accept = AsyncMock()
        extra_ws.headers = {}
        extra_ws.client = MagicMock()
        extra_ws.client.host = "127.0.0.99"
        extra_ws.close = AsyncMock()
        extra_ws.send_json = AsyncMock()
        
        connected = await connection_manager.connect(extra_ws, session_id)
        assert not connected
        extra_ws.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_connection_limit_per_ip(self, connection_manager, mock_websocket):
        """Test max connections per IP is enforced"""
        same_ip = "192.168.1.50"
        
        # Create max connections from same IP
        websockets = []
        for i in range(MAX_CONNECTIONS_PER_IP):
            ws = MagicMock()
            ws.accept = AsyncMock()
            ws.headers = {"x-forwarded-for": same_ip}
            ws.client = MagicMock()
            ws.client.host = same_ip
            ws.close = AsyncMock()
            ws.send_json = AsyncMock()
            
            connected = await connection_manager.connect(ws, f"session-{i}")
            assert connected, f"Connection {i} should succeed"
            websockets.append(ws)
        
        # Next connection from same IP should fail
        extra_ws = MagicMock()
        extra_ws.accept = AsyncMock()
        extra_ws.headers = {"x-forwarded-for": same_ip}
        extra_ws.client = MagicMock()
        extra_ws.client.host = same_ip
        extra_ws.close = AsyncMock()
        extra_ws.send_json = AsyncMock()
        
        connected = await connection_manager.connect(extra_ws, "extra-session")
        assert not connected


class TestRateLimiting:
    """Tests for WebSocket rate limiting"""
    
    @pytest.mark.asyncio
    async def test_rate_limit_enforced(self, connection_manager, mock_websocket):
        """Test rate limiting blocks messages over threshold"""
        # Setup connection
        mock_websocket.headers = {}
        await connection_manager.connect(mock_websocket, "test-session")
        
        # Record many messages to trigger rate limit
        rl = connection_manager.rate_limits.get("127.0.0.1", RateLimitInfo())
        for _ in range(RATE_LIMIT_MAX_MESSAGES + 1):
            rl.record_message()
        connection_manager.rate_limits["127.0.0.1"] = rl
        
        # Should be rate limited
        is_limited = await connection_manager._is_rate_limited(mock_websocket)
        assert is_limited


class TestMessageValidation:
    """Tests for message validation"""
    
    @pytest.mark.asyncio
    async def test_message_size_limit(self, connection_manager, mock_websocket):
        """Test oversized messages are rejected"""
        # Setup connection
        mock_websocket.headers = {}
        await connection_manager.connect(mock_websocket, "test-session")
        
        # Create oversized message
        oversized_data = "x" * (MAX_MESSAGE_SIZE + 1)
        mock_websocket.receive_text = AsyncMock(return_value=oversized_data)
        
        result = await connection_manager.validate_and_receive(mock_websocket)
        assert result is None
        
        # Should send error
        calls = mock_websocket.send_json.call_args_list
        error_calls = [c for c in calls if c[0][0].get("code") == "MESSAGE_TOO_LARGE"]
        assert len(error_calls) > 0
    
    @pytest.mark.asyncio
    async def test_invalid_json_rejected(self, connection_manager, mock_websocket):
        """Test invalid JSON is rejected"""
        # Setup connection
        mock_websocket.headers = {}
        await connection_manager.connect(mock_websocket, "test-session")
        
        mock_websocket.receive_text = AsyncMock(return_value="not valid json{{{")
        
        result = await connection_manager.validate_and_receive(mock_websocket)
        assert result is None
        
        # Should send error
        calls = mock_websocket.send_json.call_args_list
        error_calls = [c for c in calls if c[0][0].get("code") == "INVALID_JSON"]
        assert len(error_calls) > 0
    
    @pytest.mark.asyncio
    async def test_valid_message_accepted(self, connection_manager, mock_websocket):
        """Test valid messages are accepted"""
        # Setup connection
        mock_websocket.headers = {}
        await connection_manager.connect(mock_websocket, "test-session")
        
        valid_message = {"type": "ping"}
        mock_websocket.receive_text = AsyncMock(return_value=json.dumps(valid_message))
        
        result = await connection_manager.validate_and_receive(mock_websocket)
        assert result == valid_message


class TestConnectionStats:
    """Tests for connection statistics"""
    
    def test_get_connection_stats_empty(self, connection_manager):
        """Test stats with no connections"""
        stats = connection_manager.get_connection_stats()
        
        assert stats["total_connections"] == 0
        assert stats["unique_sessions"] == 0
        assert stats["unique_ips"] == 0
        assert stats["max_connections_per_session"] == MAX_CONNECTIONS_PER_SESSION
        assert stats["max_connections_per_ip"] == MAX_CONNECTIONS_PER_IP


class TestDisconnectCleanup:
    """Tests for connection cleanup on disconnect"""
    
    @pytest.mark.asyncio
    async def test_disconnect_removes_all_tracking(self, connection_manager):
        """Test disconnect cleans up all tracking data structures"""
        # Create connection
        ws = MagicMock()
        ws.accept = AsyncMock()
        ws.headers = {"x-forwarded-for": "192.168.1.10"}
        ws.client = MagicMock()
        ws.client.host = "192.168.1.10"
        ws.close = AsyncMock()
        ws.send_json = AsyncMock()
        
        session_id = "cleanup-test"
        
        await connection_manager.connect(ws, session_id)
        
        # Verify tracking exists
        assert ws in connection_manager.connection_info
        assert "192.168.1.10" in connection_manager.connections_by_ip
        assert session_id in connection_manager.active_connections
        
        # Disconnect
        connection_manager.disconnect(ws, session_id)
        
        # Verify cleanup
        assert ws not in connection_manager.connection_info
        assert "192.168.1.10" not in connection_manager.connections_by_ip
        assert session_id not in connection_manager.active_connections

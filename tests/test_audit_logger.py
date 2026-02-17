"""Tests for security audit logging

Tests cover:
- Security event creation and serialization
- All audit logging methods
- Tamper detection
- Event analysis utilities
"""

import json
import logging
import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from masterclaw_core.audit_logger import (
    SecurityEvent,
    SecurityEventType,
    SecuritySeverity,
    SecurityAuditLogger,
    SecurityEventAnalyzer,
    log_auth_failure,
    log_rate_limit,
    log_suspicious,
    log_input_validation_failure,
    audit_logger,
)


class TestSecurityEvent:
    """Test the SecurityEvent dataclass"""
    
    def test_event_creation(self):
        """Test creating a basic security event"""
        event = SecurityEvent(
            event_type=SecurityEventType.AUTHENTICATION_FAILURE,
            severity=SecuritySeverity.HIGH,
            message="Invalid API key",
            timestamp="2026-02-17T10:00:00Z",
            client_ip="192.168.1.100",
            request_id="abc123"
        )
        
        assert event.event_type == SecurityEventType.AUTHENTICATION_FAILURE
        assert event.severity == SecuritySeverity.HIGH
        assert event.message == "Invalid API key"
        assert event.client_ip == "192.168.1.100"
        assert event.request_id == "abc123"
        assert event.event_hash is not None
        assert len(event.event_hash) == 16
    
    def test_event_hash_generation(self):
        """Test that event hash is generated automatically"""
        event = SecurityEvent(
            event_type=SecurityEventType.RATE_LIMIT_EXCEEDED,
            severity=SecuritySeverity.LOW,
            message="Rate limit hit",
            timestamp="2026-02-17T10:00:00Z"
        )
        
        assert event.event_hash is not None
        assert isinstance(event.event_hash, str)
        # Should be 16 hex characters
        assert len(event.event_hash) == 16
        assert all(c in "0123456789abcdef" for c in event.event_hash)
    
    def test_event_to_dict(self):
        """Test event serialization to dictionary"""
        event = SecurityEvent(
            event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
            severity=SecuritySeverity.CRITICAL,
            message="SQL injection attempt",
            timestamp="2026-02-17T10:00:00Z",
            client_ip="10.0.0.1",
            details={"pattern": "DROP TABLE", "field": "username"}
        )
        
        data = event.to_dict()
        
        assert data["event_type"] == "activity.suspicious"
        assert data["severity"] == "critical"
        assert data["message"] == "SQL injection attempt"
        assert data["client_ip"] == "10.0.0.1"
        assert data["details"]["pattern"] == "DROP TABLE"
        assert data["version"] == "1.0"
    
    def test_event_to_json(self):
        """Test event serialization to JSON"""
        event = SecurityEvent(
            event_type=SecurityEventType.AUTHENTICATION_SUCCESS,
            severity=SecuritySeverity.INFO,
            message="User logged in",
            timestamp="2026-02-17T10:00:00Z"
        )
        
        json_str = event.to_json()
        data = json.loads(json_str)
        
        assert data["event_type"] == "auth.success"
        assert data["severity"] == "info"
        assert data["message"] == "User logged in"
        assert "event_hash" in data


class TestSecurityAuditLogger:
    """Test the SecurityAuditLogger class"""
    
    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger for testing"""
        with patch("masterclaw_core.audit_logger.logging.getLogger") as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            yield mock_logger
    
    def test_auth_success_logging(self, mock_logger):
        """Test authentication success logging"""
        logger = SecurityAuditLogger()
        
        with patch.object(logger, 'logger', mock_logger):
            logger.auth_success(
                message="API key validated",
                client_ip="192.168.1.100",
                request_id="req-123"
            )
            
            assert mock_logger.log.called
            call_args = mock_logger.log.call_args
            assert call_args[0][0] == logging.INFO  # severity level
            
            # Parse the JSON message
            json_msg = call_args[0][1]
            data = json.loads(json_msg)
            assert data["event_type"] == "auth.success"
            assert data["severity"] == "info"
            assert data["message"] == "API key validated"
            assert data["client_ip"] == "192.168.1.100"
            assert data["request_id"] == "req-123"
    
    def test_auth_failure_logging(self, mock_logger):
        """Test authentication failure logging"""
        logger = SecurityAuditLogger()
        
        with patch.object(logger, 'logger', mock_logger):
            logger.auth_failure(
                message="Invalid API key provided",
                client_ip="192.168.1.100",
                request_id="req-456",
                severity=SecuritySeverity.HIGH
            )
            
            call_args = mock_logger.log.call_args
            assert call_args[0][0] == logging.ERROR  # HIGH severity = ERROR level
            
            data = json.loads(call_args[0][1])
            assert data["event_type"] == "auth.failure"
            assert data["severity"] == "high"
    
    def test_rate_limit_logging(self, mock_logger):
        """Test rate limit exceeded logging"""
        logger = SecurityAuditLogger()
        
        with patch.object(logger, 'logger', mock_logger):
            logger.rate_limit_exceeded(
                message="Rate limit exceeded: 100/60 requests",
                client_ip="10.0.0.50",
                request_id="req-789",
                details={"limit": 60, "window": "60s", "current": 100}
            )
            
            call_args = mock_logger.log.call_args
            assert call_args[0][0] == logging.INFO  # LOW severity
            
            data = json.loads(call_args[0][1])
            assert data["event_type"] == "rate_limit.exceeded"
            assert data["details"]["limit"] == 60
            assert data["details"]["current"] == 100
    
    def test_suspicious_activity_logging(self, mock_logger):
        """Test suspicious activity logging"""
        logger = SecurityAuditLogger()
        
        with patch.object(logger, 'logger', mock_logger):
            logger.suspicious_activity(
                message="Path traversal attempt detected",
                client_ip="192.168.1.50",
                request_id="req-suspicious",
                details={"pattern": "../../etc/passwd", "field": "filename"},
                severity=SecuritySeverity.CRITICAL
            )
            
            call_args = mock_logger.log.call_args
            assert call_args[0][0] == logging.CRITICAL
            
            data = json.loads(call_args[0][1])
            assert data["event_type"] == "activity.suspicious"
            assert data["severity"] == "critical"
    
    def test_input_validation_failure(self, mock_logger):
        """Test input validation failure logging"""
        logger = SecurityAuditLogger()
        
        with patch.object(logger, 'logger', mock_logger):
            logger.input_validation_failed(
                message="XSS pattern detected in input",
                client_ip="192.168.1.75",
                details={"pattern": "<script>", "sanitized": True}
            )
            
            call_args = mock_logger.log.call_args
            data = json.loads(call_args[0][1])
            assert data["event_type"] == "input.validation_failed"
            assert data["action"] == "validate_input"
    
    def test_websocket_events(self, mock_logger):
        """Test WebSocket connection events"""
        logger = SecurityAuditLogger()
        
        with patch.object(logger, 'logger', mock_logger):
            # Test accepted connection
            logger.websocket_connected(
                message="WebSocket connection established",
                client_ip="192.168.1.100",
                resource="/v1/chat/stream/session-123"
            )
            
            call_args = mock_logger.log.call_args
            data = json.loads(call_args[0][1])
            assert data["event_type"] == "websocket.connected"
            
            # Test rejected connection
            logger.websocket_rejected(
                message="WebSocket connection rejected: too many connections",
                client_ip="192.168.1.100",
                severity=SecuritySeverity.MEDIUM
            )
            
            call_args = mock_logger.log.call_args
            data = json.loads(call_args[0][1])
            assert data["event_type"] == "websocket.rejected"
    
    def test_config_violation_logging(self, mock_logger):
        """Test configuration security violation logging"""
        logger = SecurityAuditLogger()
        
        with patch.object(logger, 'logger', mock_logger):
            logger.config_violation(
                message="CORS_ORIGINS set to '*' in production",
                details={"setting": "CORS_ORIGINS", "value": "*", "env": "production"}
            )
            
            call_args = mock_logger.log.call_args
            assert call_args[0][0] == logging.CRITICAL
            
            data = json.loads(call_args[0][1])
            assert data["event_type"] == "config.violation"
            assert data["severity"] == "critical"


class TestConvenienceFunctions:
    """Test convenience logging functions"""
    
    @patch.object(audit_logger, 'auth_failure')
    def test_log_auth_failure(self, mock_auth_failure):
        """Test auth failure convenience function"""
        log_auth_failure(
            message="Test failure",
            client_ip="192.168.1.1",
            request_id="req-1"
        )
        mock_auth_failure.assert_called_once_with(
            message="Test failure",
            client_ip="192.168.1.1",
            request_id="req-1"
        )
    
    @patch.object(audit_logger, 'rate_limit_exceeded')
    def test_log_rate_limit(self, mock_rate_limit):
        """Test rate limit convenience function"""
        log_rate_limit(message="Rate limited")
        mock_rate_limit.assert_called_once_with(message="Rate limited")
    
    @patch.object(audit_logger, 'suspicious_activity')
    def test_log_suspicious(self, mock_suspicious):
        """Test suspicious activity convenience function"""
        log_suspicious(message="Suspicious", client_ip="10.0.0.1")
        mock_suspicious.assert_called_once_with(
            message="Suspicious",
            client_ip="10.0.0.1"
        )
    
    @patch.object(audit_logger, 'input_validation_failed')
    def test_log_input_validation(self, mock_validation):
        """Test input validation convenience function"""
        log_input_validation_failure(message="Invalid input")
        mock_validation.assert_called_once_with(message="Invalid input")


class TestSecurityEventAnalyzer:
    """Test security event analysis utilities"""
    
    def test_parse_valid_event(self):
        """Test parsing a valid security event JSON"""
        event = SecurityEvent(
            event_type=SecurityEventType.AUTHENTICATION_FAILURE,
            severity=SecuritySeverity.HIGH,
            message="Test event",
            timestamp="2026-02-17T10:00:00Z",
            client_ip="192.168.1.1",
            event_hash="abc123"
        )
        
        json_str = event.to_json()
        parsed = SecurityEventAnalyzer.parse_event(json_str)
        
        assert parsed is not None
        assert parsed.event_type == SecurityEventType.AUTHENTICATION_FAILURE
        assert parsed.severity == SecuritySeverity.HIGH
        assert parsed.message == "Test event"
        assert parsed.client_ip == "192.168.1.1"
    
    def test_parse_invalid_json(self):
        """Test parsing invalid JSON"""
        result = SecurityEventAnalyzer.parse_event("not valid json")
        assert result is None
    
    def test_parse_incomplete_event(self):
        """Test parsing event with missing required fields"""
        incomplete = '{"event_type": "auth.failure"}'
        result = SecurityEventAnalyzer.parse_event(incomplete)
        assert result is None
    
    def test_verify_event_integrity_valid(self):
        """Test integrity verification with valid hash"""
        event = SecurityEvent(
            event_type=SecurityEventType.AUTHENTICATION_SUCCESS,
            severity=SecuritySeverity.INFO,
            message="Login successful",
            timestamp="2026-02-17T10:00:00Z"
        )
        
        # Hash should be valid since it was just generated
        assert SecurityEventAnalyzer.verify_event_integrity(event) is True
    
    def test_verify_event_integrity_invalid(self):
        """Test integrity verification with tampered hash"""
        event = SecurityEvent(
            event_type=SecurityEventType.AUTHENTICATION_SUCCESS,
            severity=SecuritySeverity.INFO,
            message="Login successful",
            timestamp="2026-02-17T10:00:00Z",
            event_hash="tampered_hash"
        )
        
        # Tampered hash should fail verification
        assert SecurityEventAnalyzer.verify_event_integrity(event) is False
    
    def test_verify_event_integrity_modified_message(self):
        """Test that modifying message invalidates hash"""
        event = SecurityEvent(
            event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
            severity=SecuritySeverity.HIGH,
            message="Original message",
            timestamp="2026-02-17T10:00:00Z"
        )
        
        # Store original hash
        original_hash = event.event_hash
        
        # Modify message (simulating tampering)
        event.message = "Tampered message"
        
        # Verify with original hash should fail
        event.event_hash = original_hash
        assert SecurityEventAnalyzer.verify_event_integrity(event) is False


class TestSecurityEventEnums:
    """Test security event type and severity enums"""
    
    def test_event_type_values(self):
        """Test that event types have correct string values"""
        assert SecurityEventType.AUTHENTICATION_SUCCESS == "auth.success"
        assert SecurityEventType.AUTHENTICATION_FAILURE == "auth.failure"
        assert SecurityEventType.AUTHORIZATION_DENIED == "authz.denied"
        assert SecurityEventType.RATE_LIMIT_EXCEEDED == "rate_limit.exceeded"
        assert SecurityEventType.INPUT_VALIDATION_FAILED == "input.validation_failed"
        assert SecurityEventType.SESSION_INVALID == "session.invalid"
        assert SecurityEventType.WEBSOCKET_CONNECTION_ACCEPTED == "websocket.connected"
        assert SecurityEventType.WEBSOCKET_CONNECTION_REJECTED == "websocket.rejected"
        assert SecurityEventType.SUSPICIOUS_ACTIVITY == "activity.suspicious"
        assert SecurityEventType.CONFIG_SECURITY_VIOLATION == "config.violation"
    
    def test_severity_values(self):
        """Test severity enum values"""
        assert SecuritySeverity.CRITICAL == "critical"
        assert SecuritySeverity.HIGH == "high"
        assert SecuritySeverity.MEDIUM == "medium"
        assert SecuritySeverity.LOW == "low"
        assert SecuritySeverity.INFO == "info"
    
    def test_severity_comparison(self):
        """Test that severity levels can be compared"""
        severities = [
            SecuritySeverity.INFO,
            SecuritySeverity.LOW,
            SecuritySeverity.MEDIUM,
            SecuritySeverity.HIGH,
            SecuritySeverity.CRITICAL,
        ]
        
        # Verify order
        severity_order = {
            SecuritySeverity.INFO: 0,
            SecuritySeverity.LOW: 1,
            SecuritySeverity.MEDIUM: 2,
            SecuritySeverity.HIGH: 3,
            SecuritySeverity.CRITICAL: 4,
        }
        
        for i, sev in enumerate(severities):
            assert severity_order[sev] == i


class TestIntegrationScenarios:
    """Integration tests for realistic security scenarios"""
    
    def test_brute_force_attack_detection(self, mock_logger=None):
        """Test logging for potential brute force attack"""
        logger = SecurityAuditLogger()
        mock = Mock() if mock_logger is None else mock_logger
        
        with patch.object(logger, 'logger', mock):
            # Simulate multiple failed auth attempts
            for i in range(5):
                logger.auth_failure(
                    message=f"Failed login attempt {i+1}",
                    client_ip="192.168.1.100",
                    request_id=f"req-{i}",
                    severity=SecuritySeverity.HIGH if i >= 3 else SecuritySeverity.MEDIUM,
                    details={"attempt": i+1, "username": "admin"}
                )
            
            assert mock.log.call_count == 5
    
    def test_session_hijacking_attempt(self):
        """Test logging for session-related security events"""
        logger = SecurityAuditLogger()
        mock = Mock()
        
        with patch.object(logger, 'logger', mock):
            # Invalid session ID attempt
            logger.session_invalid(
                message="Invalid session ID format: contains path traversal",
                client_ip="10.0.0.50",
                request_id="req-session",
                resource="/v1/sessions/../../../etc/passwd",
                details={"session_id": "../../../etc/passwd", "reason": "path_traversal"}
            )
            
            call_args = mock.log.call_args
            data = json.loads(call_args[0][1])
            assert data["event_type"] == "session.invalid"
            assert "path_traversal" in data["details"]["reason"]

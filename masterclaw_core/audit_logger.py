"""Security audit logging for MasterClaw Core

Provides structured, machine-parseable logging for security events to enable
security monitoring, incident response, and compliance auditing.

Features:
- Structured JSON logging for security events
- Standardized event types and severity levels
- Automatic correlation with request IDs
- Tamper-evident audit trail format
- Integration with existing logging infrastructure
"""

import json
import logging
import hashlib
import time
from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from dataclasses import dataclass, asdict


logger = logging.getLogger("masterclaw.security")


class SecurityEventType(str, Enum):
    """Standardized security event types for consistent monitoring"""
    AUTHENTICATION_SUCCESS = "auth.success"
    AUTHENTICATION_FAILURE = "auth.failure"
    AUTHORIZATION_DENIED = "authz.denied"
    RATE_LIMIT_EXCEEDED = "rate_limit.exceeded"
    INPUT_VALIDATION_FAILED = "input.validation_failed"
    SESSION_INVALID = "session.invalid"
    WEBSOCKET_CONNECTION_ACCEPTED = "websocket.connected"
    WEBSOCKET_CONNECTION_REJECTED = "websocket.rejected"
    SUSPICIOUS_ACTIVITY = "activity.suspicious"
    CONFIG_SECURITY_VIOLATION = "config.violation"


class SecuritySeverity(str, Enum):
    """Security event severity levels"""
    CRITICAL = "critical"    # Immediate action required
    HIGH = "high"           # Urgent attention needed
    MEDIUM = "medium"       # Review required
    LOW = "low"             # Informational
    INFO = "info"           # Audit trail only


@dataclass
class SecurityEvent:
    """Structured security event for audit logging
    
    Attributes:
        event_type: The type of security event
        severity: Severity level of the event
        message: Human-readable description
        timestamp: ISO format timestamp
        request_id: Request ID for correlation
        client_ip: Client IP address
        user_agent: Client user agent string
        resource: The resource being accessed
        action: The action attempted
        details: Additional event-specific details
        event_hash: Tamper-evident hash of the event
    """
    event_type: SecurityEventType
    severity: SecuritySeverity
    message: str
    timestamp: str
    request_id: Optional[str] = None
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    resource: Optional[str] = None
    action: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    event_hash: Optional[str] = None
    
    def __post_init__(self):
        """Generate tamper-evident hash for the event"""
        if not self.event_hash:
            self.event_hash = self._generate_hash()
    
    def _generate_hash(self) -> str:
        """Generate a hash of ALL event fields for comprehensive tamper detection.

        SECURITY FIX: Previously only timestamp, event_type, severity, and message
        were included in the hash. This allowed attackers to modify client_ip,
        resource, action, details, and other fields without detection.

        Now includes all fields to provide true tamper-evident audit trails.
        """
        # Include all fields in deterministic order for consistent hashing
        data_parts = [
            self.timestamp,
            str(self.event_type),
            str(self.severity),
            self.message,
            self.request_id or "",
            self.client_ip or "",
            self.user_agent or "",
            self.resource or "",
            self.action or "",
            json.dumps(self.details, sort_keys=True) if self.details else "",
        ]
        data = "|".join(data_parts)
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for JSON serialization"""
        return {
            "event_type": self.event_type.value,
            "severity": self.severity.value,
            "message": self.message,
            "timestamp": self.timestamp,
            "request_id": self.request_id,
            "client_ip": self.client_ip,
            "user_agent": self.user_agent,
            "resource": self.resource,
            "action": self.action,
            "details": self.details or {},
            "event_hash": self.event_hash,
            "version": "1.0"
        }
    
    def to_json(self) -> str:
        """Serialize event to JSON string"""
        return json.dumps(self.to_dict(), default=str)


class SecurityAuditLogger:
    """Security audit logger with structured event logging
    
    Provides a centralized logging interface for all security-related events
    with consistent formatting, severity levels, and tamper-evident records.
    
    Usage:
        >>> audit_logger = SecurityAuditLogger()
        >>> audit_logger.auth_failure(
        ...     message="Invalid API key",
        ...     client_ip="192.168.1.100",
        ...     request_id="abc123"
        ... )
    """
    
    def __init__(self):
        self.logger = logging.getLogger("masterclaw.security.audit")
    
    def _create_event(
        self,
        event_type: SecurityEventType,
        severity: SecuritySeverity,
        message: str,
        request_id: Optional[str] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        resource: Optional[str] = None,
        action: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> SecurityEvent:
        """Create a security event with current timestamp"""
        return SecurityEvent(
            event_type=event_type,
            severity=severity,
            message=message,
            timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            request_id=request_id,
            client_ip=client_ip,
            user_agent=user_agent,
            resource=resource,
            action=action,
            details=details
        )
    
    def _log_event(self, event: SecurityEvent):
        """Log a security event at the appropriate level"""
        log_message = event.to_json()
        
        # Map severity to logging level
        severity_map = {
            SecuritySeverity.CRITICAL: logging.CRITICAL,
            SecuritySeverity.HIGH: logging.ERROR,
            SecuritySeverity.MEDIUM: logging.WARNING,
            SecuritySeverity.LOW: logging.INFO,
            SecuritySeverity.INFO: logging.INFO,
        }
        
        level = severity_map.get(event.severity, logging.INFO)
        self.logger.log(level, log_message)
    
    # ===================================================================
    # Predefined security event logging methods
    # ===================================================================
    
    def auth_success(
        self,
        message: str,
        client_ip: Optional[str] = None,
        request_id: Optional[str] = None,
        user_agent: Optional[str] = None,
        resource: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log successful authentication"""
        event = self._create_event(
            event_type=SecurityEventType.AUTHENTICATION_SUCCESS,
            severity=SecuritySeverity.INFO,
            message=message,
            request_id=request_id,
            client_ip=client_ip,
            user_agent=user_agent,
            resource=resource,
            action="authenticate",
            details=details
        )
        self._log_event(event)
    
    def auth_failure(
        self,
        message: str,
        client_ip: Optional[str] = None,
        request_id: Optional[str] = None,
        user_agent: Optional[str] = None,
        resource: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        severity: SecuritySeverity = SecuritySeverity.MEDIUM
    ):
        """Log authentication failure"""
        event = self._create_event(
            event_type=SecurityEventType.AUTHENTICATION_FAILURE,
            severity=severity,
            message=message,
            request_id=request_id,
            client_ip=client_ip,
            user_agent=user_agent,
            resource=resource,
            action="authenticate",
            details=details
        )
        self._log_event(event)
    
    def authorization_denied(
        self,
        message: str,
        client_ip: Optional[str] = None,
        request_id: Optional[str] = None,
        user_agent: Optional[str] = None,
        resource: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log authorization denial (access to resource not allowed)"""
        event = self._create_event(
            event_type=SecurityEventType.AUTHORIZATION_DENIED,
            severity=SecuritySeverity.HIGH,
            message=message,
            request_id=request_id,
            client_ip=client_ip,
            user_agent=user_agent,
            resource=resource,
            action="access",
            details=details
        )
        self._log_event(event)
    
    def rate_limit_exceeded(
        self,
        message: str,
        client_ip: Optional[str] = None,
        request_id: Optional[str] = None,
        resource: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log rate limit violation"""
        event = self._create_event(
            event_type=SecurityEventType.RATE_LIMIT_EXCEEDED,
            severity=SecuritySeverity.LOW,
            message=message,
            request_id=request_id,
            client_ip=client_ip,
            resource=resource,
            action="rate_limit_check",
            details=details
        )
        self._log_event(event)
    
    def input_validation_failed(
        self,
        message: str,
        client_ip: Optional[str] = None,
        request_id: Optional[str] = None,
        user_agent: Optional[str] = None,
        resource: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        severity: SecuritySeverity = SecuritySeverity.MEDIUM
    ):
        """Log input validation failure (potential injection attack)"""
        event = self._create_event(
            event_type=SecurityEventType.INPUT_VALIDATION_FAILED,
            severity=severity,
            message=message,
            request_id=request_id,
            client_ip=client_ip,
            user_agent=user_agent,
            resource=resource,
            action="validate_input",
            details=details
        )
        self._log_event(event)
    
    def session_invalid(
        self,
        message: str,
        client_ip: Optional[str] = None,
        request_id: Optional[str] = None,
        resource: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log invalid session ID attempt"""
        event = self._create_event(
            event_type=SecurityEventType.SESSION_INVALID,
            severity=SecuritySeverity.MEDIUM,
            message=message,
            request_id=request_id,
            client_ip=client_ip,
            resource=resource,
            action="session_validation",
            details=details
        )
        self._log_event(event)
    
    def websocket_connected(
        self,
        message: str,
        client_ip: Optional[str] = None,
        request_id: Optional[str] = None,
        resource: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log successful WebSocket connection"""
        event = self._create_event(
            event_type=SecurityEventType.WEBSOCKET_CONNECTION_ACCEPTED,
            severity=SecuritySeverity.INFO,
            message=message,
            request_id=request_id,
            client_ip=client_ip,
            resource=resource,
            action="websocket_connect",
            details=details
        )
        self._log_event(event)
    
    def websocket_rejected(
        self,
        message: str,
        client_ip: Optional[str] = None,
        request_id: Optional[str] = None,
        resource: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        severity: SecuritySeverity = SecuritySeverity.MEDIUM
    ):
        """Log rejected WebSocket connection"""
        event = self._create_event(
            event_type=SecurityEventType.WEBSOCKET_CONNECTION_REJECTED,
            severity=severity,
            message=message,
            request_id=request_id,
            client_ip=client_ip,
            resource=resource,
            action="websocket_connect",
            details=details
        )
        self._log_event(event)
    
    def suspicious_activity(
        self,
        message: str,
        client_ip: Optional[str] = None,
        request_id: Optional[str] = None,
        user_agent: Optional[str] = None,
        resource: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        severity: SecuritySeverity = SecuritySeverity.HIGH
    ):
        """Log suspicious activity (potential attack patterns)"""
        event = self._create_event(
            event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
            severity=severity,
            message=message,
            request_id=request_id,
            client_ip=client_ip,
            user_agent=user_agent,
            resource=resource,
            action="monitor",
            details=details
        )
        self._log_event(event)
    
    def config_violation(
        self,
        message: str,
        request_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log configuration security violation"""
        event = self._create_event(
            event_type=SecurityEventType.CONFIG_SECURITY_VIOLATION,
            severity=SecuritySeverity.CRITICAL,
            message=message,
            request_id=request_id,
            resource="config",
            action="security_check",
            details=details
        )
        self._log_event(event)


# Global security audit logger instance
audit_logger = SecurityAuditLogger()


# =============================================================================
# Convenience functions for direct import
# =============================================================================

def log_auth_failure(**kwargs):
    """Convenience function for logging authentication failures"""
    audit_logger.auth_failure(**kwargs)


def log_rate_limit(**kwargs):
    """Convenience function for logging rate limit violations"""
    audit_logger.rate_limit_exceeded(**kwargs)


def log_suspicious(**kwargs):
    """Convenience function for logging suspicious activity"""
    audit_logger.suspicious_activity(**kwargs)


def log_input_validation_failure(**kwargs):
    """Convenience function for logging input validation failures"""
    audit_logger.input_validation_failed(**kwargs)


# =============================================================================
# Security event analysis utilities
# =============================================================================

class SecurityEventAnalyzer:
    """Utilities for analyzing security events"""
    
    @staticmethod
    def parse_event(json_line: str) -> Optional[SecurityEvent]:
        """Parse a JSON log line back into a SecurityEvent"""
        try:
            data = json.loads(json_line)
            return SecurityEvent(
                event_type=SecurityEventType(data["event_type"]),
                severity=SecuritySeverity(data["severity"]),
                message=data["message"],
                timestamp=data["timestamp"],
                request_id=data.get("request_id"),
                client_ip=data.get("client_ip"),
                user_agent=data.get("user_agent"),
                resource=data.get("resource"),
                action=data.get("action"),
                details=data.get("details"),
                event_hash=data.get("event_hash")
            )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Failed to parse security event: {e}")
            return None
    
    @staticmethod
    def verify_event_integrity(event: SecurityEvent) -> bool:
        """Verify the integrity of a security event by checking its hash.

        SECURITY FIX: The previous implementation regenerated the hash from current
        values, which meant tampering would go undetected. Now we properly compare
        the stored hash against a freshly computed hash of current values.

        If any field has been modified since the event was created, the verification
        will fail because the recomputed hash won't match the stored original.

        Args:
            event: The SecurityEvent to verify

        Returns:
            True if the event integrity is intact, False if tampered
        """
        if not event.event_hash:
            return False  # No hash to verify against

        # Store the original hash (the one we're verifying against)
        stored_hash = event.event_hash

        # Temporarily clear the hash so _generate_hash computes from current values
        event.event_hash = None

        # Generate expected hash from CURRENT field values
        expected_hash = event._generate_hash()

        # Restore the stored hash
        event.event_hash = stored_hash

        # If current values don't produce the stored hash, event was tampered
        return stored_hash == expected_hash

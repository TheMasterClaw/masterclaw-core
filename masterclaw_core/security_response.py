#!/usr/bin/env python3
"""
Security Auto-Response System for MasterClaw Core

Automatically responds to detected security threats by:
- Temporarily blocking malicious IPs
- Rate limiting aggressive clients
- Alerting administrators of critical threats
- Maintaining a blocklist with automatic expiration

This module integrates with the security monitoring system to provide
automated defense-in-depth capabilities.
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Callable
import ipaddress

from .audit_logger import (
    SecurityAuditLogger, 
    SecurityEventType, 
    SecuritySeverity,
    audit_logger
)

logger = logging.getLogger("masterclaw.security.response")


class ResponseAction(str, Enum):
    """Available auto-response actions"""
    BLOCK_IP = "block_ip"                    # Temporarily block IP address
    RATE_LIMIT = "rate_limit"                # Apply stricter rate limiting
    ALERT_ADMIN = "alert_admin"              # Send alert to administrators
    LOG_ENHANCED = "log_enhanced"            # Enable enhanced logging
    SESSION_INVALIDATE = "session_invalidate"  # Invalidate active sessions
    NONE = "none"                            # No action (monitoring only)


class BlockReason(str, Enum):
    """Reasons for blocking an IP"""
    BRUTE_FORCE = "brute_force"
    RATE_LIMIT_VIOLATION = "rate_limit_violation"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    ERROR_SPIKE = "error_spike"
    MANUAL = "manual"


@dataclass
class BlockedIP:
    """Represents a blocked IP address"""
    ip_address: str
    blocked_at: datetime
    expires_at: datetime
    reason: BlockReason
    threat_level: str
    related_events: List[str]
    blocked_by: str  # 'auto' or manual username
    
    def is_expired(self) -> bool:
        """Check if the block has expired"""
        return datetime.utcnow() >= self.expires_at
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            "ip_address": self.ip_address,
            "blocked_at": self.blocked_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "reason": self.reason.value,
            "threat_level": self.threat_level,
            "related_events": self.related_events,
            "blocked_by": self.blocked_by,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "BlockedIP":
        """Create from dictionary"""
        return cls(
            ip_address=data["ip_address"],
            blocked_at=datetime.fromisoformat(data["blocked_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]),
            reason=BlockReason(data["reason"]),
            threat_level=data["threat_level"],
            related_events=data.get("related_events", []),
            blocked_by=data.get("blocked_by", "auto"),
        )


@dataclass
class ResponseRule:
    """Rule defining when to trigger a response action"""
    name: str
    threat_types: List[str]  # Threat types that trigger this rule
    min_severity: SecuritySeverity
    action: ResponseAction
    block_duration_minutes: int = 60
    cooldown_minutes: int = 5  # Minimum time between repeated actions
    enabled: bool = True
    
    def should_trigger(self, threat_type: str, severity: SecuritySeverity) -> bool:
        """Check if this rule should trigger for a threat"""
        if not self.enabled:
            return False
        
        if threat_type not in self.threat_types:
            return False
        
        severity_levels = {
            SecuritySeverity.INFO: 0,
            SecuritySeverity.LOW: 1,
            SecuritySeverity.MEDIUM: 2,
            SecuritySeverity.HIGH: 3,
            SecuritySeverity.CRITICAL: 4,
        }
        
        return severity_levels.get(severity, 0) >= severity_levels.get(self.min_severity, 0)


class SecurityAutoResponder:
    """
    Automated security response system.
    
    Provides automatic defense mechanisms against detected threats:
    - IP blocking with automatic expiration
    - Configurable response rules
    - Alert notifications
    - Audit logging of all responses
    
    Usage:
        >>> responder = SecurityAutoResponder()
        >>> await responder.initialize()
        >>> await responder.handle_threat(threat_data)
    """
    
    DEFAULT_BLOCKLIST_PATH = Path("/data/security/blocklist.json")
    DEFAULT_RULES_PATH = Path("/data/security/response_rules.json")
    
    # Default response rules
    DEFAULT_RULES = [
        ResponseRule(
            name="critical_threat_block",
            threat_types=["privilege_escalation", "config_drift"],
            min_severity=SecuritySeverity.CRITICAL,
            action=ResponseAction.BLOCK_IP,
            block_duration_minutes=240,  # 4 hours
        ),
        ResponseRule(
            name="brute_force_protection",
            threat_types=["brute_force"],
            min_severity=SecuritySeverity.HIGH,
            action=ResponseAction.BLOCK_IP,
            block_duration_minutes=120,  # 2 hours
        ),
        ResponseRule(
            name="rate_limit_enforcement",
            threat_types=["rate_limit_violation"],
            min_severity=SecuritySeverity.MEDIUM,
            action=ResponseAction.RATE_LIMIT,
            block_duration_minutes=30,
        ),
        ResponseRule(
            name="suspicious_activity_alert",
            threat_types=["suspicious_pattern", "error_spike"],
            min_severity=SecuritySeverity.HIGH,
            action=ResponseAction.ALERT_ADMIN,
        ),
    ]
    
    def __init__(
        self,
        blocklist_path: Optional[Path] = None,
        rules_path: Optional[Path] = None,
        enabled: bool = True
    ):
        self.enabled = enabled and os.getenv("SECURITY_AUTO_RESPONSE", "true").lower() == "true"
        self.blocklist_path = blocklist_path or self.DEFAULT_BLOCKLIST_PATH
        self.rules_path = rules_path or self.DEFAULT_RULES_PATH
        
        self.blocked_ips: Dict[str, BlockedIP] = {}
        self.rules: List[ResponseRule] = []
        self._last_action_time: Dict[str, datetime] = {}  # Track cooldowns
        self._alert_handlers: List[Callable] = []
        
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def initialize(self):
        """Initialize the auto-responder"""
        if not self.enabled:
            logger.info("Security auto-response is disabled")
            return
        
        # Ensure directories exist
        self.blocklist_path.parent.mkdir(parents=True, exist_ok=True)
        self.rules_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing blocklist
        await self._load_blocklist()
        
        # Load or create default rules
        await self._load_rules()
        
        # Start cleanup task
        self._running = True
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
        
        logger.info(
            f"Security auto-responder initialized: "
            f"{len(self.blocked_ips)} IPs blocked, "
            f"{len(self.rules)} rules active"
        )
        
        # Log initialization event
        audit_logger.suspicious_activity(
            message="Security auto-responder initialized",
            severity=SecuritySeverity.INFO,
            details={
                "blocked_ips": len(self.blocked_ips),
                "active_rules": len(self.rules),
            }
        )
    
    async def shutdown(self):
        """Shutdown the auto-responder gracefully"""
        self._running = False
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Save state
        await self._save_blocklist()
        
        logger.info("Security auto-responder shutdown complete")
    
    async def _load_blocklist(self):
        """Load blocked IPs from disk"""
        if not self.blocklist_path.exists():
            return
        
        try:
            with open(self.blocklist_path, 'r') as f:
                data = json.load(f)
            
            for item in data.get("blocked_ips", []):
                try:
                    blocked = BlockedIP.from_dict(item)
                    if not blocked.is_expired():
                        self.blocked_ips[blocked.ip_address] = blocked
                except Exception as e:
                    logger.warning(f"Failed to load blocked IP entry: {e}")
            
            logger.debug(f"Loaded {len(self.blocked_ips)} active blocks from disk")
            
        except Exception as e:
            logger.error(f"Failed to load blocklist: {e}")
    
    async def _save_blocklist(self):
        """Save blocked IPs to disk"""
        try:
            data = {
                "updated_at": datetime.utcnow().isoformat(),
                "blocked_ips": [
                    ip.to_dict() for ip in self.blocked_ips.values()
                ],
            }
            
            # Write atomically
            temp_path = self.blocklist_path.with_suffix('.tmp')
            with open(temp_path, 'w') as f:
                json.dump(data, f, indent=2)
            temp_path.replace(self.blocklist_path)
            
            logger.debug(f"Saved {len(self.blocked_ips)} blocks to disk")
            
        except Exception as e:
            logger.error(f"Failed to save blocklist: {e}")
    
    async def _load_rules(self):
        """Load response rules from disk or create defaults"""
        if self.rules_path.exists():
            try:
                with open(self.rules_path, 'r') as f:
                    data = json.load(f)
                
                for rule_data in data.get("rules", []):
                    self.rules.append(ResponseRule(
                        name=rule_data["name"],
                        threat_types=rule_data["threat_types"],
                        min_severity=SecuritySeverity(rule_data["min_severity"]),
                        action=ResponseAction(rule_data["action"]),
                        block_duration_minutes=rule_data.get("block_duration_minutes", 60),
                        cooldown_minutes=rule_data.get("cooldown_minutes", 5),
                        enabled=rule_data.get("enabled", True),
                    ))
                
                logger.debug(f"Loaded {len(self.rules)} response rules from disk")
                
            except Exception as e:
                logger.error(f"Failed to load rules, using defaults: {e}")
                self.rules = self.DEFAULT_RULES.copy()
        else:
            self.rules = self.DEFAULT_RULES.copy()
            await self._save_rules()
    
    async def _save_rules(self):
        """Save response rules to disk"""
        try:
            data = {
                "updated_at": datetime.utcnow().isoformat(),
                "rules": [
                    {
                        "name": r.name,
                        "threat_types": r.threat_types,
                        "min_severity": r.min_severity.value,
                        "action": r.action.value,
                        "block_duration_minutes": r.block_duration_minutes,
                        "cooldown_minutes": r.cooldown_minutes,
                        "enabled": r.enabled,
                    }
                    for r in self.rules
                ],
            }
            
            with open(self.rules_path, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save rules: {e}")
    
    async def _periodic_cleanup(self):
        """Periodically clean up expired blocks"""
        while self._running:
            try:
                await asyncio.sleep(300)  # Clean up every 5 minutes
                
                if not self._running:
                    break
                
                expired = [
                    ip for ip, blocked in self.blocked_ips.items()
                    if blocked.is_expired()
                ]
                
                for ip in expired:
                    blocked = self.blocked_ips.pop(ip)
                    logger.info(f"Auto-unblocked expired IP: {ip} (reason: {blocked.reason.value})")
                    
                    # Log unblock event
                    audit_logger.suspicious_activity(
                        message=f"IP block expired and automatically removed: {ip}",
                        severity=SecuritySeverity.INFO,
                        details={
                            "ip_address": ip,
                            "block_reason": blocked.reason.value,
                            "blocked_duration_minutes": (
                                datetime.utcnow() - blocked.blocked_at
                            ).total_seconds() / 60,
                        }
                    )
                
                if expired:
                    await self._save_blocklist()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
    
    def is_ip_blocked(self, ip_address: str) -> bool:
        """Check if an IP address is currently blocked"""
        if ip_address in self.blocked_ips:
            blocked = self.blocked_ips[ip_address]
            if blocked.is_expired():
                # Clean up expired entry
                del self.blocked_ips[ip_address]
                return False
            return True
        return False
    
    def get_block_info(self, ip_address: str) -> Optional[BlockedIP]:
        """Get block information for an IP address"""
        return self.blocked_ips.get(ip_address)
    
    async def block_ip(
        self,
        ip_address: str,
        reason: BlockReason,
        duration_minutes: int = 60,
        threat_level: str = "medium",
        related_events: Optional[List[str]] = None,
        blocked_by: str = "auto"
    ) -> BlockedIP:
        """
        Block an IP address.
        
        Args:
            ip_address: The IP to block
            reason: Why the IP is being blocked
            duration_minutes: How long to block (0 = permanent)
            threat_level: Severity level of the threat
            related_events: IDs of related security events
            blocked_by: Who/what initiated the block
            
        Returns:
            The BlockedIP record
        """
        # Validate IP address
        try:
            ipaddress.ip_address(ip_address)
        except ValueError:
            raise ValueError(f"Invalid IP address: {ip_address}")
        
        now = datetime.utcnow()
        expires = now + timedelta(minutes=duration_minutes) if duration_minutes > 0 else None
        
        blocked = BlockedIP(
            ip_address=ip_address,
            blocked_at=now,
            expires_at=expires or datetime.max,
            reason=reason,
            threat_level=threat_level,
            related_events=related_events or [],
            blocked_by=blocked_by,
        )
        
        self.blocked_ips[ip_address] = blocked
        await self._save_blocklist()
        
        # Log the block action
        audit_logger.suspicious_activity(
            message=f"IP address blocked: {ip_address}",
            severity=SecuritySeverity.HIGH,
            details={
                "ip_address": ip_address,
                "reason": reason.value,
                "duration_minutes": duration_minutes,
                "threat_level": threat_level,
                "blocked_by": blocked_by,
            }
        )
        
        logger.warning(
            f"Blocked IP {ip_address} for {duration_minutes} minutes "
            f"(reason: {reason.value})"
        )
        
        return blocked
    
    async def unblock_ip(self, ip_address: str, unblocked_by: str = "manual") -> bool:
        """Unblock an IP address"""
        if ip_address not in self.blocked_ips:
            return False
        
        blocked = self.blocked_ips.pop(ip_address)
        await self._save_blocklist()
        
        # Log the unblock action
        audit_logger.suspicious_activity(
            message=f"IP address unblocked: {ip_address}",
            severity=SecuritySeverity.INFO,
            details={
                "ip_address": ip_address,
                "unblocked_by": unblocked_by,
                "original_reason": blocked.reason.value,
            }
        )
        
        logger.info(f"Unblocked IP {ip_address} (by: {unblocked_by})")
        return True
    
    async def handle_threat(self, threat_data: dict) -> Optional[ResponseAction]:
        """
        Process a detected threat and execute appropriate response.
        
        Args:
            threat_data: Threat information from security monitor
            
        Returns:
            The action taken, or None if no action
        """
        if not self.enabled:
            return None
        
        threat_type = threat_data.get("type", "")
        severity = SecuritySeverity(threat_data.get("level", "medium"))
        source = threat_data.get("source", "")
        
        # Find matching rules
        matching_rules = [
            r for r in self.rules
            if r.should_trigger(threat_type, severity)
        ]
        
        if not matching_rules:
            return None
        
        # Use the most aggressive rule (highest severity action)
        # Priority: BLOCK_IP > SESSION_INVALIDATE > RATE_LIMIT > ALERT_ADMIN > LOG_ENHANCED
        action_priority = {
            ResponseAction.BLOCK_IP: 5,
            ResponseAction.SESSION_INVALIDATE: 4,
            ResponseAction.RATE_LIMIT: 3,
            ResponseAction.ALERT_ADMIN: 2,
            ResponseAction.LOG_ENHANCED: 1,
            ResponseAction.NONE: 0,
        }
        
        rule = max(matching_rules, key=lambda r: action_priority.get(r.action, 0))
        
        # Check cooldown
        cooldown_key = f"{source}:{rule.action.value}"
        last_action = self._last_action_time.get(cooldown_key)
        if last_action:
            cooldown_end = last_action + timedelta(minutes=rule.cooldown_minutes)
            if datetime.utcnow() < cooldown_end:
                logger.debug(
                    f"Action {rule.action.value} for {source} in cooldown"
                )
                return None
        
        # Execute the action
        try:
            await self._execute_action(rule, threat_data)
            self._last_action_time[cooldown_key] = datetime.utcnow()
            return rule.action
            
        except Exception as e:
            logger.error(f"Failed to execute response action: {e}")
            return None
    
    async def _execute_action(self, rule: ResponseRule, threat_data: dict):
        """Execute a response action"""
        action = rule.action
        source = threat_data.get("source", "")
        
        if action == ResponseAction.BLOCK_IP:
            # Extract IP from source if it looks like an IP
            try:
                ipaddress.ip_address(source)
                await self.block_ip(
                    ip_address=source,
                    reason=BlockReason(threat_data.get("type", "suspicious_activity")),
                    duration_minutes=rule.block_duration_minutes,
                    threat_level=threat_data.get("level", "medium"),
                    related_events=threat_data.get("relatedEvents", []),
                )
            except ValueError:
                logger.warning(f"Cannot block non-IP source: {source}")
        
        elif action == ResponseAction.RATE_LIMIT:
            # Rate limiting is handled by middleware, we just log it
            audit_logger.rate_limit_exceeded(
                message=f"Enhanced rate limiting applied to {source}",
                severity=SecuritySeverity.MEDIUM,
                details={
                    "source": source,
                    "reason": threat_data.get("type"),
                    "duration_minutes": rule.block_duration_minutes,
                }
            )
        
        elif action == ResponseAction.ALERT_ADMIN:
            await self._send_alert(threat_data, rule)
        
        elif action == ResponseAction.LOG_ENHANCED:
            audit_logger.suspicious_activity(
                message=f"Enhanced logging enabled for {source}",
                severity=SecuritySeverity.LOW,
                details={
                    "source": source,
                    "threat_type": threat_data.get("type"),
                }
            )
        
        elif action == ResponseAction.SESSION_INVALIDATE:
            # Session invalidation would be implemented here
            # This requires integration with the session store
            logger.info(f"Session invalidation requested for {source}")
    
    async def _send_alert(self, threat_data: dict, rule: ResponseRule):
        """Send alert to administrators"""
        alert_message = {
            "timestamp": datetime.utcnow().isoformat(),
            "alert_type": "security_threat",
            "threat": threat_data,
            "action_taken": rule.action.value,
            "severity": threat_data.get("level", "unknown"),
        }
        
        # Log the alert
        logger.critical(f"SECURITY ALERT: {json.dumps(alert_message)}")
        
        # Call registered alert handlers
        for handler in self._alert_handlers:
            try:
                await handler(alert_message)
            except Exception as e:
                logger.error(f"Alert handler failed: {e}")
    
    def register_alert_handler(self, handler: Callable):
        """Register a handler for security alerts"""
        self._alert_handlers.append(handler)
    
    def get_stats(self) -> dict:
        """Get current auto-responder statistics"""
        now = datetime.utcnow()
        active_blocks = [
            b for b in self.blocked_ips.values() if not b.is_expired()
        ]
        
        return {
            "enabled": self.enabled,
            "active_rules": len([r for r in self.rules if r.enabled]),
            "total_rules": len(self.rules),
            "blocked_ips_total": len(self.blocked_ips),
            "blocked_ips_active": len(active_blocks),
            "block_reasons": {
                reason.value: len([
                    b for b in active_blocks if b.reason == reason
                ])
                for reason in BlockReason
            },
            "oldest_block": min(
                (b.blocked_at for b in active_blocks),
                default=None
            ),
        }
    
    def list_blocked_ips(self) -> List[BlockedIP]:
        """List all currently blocked IPs"""
        return [
            b for b in self.blocked_ips.values()
            if not b.is_expired()
        ]


# Global auto-responder instance
auto_responder = SecurityAutoResponder()


async def initialize_auto_responder():
    """Initialize the global auto-responder"""
    await auto_responder.initialize()


async def shutdown_auto_responder():
    """Shutdown the global auto-responder"""
    await auto_responder.shutdown()


def is_ip_blocked(ip_address: str) -> bool:
    """Check if an IP is blocked (convenience function)"""
    return auto_responder.is_ip_blocked(ip_address)


def get_block_info(ip_address: str) -> Optional[BlockedIP]:
    """Get block info for an IP (convenience function)"""
    return auto_responder.get_block_info(ip_address)

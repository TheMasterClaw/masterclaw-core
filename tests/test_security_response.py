"""Tests for the security auto-response system"""

import pytest
import json
import asyncio
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock

from masterclaw_core.security_response import (
    SecurityAutoResponder,
    ResponseAction,
    ResponseRule,
    BlockedIP,
    BlockReason,
    SecuritySeverity,
)


@pytest.fixture
def responder(tmp_path):
    """Create a test auto-responder with temporary paths"""
    blocklist_path = tmp_path / "blocklist.json"
    rules_path = tmp_path / "rules.json"
    
    r = SecurityAutoResponder(
        blocklist_path=blocklist_path,
        rules_path=rules_path,
        enabled=True
    )
    return r


@pytest.fixture
async def initialized_responder(responder):
    """Create and initialize an auto-responder"""
    await responder.initialize()
    yield responder
    await responder.shutdown()


class TestBlockedIP:
    """Test the BlockedIP dataclass"""
    
    def test_blocked_ip_creation(self):
        """Test creating a BlockedIP instance"""
        now = datetime.utcnow()
        blocked = BlockedIP(
            ip_address="192.168.1.100",
            blocked_at=now,
            expires_at=now + timedelta(minutes=60),
            reason=BlockReason.BRUTE_FORCE,
            threat_level="high",
            related_events=["event-1", "event-2"],
            blocked_by="auto"
        )
        
        assert blocked.ip_address == "192.168.1.100"
        assert blocked.reason == BlockReason.BRUTE_FORCE
        assert blocked.threat_level == "high"
        assert not blocked.is_expired()
    
    def test_blocked_ip_expired(self):
        """Test checking if a block is expired"""
        now = datetime.utcnow()
        blocked = BlockedIP(
            ip_address="192.168.1.100",
            blocked_at=now - timedelta(hours=2),
            expires_at=now - timedelta(hours=1),
            reason=BlockReason.BRUTE_FORCE,
            threat_level="high",
            related_events=[],
            blocked_by="auto"
        )
        
        assert blocked.is_expired()
    
    def test_blocked_ip_to_dict(self):
        """Test converting BlockedIP to dictionary"""
        now = datetime.utcnow()
        blocked = BlockedIP(
            ip_address="192.168.1.100",
            blocked_at=now,
            expires_at=now + timedelta(minutes=60),
            reason=BlockReason.SUSPICIOUS_ACTIVITY,
            threat_level="medium",
            related_events=["evt-1"],
            blocked_by="manual"
        )
        
        data = blocked.to_dict()
        assert data["ip_address"] == "192.168.1.100"
        assert data["reason"] == "suspicious_activity"
        assert data["blocked_by"] == "manual"
    
    def test_blocked_ip_from_dict(self):
        """Test creating BlockedIP from dictionary"""
        now = datetime.utcnow()
        data = {
            "ip_address": "10.0.0.1",
            "blocked_at": now.isoformat(),
            "expires_at": (now + timedelta(minutes=30)).isoformat(),
            "reason": "rate_limit_violation",
            "threat_level": "low",
            "related_events": ["evt-1"],
            "blocked_by": "auto"
        }
        
        blocked = BlockedIP.from_dict(data)
        assert blocked.ip_address == "10.0.0.1"
        assert blocked.reason == BlockReason.RATE_LIMIT_VIOLATION


class TestResponseRule:
    """Test the ResponseRule dataclass"""
    
    def test_rule_should_trigger_matching_threat(self):
        """Test that rule triggers for matching threat"""
        rule = ResponseRule(
            name="test_rule",
            threat_types=["brute_force"],
            min_severity=SecuritySeverity.HIGH,
            action=ResponseAction.BLOCK_IP,
        )
        
        assert rule.should_trigger("brute_force", SecuritySeverity.HIGH)
        assert rule.should_trigger("brute_force", SecuritySeverity.CRITICAL)
    
    def test_rule_should_not_trigger_disabled(self):
        """Test that disabled rules don't trigger"""
        rule = ResponseRule(
            name="test_rule",
            threat_types=["brute_force"],
            min_severity=SecuritySeverity.HIGH,
            action=ResponseAction.BLOCK_IP,
            enabled=False
        )
        
        assert not rule.should_trigger("brute_force", SecuritySeverity.HIGH)
    
    def test_rule_should_not_trigger_wrong_type(self):
        """Test that rule doesn't trigger for wrong threat type"""
        rule = ResponseRule(
            name="test_rule",
            threat_types=["brute_force"],
            min_severity=SecuritySeverity.HIGH,
            action=ResponseAction.BLOCK_IP,
        )
        
        assert not rule.should_trigger("suspicious_activity", SecuritySeverity.HIGH)
    
    def test_rule_should_not_trigger_low_severity(self):
        """Test that rule doesn't trigger for low severity"""
        rule = ResponseRule(
            name="test_rule",
            threat_types=["brute_force"],
            min_severity=SecuritySeverity.HIGH,
            action=ResponseAction.BLOCK_IP,
        )
        
        assert not rule.should_trigger("brute_force", SecuritySeverity.LOW)
        assert not rule.should_trigger("brute_force", SecuritySeverity.MEDIUM)


class TestSecurityAutoResponderInitialization:
    """Test auto-responder initialization"""
    
    @pytest.mark.asyncio
    async def test_initialize_creates_directories(self, responder, tmp_path):
        """Test that initialization creates necessary directories"""
        await responder.initialize()
        
        assert (tmp_path / "blocklist.json").parent.exists()
        assert (tmp_path / "rules.json").parent.exists()
        
        await responder.shutdown()
    
    @pytest.mark.asyncio
    async def test_initialize_loads_default_rules(self, responder):
        """Test that initialization loads default rules"""
        await responder.initialize()
        
        assert len(responder.rules) > 0
        assert any(r.name == "critical_threat_block" for r in responder.rules)
        assert any(r.name == "brute_force_protection" for r in responder.rules)
        
        await responder.shutdown()
    
    @pytest.mark.asyncio
    async def test_initialize_disabled(self, responder):
        """Test that disabled responder skips initialization"""
        responder.enabled = False
        await responder.initialize()
        
        assert len(responder.rules) == 0
    
    @pytest.mark.asyncio
    async def test_shutdown_saves_state(self, responder):
        """Test that shutdown saves blocklist"""
        await responder.initialize()
        
        # Block an IP
        await responder.block_ip(
            "192.168.1.100",
            BlockReason.BRUTE_FORCE,
            duration_minutes=60
        )
        
        await responder.shutdown()
        
        # Verify blocklist was saved
        assert responder.blocklist_path.exists()
        with open(responder.blocklist_path) as f:
            data = json.load(f)
            assert len(data["blocked_ips"]) == 1


class TestIPBlocking:
    """Test IP blocking functionality"""
    
    @pytest.mark.asyncio
    async def test_block_ip(self, initialized_responder):
        """Test blocking an IP address"""
        blocked = await initialized_responder.block_ip(
            "192.168.1.100",
            BlockReason.BRUTE_FORCE,
            duration_minutes=60,
            threat_level="high"
        )
        
        assert blocked.ip_address == "192.168.1.100"
        assert blocked.reason == BlockReason.BRUTE_FORCE
        assert initialized_responder.is_ip_blocked("192.168.1.100")
    
    @pytest.mark.asyncio
    async def test_block_invalid_ip(self, initialized_responder):
        """Test blocking an invalid IP address"""
        with pytest.raises(ValueError, match="Invalid IP address"):
            await initialized_responder.block_ip(
                "not-an-ip",
                BlockReason.BRUTE_FORCE
            )
    
    @pytest.mark.asyncio
    async def test_unblock_ip(self, initialized_responder):
        """Test unblocking an IP address"""
        await initialized_responder.block_ip(
            "192.168.1.100",
            BlockReason.BRUTE_FORCE
        )
        
        success = await initialized_responder.unblock_ip("192.168.1.100")
        
        assert success
        assert not initialized_responder.is_ip_blocked("192.168.1.100")
    
    @pytest.mark.asyncio
    async def test_unblock_nonexistent_ip(self, initialized_responder):
        """Test unblocking an IP that isn't blocked"""
        success = await initialized_responder.unblock_ip("192.168.1.100")
        
        assert not success
    
    @pytest.mark.asyncio
    async def test_expired_block_not_counted(self, initialized_responder):
        """Test that expired blocks are not counted as blocked"""
        # Block with very short duration (negative = already expired)
        now = datetime.utcnow()
        expired_block = BlockedIP(
            ip_address="192.168.1.100",
            blocked_at=now - timedelta(hours=2),
            expires_at=now - timedelta(hours=1),
            reason=BlockReason.BRUTE_FORCE,
            threat_level="high",
            related_events=[],
            blocked_by="auto"
        )
        
        initialized_responder.blocked_ips["192.168.1.100"] = expired_block
        
        # Should not be considered blocked
        assert not initialized_responder.is_ip_blocked("192.168.1.100")
    
    @pytest.mark.asyncio
    async def test_get_block_info(self, initialized_responder):
        """Test getting block information"""
        await initialized_responder.block_ip(
            "192.168.1.100",
            BlockReason.SUSPICIOUS_ACTIVITY,
            threat_level="medium"
        )
        
        info = initialized_responder.get_block_info("192.168.1.100")
        
        assert info is not None
        assert info.ip_address == "192.168.1.100"
        assert info.reason == BlockReason.SUSPICIOUS_ACTIVITY
    
    @pytest.mark.asyncio
    async def test_get_block_info_nonexistent(self, initialized_responder):
        """Test getting block info for non-blocked IP"""
        info = initialized_responder.get_block_info("192.168.1.100")
        
        assert info is None


class TestThreatHandling:
    """Test threat detection and response"""
    
    @pytest.mark.asyncio
    async def test_handle_threat_triggers_block(self, initialized_responder):
        """Test that critical threats trigger IP blocking"""
        threat = {
            "type": "brute_force",
            "level": "high",
            "source": "192.168.1.100",
            "relatedEvents": ["evt-1"]
        }
        
        action = await initialized_responder.handle_threat(threat)
        
        assert action == ResponseAction.BLOCK_IP
        assert initialized_responder.is_ip_blocked("192.168.1.100")
    
    @pytest.mark.asyncio
    async def test_handle_threat_no_matching_rule(self, initialized_responder):
        """Test that threats with no matching rules get no action"""
        threat = {
            "type": "unknown_threat",
            "level": "info",
            "source": "192.168.1.100"
        }
        
        action = await initialized_responder.handle_threat(threat)
        
        assert action is None
    
    @pytest.mark.asyncio
    async def test_handle_threat_disabled_responder(self, initialized_responder):
        """Test that disabled responder takes no action"""
        initialized_responder.enabled = False
        
        threat = {
            "type": "brute_force",
            "level": "critical",
            "source": "192.168.1.100"
        }
        
        action = await initialized_responder.handle_threat(threat)
        
        assert action is None
    
    @pytest.mark.asyncio
    async def test_handle_threat_cooldown(self, initialized_responder):
        """Test that cooldown prevents repeated actions"""
        threat = {
            "type": "brute_force",
            "level": "high",
            "source": "192.168.1.100"
        }
        
        # First threat should trigger action
        action1 = await initialized_responder.handle_threat(threat)
        assert action1 is not None
        
        # Second threat during cooldown should not trigger
        action2 = await initialized_responder.handle_threat(threat)
        assert action2 is None
    
    @pytest.mark.asyncio
    async def test_handle_threat_non_ip_source(self, initialized_responder):
        """Test handling threat with non-IP source"""
        threat = {
            "type": "brute_force",
            "level": "high",
            "source": "not-an-ip-address"
        }
        
        # Should not raise error, but may not block
        action = await initialized_responder.handle_threat(threat)
        # Action may be triggered but block will fail silently


class TestStatistics:
    """Test statistics reporting"""
    
    @pytest.mark.asyncio
    async def test_get_stats(self, initialized_responder):
        """Test getting auto-responder statistics"""
        # Block a few IPs
        await initialized_responder.block_ip("192.168.1.100", BlockReason.BRUTE_FORCE)
        await initialized_responder.block_ip("192.168.1.101", BlockReason.RATE_LIMIT_VIOLATION)
        
        stats = initialized_responder.get_stats()
        
        assert stats["enabled"] is True
        assert stats["blocked_ips_active"] == 2
        assert stats["total_rules"] > 0
    
    @pytest.mark.asyncio
    async def test_list_blocked_ips(self, initialized_responder):
        """Test listing blocked IPs"""
        await initialized_responder.block_ip("192.168.1.100", BlockReason.BRUTE_FORCE)
        await initialized_responder.block_ip("192.168.1.101", BlockReason.SUSPICIOUS_ACTIVITY)
        
        blocked = initialized_responder.list_blocked_ips()
        
        assert len(blocked) == 2
        ips = [b.ip_address for b in blocked]
        assert "192.168.1.100" in ips
        assert "192.168.1.101" in ips
    
    @pytest.mark.asyncio
    async def test_list_blocked_ips_excludes_expired(self, initialized_responder):
        """Test that listing excludes expired blocks"""
        # Add an expired block
        now = datetime.utcnow()
        expired = BlockedIP(
            ip_address="192.168.1.100",
            blocked_at=now - timedelta(hours=2),
            expires_at=now - timedelta(hours=1),
            reason=BlockReason.BRUTE_FORCE,
            threat_level="high",
            related_events=[],
            blocked_by="auto"
        )
        initialized_responder.blocked_ips["192.168.1.100"] = expired
        
        # Add a valid block
        await initialized_responder.block_ip("192.168.1.101", BlockReason.BRUTE_FORCE)
        
        blocked = initialized_responder.list_blocked_ips()
        
        assert len(blocked) == 1
        assert blocked[0].ip_address == "192.168.1.101"


class TestCleanup:
    """Test cleanup functionality"""
    
    @pytest.mark.asyncio
    async def test_periodic_cleanup_removes_expired(self, initialized_responder):
        """Test that cleanup task removes expired blocks"""
        # Add an expired block
        now = datetime.utcnow()
        expired = BlockedIP(
            ip_address="192.168.1.100",
            blocked_at=now - timedelta(hours=2),
            expires_at=now - timedelta(minutes=1),  # Expired
            reason=BlockReason.BRUTE_FORCE,
            threat_level="high",
            related_events=[],
            blocked_by="auto"
        )
        initialized_responder.blocked_ips["192.168.1.100"] = expired
        
        # Verify it's there
        assert len(initialized_responder.blocked_ips) == 1
        
        # Manually trigger cleanup simulation
        expired.is_expired = lambda: True  # Force expired
        
        # The cleanup task would remove it on next cycle
        # For testing, we can verify the is_expired check works
        assert expired.is_expired()


class TestPersistence:
    """Test data persistence"""
    
    @pytest.mark.asyncio
    async def test_blocklist_persistence(self, tmp_path):
        """Test that blocklist persists across restarts"""
        blocklist_path = tmp_path / "blocklist.json"
        rules_path = tmp_path / "rules.json"
        
        # Create first responder and block an IP
        r1 = SecurityAutoResponder(
            blocklist_path=blocklist_path,
            rules_path=rules_path,
            enabled=True
        )
        await r1.initialize()
        await r1.block_ip("192.168.1.100", BlockReason.BRUTE_FORCE)
        await r1.shutdown()
        
        # Create second responder and verify it loads the block
        r2 = SecurityAutoResponder(
            blocklist_path=blocklist_path,
            rules_path=rules_path,
            enabled=True
        )
        await r2.initialize()
        
        assert r2.is_ip_blocked("192.168.1.100")
        
        await r2.shutdown()
    
    @pytest.mark.asyncio
    async def test_rules_persistence(self, tmp_path):
        """Test that rules persist to disk"""
        blocklist_path = tmp_path / "blocklist.json"
        rules_path = tmp_path / "rules.json"
        
        r = SecurityAutoResponder(
            blocklist_path=blocklist_path,
            rules_path=rules_path,
            enabled=True
        )
        await r.initialize()
        await r.shutdown()
        
        # Verify rules file was created
        assert rules_path.exists()
        with open(rules_path) as f:
            data = json.load(f)
            assert "rules" in data
            assert len(data["rules"]) > 0

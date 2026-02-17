import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware
from unittest.mock import MagicMock, AsyncMock, patch
import time

from masterclaw_core.middleware import (
    RequestLoggingMiddleware, RateLimitMiddleware, SecurityHeadersMiddleware,
    require_api_key, sanitize_input, safe_compare_keys, SQL_INJECTION_PATTERN,
    XSS_PATTERN, PATH_TRAVERSAL_PATTERN
)


class TestSecurityHeadersMiddleware:
    """Test security headers middleware"""
    
    def test_security_headers_added(self):
        """Test that security headers are added to responses"""
        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)
        
        @app.get("/")
        def root():
            return {"message": "test"}
            
        client = TestClient(app)
        response = client.get("/")
        
        assert response.status_code == 200
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["X-XSS-Protection"] == "1; mode=block"
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert "default-src 'self'" in response.headers["Content-Security-Policy"]


class TestRequestLoggingMiddleware:
    """Test request logging middleware"""
    
    def test_response_time_header(self):
        """Test that response time header is added"""
        app = FastAPI()
        app.add_middleware(RequestLoggingMiddleware)
        
        @app.get("/")
        def root():
            return {"message": "test"}
            
        client = TestClient(app)
        response = client.get("/")
        
        assert response.status_code == 200
        assert "X-Response-Time" in response.headers
        # Verify it's a valid time format (e.g., "0.123s")
        time_str = response.headers["X-Response-Time"]
        assert time_str.endswith("s")
        assert float(time_str.rstrip("s")) >= 0
        
    def test_error_logging(self):
        """Test that errors are logged"""
        app = FastAPI()
        app.add_middleware(RequestLoggingMiddleware)
        
        @app.get("/error")
        def error_route():
            raise ValueError("Test error")
            
        client = TestClient(app)
        response = client.get("/error")
        
        assert response.status_code == 500


class TestRateLimitMiddleware:
    """Test rate limiting middleware"""
    
    def test_rate_limit_headers(self):
        """Test that rate limit headers are added"""
        app = FastAPI()
        app.add_middleware(RateLimitMiddleware, requests_per_minute=10)
        
        @app.get("/")
        def root():
            return {"message": "test"}
            
        client = TestClient(app)
        response = client.get("/")
        
        assert response.status_code == 200
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers
        assert response.headers["X-RateLimit-Limit"] == "10"
        
    def test_rate_limit_enforced(self):
        """Test that rate limit is enforced"""
        app = FastAPI()
        app.add_middleware(RateLimitMiddleware, requests_per_minute=2)
        
        @app.get("/")
        def root():
            return {"message": "test"}
            
        client = TestClient(app)
        
        # Make requests up to limit
        response1 = client.get("/")
        assert response1.status_code == 200
        
        response2 = client.get("/")
        assert response2.status_code == 200
        
        # Third request should be rate limited
        response3 = client.get("/")
        assert response3.status_code == 429
        data = response3.json()
        assert data["code"] == "RATE_LIMIT_EXCEEDED"
        assert "retry_after" in data
        
        # Check rate limit headers on 429 response
        assert response3.headers.get("Retry-After") is not None
        assert response3.headers["X-RateLimit-Remaining"] == "0"
        
    def test_x_forwarded_for(self):
        """Test that X-Forwarded-For header is respected"""
        app = FastAPI()
        app.add_middleware(RateLimitMiddleware, requests_per_minute=1)
        
        @app.get("/")
        def root():
            return {"message": "test"}
            
        client = TestClient(app)
        
        # Request from different IPs should have separate limits
        response1 = client.get("/", headers={"X-Forwarded-For": "1.2.3.4"})
        assert response1.status_code == 200
        
        # Same IP again should be rate limited
        response2 = client.get("/", headers={"X-Forwarded-For": "1.2.3.4"})
        assert response2.status_code == 429
        
        # Different IP should still work
        response3 = client.get("/", headers={"X-Forwarded-For": "5.6.7.8"})
        assert response3.status_code == 200
        
    def test_x_forwarded_for_chain(self):
        """Test that X-Forwarded-For chain takes first IP"""
        app = FastAPI()
        app.add_middleware(RateLimitMiddleware, requests_per_minute=1)
        
        @app.get("/")
        def root():
            return {"message": "test"}
            
        client = TestClient(app)
        
        # First IP in chain should be used
        response1 = client.get("/", headers={"X-Forwarded-For": "1.2.3.4, 5.6.7.8, 9.10.11.12"})
        assert response1.status_code == 200
        
        # Same first IP should be rate limited
        response2 = client.get("/", headers={"X-Forwarded-For": "1.2.3.4, 99.99.99.99"})
        assert response2.status_code == 429
        
        # Different first IP should work
        response3 = client.get("/", headers={"X-Forwarded-For": "5.6.7.8, 1.2.3.4"})
        assert response3.status_code == 200
        
    def test_cleanup_stale_entries(self):
        """Test that stale entries are cleaned up"""
        app = FastAPI()
        middleware = RateLimitMiddleware(
            app,
            requests_per_minute=10,
            window_seconds=1,  # 1 second window for testing
            cleanup_interval=5
        )
        app.add_middleware(RateLimitMiddleware, requests_per_minute=10, window_seconds=1)
        
        @app.get("/")
        def root():
            return {"message": "test"}
            
        client = TestClient(app)
        
        # Make a request
        response = client.get("/", headers={"X-Forwarded-For": "1.2.3.4"})
        assert response.status_code == 200
        
        # Wait for window to expire
        import time
        time.sleep(1.1)
        
        # Request should work again (old entries cleaned)
        response2 = client.get("/", headers={"X-Forwarded-For": "1.2.3.4"})
        assert response2.status_code == 200
        
    def test_rate_limiter_stats(self):
        """Test rate limiter statistics"""
        middleware = RateLimitMiddleware(
            None,
            requests_per_minute=60,
            window_seconds=60,
            max_ips_tracked=100
        )
        
        stats = middleware.get_stats()
        
        assert "tracked_ips" in stats
        assert "active_ips" in stats
        assert "total_requests_in_window" in stats
        assert "window_seconds" in stats
        assert "requests_per_minute" in stats
        assert "max_ips_tracked" in stats
        assert stats["window_seconds"] == 60
        assert stats["requests_per_minute"] == 60
        assert stats["max_ips_tracked"] == 100


class TestRequireAPIKey:
    """Test API key authentication decorator"""
    
    @pytest.mark.asyncio
    async def test_valid_api_key(self):
        """Test request with valid API key"""
        app = FastAPI()
        app.state.api_key = "test-api-key"
        
        @app.get("/protected")
        @require_api_key
        async def protected_route(request: Request):
            return {"message": "success"}
            
        client = TestClient(app)
        response = client.get("/protected", headers={"X-API-Key": "test-api-key"})
        
        assert response.status_code == 200
        
    @pytest.mark.asyncio
    async def test_invalid_api_key(self):
        """Test request with invalid API key"""
        app = FastAPI()
        app.state.api_key = "test-api-key"
        
        @app.get("/protected")
        @require_api_key
        async def protected_route(request: Request):
            return {"message": "success"}
            
        client = TestClient(app)
        response = client.get("/protected", headers={"X-API-Key": "wrong-key"})
        
        assert response.status_code == 401
        assert "Invalid" in response.json()["error"]
        
    @pytest.mark.asyncio
    async def test_missing_api_key(self):
        """Test request without API key"""
        app = FastAPI()
        app.state.api_key = "test-api-key"
        
        @app.get("/protected")
        @require_api_key
        async def protected_route(request: Request):
            return {"message": "success"}
            
        client = TestClient(app)
        response = client.get("/protected")
        
        assert response.status_code == 401
        
    @pytest.mark.asyncio
    async def test_no_api_key_configured(self):
        """Test that no API key required if not configured"""
        app = FastAPI()
        # No api_key set on app.state
        
        @app.get("/protected")
        @require_api_key
        async def protected_route(request: Request):
            return {"message": "success"}
            
        client = TestClient(app)
        response = client.get("/protected")
        
        # Should allow access when no API key is configured
        assert response.status_code == 200


class TestMiddlewareChaining:
    """Test that multiple middleware work together"""
    
    def test_all_middleware_applied(self):
        """Test that all middleware apply their headers"""
        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)
        app.add_middleware(RateLimitMiddleware, requests_per_minute=100)
        app.add_middleware(RequestLoggingMiddleware)
        
        @app.get("/")
        def root():
            return {"message": "test"}
            
        client = TestClient(app)
        response = client.get("/")
        
        assert response.status_code == 200
        # Check security headers
        assert "X-Frame-Options" in response.headers
        # Check rate limit headers
        assert "X-RateLimit-Limit" in response.headers
        # Check timing headers
        assert "X-Response-Time" in response.headers


# =============================================================================
# NEW SECURITY TESTS
# =============================================================================

class TestRequestIDTracking:
    """Test request ID generation and tracking"""
    
    def test_request_id_header_added(self):
        """Test that request ID is added to response headers"""
        app = FastAPI()
        app.add_middleware(RequestLoggingMiddleware)
        
        @app.get("/")
        def root():
            return {"message": "test"}
            
        client = TestClient(app)
        response = client.get("/")
        
        assert response.status_code == 200
        assert "X-Request-ID" in response.headers
        # Verify format (8 character hex)
        request_id = response.headers["X-Request-ID"]
        assert len(request_id) == 8
        assert all(c in "0123456789abcdef" for c in request_id)
        
    def test_request_id_preserved_from_header(self):
        """Test that provided request ID is preserved"""
        app = FastAPI()
        app.add_middleware(RequestLoggingMiddleware)
        
        @app.get("/")
        def root():
            return {"message": "test"}
            
        client = TestClient(app)
        custom_id = "abc12345"
        response = client.get("/", headers={"X-Request-ID": custom_id})
        
        assert response.headers["X-Request-ID"] == custom_id


class TestInputSanitization:
    """Test input sanitization utilities"""
    
    def test_sanitize_valid_input(self):
        """Test that valid input passes through unchanged"""
        valid_inputs = [
            "Hello world",
            "Python programming tips",
            "test@example.com",
            "https://example.com/path",
            "Normal text with numbers 123",
        ]
        for inp in valid_inputs:
            result = sanitize_input(inp)
            assert result == inp
    
    def test_sanitize_sql_injection(self):
        """Test that SQL injection patterns are rejected"""
        malicious_inputs = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "1 AND 1=1",
            "SELECT * FROM passwords",
            "UNION SELECT username, password FROM admin",
        ]
        for inp in malicious_inputs:
            with pytest.raises(ValueError, match="Potentially dangerous input"):
                sanitize_input(inp)
    
    def test_sanitize_xss_patterns(self):
        """Test that XSS patterns are rejected"""
        malicious_inputs = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img onerror=alert('xss')>",
            "<iframe src='evil.com'>",
        ]
        for inp in malicious_inputs:
            with pytest.raises(ValueError, match="Potentially dangerous input"):
                sanitize_input(inp)
    
    def test_sanitize_path_traversal(self):
        """Test that path traversal patterns are rejected"""
        malicious_inputs = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32\\config\\sam",
            "%2e%2e%2fetc%2fpasswd",
        ]
        for inp in malicious_inputs:
            with pytest.raises(ValueError, match="Potentially dangerous input"):
                sanitize_input(inp)
    
    def test_sanitize_max_length(self):
        """Test that max length is enforced"""
        long_input = "a" * 10001
        with pytest.raises(ValueError, match="exceeds maximum length"):
            sanitize_input(long_input, max_length=10000)
        
        # Should work at exactly max length
        exact_input = "a" * 10000
        result = sanitize_input(exact_input, max_length=10000)
        assert result == exact_input
    
    def test_sanitize_non_string_input(self):
        """Test that non-string inputs pass through unchanged"""
        assert sanitize_input(123) == 123
        assert sanitize_input(None) is None
        assert sanitize_input([1, 2, 3]) == [1, 2, 3]


class TestSafeKeyComparison:
    """Test timing-attack-safe key comparison"""
    
    def test_safe_compare_matching_keys(self):
        """Test that matching keys return True"""
        assert safe_compare_keys("secret", "secret") is True
        assert safe_compare_keys("a" * 100, "a" * 100) is True
    
    def test_safe_compare_different_keys(self):
        """Test that different keys return False"""
        assert safe_compare_keys("secret1", "secret2") is False
        assert safe_compare_keys("short", "muchlongerstring") is False
        assert safe_compare_keys("", "something") is False
    
    def test_safe_compare_none_keys(self):
        """Test handling of None keys"""
        assert safe_compare_keys(None, "secret") is False
        assert safe_compare_keys("secret", None) is False
        assert safe_compare_keys(None, None) is False
    
    def test_safe_compare_empty_keys(self):
        """Test handling of empty keys"""
        assert safe_compare_keys("", "") is False
        assert safe_compare_keys("", "secret") is False
    
    def test_safe_compare_timing_consistency(self):
        """Test that comparison takes roughly same time regardless of match position"""
        import time
        
        key = "a" * 50
        
        # Test different mismatch positions
        times = []
        for i in range(5):
            wrong_key = "a" * i + "b" + "a" * (49 - i)
            start = time.perf_counter()
            for _ in range(1000):
                safe_compare_keys(wrong_key, key)
            elapsed = time.perf_counter() - start
            times.append(elapsed)
        
        # All times should be reasonably similar (within 10x of each other)
        max_time = max(times)
        min_time = min(times)
        assert max_time / min_time < 10, "Timing variance suggests non-constant-time comparison"


class TestAPIKeySecurityImprovements:
    """Test API key security enhancements"""
    
    def test_malicious_api_key_rejected(self):
        """Test that API keys with suspicious content are rejected"""
        app = FastAPI()
        app.state.api_key = "valid-key"
        
        @app.get("/protected")
        @require_api_key
        async def protected_route(request: Request):
            return {"message": "success"}
            
        client = TestClient(app)
        
        # Try SQL injection in API key
        response = client.get("/protected", headers={"X-API-Key": "'; DROP TABLE--"})
        assert response.status_code == 401
        assert "Invalid API key format" in response.json()["error"]
    
    def test_request_id_in_error_response(self):
        """Test that request ID is included in error responses"""
        app = FastAPI()
        app.add_middleware(RequestLoggingMiddleware)
        
        @app.get("/error")
        def error_route():
            raise ValueError("Test error")
            
        client = TestClient(app)
        response = client.get("/error")
        
        assert response.status_code == 500
        assert "request_id" in response.json()
        assert len(response.json()["request_id"]) == 8


# =============================================================================
# HSTS Security Header Tests
# =============================================================================

class TestHSTSSecurityHeaders:
    """Test HTTP Strict Transport Security (HSTS) header functionality"""
    
    @patch.dict('os.environ', {'ENV': 'production'}, clear=True)
    def test_hsts_header_in_production(self):
        """Test that HSTS header is added in production environment"""
        app = FastAPI()
        # Create middleware instance after env patch to pick up production
        middleware = SecurityHeadersMiddleware(app)
        app.add_middleware(SecurityHeadersMiddleware)
        
        @app.get("/")
        def root():
            return {"message": "test"}
            
        client = TestClient(app)
        response = client.get("/")
        
        assert response.status_code == 200
        assert "Strict-Transport-Security" in response.headers
        hsts = response.headers["Strict-Transport-Security"]
        assert "max-age=31536000" in hsts  # Default 1 year
        assert "includeSubDomains" in hsts
        assert "preload" not in hsts  # Default is disabled
    
    @patch.dict('os.environ', {'ENV': 'development'}, clear=True)
    def test_hsts_header_not_in_development(self):
        """Test that HSTS header is NOT added in development environment"""
        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)
        
        @app.get("/")
        def root():
            return {"message": "test"}
            
        client = TestClient(app)
        response = client.get("/")
        
        assert response.status_code == 200
        assert "Strict-Transport-Security" not in response.headers
    
    @patch.dict('os.environ', {
        'ENV': 'production',
        'HSTS_MAX_AGE': '86400',
        'HSTS_INCLUDE_SUBDOMAINS': 'false',
        'HSTS_PRELOAD': 'true'
    }, clear=True)
    def test_hsts_custom_configuration(self):
        """Test HSTS with custom configuration values"""
        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)
        
        @app.get("/")
        def root():
            return {"message": "test"}
            
        client = TestClient(app)
        response = client.get("/")
        
        assert response.status_code == 200
        hsts = response.headers["Strict-Transport-Security"]
        assert "max-age=86400" in hsts  # Custom 1 day
        assert "includeSubDomains" not in hsts  # Disabled
        assert "preload" in hsts  # Enabled
    
    @patch.dict('os.environ', {
        'ENV': 'production',
        'HSTS_MAX_AGE': '63072000',  # 2 years (recommended for preload)
        'HSTS_INCLUDE_SUBDOMAINS': 'true',
        'HSTS_PRELOAD': 'true'
    }, clear=True)
    def test_hsts_preload_configuration(self):
        """Test HSTS with preload list configuration"""
        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)
        
        @app.get("/")
        def root():
            return {"message": "test"}
            
        client = TestClient(app)
        response = client.get("/")
        
        assert response.status_code == 200
        hsts = response.headers["Strict-Transport-Security"]
        assert "max-age=63072000" in hsts
        assert "includeSubDomains" in hsts
        assert "preload" in hsts
    
    @patch.dict('os.environ', {'NODE_ENV': 'production'}, clear=True)
    def test_hsts_with_node_env(self):
        """Test that HSTS works with NODE_ENV as well as ENV"""
        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)
        
        @app.get("/")
        def root():
            return {"message": "test"}
            
        client = TestClient(app)
        response = client.get("/")
        
        assert response.status_code == 200
        assert "Strict-Transport-Security" in response.headers
    
    @patch.dict('os.environ', {'ENV': 'prod'}, clear=True)
    def test_hsts_with_prod_short_form(self):
        """Test that HSTS works with 'prod' environment shorthand"""
        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)
        
        @app.get("/")
        def root():
            return {"message": "test"}
            
        client = TestClient(app)
        response = client.get("/")
        
        assert response.status_code == 200
        assert "Strict-Transport-Security" in response.headers
    
    def test_other_security_headers_preserved(self):
        """Test that other security headers are still present with HSTS"""
        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)
        
        @app.get("/")
        def root():
            return {"message": "test"}
            
        client = TestClient(app)
        response = client.get("/")
        
        assert response.status_code == 200
        # All original headers should still be present
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["X-XSS-Protection"] == "1; mode=block"
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert "default-src 'self'" in response.headers["Content-Security-Policy"]


class TestSecurityHeadersMiddlewareChaining:
    """Test that SecurityHeadersMiddleware works correctly with all other middleware"""
    
    @patch.dict('os.environ', {'ENV': 'production'}, clear=True)
    def test_all_security_headers_with_all_middleware(self):
        """Test all security headers are present with full middleware stack"""
        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)
        app.add_middleware(RateLimitMiddleware, requests_per_minute=100)
        app.add_middleware(RequestLoggingMiddleware)
        
        @app.get("/")
        def root():
            return {"message": "test"}
            
        client = TestClient(app)
        response = client.get("/")
        
        assert response.status_code == 200
        
        # Security headers
        assert "Strict-Transport-Security" in response.headers
        assert response.headers["X-Frame-Options"] == "DENY"
        assert "X-Content-Type-Options" in response.headers
        
        # Rate limiting headers
        assert "X-RateLimit-Limit" in response.headers
        
        # Request tracking headers
        assert "X-Response-Time" in response.headers
        assert "X-Request-ID" in response.headers

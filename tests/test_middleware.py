import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware
from unittest.mock import MagicMock, AsyncMock, patch
import time

from masterclaw_core.middleware import (
    RequestLoggingMiddleware, RateLimitMiddleware, SecurityHeadersMiddleware,
    require_api_key
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
        assert "Rate limit exceeded" in response3.json()["error"]
        
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

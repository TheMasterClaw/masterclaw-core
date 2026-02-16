"""Standalone test for the improved RateLimitMiddleware"""
import sys
import os
import time
import asyncio

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from masterclaw_core.middleware import RateLimitMiddleware

def test_rate_limiter_initialization():
    """Test that rate limiter initializes with correct parameters"""
    middleware = RateLimitMiddleware(
        None,
        requests_per_minute=100,
        window_seconds=120,
        max_ips_tracked=5000,
        cleanup_interval=500
    )
    
    assert middleware.requests_per_minute == 100
    assert middleware.window_seconds == 120
    assert middleware.max_ips_tracked == 5000
    assert middleware.cleanup_interval == 500
    assert middleware.requests == {}
    print("✓ Rate limiter initializes correctly")

def test_get_stats():
    """Test rate limiter statistics"""
    middleware = RateLimitMiddleware(
        None,
        requests_per_minute=60,
        window_seconds=60,
        max_ips_tracked=100
    )
    
    stats = middleware.get_stats()
    
    assert stats["tracked_ips"] == 0
    assert stats["active_ips"] == 0
    assert stats["total_requests_in_window"] == 0
    assert stats["window_seconds"] == 60
    assert stats["requests_per_minute"] == 60
    assert stats["max_ips_tracked"] == 100
    print("✓ Rate limiter stats work correctly")

def test_cleanup_stale_entries():
    """Test cleanup of stale entries"""
    middleware = RateLimitMiddleware(
        None,
        requests_per_minute=60,
        window_seconds=1,  # 1 second window for testing
        max_ips_tracked=100
    )
    
    current_time = time.time()
    
    # Add some entries
    middleware.requests["ip1"] = [(current_time, 1), (current_time - 0.5, 1)]
    middleware.requests["ip2"] = [(current_time - 2, 1)]  # Stale entry (older than 1s)
    middleware.requests["ip3"] = [(current_time - 0.8, 1)]  # Still valid
    
    assert len(middleware.requests) == 3
    
    # Run cleanup
    middleware._cleanup_stale_entries(current_time)
    
    # ip2 should be removed (stale), ip1 and ip3 should remain
    assert len(middleware.requests) == 2
    assert "ip1" in middleware.requests
    assert "ip2" not in middleware.requests
    assert "ip3" in middleware.requests
    # ip1 has 2 entries (both within window), ip3 has 1 entry
    assert len(middleware.requests["ip1"]) == 2
    assert len(middleware.requests["ip3"]) == 1
    print("✓ Stale entry cleanup works correctly")

def test_cleanup_max_ips():
    """Test cleanup when max IPs exceeded"""
    middleware = RateLimitMiddleware(
        None,
        requests_per_minute=60,
        window_seconds=60,
        max_ips_tracked=3
    )
    
    current_time = time.time()
    
    # Add 5 IPs (more than max)
    for i in range(5):
        middleware.requests[f"ip{i}"] = [(current_time - i, 1)]
    
    assert len(middleware.requests) == 5
    
    # Run cleanup
    middleware._cleanup_stale_entries(current_time)
    
    # Should be reduced to max_ips_tracked
    assert len(middleware.requests) == 3
    # ip0 should be kept (most recent), ip3 and ip4 should be removed
    assert "ip0" in middleware.requests
    assert "ip3" not in middleware.requests
    assert "ip4" not in middleware.requests
    print("✓ Max IPs cleanup works correctly")

def test_get_client_identifier():
    """Test client identifier extraction"""
    middleware = RateLimitMiddleware(None)
    
    # Create mock request
    class MockClient:
        host = "192.168.1.1"
    
    class MockRequest:
        headers = {}
        client = MockClient()
    
    request = MockRequest()
    
    # Without X-Forwarded-For, should use client host
    assert middleware._get_client_identifier(request) == "192.168.1.1"
    
    # With X-Forwarded-For, should use first IP
    request.headers = {"X-Forwarded-For": "10.0.0.1, 10.0.0.2, 10.0.0.3"}
    assert middleware._get_client_identifier(request) == "10.0.0.1"
    
    # With single IP in X-Forwarded-For
    request.headers = {"X-Forwarded-For": "10.0.0.5"}
    assert middleware._get_client_identifier(request) == "10.0.0.5"
    
    # With spaces
    request.headers = {"X-Forwarded-For": "  10.0.0.6  "}
    assert middleware._get_client_identifier(request) == "10.0.0.6"
    
    print("✓ Client identifier extraction works correctly")

async def async_test():
    """Run async tests"""
    # Import FastAPI components for async testing
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    
    app = FastAPI()
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=2,
        window_seconds=60
    )
    
    @app.get("/")
    def root():
        return {"message": "test"}
    
    client = TestClient(app)
    
    # Test rate limit headers
    response = client.get("/")
    assert response.status_code == 200
    assert "X-RateLimit-Limit" in response.headers
    assert "X-RateLimit-Remaining" in response.headers
    assert "X-RateLimit-Reset" in response.headers
    assert response.headers["X-RateLimit-Limit"] == "2"
    print("✓ Rate limit headers present")
    
    # Test rate limit enforcement
    response2 = client.get("/")
    assert response2.status_code == 200
    
    response3 = client.get("/")
    assert response3.status_code == 429
    data = response3.json()
    assert data["code"] == "RATE_LIMIT_EXCEEDED"
    assert "retry_after" in data
    assert response3.headers.get("Retry-After") is not None
    print("✓ Rate limit enforcement works")

if __name__ == "__main__":
    print("\n=== Testing Improved RateLimitMiddleware ===\n")
    
    # Run sync tests
    test_rate_limiter_initialization()
    test_get_stats()
    test_cleanup_stale_entries()
    test_cleanup_max_ips()
    test_get_client_identifier()
    
    # Run async tests
    asyncio.run(async_test())
    
    print("\n=== All tests passed! ===")

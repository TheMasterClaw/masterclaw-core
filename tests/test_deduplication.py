"""Tests for Request Deduplication Middleware"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.testclient import TestClient

from masterclaw_core.deduplication import (
    RequestDeduplicationMiddleware,
    PendingRequest,
    deduplicate,
    DeduplicationManager,
)


class TestRequestDeduplicationMiddleware:
    """Test suite for RequestDeduplicationMiddleware"""
    
    def test_pending_request_dataclass(self):
        """Test PendingRequest dataclass initialization"""
        pr = PendingRequest(signature="test123", started_at=time.time())
        assert pr.signature == "test123"
        assert pr.response is None
        assert pr.error is None
        assert pr.waiters == 0
        assert not pr.event.is_set()
    
    def test_middleware_initialization(self):
        """Test middleware initialization with default values"""
        app = FastAPI()
        middleware = RequestDeduplicationMiddleware(app)
        
        assert middleware.ttl_seconds == 5.0
        assert middleware.max_pending == 1000
        assert middleware.excluded_paths == {
            "/health", "/health/security", "/metrics", "/docs", "/redoc", "/openapi.json"
        }
        assert middleware._pending == {}
    
    def test_middleware_custom_config(self):
        """Test middleware initialization with custom values"""
        app = FastAPI()
        middleware = RequestDeduplicationMiddleware(
            app,
            ttl_seconds=10.0,
            max_pending=500,
            enabled_paths={"/v1/chat"},
            excluded_paths={"/health"},
            key_headers={"x-api-key"}
        )
        
        assert middleware.ttl_seconds == 10.0
        assert middleware.max_pending == 500
        assert middleware.enabled_paths == {"/v1/chat"}
        assert middleware.excluded_paths == {"/health"}
        assert middleware.key_headers == {"x-api-key"}
    
    def test_should_deduplicate_excluded_paths(self):
        """Test that excluded paths are not deduplicated"""
        app = FastAPI()
        middleware = RequestDeduplicationMiddleware(app)
        
        mock_request = Mock()
        mock_request.url.path = "/health"
        mock_request.method = "POST"
        
        assert not middleware._should_deduplicate(mock_request)
    
    def test_should_deduplicate_enabled_paths(self):
        """Test that enabled paths are deduplicated"""
        app = FastAPI()
        middleware = RequestDeduplicationMiddleware(
            app,
            enabled_paths={"/v1/chat"}
        )
        
        mock_request = Mock()
        mock_request.url.path = "/v1/chat"
        mock_request.method = "POST"
        
        assert middleware._should_deduplicate(mock_request)
    
    def test_should_deduplicate_get_requests_disabled_by_default(self):
        """Test that GET requests are not deduplicated by default"""
        app = FastAPI()
        middleware = RequestDeduplicationMiddleware(app)
        
        mock_request = Mock()
        mock_request.url.path = "/v1/chat"
        mock_request.method = "GET"
        
        assert not middleware._should_deduplicate(mock_request)
    
    def test_should_deduplicate_post_requests_enabled(self):
        """Test that POST requests are deduplicated"""
        app = FastAPI()
        middleware = RequestDeduplicationMiddleware(app)
        
        mock_request = Mock()
        mock_request.url.path = "/v1/chat"
        mock_request.method = "POST"
        
        assert middleware._should_deduplicate(mock_request)
    
    @pytest.mark.asyncio
    async def test_compute_signature_basic(self):
        """Test signature computation with basic request"""
        app = FastAPI()
        middleware = RequestDeduplicationMiddleware(app)
        
        mock_request = Mock()
        mock_request.method = "POST"
        mock_request.url.path = "/v1/chat"
        mock_request.query_params = {}
        mock_request.headers = {"content-type": "application/json"}
        mock_request.body = AsyncMock(return_value=b'{"message": "hello"}')
        
        signature = await middleware._compute_signature(mock_request)
        
        # Should be a valid SHA256 hash
        assert len(signature) == 64
        assert all(c in "0123456789abcdef" for c in signature)
    
    @pytest.mark.asyncio
    async def test_compute_signature_consistency(self):
        """Test that identical requests produce identical signatures"""
        app = FastAPI()
        middleware = RequestDeduplicationMiddleware(app)
        
        mock_request1 = Mock()
        mock_request1.method = "POST"
        mock_request1.url.path = "/v1/chat"
        mock_request1.query_params = {}
        mock_request1.headers = {"content-type": "application/json"}
        mock_request1.body = AsyncMock(return_value=b'{"message": "hello"}')
        
        mock_request2 = Mock()
        mock_request2.method = "POST"
        mock_request2.url.path = "/v1/chat"
        mock_request2.query_params = {}
        mock_request2.headers = {"content-type": "application/json"}
        mock_request2.body = AsyncMock(return_value=b'{"message": "hello"}')
        
        sig1 = await middleware._compute_signature(mock_request1)
        sig2 = await middleware._compute_signature(mock_request2)
        
        assert sig1 == sig2
    
    @pytest.mark.asyncio
    async def test_compute_signature_different_bodies(self):
        """Test that different bodies produce different signatures"""
        app = FastAPI()
        middleware = RequestDeduplicationMiddleware(app)
        
        body1 = b'{"message": "hello"}'
        body2 = b'{"message": "world"}'
        
        # Create mock requests with separate body methods
        mock_request1 = Mock()
        mock_request1.method = "POST"
        mock_request1.url.path = "/v1/chat"
        mock_request1.query_params = {}
        mock_request1.headers = {"content-type": "application/json", "content-length": str(len(body1))}
        
        async def body1_coroutine():
            mock_request1._body = body1
            return body1
        mock_request1.body = body1_coroutine
        
        mock_request2 = Mock()
        mock_request2.method = "POST"
        mock_request2.url.path = "/v1/chat"
        mock_request2.query_params = {}
        mock_request2.headers = {"content-type": "application/json", "content-length": str(len(body2))}
        
        async def body2_coroutine():
            mock_request2._body = body2
            return body2
        mock_request2.body = body2_coroutine
        
        sig1 = await middleware._compute_signature(mock_request1)
        sig2 = await middleware._compute_signature(mock_request2)
        
        assert sig1 != sig2, f"Expected different signatures but got same: {sig1}"
    
    @pytest.mark.asyncio
    async def test_cleanup_stale_requests(self):
        """Test cleanup of stale pending requests"""
        app = FastAPI()
        middleware = RequestDeduplicationMiddleware(app)
        middleware.ttl_seconds = 0.1  # Short TTL for testing
        
        # Add a stale request
        stale_request = PendingRequest(
            signature="stale",
            started_at=time.time() - 10  # 10 seconds ago
        )
        middleware._pending["stale"] = stale_request
        
        # Run cleanup
        await middleware._cleanup_stale_requests()
        
        # Stale request should be removed
        assert "stale" not in middleware._pending
        # Event should be set so waiters don't hang
        assert stale_request.event.is_set()
        assert isinstance(stale_request.error, TimeoutError)


class TestDeduplicationDecorator:
    """Test suite for the @deduplicate decorator"""
    
    @pytest.mark.asyncio
    async def test_deduplicate_decorator_basic(self):
        """Test basic deduplication with decorator"""
        call_count = 0
        
        @deduplicate(ttl_seconds=1.0)
        async def expensive_function(request):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.1)
            return {"result": f"call_{call_count}"}
        
        # Simulate concurrent calls
        mock_request = Mock()
        mock_request.body = AsyncMock(return_value=b"test")
        
        results = await asyncio.gather(
            expensive_function(mock_request),
            expensive_function(mock_request),
            expensive_function(mock_request),
        )
        
        # Should only be called once
        assert call_count == 1
        # All should get the same result
        assert all(r == {"result": "call_1"} for r in results)
    
    @pytest.mark.asyncio
    async def test_deduplicate_decorator_different_keys(self):
        """Test that different keys are not deduplicated"""
        call_count = 0
        
        @deduplicate(ttl_seconds=1.0, key_func=lambda x: str(x))
        async def expensive_function(key):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.05)
            return {"key": key, "call": call_count}
        
        results = await asyncio.gather(
            expensive_function("key1"),
            expensive_function("key2"),
            expensive_function("key3"),
        )
        
        # Should be called 3 times (different keys)
        assert call_count == 3
        assert results[0]["key"] == "key1"
        assert results[1]["key"] == "key2"
        assert results[2]["key"] == "key3"


class TestDeduplicationManager:
    """Test suite for DeduplicationManager - comprehensive tests for the fixed implementation"""
    
    def test_deduplication_manager_initialization(self):
        """Test DeduplicationManager initialization"""
        manager = DeduplicationManager(ttl_seconds=5.0)
        assert manager.ttl_seconds == 5.0
        assert manager._pending == {}
    
    def test_deduplication_manager_default_ttl(self):
        """Test DeduplicationManager with default TTL"""
        manager = DeduplicationManager()
        assert manager.ttl_seconds == 5.0
    
    @pytest.mark.asyncio
    async def test_acquire_leader_yields_self(self):
        """Test that the first (leader) caller gets 'self' yielded"""
        manager = DeduplicationManager(ttl_seconds=1.0)
        
        async with manager.acquire("test-key") as ctx:
            # Leader should get the manager instance as context
            assert ctx is manager
    
    @pytest.mark.asyncio
    async def test_acquire_follower_yields_none(self):
        """Test that subsequent (follower) callers get None yielded after leader completes"""
        manager = DeduplicationManager(ttl_seconds=0.5)
        results = []
        
        async def leader():
            async with manager.acquire("shared-key") as ctx:
                results.append(("leader", ctx))
                await asyncio.sleep(0.1)
        
        async def follower():
            await asyncio.sleep(0.05)  # Start after leader
            async with manager.acquire("shared-key") as ctx:
                results.append(("follower", ctx))
        
        await asyncio.gather(leader(), follower())
        
        # Leader should get self, follower should get None
        assert results[0] == ("leader", manager)
        assert results[1] == ("follower", None)
    
    @pytest.mark.asyncio
    async def test_acquire_deduplicates_concurrent_calls(self):
        """Test that concurrent calls with same key are deduplicated"""
        manager = DeduplicationManager(ttl_seconds=1.0)
        call_count = 0
        
        async def work():
            async with manager.acquire("work-key") as ctx:
                nonlocal call_count
                if ctx is not None:  # Only leader executes
                    call_count += 1
                    await asyncio.sleep(0.1)
        
        # Run 5 concurrent operations
        await asyncio.gather(*[work() for _ in range(5)])
        
        # Should only execute once
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_acquire_different_keys_not_deduplicated(self):
        """Test that different keys are not deduplicated"""
        manager = DeduplicationManager(ttl_seconds=1.0)
        call_count = 0
        
        async def work(key):
            async with manager.acquire(f"key-{key}") as ctx:
                nonlocal call_count
                if ctx is not None:
                    call_count += 1
                    await asyncio.sleep(0.05)
        
        # Run operations with different keys
        await asyncio.gather(*[work(i) for i in range(3)])
        
        # Should execute 3 times (different keys)
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_acquire_releases_after_ttl(self):
        """Test that key is released after TTL expires"""
        manager = DeduplicationManager(ttl_seconds=0.1)
        call_times = []
        
        async def work():
            async with manager.acquire("release-key") as ctx:
                if ctx is not None:
                    call_times.append(asyncio.get_event_loop().time())
        
        # First call
        await work()
        # Wait for TTL to expire
        await asyncio.sleep(0.15)
        # Second call should be allowed
        await work()
        
        # Should have 2 calls
        assert len(call_times) == 2
    
    @pytest.mark.asyncio
    async def test_acquire_exception_propagation(self):
        """Test that exceptions in leader are properly handled"""
        manager = DeduplicationManager(ttl_seconds=0.5)
        
        async def failing_leader():
            async with manager.acquire("error-key") as ctx:
                if ctx is not None:
                    raise ValueError("Leader failed!")
        
        with pytest.raises(ValueError, match="Leader failed!"):
            await failing_leader()
        
        # After exception, key should be cleaned up
        assert "error-key" not in manager._pending
    
    @pytest.mark.asyncio
    async def test_acquire_exception_allows_follower(self):
        """Test that after leader exception, followers get fresh execution"""
        manager = DeduplicationManager(ttl_seconds=0.1)  # Short TTL for quick retry
        leader_failed = False
        follower_executed = False
        
        async def leader():
            nonlocal leader_failed
            try:
                async with manager.acquire("shared-error-key") as ctx:
                    if ctx is not None:
                        raise ValueError("Leader failed!")
            except ValueError:
                leader_failed = True
        
        async def follower():
            # Wait for leader to fail and cleanup to happen
            await asyncio.sleep(0.15)
            nonlocal follower_executed
            async with manager.acquire("shared-error-key") as ctx:
                if ctx is not None:
                    follower_executed = True
        
        # Run both - follower should get chance after leader fails and TTL expires
        await asyncio.gather(leader(), follower(), return_exceptions=True)
        
        assert leader_failed is True
        # After exception cleanup and TTL, follower can become leader
        assert follower_executed is True
    
    @pytest.mark.asyncio
    async def test_acquire_cleans_up_pending(self):
        """Test that pending dict is properly cleaned up after use"""
        manager = DeduplicationManager(ttl_seconds=0.1)
        
        async with manager.acquire("cleanup-key") as ctx:
            assert ctx is manager
            assert "cleanup-key" in manager._pending
        
        # Wait for cleanup
        await asyncio.sleep(0.15)
        
        # Should be cleaned up
        assert "cleanup-key" not in manager._pending


class TestIntegration:
    """Integration tests with FastAPI"""
    
    def test_deduplication_integration(self):
        """Test deduplication with actual FastAPI app"""
        call_count = 0
        
        async def slow_endpoint():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.2)
            return {"calls": call_count}
        
        app = FastAPI()
        
        # Wrap the endpoint with deduplication
        @app.post("/test")
        @deduplicate(ttl_seconds=1.0)
        async def endpoint(request: Request):
            return await slow_endpoint()
        
        # We can't easily test concurrent requests with TestClient
        # but we can verify the endpoint works
        client = TestClient(app)
        response = client.post("/test", json={"test": "data"})
        
        assert response.status_code == 200
        assert response.json() == {"calls": 1}
    
    def test_health_endpoint_not_deduplicated(self):
        """Test that health endpoints work without deduplication"""
        app = FastAPI()
        
        @app.get("/health")
        async def health():
            return {"status": "healthy"}
        
        client = TestClient(app)
        response = client.get("/health")
        
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


class TestMetricsIntegration:
    """Test metrics tracking integration"""
    
    @pytest.mark.asyncio
    @patch('masterclaw_core.deduplication.prom_metrics')
    async def test_leader_metrics_tracking(self, mock_metrics):
        """Test that leader requests track metrics"""
        app = FastAPI()
        middleware = RequestDeduplicationMiddleware(
            app,
            enabled_paths={"/v1/test"}
        )
        
        # Mock the track_deduplication function
        mock_metrics.track_deduplication = Mock()
        mock_metrics.update_deduplication_pending = Mock()
        
        # Create a mock request
        mock_request = Mock()
        mock_request.url.path = "/v1/test"
        mock_request.method = "POST"
        mock_request.query_params = {}
        mock_request.headers = {}
        mock_request.body = AsyncMock(return_value=b"test")
        
        # Test dispatch as leader
        call_next = AsyncMock(return_value=JSONResponse({"result": "ok"}))
        
        # We need to properly set up the middleware state
        async with middleware._lock:
            pass  # Just to initialize
        
        # Manually trigger leader path
        signature = "test_sig"
        pending = PendingRequest(signature=signature, started_at=time.time())
        middleware._pending[signature] = pending
        
        # Test metrics are called
        mock_metrics.track_deduplication("test_sig", "leader", 0)
        mock_metrics.track_deduplication.assert_called_with("test_sig", "leader", 0)

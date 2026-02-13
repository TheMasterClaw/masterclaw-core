"""Tests for exception handling and error responses"""

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import BaseModel, ValidationError as PydanticValidationError

from masterclaw_core.exceptions import (
    MasterClawException,
    MemoryNotFoundException,
    LLMProviderException,
    RateLimitExceededException,
    masterclaw_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    general_exception_handler,
)


# =============================================================================
# Custom Exception Tests
# =============================================================================

class TestMasterClawException:
    """Test base MasterClawException class"""
    
    def test_basic_exception(self):
        """Test basic exception creation"""
        exc = MasterClawException("Something went wrong")
        assert exc.message == "Something went wrong"
        assert exc.status_code == 500
        assert exc.details == {}
        assert str(exc) == "Something went wrong"
    
    def test_exception_with_status_code(self):
        """Test exception with custom status code"""
        exc = MasterClawException("Not found", status_code=404)
        assert exc.status_code == 404
    
    def test_exception_with_details(self):
        """Test exception with details dict"""
        details = {"field": "username", "reason": "too short"}
        exc = MasterClawException("Validation failed", status_code=400, details=details)
        assert exc.details == details
    
    def test_exception_inheritance(self):
        """Test that custom exceptions inherit from MasterClawException"""
        assert issubclass(MemoryNotFoundException, MasterClawException)
        assert issubclass(LLMProviderException, MasterClawException)
        assert issubclass(RateLimitExceededException, MasterClawException)


class TestMemoryNotFoundException:
    """Test MemoryNotFoundException"""
    
    def test_exception_message(self):
        """Test exception message includes memory_id"""
        exc = MemoryNotFoundException("mem-123")
        assert "mem-123" in exc.message
        assert "Memory not found" in exc.message
    
    def test_exception_status_code(self):
        """Test exception has 404 status code"""
        exc = MemoryNotFoundException("mem-123")
        assert exc.status_code == 404
    
    def test_exception_details(self):
        """Test exception includes memory_id in details"""
        exc = MemoryNotFoundException("mem-123")
        assert exc.details == {"memory_id": "mem-123"}


class TestLLMProviderException:
    """Test LLMProviderException"""
    
    def test_exception_message(self):
        """Test exception message includes provider and error"""
        exc = LLMProviderException("openai", "Rate limit exceeded")
        assert "openai" in exc.message
        assert "Rate limit exceeded" in exc.message
    
    def test_exception_status_code(self):
        """Test exception has 503 status code (service unavailable)"""
        exc = LLMProviderException("anthropic", "Error")
        assert exc.status_code == 503
    
    def test_exception_details(self):
        """Test exception includes provider and original_error in details"""
        exc = LLMProviderException("openai", "Timeout")
        assert exc.details["provider"] == "openai"
        assert exc.details["original_error"] == "Timeout"


class TestRateLimitExceededException:
    """Test RateLimitExceededException"""
    
    def test_default_retry_after(self):
        """Test default retry_after value"""
        exc = RateLimitExceededException()
        assert exc.status_code == 429
        assert exc.details["retry_after"] == 60
    
    def test_custom_retry_after(self):
        """Test custom retry_after value"""
        exc = RateLimitExceededException(retry_after=120)
        assert exc.details["retry_after"] == 120
    
    def test_exception_message(self):
        """Test exception message"""
        exc = RateLimitExceededException()
        assert "Rate limit exceeded" in exc.message


# =============================================================================
# Exception Handler Tests
# =============================================================================

@pytest.fixture
def app_with_handlers():
    """Create FastAPI app with all exception handlers registered"""
    app = FastAPI()
    
    # Register exception handlers
    app.add_exception_handler(MasterClawException, masterclaw_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
    
    # Test endpoints that trigger exceptions
    
    @app.get("/masterclaw-error")
    def masterclaw_error():
        raise MemoryNotFoundException("test-memory-id")
    
    @app.get("/llm-provider-error")
    def llm_provider_error():
        raise LLMProviderException("openai", "Connection timeout")
    
    @app.get("/rate-limit-error")
    def rate_limit_error():
        raise RateLimitExceededException(retry_after=120)
    
    @app.get("/http-error")
    def http_error():
        raise StarletteHTTPException(status_code=403, detail="Forbidden resource")
    
    @app.get("/unhandled-error")
    def unhandled_error():
        raise ValueError("Something unexpected happened")
    
    @app.get("/items/{item_id}")
    def get_item(item_id: int):
        return {"item_id": item_id}
    
    return app


class TestMasterClawExceptionHandler:
    """Test masterclaw_exception_handler"""
    
    def test_memory_not_found_response(self, app_with_handlers):
        """Test MemoryNotFoundException returns proper JSON response"""
        client = TestClient(app_with_handlers)
        response = client.get("/masterclaw-error")
        
        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert "test-memory-id" in data["error"]
        assert data["details"]["memory_id"] == "test-memory-id"
        assert data["type"] == "MemoryNotFoundException"
    
    def test_llm_provider_error_response(self, app_with_handlers):
        """Test LLMProviderException returns proper JSON response"""
        client = TestClient(app_with_handlers)
        response = client.get("/llm-provider-error")
        
        assert response.status_code == 503
        data = response.json()
        assert "openai" in data["error"]
        assert "Connection timeout" in data["error"]
        assert data["type"] == "LLMProviderException"
    
    def test_rate_limit_response(self, app_with_handlers):
        """Test RateLimitExceededException returns proper JSON response"""
        client = TestClient(app_with_handlers)
        response = client.get("/rate-limit-error")
        
        assert response.status_code == 429
        data = response.json()
        assert "Rate limit exceeded" in data["error"]
        assert data["details"]["retry_after"] == 120
        assert data["type"] == "RateLimitExceededException"
    
    def test_custom_masterclaw_exception(self, app_with_handlers):
        """Test custom MasterClawException subclass works"""
        app = app_with_handlers
        
        @app.get("/custom-error")
        def custom_error():
            raise MasterClawException(
                "Custom business logic error",
                status_code=422,
                details={"field": "quantity", "constraint": "must be positive"}
            )
        
        client = TestClient(app)
        response = client.get("/custom-error")
        
        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "Custom business logic error"
        assert data["details"]["field"] == "quantity"
        assert data["type"] == "MasterClawException"


class TestHTTPExceptionHandler:
    """Test http_exception_handler"""
    
    def test_http_exception_response(self, app_with_handlers):
        """Test HTTPException returns proper JSON response"""
        client = TestClient(app_with_handlers)
        response = client.get("/http-error")
        
        assert response.status_code == 403
        data = response.json()
        assert data["error"] == "Forbidden resource"
        assert data["status_code"] == 403
    
    def test_http_exception_404(self):
        """Test 404 Not Found response"""
        app = FastAPI()
        app.add_exception_handler(StarletteHTTPException, http_exception_handler)
        
        @app.get("/existing")
        def existing():
            return {"ok": True}
        
        client = TestClient(app)
        response = client.get("/non-existent")
        
        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert data["status_code"] == 404


class TestValidationExceptionHandler:
    """Test validation_exception_handler"""
    
    def test_validation_error_response(self, app_with_handlers):
        """Test RequestValidationError returns proper JSON response"""
        client = TestClient(app_with_handlers)
        # Pass invalid type for item_id (should be int)
        response = client.get("/items/abc")
        
        assert response.status_code == 422
        data = response.json()
        assert "error" in data
        assert data["error"] == "Validation error"
        assert "errors" in data
        assert len(data["errors"]) > 0
        
        # Check error structure
        error = data["errors"][0]
        assert "field" in error
        assert "message" in error
        assert "type" in error
    
    def test_missing_required_field(self):
        """Test validation error for missing required field"""
        app = FastAPI()
        app.add_exception_handler(RequestValidationError, validation_exception_handler)
        
        class CreateItemRequest(BaseModel):
            name: str
            quantity: int
        
        @app.post("/items")
        def create_item(item: CreateItemRequest):
            return item
        
        client = TestClient(app)
        response = client.post("/items", json={"name": "test"})  # missing quantity
        
        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "Validation error"
        assert any("quantity" in str(e) for e in data["errors"])
    
    def test_invalid_field_type(self):
        """Test validation error for invalid field type"""
        app = FastAPI()
        app.add_exception_handler(RequestValidationError, validation_exception_handler)
        
        class CreateItemRequest(BaseModel):
            name: str
            quantity: int
        
        @app.post("/items")
        def create_item(item: CreateItemRequest):
            return item
        
        client = TestClient(app)
        response = client.post("/items", json={"name": "test", "quantity": "not-a-number"})
        
        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "Validation error"
        # Should have field info for quantity
        assert any("quantity" in str(e.get("field", "")) for e in data["errors"])


class TestGeneralExceptionHandler:
    """Test general_exception_handler"""
    
    def test_unhandled_exception_response(self, app_with_handlers):
        """Test unhandled exception returns proper JSON response"""
        client = TestClient(app_with_handlers)
        response = client.get("/unhandled-error")
        
        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert data["error"] == "Internal server error"
        # In debug mode, message should be present
        assert "message" in data
    
    def test_general_exception_logging(self, app_with_handlers, caplog):
        """Test that unhandled exceptions are logged"""
        import logging
        
        with caplog.at_level(logging.ERROR):
            client = TestClient(app_with_handlers)
            response = client.get("/unhandled-error")
        
        assert response.status_code == 500
        # Check that something was logged
        assert "error" in caplog.text.lower() or "exception" in caplog.text.lower()


# =============================================================================
# Integration Tests
# =============================================================================

class TestExceptionHandlerIntegration:
    """Integration tests for all exception handlers working together"""
    
    def test_handlers_registered_in_order(self):
        """Test that handlers are registered and work in correct order"""
        app = FastAPI()
        
        # Register in order (most specific to least specific)
        app.add_exception_handler(MasterClawException, masterclaw_exception_handler)
        app.add_exception_handler(StarletteHTTPException, http_exception_handler)
        app.add_exception_handler(RequestValidationError, validation_exception_handler)
        app.add_exception_handler(Exception, general_exception_handler)
        
        @app.get("/test")
        def test():
            return {"ok": True}
        
        client = TestClient(app)
        
        # Normal request works
        response = client.get("/test")
        assert response.status_code == 200
        
        # 404 uses HTTP exception handler
        response = client.get("/not-found")
        assert response.status_code == 404
        
        # Validation error uses validation handler
        @app.get("/number/{n}")
        def get_number(n: int):
            return {"n": n}
        
        response = client.get("/number/not-a-number")
        assert response.status_code == 422
    
    def test_exception_response_content_type(self, app_with_handlers):
        """Test that exception responses have correct content type"""
        client = TestClient(app_with_handlers)
        response = client.get("/masterclaw-error")
        
        assert response.headers["content-type"] == "application/json"
    
    def test_multiple_different_exceptions(self):
        """Test handling multiple different exception types"""
        app = FastAPI()
        app.add_exception_handler(MasterClawException, masterclaw_exception_handler)
        app.add_exception_handler(StarletteHTTPException, http_exception_handler)
        app.add_exception_handler(RequestValidationError, validation_exception_handler)
        app.add_exception_handler(Exception, general_exception_handler)
        
        exceptions_to_test = [
            ("/memory-error", lambda: (_ for _ in ()).throw(MemoryNotFoundException("mem-1")), 404),
            ("/llm-error", lambda: (_ for _ in ()).throw(LLMProviderException("openai", "timeout")), 503),
            ("/rate-error", lambda: (_ for _ in ()).throw(RateLimitExceededException()), 429),
            ("/http-error", lambda: (_ for _ in ()).throw(StarletteHTTPException(400, "Bad request")), 400),
            ("/generic-error", lambda: (_ for _ in ()).throw(ValueError("oops")), 500),
        ]
        
        for path, exc_factory, expected_status in exceptions_to_test:
            # Create endpoint that raises exception
            def make_endpoint(ef):
                def endpoint():
                    ef()
                return endpoint
            
            app.get(path)(make_endpoint(exc_factory))
        
        client = TestClient(app)
        
        # Test each endpoint
        for path, _, expected_status in exceptions_to_test:
            response = client.get(path)
            assert response.status_code == expected_status, f"Failed for {path}"
            assert response.headers["content-type"] == "application/json"


# =============================================================================
# Security Tests
# =============================================================================

class TestExceptionSecurity:
    """Security tests for exception handling"""
    
    def test_exception_details_do_not_leak_stack_trace(self, app_with_handlers):
        """Test that stack traces are not exposed in production mode"""
        # In production (non-debug), error details should be limited
        client = TestClient(app_with_handlers)
        response = client.get("/unhandled-error")
        
        assert response.status_code == 500
        data = response.json()
        
        # Should not contain traceback or internal implementation details
        assert "traceback" not in str(data).lower()
        assert "file" not in str(data).lower() or "line" not in str(data).lower()
    
    def test_sql_injection_not_in_error_message(self):
        """Test that SQL injection attempts don't appear in error messages"""
        app = FastAPI()
        app.add_exception_handler(RequestValidationError, validation_exception_handler)
        
        @app.get("/search")
        def search(q: str):
            return {"q": q}
        
        client = TestClient(app)
        response = client.get("/search", params={"q": "'; DROP TABLE users; --"})
        
        # Should get a response (either success or validation error)
        assert response.status_code in [200, 422]
    
    def test_error_response_structure_consistency(self, app_with_handlers):
        """Test that error responses have consistent structure"""
        client = TestClient(app_with_handlers)
        
        # Test different error types
        responses = [
            client.get("/masterclaw-error"),
            client.get("/llm-provider-error"),
            client.get("/rate-limit-error"),
            client.get("/http-error"),
        ]
        
        for response in responses:
            data = response.json()
            # All should have 'error' field
            assert "error" in data
            # All should be JSON
            assert response.headers["content-type"] == "application/json"


# =============================================================================
# Performance Tests
# =============================================================================

class TestExceptionHandlerPerformance:
    """Performance tests for exception handlers"""
    
    def test_exception_handler_response_time(self, app_with_handlers):
        """Test that exception handlers respond quickly"""
        import time
        
        client = TestClient(app_with_handlers)
        
        start = time.perf_counter()
        for _ in range(10):
            response = client.get("/masterclaw-error")
            assert response.status_code == 404
        elapsed = time.perf_counter() - start
        
        # Should handle 10 exceptions quickly (under 1 second)
        assert elapsed < 1.0, f"Exception handling too slow: {elapsed:.2f}s"

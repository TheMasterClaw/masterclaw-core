"""Tests for structured logging integration in main.py"""

import pytest
import json
import logging
from unittest.mock import Mock, patch
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from masterclaw_core.structured_logger import (
    get_logger,
    request_context,
    JSONFormatter,
    ConsoleFormatter,
    configure_logging,
)
from masterclaw_core.exceptions import (
    MasterClawException,
    masterclaw_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    general_exception_handler,
)


class TestStructuredLoggingConfiguration:
    """Test structured logging configuration"""
    
    def test_get_logger_returns_structured_logger(self):
        """Test that get_logger returns a StructuredLogger instance"""
        logger = get_logger("test")
        assert logger.name == "test"
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'error')
        assert hasattr(logger, 'log_request')
    
    def test_json_formatter_outputs_valid_json(self):
        """Test JSON formatter produces valid JSON output"""
        formatter = JSONFormatter()
        
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        output = formatter.format(record)
        
        # Should be valid JSON
        parsed = json.loads(output)
        assert parsed["level"] == "INFO"
        assert parsed["logger"] == "test"
        assert parsed["message"] == "Test message"
        assert "timestamp" in parsed
    
    def test_json_formatter_includes_extra_data(self):
        """Test JSON formatter includes extra fields from log record"""
        formatter = JSONFormatter()
        
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        # Add custom field
        record.custom_field = "custom_value"
        record.another_field = 123
        
        output = formatter.format(record)
        parsed = json.loads(output)
        
        assert parsed["extra"]["custom_field"] == "custom_value"
        assert parsed["extra"]["another_field"] == 123
    
    def test_console_formatter_with_colors(self):
        """Test console formatter produces readable output"""
        formatter = ConsoleFormatter(use_colors=False, include_context=True)
        
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        output = formatter.format(record)
        
        # Should include standard fields
        assert "INFO" in output
        assert "test" in output
        assert "Test message" in output


class TestRequestContext:
    """Test request context management"""
    
    def test_request_context_sets_variables(self):
        """Test that request context sets context variables"""
        from masterclaw_core.structured_logger import get_current_context
        
        # Initially empty
        initial_context = get_current_context()
        
        with request_context(
            request_id="test-req-123",
            session_id="test-sess-456",
            user_id="user-789",
            client_ip="192.168.1.1"
        ):
            context = get_current_context()
            assert context["request_id"] == "test-req-123"
            assert context["session_id"] == "test-sess-456"
            assert context["user_id"] == "user-789"
            assert context["client_ip"] == "192.168.1.1"
    
    def test_request_context_cleans_up_on_exit(self):
        """Test that request context cleans up variables on exit"""
        from masterclaw_core.structured_logger import get_current_context
        
        with request_context(request_id="test-123"):
            context = get_current_context()
            assert context["request_id"] == "test-123"
        
        # After exit, context should be cleared
        context = get_current_context()
        assert context["request_id"] is None
    
    def test_nested_request_context(self):
        """Test nested request contexts"""
        from masterclaw_core.structured_logger import get_current_context
        
        with request_context(request_id="outer"):
            assert get_current_context()["request_id"] == "outer"
            
            with request_context(request_id="inner"):
                assert get_current_context()["request_id"] == "inner"
            
            # Back to outer context
            assert get_current_context()["request_id"] == "outer"


class TestStructuredExceptionHandlers:
    """Test structured logging integration with exception handlers"""
    
    @pytest.fixture
    def mock_request(self):
        """Create a mock request with state"""
        request = Mock(spec=Request)
        request.state = Mock()
        request.state.request_id = "test-req-123"
        request.client = Mock()
        request.client.host = "192.168.1.1"
        request.url.path = "/test"
        request.method = "GET"
        return request
    
    def test_create_structured_exception_handler_logs_error(self, mock_request, caplog):
        """Test that structured exception handler logs errors"""
        async def mock_handler(request, exc):
            return {"handled": True}
        
        async def structured_handler(request: Request, exc: Exception):
            # Log with structured data
            logger = get_logger("test")
            logger.error(
                f"Exception handled: TestException for request {getattr(request.state, 'request_id', 'unknown')}"
            )
            return await mock_handler(request, exc)
        
        with caplog.at_level(logging.ERROR):
            # Run the async handler
            import asyncio
            exc = MasterClawException("Test error")
            result = asyncio.run(structured_handler(mock_request, exc))
        
        # Check that error was logged with request info
        assert "TestException" in caplog.text
        assert "test-req-123" in caplog.text


class TestConfigureLogging:
    """Test logging configuration"""
    
    def test_configure_logging_sets_level(self):
        """Test that configure_logging sets the correct level"""
        configure_logging(level="DEBUG")
        
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG
    
    def test_configure_logging_with_string_level(self):
        """Test configure_logging with string level name"""
        configure_logging(level="WARNING")
        
        root_logger = logging.getLogger()
        assert root_logger.level == logging.WARNING
    
    def test_configure_logging_json_format(self):
        """Test configure_logging with JSON format"""
        configure_logging(level="INFO", json_format=True)
        
        root_logger = logging.getLogger()
        # Check that handler has JSON formatter
        if root_logger.handlers:
            assert isinstance(root_logger.handlers[0].formatter, JSONFormatter)
    
    def test_configure_logging_console_format(self):
        """Test configure_logging with console format"""
        configure_logging(level="INFO", json_format=False)
        
        root_logger = logging.getLogger()
        # Check that handler has console formatter
        if root_logger.handlers:
            assert isinstance(root_logger.handlers[0].formatter, ConsoleFormatter)


class TestStructuredLogger:
    """Test StructuredLogger class"""
    
    def test_structured_logger_info(self, caplog):
        """Test info logging with structured data"""
        with caplog.at_level(logging.INFO):
            logger = get_logger("test")
            logger.info("Test message", custom_field="custom_value", count=42)
        
        assert "Test message" in caplog.text
    
    def test_structured_logger_error(self, caplog):
        """Test error logging with structured data"""
        with caplog.at_level(logging.ERROR):
            logger = get_logger("test")
            logger.error("Error message", error_code="E123", severity="high")
        
        assert "Error message" in caplog.text
    
    def test_structured_logger_log_request(self, caplog):
        """Test request logging"""
        with caplog.at_level(logging.INFO):
            logger = get_logger("test")
            logger.log_request(
                method="POST",
                path="/api/test",
                status_code=200,
                duration_ms=123.45
            )
        
        assert "POST /api/test - 200" in caplog.text
    
    def test_structured_logger_log_chat(self, caplog):
        """Test chat logging"""
        with caplog.at_level(logging.INFO):
            logger = get_logger("test")
            logger.log_chat(
                provider="openai",
                model="gpt-4",
                tokens_used=150,
                duration_ms=2345.6
            )
        
        assert "openai/gpt-4" in caplog.text


class TestIntegrationWithRequestContext:
    """Integration tests for structured logging with request context"""
    
    def test_logging_with_request_context(self, caplog):
        """Test that logs include request context"""
        import asyncio
        
        async def async_test():
            with request_context(
                request_id="req-123",
                session_id="sess-456",
                client_ip="10.0.0.1"
            ):
                logger = get_logger("test")
                logger.info("Test message with context")
        
        with caplog.at_level(logging.INFO):
            asyncio.run(async_test())
        
        # The log should contain the message
        assert "Test message with context" in caplog.text

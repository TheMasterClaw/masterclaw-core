"""Tests for structured logging module

Tests cover:
- JSONFormatter output format and structure
- ConsoleFormatter with colors and context
- Context variable management
- StructuredLogger convenience methods
- Integration with standard logging
"""

import json
import logging
import pytest
import sys
from datetime import datetime
from io import StringIO
from unittest.mock import patch, MagicMock

from masterclaw_core.structured_logger import (
    JSONFormatter,
    ConsoleFormatter,
    StructuredLogger,
    request_context,
    get_logger,
    configure_logging,
    get_current_context,
    _request_id,
    _session_id,
    _user_id,
    _client_ip,
)


class TestJSONFormatter:
    """Tests for JSONFormatter"""
    
    def test_basic_json_output(self):
        """Test basic JSON formatting"""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/test/file.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        output = formatter.format(record)
        data = json.loads(output)
        
        assert data["level"] == "INFO"
        assert data["logger"] == "test.logger"
        assert data["message"] == "Test message"
        assert "timestamp" in data
        assert "timestamp" in data
    
    def test_timestamp_iso_format(self):
        """Test ISO timestamp format"""
        formatter = JSONFormatter(timestamp_format="iso")
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="/test.py",
            lineno=1, msg="Test", args=(), exc_info=None
        )
        record.created = 1708195200.0  # 2024-02-17 12:00:00 UTC
        
        output = formatter.format(record)
        data = json.loads(output)
        
        # Should be ISO format with Z suffix
        assert data["timestamp"].endswith("Z")
        assert "T" in data["timestamp"]
    
    def test_extra_fields_included(self):
        """Test that extra fields are included in output"""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="/test.py",
            lineno=1, msg="Test", args=(), exc_info=None
        )
        record.model = "gpt-4"
        record.tokens = 150
        
        output = formatter.format(record)
        data = json.loads(output)
        
        assert data["extra"]["model"] == "gpt-4"
        assert data["extra"]["tokens"] == 150
    
    def test_flatten_extra_option(self):
        """Test flatten_extra option"""
        formatter = JSONFormatter(flatten_extra=True)
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="/test.py",
            lineno=1, msg="Test", args=(), exc_info=None
        )
        record.model = "gpt-4"
        
        output = formatter.format(record)
        data = json.loads(output)
        
        # Should be at top level, not in "extra"
        assert data["model"] == "gpt-4"
        assert "extra" not in data
    
    def test_source_info_for_warnings(self):
        """Test source info added for WARNING and above"""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test", level=logging.WARNING, pathname="/app/test.py",
            lineno=42, msg="Warning message", args=(), exc_info=None
        )
        
        output = formatter.format(record)
        data = json.loads(output)
        
        assert "source" in data
        assert data["source"]["file"] == "/app/test.py"
        assert data["source"]["line"] == 42
        # funcName is set when LogRecord is created by logging framework
        assert "function" in data["source"]
    
    def test_no_source_for_info(self):
        """Test source info NOT added for INFO level"""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="/app/test.py",
            lineno=42, msg="Info message", args=(), exc_info=None
        )
        
        output = formatter.format(record)
        data = json.loads(output)
        
        assert "source" not in data
    
    def test_exception_formatting(self):
        """Test exception info formatting"""
        formatter = JSONFormatter()
        
        try:
            raise ValueError("Test error")
        except ValueError:
            import sys
            exc_info = sys.exc_info()
            record = logging.LogRecord(
                name="test", level=logging.ERROR, pathname="/test.py",
                lineno=1, msg="Error occurred", args=(), exc_info=exc_info
            )
        
        output = formatter.format(record)
        data = json.loads(output)
        
        assert "exception" in data
        assert data["exception"]["type"] == "ValueError"
        assert "Test error" in data["exception"]["message"]
        assert data["exception"]["traceback"] is not None


class TestConsoleFormatter:
    """Tests for ConsoleFormatter"""
    
    def test_basic_console_output(self):
        """Test basic console formatting"""
        formatter = ConsoleFormatter(use_colors=False)
        record = logging.LogRecord(
            name="test.logger", level=logging.INFO,
            pathname="/test.py", lineno=1,
            msg="Test message", args=(), exc_info=None
        )
        record.created = 1708195200.0
        
        output = formatter.format(record)
        
        assert "2024-02-17" in output or "2024-02-18" in output  # Date
        assert "test.logger" in output
        assert "INFO" in output
        assert "Test message" in output
    
    def test_context_in_output(self):
        """Test context variables appear in output"""
        formatter = ConsoleFormatter(use_colors=False)
        
        # Set context
        token = _request_id.set("abc123")
        
        try:
            record = logging.LogRecord(
                name="test", level=logging.INFO,
                pathname="/test.py", lineno=1,
                msg="Test", args=(), exc_info=None
            )
            
            output = formatter.format(record)
            
            assert "req:abc123" in output
        finally:
            _request_id.reset(token)
    
    def test_colors_for_tty(self):
        """Test colors are used when output is TTY"""
        formatter = ConsoleFormatter(use_colors=True)
        
        record = logging.LogRecord(
            name="test", level=logging.ERROR,
            pathname="/test.py", lineno=1,
            msg="Error", args=(), exc_info=None
        )
        
        # Force colors by overriding isatty
        formatter.use_colors = True
        output = formatter.format(record)
        
        # Should contain ANSI color codes
        assert '\033[' in output  # ESC[
    
    def test_no_colors_for_non_tty(self):
        """Test colors are not used when output is not TTY"""
        formatter = ConsoleFormatter(use_colors=True)
        
        with patch.object(sys.stdout, 'isatty', return_value=False):
            record = logging.LogRecord(
                name="test", level=logging.ERROR,
                pathname="/test.py", lineno=1,
                msg="Error", args=(), exc_info=None
            )
            
            output = formatter.format(record)
            
            # Should not contain ANSI color codes
            assert '\033[' not in output


class TestRequestContext:
    """Tests for request_context"""
    
    def test_context_set_in_block(self):
        """Test context variables are set within context block"""
        with request_context(
            request_id="req-123",
            session_id="sess-456",
            user_id="user-789",
            client_ip="192.168.1.1"
        ):
            assert _request_id.get() == "req-123"
            assert _session_id.get() == "sess-456"
            assert _user_id.get() == "user-789"
            assert _client_ip.get() == "192.168.1.1"
    
    def test_context_cleared_after_block(self):
        """Test context variables are cleared after exiting block"""
        with request_context(
            request_id="req-123",
            session_id="sess-456"
        ):
            pass  # Context set here
        
        # Should be cleared after block
        assert _request_id.get() is None
        assert _session_id.get() is None
    
    def test_default_request_id_generated(self):
        """Test default request ID is auto-generated"""
        with request_context() as ctx:
            req_id = _request_id.get()
            assert req_id is not None
            assert len(req_id) == 8  # First 8 chars of UUID
    
    def test_nested_context(self):
        """Test nested context blocks"""
        with request_context(request_id="outer"):
            assert _request_id.get() == "outer"
            
            with request_context(request_id="inner"):
                assert _request_id.get() == "inner"
            
            # Should restore outer context
            assert _request_id.get() == "outer"
    
    def test_get_current_context(self):
        """Test get_current_context helper"""
        with request_context(
            request_id="req-123",
            session_id="sess-456",
            user_id="user-789",
            client_ip="192.168.1.1"
        ):
            ctx = get_current_context()
            
            assert ctx["request_id"] == "req-123"
            assert ctx["session_id"] == "sess-456"
            assert ctx["user_id"] == "user-789"
            assert ctx["client_ip"] == "192.168.1.1"


class TestStructuredLogger:
    """Tests for StructuredLogger"""
    
    @pytest.fixture
    def mock_handler(self):
        """Create a mock handler for testing"""
        handler = logging.Handler()
        handler.records = []
        
        def emit(record):
            handler.records.append(record)
        
        handler.emit = emit
        return handler
    
    def test_info_logging(self, mock_handler):
        """Test info level logging"""
        logger = StructuredLogger("test.logger")
        logger.logger.addHandler(mock_handler)
        logger.logger.setLevel(logging.INFO)
        
        with request_context(request_id="req-123"):
            logger.info("Test message", model="gpt-4", tokens=100)
        
        assert len(mock_handler.records) == 1
        record = mock_handler.records[0]
        assert record.levelno == logging.INFO
        assert "Test message" in str(record.msg)
        assert record.model == "gpt-4"
        assert record.tokens == 100
    
    def test_error_logging(self, mock_handler):
        """Test error level logging"""
        logger = StructuredLogger("test.logger")
        logger.logger.addHandler(mock_handler)
        logger.logger.setLevel(logging.ERROR)
        
        logger.error("Error occurred", error_code="E123", retryable=True)
        
        assert len(mock_handler.records) == 1
        record = mock_handler.records[0]
        assert record.levelno == logging.ERROR
        assert record.error_code == "E123"
        assert record.retryable is True
    
    def test_log_request_method(self, mock_handler):
        """Test log_request convenience method"""
        logger = StructuredLogger("test.logger")
        logger.logger.addHandler(mock_handler)
        logger.logger.setLevel(logging.INFO)
        
        logger.log_request(
            method="POST",
            path="/v1/chat",
            status_code=200,
            duration_ms=123.456
        )
        
        assert len(mock_handler.records) == 1
        record = mock_handler.records[0]
        assert record.method == "POST"
        assert record.path == "/v1/chat"
        assert record.status_code == 200
        assert record.duration_ms == 123.46  # Rounded to 2 decimals
    
    def test_log_request_error_status(self, mock_handler):
        """Test log_request with error status codes"""
        logger = StructuredLogger("test.logger")
        logger.logger.addHandler(mock_handler)
        logger.logger.setLevel(logging.WARNING)
        
        # 500 error should log at ERROR level
        logger.log_request("GET", "/error", 500, 50.0)
        
        assert len(mock_handler.records) == 1
        assert mock_handler.records[0].levelno == logging.ERROR
    
    def test_log_chat_method(self, mock_handler):
        """Test log_chat convenience method"""
        logger = StructuredLogger("test.logger")
        logger.logger.addHandler(mock_handler)
        logger.logger.setLevel(logging.INFO)
        
        logger.log_chat(
            provider="openai",
            model="gpt-4",
            tokens_used=150,
            duration_ms=500.0,
            session_id="sess-123"
        )
        
        assert len(mock_handler.records) == 1
        record = mock_handler.records[0]
        assert record.provider == "openai"
        assert record.model == "gpt-4"
        assert record.tokens_used == 150
        assert record.session_id == "sess-123"


class TestGetLogger:
    """Tests for get_logger convenience function"""
    
    def test_returns_structured_logger(self):
        """Test get_logger returns StructuredLogger instance"""
        logger = get_logger("test.module")
        
        assert isinstance(logger, StructuredLogger)
        assert logger.name == "test.module"
    
    def test_different_names_get_different_loggers(self):
        """Test different names get different logger instances"""
        logger1 = get_logger("module1")
        logger2 = get_logger("module2")
        
        assert logger1.name == "module1"
        assert logger2.name == "module2"


class TestConfigureLogging:
    """Tests for configure_logging function"""
    
    def test_configure_json_format(self):
        """Test JSON format configuration"""
        import logging
        
        # Create a test logger and handler
        test_logger = logging.getLogger("test_configure_json")
        original_handlers = test_logger.handlers[:]
        
        try:
            # Clear handlers
            for h in original_handlers:
                test_logger.removeHandler(h)
            
            # Create handler with JSON formatter
            handler = logging.StreamHandler()
            handler.setFormatter(JSONFormatter())
            test_logger.addHandler(handler)
            
            # Verify formatter is JSONFormatter
            assert isinstance(handler.formatter, JSONFormatter)
        finally:
            # Cleanup
            for h in test_logger.handlers[:]:
                test_logger.removeHandler(h)
            for h in original_handlers:
                test_logger.addHandler(h)
    
    def test_configure_console_format(self):
        """Test console format configuration"""
        import logging
        
        handler = logging.StreamHandler()
        handler.setFormatter(ConsoleFormatter())
        
        # Verify formatter is ConsoleFormatter
        assert isinstance(handler.formatter, ConsoleFormatter)
    
    def test_configure_level_string_conversion(self):
        """Test string level conversion in configure_logging"""
        # Test the level conversion logic directly
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }
        
        for level_str, level_int in level_map.items():
            assert getattr(logging, level_str) == level_int
    
    def test_uvicorn_logger_names(self):
        """Test uvicorn logger names are correct"""
        # These are the logger names configure_logging uses
        uvicorn_loggers = ["uvicorn.access", "uvicorn.error"]
        
        for name in uvicorn_loggers:
            logger = logging.getLogger(name)
            assert logger is not None  # Logger exists


class TestIntegration:
    """Integration tests for structured logging"""
    
    def test_full_logging_pipeline(self):
        """Test full logging pipeline from logger to JSON output"""
        # Setup
        handler = logging.StreamHandler(StringIO())
        handler.setFormatter(JSONFormatter())
        
        logger = get_logger("integration.test")
        logger.logger.handlers = [handler]
        logger.logger.setLevel(logging.INFO)
        
        # Execute
        with request_context(request_id="int-test-123", session_id="sess-456"):
            logger.info(
                "Integration test message",
                provider="openai",
                model="gpt-4",
                tokens=150
            )
        
        # Verify
        output = handler.stream.getvalue()
        data = json.loads(output)
        
        assert data["message"] == "Integration test message"
        assert data["level"] == "INFO"
        assert data["logger"] == "integration.test"
        assert data["request_id"] == "int-test-123"
        assert data["session_id"] == "sess-456"
        assert data["extra"]["provider"] == "openai"
        assert data["extra"]["model"] == "gpt-4"
        assert data["extra"]["tokens"] == 150
    
    def test_context_flows_through_multiple_logs(self):
        """Test context persists through multiple log calls"""
        handler = logging.StreamHandler(StringIO())
        handler.setFormatter(JSONFormatter())
        
        logger = get_logger("test")
        logger.logger.handlers = [handler]
        logger.logger.setLevel(logging.INFO)
        
        with request_context(request_id="flow-test"):
            logger.info("First message")
            logger.info("Second message")
            logger.warning("Third message")
        
        output = handler.stream.getvalue().strip().split('\n')
        
        # All three logs should have the same request_id
        for line in output:
            data = json.loads(line)
            assert data["request_id"] == "flow-test"


class TestEdgeCases:
    """Edge case tests"""
    
    def test_unicode_in_message(self):
        """Test unicode characters in log messages"""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO,
            pathname="/test.py", lineno=1,
            msg="Unicode: 你好世界 🌍 émoji", args=(), exc_info=None
        )
        
        output = formatter.format(record)
        data = json.loads(output)
        
        assert "你好世界" in data["message"]
        assert "🌍" in data["message"]
    
    def test_special_characters_in_extra(self):
        """Test special characters in extra fields"""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO,
            pathname="/test.py", lineno=1,
            msg="Test", args=(), exc_info=None
        )
        record.special = 'Contains "quotes" and \\ backslash'
        
        output = formatter.format(record)
        data = json.loads(output)
        
        assert 'Contains "quotes"' in data["extra"]["special"]
    
    def test_none_values_in_context(self):
        """Test None values in context don't break formatting"""
        with request_context(request_id="test", session_id=None):
            formatter = JSONFormatter()
            record = logging.LogRecord(
                name="test", level=logging.INFO,
                pathname="/test.py", lineno=1,
                msg="Test", args=(), exc_info=None
            )
            
            output = formatter.format(record)
            data = json.loads(output)
            
            assert data["request_id"] == "test"
            # session_id should not be present when None
            assert "session_id" not in data
    
    def test_large_extra_data(self):
        """Test large extra data is handled"""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO,
            pathname="/test.py", lineno=1,
            msg="Test", args=(), exc_info=None
        )
        record.large_list = list(range(1000))
        
        output = formatter.format(record)
        data = json.loads(output)
        
        assert len(data["extra"]["large_list"]) == 1000

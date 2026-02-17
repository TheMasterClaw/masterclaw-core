"""Tests for Prometheus metrics module

Ensures all metrics are properly tracked and exposed for monitoring.
Missing metrics in production could lead to blind spots in system health monitoring.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from prometheus_client import REGISTRY

# Import after mocking to avoid registration issues
with patch('prometheus_client.REGISTRY'):
    from masterclaw_core import metrics


class TestMetricsTracking:
    """Test metrics tracking functions"""
    
    @pytest.fixture(autouse=True)
    def reset_metrics(self):
        """Reset metrics registry before each test"""
        # Store original collectors
        original_collectors = list(REGISTRY._collector_to_names.keys())
        yield
        # Cleanup: remove any collectors added during tests
        current_collectors = list(REGISTRY._collector_to_names.keys())
        for collector in current_collectors:
            if collector not in original_collectors:
                try:
                    REGISTRY.unregister(collector)
                except Exception:
                    pass

    def test_track_request_increments_counter(self):
        """Test that track_request increments the HTTP request counter"""
        with patch.object(metrics.http_requests_total, 'labels') as mock_labels:
            mock_counter = Mock()
            mock_labels.return_value = mock_counter
            
            metrics.track_request("GET", "/v1/chat", 200, 150.0)
            
            mock_labels.assert_called_once_with(
                method="GET",
                endpoint="/v1/chat",
                status_code="200"
            )
            mock_counter.inc.assert_called_once()

    def test_track_request_records_duration(self):
        """Test that track_request records request duration"""
        with patch.object(metrics.http_request_duration_seconds, 'labels') as mock_labels:
            mock_histogram = Mock()
            mock_labels.return_value = mock_histogram
            
            metrics.track_request("POST", "/v1/memory/search", 200, 500.0)
            
            mock_labels.assert_called_once_with(method="POST", endpoint="/v1/memory/search")
            mock_histogram.observe.assert_called_once_with(0.5)  # 500ms -> 0.5s

    def test_track_request_converts_ms_to_seconds(self):
        """Test that duration is correctly converted from milliseconds to seconds"""
        with patch.object(metrics.http_request_duration_seconds, 'labels') as mock_labels:
            mock_histogram = Mock()
            mock_labels.return_value = mock_histogram
            
            test_cases = [
                (1000.0, 1.0),
                (500.0, 0.5),
                (100.0, 0.1),
                (0.0, 0.0),
            ]
            
            for duration_ms, expected_seconds in test_cases:
                mock_histogram.reset_mock()
                metrics.track_request("GET", "/test", 200, duration_ms)
                mock_histogram.observe.assert_called_with(expected_seconds)

    def test_track_chat_increments_counter(self):
        """Test that track_chat increments chat request counter"""
        with patch.object(metrics.chat_requests_total, 'labels') as mock_labels:
            mock_counter = Mock()
            mock_labels.return_value = mock_counter
            
            metrics.track_chat("openai", "gpt-4", 100)
            
            mock_labels.assert_called_once_with(provider="openai", model="gpt-4")
            mock_counter.inc.assert_called_once()

    def test_track_chat_records_tokens(self):
        """Test that track_chat records token usage"""
        with patch.object(metrics.chat_tokens_total, 'labels') as mock_labels:
            mock_counter = Mock()
            mock_labels.return_value = mock_counter
            
            metrics.track_chat("anthropic", "claude-3", 150)
            
            mock_labels.assert_called_once_with(provider="anthropic", model="claude-3")
            mock_counter.inc.assert_called_once_with(150)

    def test_track_chat_zero_tokens(self):
        """Test that track_chat doesn't record tokens when count is zero"""
        with patch.object(metrics.chat_tokens_total, 'labels') as mock_labels:
            mock_counter = Mock()
            mock_labels.return_value = mock_counter
            
            metrics.track_chat("openai", "gpt-4", 0)
            
            # chat_tokens_total.labels should NOT be called when tokens is 0
            # (but chat_requests_total.labels still is)
            mock_labels.assert_not_called()
            mock_counter.inc.assert_not_called()

    def test_track_memory_operation_success(self):
        """Test tracking successful memory operations"""
        with patch.object(metrics.memory_operations_total, 'labels') as mock_labels:
            mock_counter = Mock()
            mock_labels.return_value = mock_counter
            
            metrics.track_memory_operation("search", success=True)
            
            mock_labels.assert_called_once_with(operation="search", status="success")
            mock_counter.inc.assert_called_once()

    def test_track_memory_operation_error(self):
        """Test tracking failed memory operations"""
        with patch.object(metrics.memory_operations_total, 'labels') as mock_labels:
            mock_counter = Mock()
            mock_labels.return_value = mock_counter
            
            metrics.track_memory_operation("add", success=False)
            
            mock_labels.assert_called_once_with(operation="add", status="error")
            mock_counter.inc.assert_called_once()

    def test_track_memory_search_duration(self):
        """Test that memory search duration is recorded"""
        with patch.object(metrics.memory_search_duration_seconds, 'observe') as mock_observe:
            metrics.track_memory_search(250.0)
            mock_observe.assert_called_once_with(0.25)

    def test_track_llm_request_success(self):
        """Test tracking successful LLM requests"""
        with patch.object(metrics.llm_requests_total, 'labels') as mock_req_labels, \
             patch.object(metrics.llm_request_duration_seconds, 'labels') as mock_dur_labels:
            
            mock_req_counter = Mock()
            mock_req_labels.return_value = mock_req_counter
            
            mock_dur_histogram = Mock()
            mock_dur_labels.return_value = mock_dur_histogram
            
            metrics.track_llm_request("openai", 1200.0, success=True)
            
            mock_req_labels.assert_called_once_with(provider="openai", status="success")
            mock_req_counter.inc.assert_called_once()
            mock_dur_labels.assert_called_once_with(provider="openai")
            mock_dur_histogram.observe.assert_called_once_with(1.2)

    def test_track_llm_request_error(self):
        """Test tracking failed LLM requests"""
        with patch.object(metrics.llm_requests_total, 'labels') as mock_labels:
            mock_counter = Mock()
            mock_labels.return_value = mock_counter
            
            metrics.track_llm_request("anthropic", 500.0, success=False)
            
            mock_labels.assert_called_once_with(provider="anthropic", status="error")
            mock_counter.inc.assert_called_once()

    def test_update_active_sessions(self):
        """Test updating active sessions gauge"""
        with patch.object(metrics.active_sessions, 'set') as mock_set:
            metrics.update_active_sessions(42)
            mock_set.assert_called_once_with(42)

    def test_update_memory_entries(self):
        """Test updating memory entries gauge"""
        with patch.object(metrics.memory_entries_total, 'set') as mock_set:
            metrics.update_memory_entries(1000)
            mock_set.assert_called_once_with(1000)


class TestGetMetricsResponse:
    """Test the metrics export endpoint"""

    def test_get_metrics_response_returns_response_object(self):
        """Test that get_metrics_response returns a proper Response object"""
        response = metrics.get_metrics_response()
        
        from starlette.responses import Response
        assert isinstance(response, Response)

    def test_get_metrics_response_has_correct_content_type(self):
        """Test that metrics response has Prometheus content type"""
        response = metrics.get_metrics_response()
        
        # Content type should be text/plain with prometheus version info
        assert response.media_type.startswith("text/plain")
        assert "version=" in response.media_type
        assert "charset=utf-8" in response.media_type

    def test_get_metrics_response_contains_metrics(self):
        """Test that response contains actual metric data"""
        # First track some metrics to ensure data exists
        metrics.track_request("GET", "/test", 200, 100.0)
        
        response = metrics.get_metrics_response()
        content = response.body.decode('utf-8')
        
        # Check for expected metric names
        assert "masterclaw_http_requests_total" in content
        assert "masterclaw_http_request_duration_seconds" in content


class TestMetricsLabels:
    """Test that metrics use correct label combinations"""

    def test_http_requests_labels(self):
        """Test HTTP request counter has correct labels"""
        with patch.object(metrics.http_requests_total, 'labels') as mock_labels:
            mock_counter = Mock()
            mock_labels.return_value = mock_counter
            
            # Test various status codes
            for status in [200, 201, 400, 401, 403, 404, 429, 500, 503]:
                metrics.track_request("GET", "/test", status, 100.0)
                call_args = mock_labels.call_args
                assert call_args[1]["status_code"] == str(status)

    def test_chat_labels_provider_model_variations(self):
        """Test chat metrics with various provider/model combinations"""
        with patch.object(metrics.chat_requests_total, 'labels') as mock_labels:
            mock_counter = Mock()
            mock_labels.return_value = mock_counter
            
            test_cases = [
                ("openai", "gpt-4"),
                ("openai", "gpt-4o"),
                ("openai", "gpt-4o-mini"),
                ("anthropic", "claude-3-opus-20240229"),
                ("anthropic", "claude-3-sonnet-20240229"),
                ("anthropic", "claude-3-haiku-20240307"),
            ]
            
            for provider, model in test_cases:
                mock_labels.reset_mock()
                metrics.track_chat(provider, model, 100)
                mock_labels.assert_called_with(provider=provider, model=model)

    def test_memory_operation_types(self):
        """Test memory operation tracking for all operation types"""
        with patch.object(metrics.memory_operations_total, 'labels') as mock_labels:
            mock_counter = Mock()
            mock_labels.return_value = mock_counter
            
            operations = ["search", "add", "get", "delete"]
            
            for op in operations:
                for success in [True, False]:
                    mock_labels.reset_mock()
                    status = "success" if success else "error"
                    metrics.track_memory_operation(op, success=success)
                    mock_labels.assert_called_with(operation=op, status=status)


class TestMetricsEdgeCases:
    """Test edge cases and error handling"""

    def test_track_request_with_empty_endpoint(self):
        """Test tracking request with empty endpoint string"""
        with patch.object(metrics.http_requests_total, 'labels') as mock_labels:
            mock_counter = Mock()
            mock_labels.return_value = mock_counter
            
            metrics.track_request("GET", "", 200, 100.0)
            mock_labels.assert_called_with(method="GET", endpoint="", status_code="200")

    def test_track_request_with_special_characters_in_endpoint(self):
        """Test tracking request with special characters in endpoint"""
        with patch.object(metrics.http_requests_total, 'labels') as mock_labels:
            mock_counter = Mock()
            mock_labels.return_value = mock_counter
            
            special_endpoint = "/v1/memory/test-123_session.foo?query=value"
            metrics.track_request("GET", special_endpoint, 200, 100.0)
            mock_labels.assert_called_with(
                method="GET",
                endpoint=special_endpoint,
                status_code="200"
            )

    def test_track_chat_with_large_token_count(self):
        """Test tracking chat with very large token count"""
        with patch.object(metrics.chat_tokens_total, 'labels') as mock_labels:
            mock_counter = Mock()
            mock_labels.return_value = mock_counter
            
            large_token_count = 1000000
            metrics.track_chat("openai", "gpt-4", large_token_count)
            mock_counter.inc.assert_called_once_with(large_token_count)

    def test_negative_duration_handling(self):
        """Test behavior with negative duration (should still record)"""
        with patch.object(metrics.http_request_duration_seconds, 'labels') as mock_labels:
            mock_histogram = Mock()
            mock_labels.return_value = mock_histogram
            
            # Negative duration is unusual but should be handled gracefully
            metrics.track_request("GET", "/test", 200, -100.0)
            mock_histogram.observe.assert_called_once_with(-0.1)


class TestMetricsIntegration:
    """Integration-style tests for metrics module"""

    def test_multiple_track_calls_accumulate(self):
        """Test that multiple tracking calls accumulate values"""
        with patch.object(metrics.http_requests_total, 'labels') as mock_labels:
            mock_counter = Mock()
            mock_labels.return_value = mock_counter
            
            # Track multiple requests
            for _ in range(5):
                metrics.track_request("GET", "/v1/chat", 200, 100.0)
            
            assert mock_counter.inc.call_count == 5

    def test_different_endpoints_separate_metrics(self):
        """Test that different endpoints create separate metric series"""
        with patch.object(metrics.http_requests_total, 'labels') as mock_labels:
            mock_counter = Mock()
            mock_labels.return_value = mock_counter
            
            endpoints = ["/v1/chat", "/v1/memory/search", "/v1/memory/add", "/health"]
            
            for endpoint in endpoints:
                metrics.track_request("GET", endpoint, 200, 100.0)
            
            # Each endpoint should have its own labels call
            assert mock_labels.call_count == len(endpoints)

    def test_metrics_preserve_state_between_calls(self):
        """Test that metric values are preserved between tracking calls"""
        with patch.object(metrics.chat_tokens_total, 'labels') as mock_labels:
            mock_counter = Mock()
            mock_labels.return_value = mock_counter
            
            # Simulate tracking tokens over multiple chats
            token_counts = [100, 200, 150, 300, 50]
            for tokens in token_counts:
                metrics.track_chat("openai", "gpt-4", tokens)
            
            # Each call should increment by the specific amount
            expected_calls = [call(tokens) for tokens in token_counts]
            mock_counter.inc.assert_has_calls(expected_calls, any_order=False)


class TestMetricsDocumentation:
    """Test that metrics have proper documentation"""

    def test_all_metrics_have_docstrings(self):
        """Verify all public functions have docstrings"""
        functions = [
            metrics.track_request,
            metrics.track_chat,
            metrics.track_memory_operation,
            metrics.track_memory_search,
            metrics.track_llm_request,
            metrics.update_active_sessions,
            metrics.update_memory_entries,
            metrics.get_metrics_response,
        ]
        
        for func in functions:
            assert func.__doc__ is not None, f"{func.__name__} missing docstring"
            assert len(func.__doc__.strip()) > 0, f"{func.__name__} has empty docstring"

    def test_metric_objects_have_descriptions(self):
        """Test that Prometheus metric objects have descriptions"""
        metric_objects = [
            metrics.http_requests_total,
            metrics.http_request_duration_seconds,
            metrics.chat_requests_total,
            metrics.chat_tokens_total,
            metrics.memory_operations_total,
            metrics.memory_search_duration_seconds,
            metrics.active_sessions,
            metrics.memory_entries_total,
            metrics.llm_requests_total,
            metrics.llm_request_duration_seconds,
        ]
        
        for metric in metric_objects:
            assert metric._documentation is not None
            assert len(metric._documentation) > 0


class TestMetricsThreadSafety:
    """Test thread safety of metrics operations"""

    def test_concurrent_track_calls(self):
        """Test that concurrent tracking calls don't corrupt metrics"""
        import threading
        import time
        
        with patch.object(metrics.http_requests_total, 'labels') as mock_labels:
            mock_counter = Mock()
            mock_labels.return_value = mock_counter
            
            errors = []
            
            def track_requests():
                try:
                    for _ in range(100):
                        metrics.track_request("GET", "/test", 200, 100.0)
                        time.sleep(0.001)
                except Exception as e:
                    errors.append(e)
            
            # Run concurrent tracking
            threads = [threading.Thread(target=track_requests) for _ in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            
            assert len(errors) == 0, f"Errors during concurrent tracking: {errors}"
            assert mock_counter.inc.call_count == 500


class TestMetricsExporter:
    """Test Prometheus metrics export functionality"""

    def test_generate_latest_called(self):
        """Test that generate_latest is called when getting metrics"""
        with patch('masterclaw_core.metrics.generate_latest') as mock_generate:
            mock_generate.return_value = b"# Test metrics"
            
            response = metrics.get_metrics_response()
            
            mock_generate.assert_called_once()
            assert response.body == b"# Test metrics"

    def test_content_type_latest_used(self):
        """Test that CONTENT_TYPE_LATEST is used for response"""
        with patch('masterclaw_core.metrics.CONTENT_TYPE_LATEST', 'test/content-type'):
            with patch('masterclaw_core.metrics.generate_latest', return_value=b"test"):
                response = metrics.get_metrics_response()
                assert response.media_type == 'test/content-type'

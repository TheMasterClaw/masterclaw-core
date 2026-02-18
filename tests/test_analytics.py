"""Tests for analytics module - Cost tracking and usage analytics

This module tests the analytics functionality including:
- Cost calculations for different providers and models
- CostTracker functionality
- Analytics metrics tracking
- Edge cases and error handling
"""

import pytest
from datetime import datetime, timedelta
from masterclaw_core.analytics import (
    calculate_cost,
    CostTracker,
    Analytics,
    PRICING,
)


class TestCalculateCost:
    """Test the calculate_cost function"""
    
    def test_calculate_cost_openai_gpt4(self):
        """Test cost calculation for OpenAI GPT-4"""
        result = calculate_cost("openai", "gpt-4", input_tokens=1000, output_tokens=500)
        
        # GPT-4 pricing: input $0.03/1K, output $0.06/1K
        expected_input_cost = 0.03  # 1000 * 0.03 / 1000
        expected_output_cost = 0.03  # 500 * 0.06 / 1000
        
        assert result["input_cost"] == round(expected_input_cost, 6)
        assert result["output_cost"] == round(expected_output_cost, 6)
        assert result["total_cost"] == round(expected_input_cost + expected_output_cost, 6)
        assert result["input_tokens"] == 1000
        assert result["output_tokens"] == 500
    
    def test_calculate_cost_openai_gpt4o_mini(self):
        """Test cost calculation for OpenAI GPT-4o-mini (cheapest model)"""
        result = calculate_cost("openai", "gpt-4o-mini", input_tokens=10000, output_tokens=5000)
        
        # GPT-4o-mini pricing: input $0.00015/1K, output $0.0006/1K
        expected_input_cost = 0.0015  # 10000 * 0.00015 / 1000
        expected_output_cost = 0.003  # 5000 * 0.0006 / 1000
        
        assert result["input_cost"] == round(expected_input_cost, 6)
        assert result["output_cost"] == round(expected_output_cost, 6)
        assert result["total_cost"] == round(expected_input_cost + expected_output_cost, 6)
    
    def test_calculate_cost_anthropic_claude_opus(self):
        """Test cost calculation for Anthropic Claude-3-Opus"""
        result = calculate_cost("anthropic", "claude-3-opus-20240229", input_tokens=2000, output_tokens=1000)
        
        # Claude-3-Opus pricing: input $0.015/1K, output $0.075/1K
        expected_input_cost = 0.03  # 2000 * 0.015 / 1000
        expected_output_cost = 0.075  # 1000 * 0.075 / 1000
        
        assert result["input_cost"] == round(expected_input_cost, 6)
        assert result["output_cost"] == round(expected_output_cost, 6)
        assert result["total_cost"] == round(expected_input_cost + expected_output_cost, 6)
    
    def test_calculate_cost_anthropic_claude_haiku(self):
        """Test cost calculation for Anthropic Claude-3-Haiku (cheapest)"""
        result = calculate_cost("anthropic", "claude-3-haiku-20240307", input_tokens=5000, output_tokens=2000)
        
        # Claude-3-Haiku pricing: input $0.00025/1K, output $0.00125/1K
        expected_input_cost = 0.00125  # 5000 * 0.00025 / 1000
        expected_output_cost = 0.0025  # 2000 * 0.00125 / 1000
        
        assert result["input_cost"] == round(expected_input_cost, 6)
        assert result["output_cost"] == round(expected_output_cost, 6)
    
    def test_calculate_cost_zero_tokens(self):
        """Test cost calculation with zero tokens"""
        result = calculate_cost("openai", "gpt-4", input_tokens=0, output_tokens=0)
        
        assert result["input_cost"] == 0.0
        assert result["output_cost"] == 0.0
        assert result["total_cost"] == 0.0
    
    def test_calculate_cost_unknown_provider(self):
        """Test cost calculation with unknown provider uses default pricing"""
        result = calculate_cost("unknown_provider", "some-model", input_tokens=1000, output_tokens=500)
        
        # Should use default pricing (0,0) for unknown providers
        assert result["input_cost"] == 0.0
        assert result["output_cost"] == 0.0
        assert result["total_cost"] == 0.0
    
    def test_calculate_cost_unknown_model_uses_default(self):
        """Test that unknown models use the provider's default pricing"""
        result = calculate_cost("openai", "unknown-model", input_tokens=1000, output_tokens=500)
        
        # Should use OpenAI default pricing
        expected_input_cost = 0.03
        expected_output_cost = 0.03
        
        assert result["input_cost"] == round(expected_input_cost, 6)
        assert result["output_cost"] == round(expected_output_cost, 6)
    
    def test_calculate_cost_large_token_counts(self):
        """Test cost calculation with large token counts"""
        result = calculate_cost("openai", "gpt-4", input_tokens=1000000, output_tokens=500000)
        
        # GPT-4 pricing: input $0.03/1K, output $0.06/1K
        expected_input_cost = 30.0  # 1000000 * 0.03 / 1000
        expected_output_cost = 30.0  # 500000 * 0.06 / 1000
        
        assert result["total_cost"] == round(expected_input_cost + expected_output_cost, 6)


class TestCostTracker:
    """Test the CostTracker class"""
    
    def test_init(self):
        """Test CostTracker initialization"""
        tracker = CostTracker()
        assert tracker.costs == []
    
    def test_track_cost_single_entry(self):
        """Test tracking a single cost entry"""
        tracker = CostTracker()
        
        result = tracker.track_cost(
            provider="openai",
            model="gpt-4",
            input_tokens=1000,
            output_tokens=500,
            session_id="test-session-123"
        )
        
        assert len(tracker.costs) == 1
        assert result["total_cost"] > 0
        
        entry = tracker.costs[0]
        assert entry["provider"] == "openai"
        assert entry["model"] == "gpt-4"
        assert entry["session_id"] == "test-session-123"
        assert entry["input_tokens"] == 1000
        assert entry["output_tokens"] == 500
        assert "timestamp" in entry
    
    def test_track_cost_no_session(self):
        """Test tracking cost without session ID"""
        tracker = CostTracker()
        
        tracker.track_cost(
            provider="anthropic",
            model="claude-3-opus-20240229",
            input_tokens=500,
            output_tokens=250,
            session_id=None
        )
        
        assert len(tracker.costs) == 1
        assert tracker.costs[0]["session_id"] is None
    
    def test_track_cost_multiple_entries(self):
        """Test tracking multiple cost entries"""
        tracker = CostTracker()
        
        # Add multiple entries
        tracker.track_cost("openai", "gpt-4", 1000, 500, "session-1")
        tracker.track_cost("openai", "gpt-4", 2000, 1000, "session-1")
        tracker.track_cost("anthropic", "claude-3-opus-20240229", 1500, 750, "session-2")
        
        assert len(tracker.costs) == 3
        assert tracker.costs[0]["provider"] == "openai"
        assert tracker.costs[1]["provider"] == "openai"
        assert tracker.costs[2]["provider"] == "anthropic"
    
    def test_get_cost_summary_empty(self):
        """Test cost summary with no entries"""
        tracker = CostTracker()
        
        summary = tracker.get_cost_summary(days=30)
        
        assert summary["period_days"] == 30
        assert summary["total_cost"] == 0.0
        assert summary["total_requests"] == 0
        assert summary["average_cost_per_request"] == 0
        assert summary["by_provider"] == {}
        assert summary["by_model"] == {}
        assert summary["top_sessions"] == []
    
    def test_get_cost_summary_single_entry(self):
        """Test cost summary with single entry"""
        tracker = CostTracker()
        
        tracker.track_cost("openai", "gpt-4", 1000, 500, "session-1")
        
        summary = tracker.get_cost_summary(days=30)
        
        assert summary["total_requests"] == 1
        assert summary["total_cost"] > 0
        assert summary["by_provider"]["openai"]["requests"] == 1
        assert summary["by_model"]["gpt-4"]["requests"] == 1
        assert len(summary["top_sessions"]) == 1
        assert summary["top_sessions"][0]["session_id"] == "session-1"
    
    def test_get_cost_summary_multiple_providers(self):
        """Test cost summary aggregation across multiple providers"""
        tracker = CostTracker()
        
        # Add costs from different providers
        tracker.track_cost("openai", "gpt-4", 1000, 500, "session-1")
        tracker.track_cost("anthropic", "claude-3-opus-20240229", 2000, 1000, "session-2")
        tracker.track_cost("openai", "gpt-4o", 3000, 1500, "session-3")
        
        summary = tracker.get_cost_summary(days=30)
        
        assert summary["total_requests"] == 3
        assert "openai" in summary["by_provider"]
        assert "anthropic" in summary["by_provider"]
        assert summary["by_provider"]["openai"]["requests"] == 2
        assert summary["by_provider"]["anthropic"]["requests"] == 1
    
    def test_get_cost_summary_top_sessions_limit(self):
        """Test that top sessions is limited to 10"""
        tracker = CostTracker()
        
        # Add 15 sessions
        for i in range(15):
            tracker.track_cost("openai", "gpt-4", 1000 * (i + 1), 500, f"session-{i}")
        
        summary = tracker.get_cost_summary(days=30)
        
        assert len(summary["top_sessions"]) == 10  # Should be limited to 10
    
    def test_get_cost_summary_date_filtering(self):
        """Test that old entries are filtered out based on days parameter"""
        tracker = CostTracker()
        
        # Add a recent entry
        tracker.track_cost("openai", "gpt-4", 1000, 500, "session-1")
        
        # Manually add an old entry (40 days ago)
        old_entry = {
            "provider": "openai",
            "model": "gpt-4",
            "session_id": "session-old",
            "input_tokens": 10000,
            "output_tokens": 5000,
            "input_cost": 0.3,
            "output_cost": 0.3,
            "total_cost": 0.6,
            "timestamp": (datetime.utcnow() - timedelta(days=40)).isoformat(),
        }
        tracker.costs.append(old_entry)
        
        # Summary for last 30 days should not include the old entry
        summary = tracker.get_cost_summary(days=30)
        
        assert summary["total_requests"] == 1  # Only the recent entry
        assert summary["top_sessions"][0]["session_id"] == "session-1"
    
    def test_get_daily_costs_empty(self):
        """Test daily costs with no entries"""
        tracker = CostTracker()
        
        daily = tracker.get_daily_costs(days=30)
        
        assert daily == []
    
    def test_get_daily_costs_grouping(self):
        """Test that costs are correctly grouped by day"""
        tracker = CostTracker()
        
        # Add entries for today
        tracker.track_cost("openai", "gpt-4", 1000, 500, "session-1")
        tracker.track_cost("openai", "gpt-4", 2000, 1000, "session-2")
        
        daily = tracker.get_daily_costs(days=30)
        
        assert len(daily) == 1  # All entries are from today
        assert daily[0]["requests"] == 2
        assert daily[0]["cost"] > 0
        assert daily[0]["tokens"] == 4500  # (1000+500) + (2000+1000)
    
    def test_get_daily_costs_sorted(self):
        """Test that daily costs are sorted by date"""
        tracker = CostTracker()
        
        # Manually add entries for different days
        today = datetime.utcnow()
        
        for days_ago in [2, 0, 1]:  # Add out of order
            entry = {
                "provider": "openai",
                "model": "gpt-4",
                "session_id": f"session-{days_ago}",
                "input_tokens": 1000,
                "output_tokens": 500,
                "input_cost": 0.03,
                "output_cost": 0.03,
                "total_cost": 0.06,
                "timestamp": (today - timedelta(days=days_ago)).isoformat(),
            }
            tracker.costs.append(entry)
        
        daily = tracker.get_daily_costs(days=30)
        
        assert len(daily) == 3
        # Should be sorted by date (oldest first)
        dates = [d["date"] for d in daily]
        assert dates == sorted(dates)


class TestAnalytics:
    """Test the Analytics class"""
    
    def test_init(self):
        """Test Analytics initialization"""
        analytics = Analytics()
        assert analytics.metrics == {}
        assert isinstance(analytics.cost_tracker, CostTracker)
    
    def test_track_request(self):
        """Test tracking API requests"""
        analytics = Analytics()
        
        analytics.track_request("/v1/chat", duration_ms=150.5, status_code=200)
        analytics.track_request("/v1/memory/search", duration_ms=50.0, status_code=200)
        analytics.track_request("/v1/chat", duration_ms=200.0, status_code=500)
        
        assert len(analytics.metrics["requests"]) == 3
        
        # Check first request
        req = analytics.metrics["requests"][0]
        assert req["endpoint"] == "/v1/chat"
        assert req["duration_ms"] == 150.5
        assert req["status_code"] == 200
        assert "timestamp" in req
    
    def test_track_chat_without_cost(self):
        """Test tracking chat without token breakdown (no cost tracking)"""
        analytics = Analytics()
        
        analytics.track_chat(provider="openai", model="gpt-4", tokens_used=500)
        
        assert len(analytics.metrics["chats"]) == 1
        assert len(analytics.cost_tracker.costs) == 0  # No cost tracked
        
        chat = analytics.metrics["chats"][0]
        assert chat["provider"] == "openai"
        assert chat["model"] == "gpt-4"
        assert chat["tokens_used"] == 500
    
    def test_track_chat_with_cost(self):
        """Test tracking chat with token breakdown (includes cost tracking)"""
        analytics = Analytics()
        
        analytics.track_chat(
            provider="anthropic",
            model="claude-3-opus-20240229",
            tokens_used=3000,
            input_tokens=2000,
            output_tokens=1000,
            session_id="test-session"
        )
        
        assert len(analytics.metrics["chats"]) == 1
        assert len(analytics.cost_tracker.costs) == 1  # Cost tracked
        
        cost_entry = analytics.cost_tracker.costs[0]
        assert cost_entry["provider"] == "anthropic"
        assert cost_entry["session_id"] == "test-session"
    
    def test_track_memory_search(self):
        """Test tracking memory search metrics"""
        analytics = Analytics()
        
        analytics.track_memory_search(results_count=5, query_time_ms=25.5)
        analytics.track_memory_search(results_count=10, query_time_ms=50.0)
        
        assert len(analytics.metrics["memory_searches"]) == 2
        
        search = analytics.metrics["memory_searches"][0]
        assert search["results_count"] == 5
        assert search["query_time_ms"] == 25.5
        assert "timestamp" in search
    
    def test_get_stats_empty(self):
        """Test get_stats with no data"""
        analytics = Analytics()
        
        stats = analytics.get_stats(days=7)
        
        assert stats["period_days"] == 7
        assert stats["total_requests"] == 0
        assert stats["avg_response_time_ms"] == 0
        assert stats["total_chats"] == 0
        assert stats["total_tokens"] == 0
        assert stats["provider_usage"] == {}
        assert stats["error_rate"] == 0
    
    def test_get_stats_with_data(self):
        """Test get_stats with sample data"""
        analytics = Analytics()
        
        # Add requests
        analytics.track_request("/v1/chat", duration_ms=100.0, status_code=200)
        analytics.track_request("/v1/chat", duration_ms=200.0, status_code=200)
        analytics.track_request("/v1/memory", duration_ms=50.0, status_code=500)  # Error
        
        # Add chats
        analytics.track_chat("openai", "gpt-4", tokens_used=1000)
        analytics.track_chat("anthropic", "claude-3-opus-20240229", tokens_used=2000)
        analytics.track_chat("openai", "gpt-4", tokens_used=500)
        
        stats = analytics.get_stats(days=7)
        
        assert stats["total_requests"] == 3
        assert stats["avg_response_time_ms"] == 116.67  # (100 + 200 + 50) / 3
        assert stats["total_chats"] == 3
        assert stats["total_tokens"] == 3500  # 1000 + 2000 + 500
        assert stats["provider_usage"]["openai"] == 2
        assert stats["provider_usage"]["anthropic"] == 1
        assert stats["error_rate"] == 1/3  # 1 error out of 3 requests
    
    def test_get_stats_date_filtering(self):
        """Test that get_stats filters by date"""
        analytics = Analytics()
        
        # Add recent request
        analytics.track_request("/v1/chat", duration_ms=100.0, status_code=200)
        
        # Add old request (manually with old timestamp)
        old_request = {
            "endpoint": "/v1/chat",
            "duration_ms": 500.0,
            "status_code": 200,
            "timestamp": (datetime.utcnow() - timedelta(days=10)).isoformat(),
        }
        analytics.metrics["requests"] = [old_request]
        
        # Should only count recent requests (last 7 days)
        stats = analytics.get_stats(days=7)
        
        assert stats["total_requests"] == 0  # Old request filtered out
    
    def test_get_stats_error_rate_calculation(self):
        """Test error rate calculation"""
        analytics = Analytics()
        
        # Add mix of success and error responses
        for i in range(8):
            analytics.track_request("/v1/chat", duration_ms=100.0, status_code=200)
        for i in range(2):
            analytics.track_request("/v1/chat", duration_ms=100.0, status_code=500)
        
        stats = analytics.get_stats(days=7)
        
        assert stats["total_requests"] == 10
        assert stats["error_rate"] == 0.2  # 2/10 errors
    
    def test_get_stats_no_division_by_zero(self):
        """Test that stats handles edge case with no requests"""
        analytics = Analytics()
        
        stats = analytics.get_stats(days=7)
        
        # Should not raise division by zero
        assert stats["avg_response_time_ms"] == 0
        assert stats["error_rate"] == 0


class TestPricingConstants:
    """Test the pricing constants"""
    
    def test_pricing_structure(self):
        """Test that pricing dictionary has correct structure"""
        assert "openai" in PRICING
        assert "anthropic" in PRICING
        
        for provider, models in PRICING.items():
            assert "default" in models, f"{provider} missing default pricing"
            for model, pricing in models.items():
                assert "input" in pricing
                assert "output" in pricing
                assert pricing["input"] >= 0
                assert pricing["output"] >= 0
    
    def test_openai_models_priced(self):
        """Test that all OpenAI models have pricing"""
        openai_models = [
            "gpt-4",
            "gpt-4-turbo",
            "gpt-4-turbo-preview",
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-3.5-turbo",
            "gpt-3.5-turbo-16k",
        ]
        
        for model in openai_models:
            assert model in PRICING["openai"], f"OpenAI model {model} not priced"
    
    def test_anthropic_models_priced(self):
        """Test that all Anthropic models have pricing"""
        anthropic_models = [
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
            "claude-3-5-sonnet-20241022",
        ]
        
        for model in anthropic_models:
            assert model in PRICING["anthropic"], f"Anthropic model {model} not priced"
    
    def test_pricing_ordering(self):
        """Test that pricing generally follows model capability ordering"""
        # GPT-4 should be more expensive than GPT-3.5
        assert PRICING["openai"]["gpt-4"]["input"] > PRICING["openai"]["gpt-3.5-turbo"]["input"]
        
        # Claude Opus should be more expensive than Haiku
        assert (PRICING["anthropic"]["claude-3-opus-20240229"]["input"] > 
                PRICING["anthropic"]["claude-3-haiku-20240307"]["input"])


class TestEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_calculate_cost_negative_tokens(self):
        """Test behavior with negative token counts"""
        # This tests current behavior - negative tokens produce negative costs
        result = calculate_cost("openai", "gpt-4", input_tokens=-1000, output_tokens=-500)
        
        assert result["input_cost"] < 0
        assert result["output_cost"] < 0
        assert result["total_cost"] < 0
    
    def test_large_number_of_entries(self):
        """Test handling large number of cost entries"""
        tracker = CostTracker()
        
        # Add 1000 entries
        for i in range(1000):
            tracker.track_cost("openai", "gpt-4", 1000, 500, f"session-{i}")
        
        summary = tracker.get_cost_summary(days=30)
        
        assert summary["total_requests"] == 1000
        assert len(summary["top_sessions"]) == 10  # Still limited to 10
    
    def test_cost_tracker_preserves_precision(self):
        """Test that cost calculations preserve precision"""
        tracker = CostTracker()
        
        # Add many small costs
        for _ in range(1000):
            tracker.track_cost("openai", "gpt-4o-mini", 1, 1)  # Very cheap
        
        summary = tracker.get_cost_summary(days=30)
        
        # Total cost should be small but non-zero
        assert summary["total_cost"] > 0
        assert summary["total_tokens"] == 2000  # 1000 * (1+1)

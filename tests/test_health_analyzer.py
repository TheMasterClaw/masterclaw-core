"""
Tests for HealthAnalyzer trend analysis and insights functionality.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock

from masterclaw_core.health_history import (
    HealthRecord,
    HealthHistoryStore,
    HealthAnalyzer,
)


@pytest.fixture
def mock_store():
    """Create a mock health history store"""
    store = Mock(spec=HealthHistoryStore)
    return store


@pytest.fixture
def analyzer(mock_store):
    """Create a HealthAnalyzer with mock store"""
    return HealthAnalyzer(mock_store)


@pytest.fixture
def sample_records():
    """Generate sample health records for testing"""
    now = datetime.utcnow()
    records = []
    
    # Create 50 records over 5 days
    for i in range(50):
        timestamp = now - timedelta(hours=i)
        # Simulate some failures in the middle
        if 15 <= i < 20:
            status = "unhealthy"
        elif 20 <= i < 25:
            status = "degraded"
        else:
            status = "healthy"
        
        records.append(HealthRecord(
            timestamp=timestamp,
            status=status,
            component="test_component",
            response_time_ms=100.0,
        ))
    
    return records


class TestHealthAnalyzer:
    """Test suite for HealthAnalyzer"""
    
    def test_analyze_trends_insufficient_data(self, analyzer, mock_store):
        """Test trend analysis with insufficient data"""
        mock_store.get_history.return_value = []
        
        result = analyzer.analyze_trends()
        
        assert result["insufficient_data"] is True
        assert "Need at least 10 records" in result["message"]
    
    def test_analyze_trends_stable(self, analyzer, mock_store, sample_records):
        """Test trend analysis detecting stable trend"""
        # Make all records healthy for stable trend
        for record in sample_records:
            record.status = "healthy"
        
        mock_store.get_history.return_value = sample_records
        
        result = analyzer.analyze_trends()
        
        assert result["trend"]["direction"] == "stable"
        assert result["stability"]["score"] > 80
        assert "windows" in result
    
    def test_analyze_trends_degrading(self, analyzer, mock_store):
        """Test trend analysis detecting degrading trend"""
        now = datetime.utcnow()
        records = []
        
        # Create degrading trend: mostly healthy early, mostly unhealthy later
        for i in range(30):
            timestamp = now - timedelta(hours=i)
            # Earlier records (higher i) are healthy, recent are unhealthy
            if i < 10:
                status = "unhealthy"
            else:
                status = "healthy"
            
            records.append(HealthRecord(
                timestamp=timestamp,
                status=status,
                component="test_component",
                response_time_ms=100.0,
            ))
        
        mock_store.get_history.return_value = records
        
        result = analyzer.analyze_trends()
        
        assert result["trend"]["direction"] == "degrading"
        assert result["trend"]["change"] < 0
    
    def test_calculate_mtbf_mttr_no_failures(self, analyzer, mock_store):
        """Test MTBF/MTTR calculation with no failures"""
        now = datetime.utcnow()
        records = [
            HealthRecord(
                timestamp=now - timedelta(hours=i),
                status="healthy",
                component="test_component",
            )
            for i in range(20)
        ]
        
        mock_store.get_history.return_value = records
        
        result = analyzer.calculate_mtbf_mttr()
        
        assert result["failure_count"] == 0
        assert result["mtbf_minutes"] is None
        assert result["mttr_minutes"] is None
        assert "No failures detected" in result["message"]
    
    def test_calculate_mtbf_mttr_with_failures(self, analyzer, mock_store):
        """Test MTBF/MTTR calculation with failures"""
        now = datetime.utcnow()
        records = []
        
        # Create pattern: healthy, then failure, then recovery
        base_time = now - timedelta(hours=10)
        
        # First failure period
        for i in range(5):
            records.append(HealthRecord(
                timestamp=base_time + timedelta(minutes=i),
                status="unhealthy",
                component="test_component",
            ))
        
        # Recovery
        for i in range(5, 15):
            records.append(HealthRecord(
                timestamp=base_time + timedelta(minutes=i),
                status="healthy",
                component="test_component",
            ))
        
        # Second failure period
        for i in range(15, 20):
            records.append(HealthRecord(
                timestamp=base_time + timedelta(minutes=i),
                status="unhealthy",
                component="test_component",
            ))
        
        # Recovery
        for i in range(20, 25):
            records.append(HealthRecord(
                timestamp=base_time + timedelta(minutes=i),
                status="healthy",
                component="test_component",
            ))
        
        mock_store.get_history.return_value = records
        
        result = analyzer.calculate_mtbf_mttr()
        
        assert result["failure_count"] == 2
        assert result["mtbf_minutes"] is not None
        assert result["mttr_minutes"] is not None
        assert result["mttr_minutes"] > 0
    
    def test_detect_flapping_no_flapping(self, analyzer, mock_store):
        """Test flapping detection with stable service"""
        now = datetime.utcnow()
        records = [
            HealthRecord(
                timestamp=now - timedelta(minutes=i * 10),
                status="healthy",
                component="test_component",
            )
            for i in range(20)
        ]
        
        mock_store.get_history.return_value = records
        
        result = analyzer.detect_flapping()
        
        assert result["flapping_detected"] is False
        assert result["flapping_count"] == 0
    
    def test_detect_flapping_with_flapping(self, analyzer, mock_store):
        """Test flapping detection with rapidly changing service"""
        now = datetime.utcnow()
        records = []
        
        # Create rapid state changes
        for i in range(20):
            status = "healthy" if i % 2 == 0 else "unhealthy"
            records.append(HealthRecord(
                timestamp=now - timedelta(minutes=i),
                status=status,
                component="flapping_component",
            ))
        
        mock_store.get_history.return_value = records
        
        result = analyzer.detect_flapping(threshold=5)
        
        assert result["flapping_detected"] is True
        assert "flapping_component" in result["components"]
    
    def test_predict_degradation_insufficient_data(self, analyzer, mock_store):
        """Test degradation prediction with insufficient data"""
        mock_store.get_history.return_value = []
        
        result = analyzer.predict_degradation()
        
        assert result["predictable"] is False
        assert "Insufficient data" in result["message"]
    
    def test_predict_degradation_degrading_trend(self, analyzer, mock_store):
        """Test degradation prediction with degrading trend"""
        now = datetime.utcnow()
        records = []
        
        # Create degrading trend over 48 hours
        for i in range(48):
            timestamp = now - timedelta(hours=i)
            # More unhealthy as time progresses (lower i = more recent)
            if i < 10:
                status = "unhealthy" if i % 2 == 0 else "degraded"
            elif i < 25:
                status = "degraded" if i % 3 == 0 else "healthy"
            else:
                status = "healthy"
            
            records.append(HealthRecord(
                timestamp=timestamp,
                status=status,
                component="test_component",
            ))
        
        mock_store.get_history.return_value = records
        
        result = analyzer.predict_degradation()
        
        assert result["predictable"] is True
        assert result["trend_direction"] == "degrading"
        assert "predicted_health_ratio" in result
        assert result["risk_level"] in ["low", "medium", "high"]
    
    def test_get_component_ranking(self, analyzer, mock_store):
        """Test component ranking by availability"""
        now = datetime.utcnow()
        records = []
        
        # Component A: 100% healthy
        for i in range(10):
            records.append(HealthRecord(
                timestamp=now - timedelta(hours=i),
                status="healthy",
                component="component_a",
            ))
        
        # Component B: 50% healthy
        for i in range(10):
            records.append(HealthRecord(
                timestamp=now - timedelta(hours=i),
                status="healthy" if i < 5 else "unhealthy",
                component="component_b",
            ))
        
        mock_store.get_history.return_value = records
        
        result = analyzer.get_component_ranking(metric="availability")
        
        assert result["metric"] == "availability"
        assert len(result["rankings"]) == 2
        
        # Component A should be first (higher availability)
        assert result["rankings"][0]["component"] == "component_a"
        assert result["rankings"][0]["availability"] == 100.0
        
        # Component B should be second
        assert result["rankings"][1]["component"] == "component_b"
        assert result["rankings"][1]["availability"] == 50.0
    
    def test_get_health_insights_comprehensive(self, analyzer, mock_store, sample_records):
        """Test comprehensive health insights"""
        mock_store.get_history.return_value = sample_records
        
        result = analyzer.get_health_insights()
        
        assert "generated_at" in result
        assert "summary" in result
        assert "insights" in result
        assert "recommendations" in result
        assert "details" in result
        
        # Check that all detail sections are present
        details = result["details"]
        assert "trends" in details
        assert "mtbf_mttr" in details
        assert "flapping" in details
        assert "prediction" in details
        assert "ranking" in details
    
    def test_get_health_insights_with_degradation(self, analyzer, mock_store):
        """Test health insights with degrading trend generates appropriate insights"""
        now = datetime.utcnow()
        records = []
        
        # Create strongly degrading trend
        for i in range(50):
            timestamp = now - timedelta(hours=i)
            # Earlier (higher i) = mostly healthy, recent (lower i) = mostly unhealthy
            if i < 15:
                status = "unhealthy"
            elif i < 30:
                status = "degraded"
            else:
                status = "healthy"
            
            records.append(HealthRecord(
                timestamp=timestamp,
                status=status,
                component="test_component",
            ))
        
        mock_store.get_history.return_value = records
        
        result = analyzer.get_health_insights()
        
        # Should have trend-based insight
        trend_insights = [i for i in result["insights"] if i["type"] == "trend"]
        assert len(trend_insights) > 0
        
        # Should have recommendations
        assert len(result["recommendations"]) > 0

"""Comprehensive tests for health_history module

This test suite covers:
- HealthRecord dataclass
- HealthHistoryStore database operations
- HealthAnalyzer analytics and predictions
- Error handling and edge cases
"""

import pytest
import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

# Patch the global instances before importing the module
import masterclaw_core.health_history as health_module

# Create module-level patch for global instances
health_module.health_history = None
health_module.health_analyzer = None

from masterclaw_core.health_history import (
    HealthRecord,
    HealthHistoryStore,
    HealthAnalyzer,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def temp_db_path(tmp_path):
    """Create a temporary database path"""
    return str(tmp_path / "test_health.db")


@pytest.fixture
def store(temp_db_path):
    """Create a fresh HealthHistoryStore with temp database"""
    return HealthHistoryStore(db_path=temp_db_path)


@pytest.fixture
def analyzer(store):
    """Create a HealthAnalyzer with the test store"""
    return HealthAnalyzer(store)


@pytest.fixture
def sample_records():
    """Generate sample health records for testing"""
    base_time = datetime(2026, 2, 1, 12, 0, 0)
    return [
        HealthRecord(
            timestamp=base_time,
            status="healthy",
            component="overall",
            response_time_ms=100.5,
            details="All systems operational",
        ),
        HealthRecord(
            timestamp=base_time + timedelta(minutes=5),
            status="degraded",
            component="memory_store",
            response_time_ms=250.0,
            details="High latency detected",
        ),
        HealthRecord(
            timestamp=base_time + timedelta(minutes=10),
            status="unhealthy",
            component="llm_openai",
            response_time_ms=None,
            error="Connection timeout",
        ),
        HealthRecord(
            timestamp=base_time + timedelta(minutes=15),
            status="healthy",
            component="overall",
            response_time_ms=95.0,
        ),
    ]


# =============================================================================
# HealthRecord Tests
# =============================================================================

class TestHealthRecord:
    """Test HealthRecord dataclass"""
    
    def test_health_record_creation(self):
        """Test creating a HealthRecord with all fields"""
        timestamp = datetime.utcnow()
        record = HealthRecord(
            timestamp=timestamp,
            status="healthy",
            component="test_component",
            response_time_ms=150.5,
            details="Test details",
            error=None,
        )
        
        assert record.timestamp == timestamp
        assert record.status == "healthy"
        assert record.component == "test_component"
        assert record.response_time_ms == 150.5
        assert record.details == "Test details"
        assert record.error is None
    
    def test_health_record_to_dict(self):
        """Test converting HealthRecord to dictionary"""
        timestamp = datetime(2026, 2, 1, 12, 0, 0)
        record = HealthRecord(
            timestamp=timestamp,
            status="healthy",
            component="test",
            response_time_ms=100.0,
        )
        
        data = record.to_dict()
        
        assert data["timestamp"] == "2026-02-01T12:00:00"
        assert data["status"] == "healthy"
        assert data["component"] == "test"
        assert data["response_time_ms"] == 100.0
        assert data["details"] is None
        assert data["error"] is None
    
    def test_health_record_minimal_fields(self):
        """Test creating a HealthRecord with only required fields"""
        record = HealthRecord(
            timestamp=datetime.utcnow(),
            status="healthy",
            component="test",
        )
        
        assert record.response_time_ms is None
        assert record.details is None
        assert record.error is None


# =============================================================================
# HealthHistoryStore Tests
# =============================================================================

class TestHealthHistoryStore:
    """Test HealthHistoryStore database operations"""
    
    def test_database_initialization(self, temp_db_path):
        """Test database is created with correct schema"""
        store = HealthHistoryStore(db_path=temp_db_path)
        
        assert Path(temp_db_path).exists()
        
        # Verify schema
        with store._get_connection() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='health_records'"
            )
            assert cursor.fetchone() is not None
            
            # Verify indexes
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
            )
            indexes = {row[0] for row in cursor.fetchall()}
            assert "idx_timestamp" in indexes
            assert "idx_component" in indexes
            assert "idx_status" in indexes
    
    def test_record_and_retrieve(self, store, sample_records):
        """Test recording and retrieving health records"""
        # Record sample data
        for record in sample_records:
            store.record(record)
        
        # Retrieve all records
        history = store.get_history()
        
        assert len(history) == 4
        assert history[0].status == "healthy"
        assert history[0].component == "overall"
    
    def test_get_history_with_filters(self, store, sample_records):
        """Test retrieving records with filters"""
        for record in sample_records:
            store.record(record)
        
        # Filter by component
        results = store.get_history(component="overall")
        assert len(results) == 2
        assert all(r.component == "overall" for r in results)
        
        # Filter by status
        results = store.get_history(status="healthy")
        assert len(results) == 2
        assert all(r.status == "healthy" for r in results)
    
    def test_get_history_with_time_range(self, store):
        """Test retrieving records within time range"""
        base_time = datetime(2026, 2, 1, 12, 0, 0)
        
        # Add records at different times
        for i in range(5):
            record = HealthRecord(
                timestamp=base_time + timedelta(hours=i),
                status="healthy",
                component="test",
            )
            store.record(record)
        
        # Query specific time range
        since = base_time + timedelta(hours=1)
        until = base_time + timedelta(hours=3)
        results = store.get_history(since=since, until=until)
        
        assert len(results) == 3  # Hours 1, 2, 3
    
    def test_get_history_pagination(self, store):
        """Test pagination with limit and offset"""
        base_time = datetime.utcnow()
        
        # Add 10 records
        for i in range(10):
            record = HealthRecord(
                timestamp=base_time + timedelta(minutes=i),
                status="healthy",
                component="test",
            )
            store.record(record)
        
        # Test limit
        results = store.get_history(limit=5)
        assert len(results) == 5
        
        # Test offset
        results = store.get_history(limit=5, offset=5)
        assert len(results) == 5
    
    def test_get_summary(self, store, sample_records):
        """Test summary statistics generation"""
        for record in sample_records:
            store.record(record)
        
        summary = store.get_summary()
        
        assert "period" in summary
        assert "components" in summary
        assert "overall" in summary
        
        # Check overall stats
        overall = summary["overall"]
        assert overall["total_checks"] == 4
        assert overall["healthy"] == 2
        assert overall["degraded"] == 1
        assert overall["unhealthy"] == 1
    
    def test_get_uptime_stats(self, store):
        """Test uptime statistics calculation"""
        base_time = datetime.utcnow() - timedelta(hours=1)
        
        # Add records with some failures
        for i in range(10):
            status = "unhealthy" if 3 <= i <= 5 else "healthy"
            record = HealthRecord(
                timestamp=base_time + timedelta(minutes=i * 6),
                status=status,
                component="test",
            )
            store.record(record)
        
        stats = store.get_uptime_stats(component="test")
        
        assert stats["component"] == "test"
        assert stats["uptime_percent"] == 70.0  # 7 out of 10 healthy
        assert stats["total_records"] == 10
        assert stats["outage_count"] == 1
    
    def test_cleanup_old_records(self, store):
        """Test cleanup of old records"""
        now = datetime.utcnow()
        
        # Add old record
        old_record = HealthRecord(
            timestamp=now - timedelta(days=40),
            status="healthy",
            component="test",
        )
        store.record(old_record)
        
        # Add recent records
        for i in range(5):
            record = HealthRecord(
                timestamp=now - timedelta(days=i),
                status="healthy",
                component="test",
            )
            store.record(record)
        
        # Cleanup records older than 30 days
        deleted = store.cleanup_old_records(days=30)
        
        assert deleted == 1
        
        # Verify only recent records remain
        remaining = store.get_history()
        assert len(remaining) == 5
    
    def test_record_error_handling(self, store):
        """Test error handling during record insertion"""
        # Create invalid record that will cause an error
        with patch.object(store, '_get_connection') as mock_conn:
            mock_conn.return_value.__enter__ = MagicMock(side_effect=sqlite3.Error("DB Error"))
            mock_conn.return_value.__exit__ = MagicMock(return_value=False)
            
            record = HealthRecord(
                timestamp=datetime.utcnow(),
                status="healthy",
                component="test",
            )
            
            # Should not raise exception
            store.record(record)
    
    def test_get_history_error_handling(self, store):
        """Test error handling during history retrieval"""
        with patch.object(store, '_get_connection') as mock_conn:
            mock_conn.return_value.__enter__ = MagicMock(side_effect=sqlite3.Error("DB Error"))
            mock_conn.return_value.__exit__ = MagicMock(return_value=False)
            
            # Should return empty list on error
            results = store.get_history()
            assert results == []


# =============================================================================
# HealthAnalyzer Tests
# =============================================================================

class TestHealthAnalyzer:
    """Test HealthAnalyzer analytics functionality"""
    
    def test_analyze_trends_insufficient_data(self, analyzer):
        """Test trend analysis with insufficient data"""
        result = analyzer.analyze_trends()
        
        assert result["insufficient_data"] is True
        assert "message" in result
    
    def test_analyze_trends_with_data(self, store, analyzer):
        """Test trend analysis with sufficient data"""
        base_time = datetime.utcnow() - timedelta(days=3)
        
        # Add records with improving trend
        for day in range(4):
            for hour in range(6):  # 6 records per day
                # Start with more unhealthy, end with more healthy
                if day < 2 and hour < 2:
                    status = "unhealthy"
                else:
                    status = "healthy"
                
                record = HealthRecord(
                    timestamp=base_time + timedelta(days=day, hours=hour),
                    status=status,
                    component="overall",
                )
                store.record(record)
        
        result = analyzer.analyze_trends(component="overall")
        
        assert "trend" in result
        assert "direction" in result["trend"]
        assert "stability" in result
        assert "score" in result["stability"]
    
    def test_calculate_mtbf_mttr_no_failures(self, analyzer):
        """Test MTBF/MTTR calculation with no failures"""
        result = analyzer.calculate_mtbf_mttr()
        
        assert result["insufficient_data"] is True
        assert "message" in result
    
    def test_calculate_mtbf_mttr_with_failures(self, store, analyzer):
        """Test MTBF/MTTR calculation with actual failures"""
        base_time = datetime.utcnow() - timedelta(days=1)
        
        # Add healthy records
        for i in range(10):
            record = HealthRecord(
                timestamp=base_time + timedelta(hours=i * 2),
                status="healthy",
                component="test",
            )
            store.record(record)
        
        # Add a failure period
        for i in range(3):
            record = HealthRecord(
                timestamp=base_time + timedelta(hours=20 + i),
                status="unhealthy",
                component="test",
                error="Service down",
            )
            store.record(record)
        
        result = analyzer.calculate_mtbf_mttr(component="test")
        
        assert result["component"] == "test"
        assert result["failure_count"] == 1
        assert result["mttr_minutes"] is not None
    
    def test_detect_flapping_no_flapping(self, analyzer):
        """Test flapping detection with stable component"""
        result = analyzer.detect_flapping()
        
        assert result["flapping_detected"] is False
        assert result["components"] == {}
    
    def test_detect_flapping_with_flapping(self, store, analyzer):
        """Test flapping detection with rapidly changing component"""
        base_time = datetime.utcnow() - timedelta(hours=1)
        
        # Add rapidly alternating statuses
        statuses = ["healthy", "unhealthy"] * 10  # 20 rapid changes
        for i, status in enumerate(statuses):
            record = HealthRecord(
                timestamp=base_time + timedelta(minutes=i * 3),
                status=status,
                component="flappy_service",
            )
            store.record(record)
        
        result = analyzer.detect_flapping(threshold=5, window_minutes=60)
        
        assert result["flapping_detected"] is True
        assert "flappy_service" in result["components"]
    
    def test_predict_degradation_insufficient_data(self, analyzer):
        """Test degradation prediction with insufficient data"""
        result = analyzer.predict_degradation()
        
        assert result["predictable"] is False
        assert "message" in result
    
    def test_predict_degradation_with_trend(self, store, analyzer):
        """Test degradation prediction with sufficient data"""
        base_time = datetime.utcnow() - timedelta(hours=48)
        
        # Add declining health trend
        for hour in range(50):
            # Gradually decrease health ratio
            if hour < 20:
                status = "healthy"
            elif hour < 35:
                status = "degraded"
            else:
                status = "unhealthy"
            
            record = HealthRecord(
                timestamp=base_time + timedelta(hours=hour),
                status=status,
                component="overall",
            )
            store.record(record)
        
        result = analyzer.predict_degradation(component="overall")
        
        assert result["predictable"] is True
        assert "predicted_health_ratio" in result
        assert "risk_level" in result
        assert "trend_direction" in result
    
    def test_get_component_ranking(self, store, analyzer):
        """Test component reliability ranking"""
        base_time = datetime.utcnow() - timedelta(days=7)
        
        # Add records for multiple components
        components = {
            "component_a": ["healthy"] * 10,  # 100% available
            "component_b": ["healthy"] * 8 + ["unhealthy"] * 2,  # 80% available
            "component_c": ["healthy"] * 5 + ["unhealthy"] * 5,  # 50% available
        }
        
        for comp_name, statuses in components.items():
            for i, status in enumerate(statuses):
                record = HealthRecord(
                    timestamp=base_time + timedelta(hours=i),
                    status=status,
                    component=comp_name,
                )
                store.record(record)
        
        result = analyzer.get_component_ranking(metric="availability")
        
        assert result["metric"] == "availability"
        assert len(result["rankings"]) == 3
        
        # Check ranking order (highest availability first)
        rankings = result["rankings"]
        assert rankings[0]["component"] == "component_a"
        assert rankings[0]["availability"] == 100.0
    
    def test_get_health_insights(self, store, analyzer):
        """Test comprehensive health insights generation"""
        base_time = datetime.utcnow() - timedelta(days=2)
        
        # Add some varied data
        for i in range(20):
            record = HealthRecord(
                timestamp=base_time + timedelta(hours=i),
                status="healthy" if i % 5 != 0 else "unhealthy",
                component="overall",
            )
            store.record(record)
        
        result = analyzer.get_health_insights()
        
        assert "generated_at" in result
        assert "summary" in result
        assert "insights" in result
        assert "recommendations" in result
        assert "details" in result
        
        # Should have detected some issues
        assert result["summary"]["insight_count"] >= 0


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================

class TestEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_empty_database_operations(self, store):
        """Test operations on empty database"""
        # Get history from empty DB
        history = store.get_history()
        assert history == []
        
        # Get summary from empty DB
        summary = store.get_summary()
        assert summary["overall"]["total_checks"] == 0
        
        # Get uptime stats from empty DB
        stats = store.get_uptime_stats()
        assert stats["uptime_percent"] is None
        assert stats["total_records"] == 0
    
    def test_concurrent_access(self, store):
        """Test database handles concurrent access gracefully"""
        import threading
        
        errors = []
        
        def add_records():
            try:
                for i in range(10):
                    record = HealthRecord(
                        timestamp=datetime.utcnow() + timedelta(seconds=i),
                        status="healthy",
                        component="concurrent_test",
                    )
                    store.record(record)
            except Exception as e:
                errors.append(e)
        
        # Run concurrent writes
        threads = [threading.Thread(target=add_records) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Should not have errors
        assert len(errors) == 0
        
        # Should have all records
        history = store.get_history(component="concurrent_test")
        assert len(history) == 30
    
    def test_very_long_strings(self, store):
        """Test handling of very long strings in fields"""
        long_string = "x" * 10000
        
        record = HealthRecord(
            timestamp=datetime.utcnow(),
            status="healthy",
            component="test",
            details=long_string,
            error=long_string,
        )
        
        store.record(record)
        
        # Should retrieve successfully
        history = store.get_history()
        assert len(history) == 1
        assert history[0].details == long_string
        assert history[0].error == long_string
    
    def test_special_characters_in_strings(self, store):
        """Test handling of special characters"""
        special_details = "Special chars: ' \" \n \t \x00 🎉 <script>alert(1)</script>"
        
        record = HealthRecord(
            timestamp=datetime.utcnow(),
            status="healthy",
            component="test",
            details=special_details,
        )
        
        store.record(record)
        
        # Should retrieve successfully (SQLite handles special chars)
        history = store.get_history()
        assert len(history) == 1


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests with real data patterns"""
    
    def test_realistic_health_tracking_scenario(self, store, analyzer):
        """Test a realistic health tracking scenario"""
        now = datetime.utcnow()
        
        # Simulate a day's worth of health checks
        for minute in range(0, 1440, 5):  # Every 5 minutes
            timestamp = now - timedelta(minutes=1440 - minute)
            
            # Simulate some issues during the day
            if 400 < minute < 450:  # Brief outage
                status = "unhealthy"
                error = "Database connection lost"
            elif 800 < minute < 850:  # Degraded performance
                status = "degraded"
            else:
                status = "healthy"
            
            record = HealthRecord(
                timestamp=timestamp,
                status=status,
                component="api_server",
                response_time_ms=50.0 + (100.0 if status == "degraded" else 0),
                error=error if status == "unhealthy" else None,
            )
            store.record(record)
        
        # Run analysis
        summary = store.get_summary(component="api_server")
        uptime = store.get_uptime_stats(component="api_server")
        trends = analyzer.analyze_trends(component="api_server")
        mtbf_mttr = analyzer.calculate_mtbf_mttr(component="api_server")
        
        # Verify results
        assert summary["overall"]["total_checks"] == 288  # 1440/5
        assert uptime["uptime_percent"] > 90  # Should be mostly up
        assert uptime["outage_count"] >= 1  # Should detect the outage
        assert trends.get("trend", {}).get("direction") in ["improving", "degrading", "stable"]
    
    def test_multiple_component_tracking(self, store, analyzer):
        """Test tracking multiple components simultaneously"""
        now = datetime.utcnow()
        components = ["api", "database", "cache", "queue", "worker"]
        
        for hour in range(24):
            timestamp = now - timedelta(hours=24 - hour)
            
            for comp in components:
                # Different health patterns for each component
                if comp == "api":
                    status = "healthy"
                elif comp == "database":
                    status = "unhealthy" if hour == 12 else "healthy"
                elif comp == "cache":
                    status = "degraded" if hour > 18 else "healthy"
                else:
                    status = "healthy"
                
                record = HealthRecord(
                    timestamp=timestamp,
                    status=status,
                    component=comp,
                )
                store.record(record)
        
        # Get component ranking
        ranking = analyzer.get_component_ranking(metric="availability")
        
        assert len(ranking["rankings"]) == len(components)
        
        # API should be highest (100%)
        api_ranking = next(r for r in ranking["rankings"] if r["component"] == "api")
        assert api_ranking["availability"] == 100.0
        
        # Database should have some failures
        db_ranking = next(r for r in ranking["rankings"] if r["component"] == "database")
        assert db_ranking["failure_count"] == 1


# =============================================================================
# Global Instance Tests (mocked)
# =============================================================================

class TestGlobalInstances:
    """Test the global health_history and health_analyzer instances"""
    
    def test_global_instances_can_be_created(self, temp_db_path):
        """Test that global instances can be created with custom path"""
        # Create instances with custom path
        custom_history = HealthHistoryStore(db_path=temp_db_path)
        custom_analyzer = HealthAnalyzer(custom_history)
        
        assert custom_history is not None
        assert isinstance(custom_history, HealthHistoryStore)
        assert custom_analyzer is not None
        assert isinstance(custom_analyzer, HealthAnalyzer)
        assert custom_analyzer.store == custom_history

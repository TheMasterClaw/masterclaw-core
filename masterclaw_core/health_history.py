"""
Health Check History Tracking

Tracks health check results over time for debugging intermittent issues
and monitoring service reliability.
"""

import json
import logging
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from contextlib import contextmanager

logger = logging.getLogger("masterclaw.health_history")

# Default database path - uses environment variable or falls back to local data directory
DEFAULT_HEALTH_DB_PATH = os.getenv(
    "HEALTH_HISTORY_DB_PATH",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "health_history.db")
)


@dataclass
class HealthRecord:
    """A single health check record"""
    timestamp: datetime
    status: str  # "healthy", "degraded", "unhealthy"
    component: str  # "overall", "memory_store", "llm_*", "task_queue", etc.
    response_time_ms: Optional[float] = None
    details: Optional[str] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "status": self.status,
            "component": self.component,
            "response_time_ms": self.response_time_ms,
            "details": self.details,
            "error": self.error,
        }


class HealthHistoryStore:
    """Store and retrieve health check history
    
    The database path can be configured via the HEALTH_HISTORY_DB_PATH
    environment variable. Defaults to ./data/health_history.db relative
    to the workspace root.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize the health history store.
        
        Args:
            db_path: Path to the SQLite database file. If None, uses
                    the HEALTH_HISTORY_DB_PATH environment variable
                    or falls back to a default local path.
        """
        self.db_path = Path(db_path or DEFAULT_HEALTH_DB_PATH)
        self._init_db()
    
    @contextmanager
    def _get_connection(self):
        """Get a database connection with proper cleanup"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def _init_db(self):
        """Initialize the database schema
        
        Creates the database directory if it doesn't exist and sets up
        the required tables and indexes. Logs warnings on permission errors
        but does not crash to allow the application to start even if
        health history tracking is unavailable.
        """
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            logger.warning(
                f"Cannot create health history directory: {self.db_path.parent}. "
                f"Health history tracking will be disabled. "
                f"Set HEALTH_HISTORY_DB_PATH to a writable location."
            )
            self._db_available = False
            return
        except OSError as e:
            logger.error(f"Failed to initialize health history database directory: {e}")
            self._db_available = False
            return
        
        self._db_available = True
        
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS health_records (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        status TEXT NOT NULL,
                        component TEXT NOT NULL,
                        response_time_ms REAL,
                        details TEXT,
                        error TEXT
                    )
                """)
                
                # Create indexes for efficient queries
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_timestamp 
                    ON health_records(timestamp)
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_component 
                    ON health_records(component)
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_status 
                    ON health_records(status)
                """)
                
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Failed to initialize health history database schema: {e}")
            self._db_available = False
    
    def record(self, record: HealthRecord) -> None:
        """Record a health check result
        
        If the database is not available (e.g., due to permission issues),
        the record is silently dropped and an error is logged.
        """
        if not getattr(self, '_db_available', False):
            logger.debug("Health history database not available, skipping record")
            return
            
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT INTO health_records 
                    (timestamp, status, component, response_time_ms, details, error)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    record.timestamp.isoformat(),
                    record.status,
                    record.component,
                    record.response_time_ms,
                    record.details,
                    record.error,
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to record health check: {e}")
    
    def get_history(
        self,
        component: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[HealthRecord]:
        """Retrieve health check history with filters

        Returns empty list if the database is not available.
        """
        if not getattr(self, '_db_available', False):
            logger.debug("Health history database not available, returning empty history")
            return []

        query = "SELECT * FROM health_records WHERE 1=1"
        params = []

        if component:
            query += " AND component = ?"
            params.append(component)

        if since:
            query += " AND timestamp >= ?"
            params.append(since.isoformat())

        if until:
            query += " AND timestamp <= ?"
            params.append(until.isoformat())

        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        try:
            with self._get_connection() as conn:
                rows = conn.execute(query, params).fetchall()

                return [
                    HealthRecord(
                        timestamp=datetime.fromisoformat(row["timestamp"]),
                        status=row["status"],
                        component=row["component"],
                        response_time_ms=row["response_time_ms"],
                        details=row["details"],
                        error=row["error"],
                    )
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Failed to retrieve health history: {e}")
            return []
    
    def get_summary(
        self,
        since: Optional[datetime] = None,
        component: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get a summary of health status over time
        
        Returns empty dict with error metadata if database is not available.
        """
        if not getattr(self, '_db_available', False):
            logger.debug("Health history database not available, returning empty summary")
            return {
                "period": {},
                "components": {},
                "overall": {
                    "total_checks": 0,
                    "healthy": 0,
                    "degraded": 0,
                    "unhealthy": 0,
                    "availability_percent": 0.0,
                },
                "error": "Database not available",
            }

        if since is None:
            since = datetime.utcnow() - timedelta(hours=24)
        
        query = """
            SELECT 
                component,
                status,
                COUNT(*) as count,
                AVG(response_time_ms) as avg_response_time,
                MIN(timestamp) as first_seen,
                MAX(timestamp) as last_seen
            FROM health_records
            WHERE timestamp >= ?
        """
        params = [since.isoformat()]
        
        if component:
            query += " AND component = ?"
            params.append(component)
        
        query += " GROUP BY component, status"
        
        try:
            with self._get_connection() as conn:
                rows = conn.execute(query, params).fetchall()
                
                summary = {
                    "period": {
                        "since": since.isoformat(),
                        "until": datetime.utcnow().isoformat(),
                    },
                    "components": {},
                    "overall": {
                        "total_checks": 0,
                        "healthy": 0,
                        "degraded": 0,
                        "unhealthy": 0,
                        "availability_percent": 0.0,
                    },
                }
                
                for row in rows:
                    comp_name = row["component"]
                    if comp_name not in summary["components"]:
                        summary["components"][comp_name] = {
                            "total": 0,
                            "healthy": 0,
                            "degraded": 0,
                            "unhealthy": 0,
                            "avg_response_time_ms": row["avg_response_time"],
                            "first_seen": row["first_seen"],
                            "last_seen": row["last_seen"],
                        }
                    
                    summary["components"][comp_name][row["status"]] = row["count"]
                    summary["components"][comp_name]["total"] += row["count"]
                    
                    # Update overall stats
                    summary["overall"]["total_checks"] += row["count"]
                    summary["overall"][row["status"]] += row["count"]
                
                # Calculate availability percentage
                total = summary["overall"]["total_checks"]
                if total > 0:
                    healthy_degraded = summary["overall"]["healthy"] + summary["overall"]["degraded"]
                    summary["overall"]["availability_percent"] = round((healthy_degraded / total) * 100, 2)
                
                return summary
                
        except Exception as e:
            logger.error(f"Failed to get health summary: {e}")
            return {}
    
    def get_uptime_stats(
        self,
        component: str = "overall",
        since: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Calculate uptime statistics for a component
        
        Returns empty stats with error metadata if database is not available.
        """
        if not getattr(self, '_db_available', False):
            logger.debug("Health history database not available, returning empty uptime stats")
            return {
                "component": component,
                "period": {},
                "uptime_percent": None,
                "total_records": 0,
                "error": "Database not available",
            }

        if since is None:
            since = datetime.utcnow() - timedelta(days=7)
        
        try:
            with self._get_connection() as conn:
                # Get all records for the component in the time period
                rows = conn.execute("""
                    SELECT timestamp, status
                    FROM health_records
                    WHERE component = ? AND timestamp >= ?
                    ORDER BY timestamp ASC
                """, (component, since.isoformat())).fetchall()
                
                if not rows:
                    return {
                        "component": component,
                        "period": {"since": since.isoformat()},
                        "uptime_percent": None,
                        "total_records": 0,
                    }
                
                # Calculate uptime (healthy + degraded count as up)
                up_count = sum(1 for r in rows if r["status"] in ("healthy", "degraded"))
                total = len(rows)
                
                # Find outages (consecutive unhealthy records)
                outages = []
                current_outage_start = None
                
                for row in rows:
                    if row["status"] == "unhealthy":
                        if current_outage_start is None:
                            current_outage_start = row["timestamp"]
                    else:
                        if current_outage_start is not None:
                            outages.append({
                                "started": current_outage_start,
                                "ended": row["timestamp"],
                            })
                            current_outage_start = None
                
                # Handle ongoing outage
                if current_outage_start is not None:
                    outages.append({
                        "started": current_outage_start,
                        "ended": None,
                        "ongoing": True,
                    })
                
                return {
                    "component": component,
                    "period": {
                        "since": since.isoformat(),
                        "until": rows[-1]["timestamp"] if rows else None,
                    },
                    "uptime_percent": round((up_count / total) * 100, 2) if total > 0 else 0,
                    "total_records": total,
                    "outages": outages,
                    "outage_count": len(outages),
                }
                
        except Exception as e:
            logger.error(f"Failed to get uptime stats: {e}")
            return {}
    
    def cleanup_old_records(self, days: int = 30) -> int:
        """Remove records older than specified days
        
        Returns 0 if database is not available.
        """
        if not getattr(self, '_db_available', False):
            logger.debug("Health history database not available, skipping cleanup")
            return 0

        cutoff = datetime.utcnow() - timedelta(days=days)
        
        try:
            with self._get_connection() as conn:
                result = conn.execute(
                    "DELETE FROM health_records WHERE timestamp < ?",
                    (cutoff.isoformat(),)
                )
                conn.commit()
                deleted = result.rowcount
                logger.info(f"Cleaned up {deleted} old health records")
                return deleted
        except Exception as e:
            logger.error(f"Failed to cleanup old records: {e}")
            return 0


class HealthAnalyzer:
    """
    Analyze health trends and patterns to provide actionable insights.
    
    Features:
    - Trend direction detection (improving/degrading/stable)
    - MTBF (Mean Time Between Failures) calculation
    - MTTR (Mean Time To Recovery) calculation
    - Flapping detection (rapid state changes)
    - Degradation prediction
    - Component reliability ranking
    """
    
    def __init__(self, store: HealthHistoryStore):
        self.store = store
    
    def analyze_trends(
        self,
        component: Optional[str] = None,
        since: Optional[datetime] = None,
        window_hours: int = 24,
    ) -> Dict[str, Any]:
        """
        Analyze health trends over time.
        
        Returns trend direction, change rate, and stability metrics.
        """
        if since is None:
            since = datetime.utcnow() - timedelta(days=7)
        
        records = self.store.get_history(
            component=component,
            since=since,
            limit=10000,
        )
        
        if len(records) < 10:
            return {
                "component": component or "all",
                "insufficient_data": True,
                "message": f"Need at least 10 records, found {len(records)}",
            }
        
        # Sort by timestamp
        records.sort(key=lambda r: r.timestamp)
        
        # Split into windows for trend analysis
        now = datetime.utcnow()
        window_size = timedelta(hours=window_hours)
        
        windows = []
        current_window_start = since
        
        while current_window_start < now:
            window_end = min(current_window_start + window_size, now)
            window_records = [
                r for r in records
                if current_window_start <= r.timestamp < window_end
            ]
            
            if window_records:
                healthy_count = sum(1 for r in window_records if r.status == "healthy")
                total = len(window_records)
                health_ratio = healthy_count / total if total > 0 else 0
                
                windows.append({
                    "start": current_window_start.isoformat(),
                    "end": window_end.isoformat(),
                    "health_ratio": health_ratio,
                    "total_checks": total,
                    "healthy": healthy_count,
                    "unhealthy": sum(1 for r in window_records if r.status == "unhealthy"),
                })
            
            current_window_start = window_end
        
        if len(windows) < 2:
            return {
                "component": component or "all",
                "insufficient_data": True,
                "message": "Need at least 2 time windows for trend analysis",
            }
        
        # Calculate trend direction
        recent_ratio = windows[-1]["health_ratio"] if windows else 0
        previous_ratio = windows[-2]["health_ratio"] if len(windows) >= 2 else recent_ratio
        
        # Compare first half vs second half for overall trend
        mid_point = len(windows) // 2
        first_half_avg = sum(w["health_ratio"] for w in windows[:mid_point]) / mid_point if mid_point > 0 else 0
        second_half_avg = sum(w["health_ratio"] for w in windows[mid_point:]) / (len(windows) - mid_point) if len(windows) > mid_point else 0
        
        # Determine trend direction
        trend_change = second_half_avg - first_half_avg
        if trend_change > 0.1:
            trend_direction = "improving"
        elif trend_change < -0.1:
            trend_direction = "degrading"
        else:
            trend_direction = "stable"
        
        # Calculate volatility (standard deviation of health ratios)
        if len(windows) >= 2:
            mean_ratio = sum(w["health_ratio"] for w in windows) / len(windows)
            variance = sum((w["health_ratio"] - mean_ratio) ** 2 for w in windows) / len(windows)
            volatility = variance ** 0.5
        else:
            volatility = 0
        
        # Stability score (0-100)
        stability_score = max(0, min(100, 100 - (volatility * 100)))
        
        return {
            "component": component or "all",
            "period": {
                "since": since.isoformat(),
                "until": now.isoformat(),
            },
            "windows": windows,
            "trend": {
                "direction": trend_direction,
                "change": round(trend_change, 3),
                "current_health_ratio": round(recent_ratio, 3),
                "previous_health_ratio": round(previous_ratio, 3),
            },
            "stability": {
                "score": round(stability_score, 1),
                "volatility": round(volatility, 3),
                "classification": "stable" if stability_score > 80 else "moderate" if stability_score > 50 else "unstable",
            },
        }
    
    def calculate_mtbf_mttr(
        self,
        component: str = "overall",
        since: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Calculate MTBF (Mean Time Between Failures) and MTTR (Mean Time To Recovery).
        
        MTBF: Average time between the start of failures
        MTTR: Average time to recover from a failure
        """
        if since is None:
            since = datetime.utcnow() - timedelta(days=30)
        
        records = self.store.get_history(
            component=component,
            since=since,
            limit=10000,
        )
        
        if not records:
            return {
                "component": component,
                "insufficient_data": True,
                "message": "No records found for the specified period",
            }
        
        # Sort by timestamp
        records.sort(key=lambda r: r.timestamp)
        
        # Find failure periods (consecutive unhealthy records)
        failures = []
        current_failure_start = None
        last_failure_end = None
        
        for i, record in enumerate(records):
            if record.status == "unhealthy":
                if current_failure_start is None:
                    current_failure_start = record.timestamp
            else:
                if current_failure_start is not None:
                    failure_end = record.timestamp
                    failures.append({
                        "started": current_failure_start,
                        "ended": failure_end,
                        "duration_minutes": (failure_end - current_failure_start).total_seconds() / 60,
                    })
                    last_failure_end = failure_end
                    current_failure_start = None
        
        # Handle ongoing failure
        if current_failure_start is not None:
            failures.append({
                "started": current_failure_start,
                "ended": None,
                "duration_minutes": (datetime.utcnow() - current_failure_start).total_seconds() / 60,
                "ongoing": True,
            })
        
        if not failures:
            return {
                "component": component,
                "period": {
                    "since": since.isoformat(),
                    "until": datetime.utcnow().isoformat(),
                },
                "mtbf_minutes": None,
                "mttr_minutes": None,
                "failure_count": 0,
                "message": "No failures detected in the specified period",
            }
        
        # Calculate MTTR (Mean Time To Recovery)
        completed_failures = [f for f in failures if not f.get("ongoing")]
        if completed_failures:
            mttr_minutes = sum(f["duration_minutes"] for f in completed_failures) / len(completed_failures)
        else:
            mttr_minutes = None
        
        # Calculate MTBF (Mean Time Between Failures)
        if len(failures) >= 2:
            # Time between start of consecutive failures
            time_between_failures = []
            for i in range(1, len(failures)):
                prev_start = failures[i - 1]["started"]
                curr_start = failures[i]["started"]
                time_between = (curr_start - prev_start).total_seconds() / 60
                time_between_failures.append(time_between)
            
            mtbf_minutes = sum(time_between_failures) / len(time_between_failures) if time_between_failures else None
        else:
            mtbf_minutes = None
        
        # Calculate availability from records
        up_count = sum(1 for r in records if r.status in ("healthy", "degraded"))
        total = len(records)
        availability = (up_count / total) * 100 if total > 0 else 0
        
        return {
            "component": component,
            "period": {
                "since": since.isoformat(),
                "until": datetime.utcnow().isoformat(),
            },
            "mtbf_minutes": round(mtbf_minutes, 2) if mtbf_minutes else None,
            "mttr_minutes": round(mttr_minutes, 2) if mttr_minutes else None,
            "failure_count": len(failures),
            "completed_failures": len(completed_failures),
            "ongoing_failures": len(failures) - len(completed_failures),
            "availability_percent": round(availability, 2),
            "failures": [
                {
                    "started": f["started"].isoformat(),
                    "ended": f["ended"].isoformat() if f["ended"] else None,
                    "duration_minutes": round(f["duration_minutes"], 2),
                    "ongoing": f.get("ongoing", False),
                }
                for f in failures[-10:]  # Last 10 failures
            ],
        }
    
    def detect_flapping(
        self,
        component: Optional[str] = None,
        since: Optional[datetime] = None,
        threshold: int = 5,
        window_minutes: int = 60,
    ) -> Dict[str, Any]:
        """
        Detect 'flapping' - services that rapidly switch between healthy and unhealthy states.
        
        Args:
            threshold: Minimum number of state changes to consider as flapping
            window_minutes: Time window to analyze
        """
        if since is None:
            since = datetime.utcnow() - timedelta(hours=24)
        
        records = self.store.get_history(
            component=component,
            since=since,
            limit=10000,
        )
        
        if not records:
            return {
                "flapping_detected": False,
                "components": {},
            }
        
        # Group by component
        by_component = {}
        for record in records:
            comp = record.component
            if comp not in by_component:
                by_component[comp] = []
            by_component[comp].append(record)
        
        flapping_components = {}
        
        for comp, comp_records in by_component.items():
            # Sort by timestamp
            comp_records.sort(key=lambda r: r.timestamp)
            
            # Count state changes
            state_changes = 0
            last_status = None
            
            window_end = datetime.utcnow()
            window_start = window_end - timedelta(minutes=window_minutes)
            
            for record in comp_records:
                if window_start <= record.timestamp <= window_end:
                    if last_status is not None and record.status != last_status:
                        state_changes += 1
                    last_status = record.status
            
            # Check if flapping
            is_flapping = state_changes >= threshold
            
            if is_flapping:
                flapping_components[comp] = {
                    "state_changes": state_changes,
                    "threshold": threshold,
                    "window_minutes": window_minutes,
                    "severity": "critical" if state_changes >= threshold * 2 else "warning",
                    "recommendation": "Check for resource contention, network issues, or dependency problems",
                }
        
        return {
            "flapping_detected": len(flapping_components) > 0,
            "flapping_count": len(flapping_components),
            "components": flapping_components,
            "analysis_window_minutes": window_minutes,
            "threshold": threshold,
        }
    
    def predict_degradation(
        self,
        component: str = "overall",
        lookahead_hours: int = 24,
    ) -> Dict[str, Any]:
        """
        Predict potential degradation based on recent trends.
        
        Uses simple linear extrapolation to estimate future health status.
        """
        # Get recent data (last 48 hours)
        since = datetime.utcnow() - timedelta(hours=48)
        records = self.store.get_history(
            component=component,
            since=since,
            limit=10000,
        )
        
        if len(records) < 20:
            return {
                "component": component,
                "predictable": False,
                "message": "Insufficient data for prediction (need 20+ records)",
            }
        
        # Sort by timestamp
        records.sort(key=lambda r: r.timestamp)
        
        # Create hourly buckets
        hourly_health = []
        current_hour = records[0].timestamp.replace(minute=0, second=0, microsecond=0)
        end_hour = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        
        while current_hour <= end_hour:
            hour_records = [
                r for r in records
                if current_hour <= r.timestamp < current_hour + timedelta(hours=1)
            ]
            
            if hour_records:
                healthy_count = sum(1 for r in hour_records if r.status == "healthy")
                health_ratio = healthy_count / len(hour_records)
                hourly_health.append({
                    "hour": current_hour,
                    "health_ratio": health_ratio,
                })
            
            current_hour += timedelta(hours=1)
        
        if len(hourly_health) < 6:
            return {
                "component": component,
                "predictable": False,
                "message": "Insufficient hourly data for prediction",
            }
        
        # Simple linear regression for trend
        n = len(hourly_health)
        x_values = list(range(n))
        y_values = [h["health_ratio"] for h in hourly_health]
        
        x_mean = sum(x_values) / n
        y_mean = sum(y_values) / n
        
        # Calculate slope
        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values))
        denominator = sum((x - x_mean) ** 2 for x in x_values)
        
        slope = numerator / denominator if denominator != 0 else 0
        
        # Predict future health ratio
        current_health = y_values[-1]
        predicted_health = current_health + (slope * lookahead_hours)
        predicted_health = max(0, min(1, predicted_health))  # Clamp to 0-1
        
        # Determine risk level
        if predicted_health < 0.5:
            risk_level = "high"
            recommendation = "Immediate attention required - service likely to become unhealthy"
        elif predicted_health < 0.8:
            risk_level = "medium"
            recommendation = "Monitor closely - degradation trend detected"
        else:
            risk_level = "low"
            recommendation = "Service stability expected to continue"
        
        return {
            "component": component,
            "predictable": True,
            "current_health_ratio": round(current_health, 3),
            "predicted_health_ratio": round(predicted_health, 3),
            "lookahead_hours": lookahead_hours,
            "trend_slope": round(slope, 6),
            "trend_direction": "improving" if slope > 0.01 else "degrading" if slope < -0.01 else "stable",
            "risk_level": risk_level,
            "recommendation": recommendation,
        }
    
    def get_component_ranking(
        self,
        since: Optional[datetime] = None,
        metric: str = "availability",
    ) -> Dict[str, Any]:
        """
        Rank components by reliability/health metrics.
        
        Args:
            metric: 'availability', 'stability', 'mttr', or 'failures'
        """
        if since is None:
            since = datetime.utcnow() - timedelta(days=7)
        
        # Get all unique components
        all_records = self.store.get_history(
            since=since,
            limit=10000,
        )
        
        components = set(r.component for r in all_records)
        
        rankings = []
        
        for component in components:
            records = [r for r in all_records if r.component == component]
            
            if not records:
                continue
            
            # Calculate metrics
            up_count = sum(1 for r in records if r.status in ("healthy", "degraded"))
            total = len(records)
            availability = (up_count / total) * 100 if total > 0 else 0
            
            failure_count = sum(1 for r in records if r.status == "unhealthy")
            
            # Count state changes for stability
            sorted_records = sorted(records, key=lambda r: r.timestamp)
            state_changes = sum(
                1 for i in range(1, len(sorted_records))
                if sorted_records[i].status != sorted_records[i-1].status
            )
            
            rankings.append({
                "component": component,
                "availability": round(availability, 2),
                "failure_count": failure_count,
                "state_changes": state_changes,
                "total_checks": total,
                "stability_score": max(0, 100 - (state_changes * 5)),  # Deduct 5 points per state change
            })
        
        # Sort by the requested metric
        if metric == "availability":
            rankings.sort(key=lambda x: x["availability"], reverse=True)
        elif metric == "stability":
            rankings.sort(key=lambda x: x["stability_score"], reverse=True)
        elif metric == "failures":
            rankings.sort(key=lambda x: x["failure_count"])
        elif metric == "mttr":
            # Would need MTTR data here
            rankings.sort(key=lambda x: x["failure_count"])
        
        return {
            "metric": metric,
            "period": {
                "since": since.isoformat(),
                "until": datetime.utcnow().isoformat(),
            },
            "rankings": rankings,
            "healthiest": rankings[0] if rankings else None,
            "least_healthy": rankings[-1] if rankings else None,
        }
    
    def get_health_insights(
        self,
        since: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Get comprehensive health insights combining all analyses.
        
        This is the main entry point for health analysis.
        """
        if since is None:
            since = datetime.utcnow() - timedelta(days=7)
        
        # Run all analyses
        trends = self.analyze_trends(since=since)
        flapping = self.detect_flapping(since=since)
        ranking = self.get_component_ranking(since=since)
        mtbf_mttr = self.calculate_mtbf_mttr(since=since)
        prediction = self.predict_degradation()
        
        # Generate insights
        insights = []
        recommendations = []
        
        # Trend-based insights
        if trends.get("trend", {}).get("direction") == "degrading":
            insights.append({
                "type": "trend",
                "severity": "warning",
                "message": f"Overall health is degrading (change: {trends['trend']['change']:.2f})",
            })
            recommendations.append("Investigate recent changes or increased load")
        
        # Flapping insights
        if flapping.get("flapping_detected"):
            insights.append({
                "type": "flapping",
                "severity": "critical" if flapping["flapping_count"] > 1 else "warning",
                "message": f"{flapping['flapping_count']} component(s) showing flapping behavior",
                "components": list(flapping["components"].keys()),
            })
            recommendations.append("Check for resource contention or dependency issues")
        
        # Prediction insights
        if prediction.get("predictable") and prediction.get("risk_level") in ("high", "medium"):
            insights.append({
                "type": "prediction",
                "severity": prediction["risk_level"],
                "message": f"Predicted health degradation to {prediction['predicted_health_ratio']:.1%} in 24h",
            })
            recommendations.append(prediction["recommendation"])
        
        # MTBF insights
        if mtbf_mttr.get("mtbf_minutes") and mtbf_mttr["mtbf_minutes"] < 60:
            insights.append({
                "type": "reliability",
                "severity": "warning",
                "message": f"Low MTBF ({mtbf_mttr['mtbf_minutes']:.0f} min) - frequent failures detected",
            })
            recommendations.append("Investigate root cause of frequent failures")
        
        return {
            "generated_at": datetime.utcnow().isoformat(),
            "period": {
                "since": since.isoformat(),
                "until": datetime.utcnow().isoformat(),
            },
            "summary": {
                "insight_count": len(insights),
                "recommendation_count": len(recommendations),
                "overall_health": trends.get("trend", {}).get("current_health_ratio", 0),
            },
            "insights": insights,
            "recommendations": recommendations,
            "details": {
                "trends": trends,
                "flapping": flapping,
                "ranking": ranking,
                "mtbf_mttr": mtbf_mttr,
                "prediction": prediction,
            },
        }


# Global store instance
health_history = HealthHistoryStore()

# Global analyzer instance
health_analyzer = HealthAnalyzer(health_history)

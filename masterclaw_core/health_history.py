"""
Health Check History Tracking

Tracks health check results over time for debugging intermittent issues
and monitoring service reliability.
"""

import json
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from contextlib import contextmanager

logger = logging.getLogger("masterclaw.health_history")


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
    """Store and retrieve health check history"""
    
    def __init__(self, db_path: str = "/data/health_history.db"):
        self.db_path = Path(db_path)
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
        """Initialize the database schema"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
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
    
    def record(self, record: HealthRecord) -> None:
        """Record a health check result"""
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
        """Retrieve health check history with filters"""
        
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
        """Get a summary of health status over time"""
        
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
        """Calculate uptime statistics for a component"""
        
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
        """Remove records older than specified days"""
        
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


# Global store instance
health_history = HealthHistoryStore()

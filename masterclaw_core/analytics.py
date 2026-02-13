"""Analytics and metrics for MasterClaw"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict


class Analytics:
    """Track usage analytics and metrics"""
    
    def __init__(self):
        self.metrics = defaultdict(list)
    
    def track_request(self, endpoint: str, duration_ms: float, status_code: int):
        """Track API request metrics"""
        self.metrics['requests'].append({
            'endpoint': endpoint,
            'duration_ms': duration_ms,
            'status_code': status_code,
            'timestamp': datetime.utcnow().isoformat(),
        })
    
    def track_chat(self, provider: str, model: str, tokens_used: int):
        """Track chat usage"""
        self.metrics['chats'].append({
            'provider': provider,
            'model': model,
            'tokens_used': tokens_used,
            'timestamp': datetime.utcnow().isoformat(),
        })
    
    def track_memory_search(self, results_count: int, query_time_ms: float):
        """Track memory search metrics"""
        self.metrics['memory_searches'].append({
            'results_count': results_count,
            'query_time_ms': query_time_ms,
            'timestamp': datetime.utcnow().isoformat(),
        })
    
    def get_stats(self, days: int = 7) -> Dict:
        """Get analytics statistics"""
        since = datetime.utcnow() - timedelta(days=days)
        
        # Filter recent metrics
        recent_requests = [
            r for r in self.metrics['requests']
            if datetime.fromisoformat(r['timestamp']) > since
        ]
        
        recent_chats = [
            c for c in self.metrics['chats']
            if datetime.fromisoformat(c['timestamp']) > since
        ]
        
        # Calculate stats
        total_requests = len(recent_requests)
        avg_response_time = (
            sum(r['duration_ms'] for r in recent_requests) / total_requests
            if total_requests > 0 else 0
        )
        
        total_tokens = sum(c['tokens_used'] for c in recent_chats)
        
        # Provider usage breakdown
        provider_usage = defaultdict(int)
        for chat in recent_chats:
            provider_usage[chat['provider']] += 1
        
        return {
            'period_days': days,
            'total_requests': total_requests,
            'avg_response_time_ms': round(avg_response_time, 2),
            'total_chats': len(recent_chats),
            'total_tokens': total_tokens,
            'provider_usage': dict(provider_usage),
            'error_rate': (
                sum(1 for r in recent_requests if r['status_code'] >= 400) / total_requests
                if total_requests > 0 else 0
            ),
        }


# Global analytics instance
analytics = Analytics()

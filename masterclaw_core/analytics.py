"""Analytics and metrics for MasterClaw"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict


# Pricing per 1K tokens (as of Feb 2024)
# Update these as pricing changes
PRICING = {
    "openai": {
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-4-turbo-preview": {"input": 0.01, "output": 0.03},
        "gpt-4o": {"input": 0.005, "output": 0.015},
        "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
        "gpt-3.5-turbo-16k": {"input": 0.001, "output": 0.002},
        "default": {"input": 0.03, "output": 0.06},  # Default to GPT-4 pricing
    },
    "anthropic": {
        "claude-3-opus-20240229": {"input": 0.015, "output": 0.075},
        "claude-3-sonnet-20240229": {"input": 0.003, "output": 0.015},
        "claude-3-haiku-20240307": {"input": 0.00025, "output": 0.00125},
        "claude-3-5-sonnet-20241022": {"input": 0.003, "output": 0.015},
        "default": {"input": 0.015, "output": 0.075},  # Default to Opus pricing
    },
}


def calculate_cost(provider: str, model: str, input_tokens: int, output_tokens: int) -> Dict[str, float]:
    """
    Calculate the cost for a given provider, model, and token usage.
    
    Returns:
        Dict with input_cost, output_cost, and total_cost in USD
    """
    provider_pricing = PRICING.get(provider, {})
    model_pricing = provider_pricing.get(model, provider_pricing.get("default", {"input": 0, "output": 0}))
    
    input_cost = (input_tokens / 1000) * model_pricing["input"]
    output_cost = (output_tokens / 1000) * model_pricing["output"]
    
    return {
        "input_cost": round(input_cost, 6),
        "output_cost": round(output_cost, 6),
        "total_cost": round(input_cost + output_cost, 6),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }


class CostTracker:
    """Track LLM usage costs"""
    
    def __init__(self):
        self.costs: List[Dict] = []
    
    def track_cost(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        session_id: Optional[str] = None,
    ) -> Dict[str, float]:
        """Track a cost entry and return the calculated cost"""
        cost_data = calculate_cost(provider, model, input_tokens, output_tokens)
        
        entry = {
            "provider": provider,
            "model": model,
            "session_id": session_id,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "input_cost": cost_data["input_cost"],
            "output_cost": cost_data["output_cost"],
            "total_cost": cost_data["total_cost"],
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        self.costs.append(entry)
        return cost_data
    
    def get_cost_summary(self, days: int = 30) -> Dict:
        """Get cost summary for the specified period"""
        since = datetime.utcnow() - timedelta(days=days)
        
        recent_costs = [
            c for c in self.costs
            if datetime.fromisoformat(c["timestamp"]) > since
        ]
        
        # Total costs
        total_input_cost = sum(c["input_cost"] for c in recent_costs)
        total_output_cost = sum(c["output_cost"] for c in recent_costs)
        total_cost = sum(c["total_cost"] for c in recent_costs)
        
        # Token counts
        total_input_tokens = sum(c["input_tokens"] for c in recent_costs)
        total_output_tokens = sum(c["output_tokens"] for c in recent_costs)
        total_tokens = total_input_tokens + total_output_tokens
        
        # By provider
        provider_costs = defaultdict(lambda: {"cost": 0.0, "tokens": 0, "requests": 0})
        for c in recent_costs:
            provider_costs[c["provider"]]["cost"] += c["total_cost"]
            provider_costs[c["provider"]]["tokens"] += c["input_tokens"] + c["output_tokens"]
            provider_costs[c["provider"]]["requests"] += 1
        
        # By model
        model_costs = defaultdict(lambda: {"cost": 0.0, "tokens": 0, "requests": 0})
        for c in recent_costs:
            model_costs[c["model"]]["cost"] += c["total_cost"]
            model_costs[c["model"]]["tokens"] += c["input_tokens"] + c["output_tokens"]
            model_costs[c["model"]]["requests"] += 1
        
        # By session (top 10)
        session_costs = defaultdict(lambda: {"cost": 0.0, "tokens": 0, "requests": 0})
        for c in recent_costs:
            sid = c.get("session_id") or "unknown"
            session_costs[sid]["cost"] += c["total_cost"]
            session_costs[sid]["tokens"] += c["input_tokens"] + c["output_tokens"]
            session_costs[sid]["requests"] += 1
        
        # Sort sessions by cost and take top 10
        sorted_sessions = sorted(
            [(sid, data) for sid, data in session_costs.items()],
            key=lambda x: x[1]["cost"],
            reverse=True
        )[:10]
        
        return {
            "period_days": days,
            "total_cost": round(total_cost, 4),
            "total_input_cost": round(total_input_cost, 4),
            "total_output_cost": round(total_output_cost, 4),
            "total_tokens": total_tokens,
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "total_requests": len(recent_costs),
            "average_cost_per_request": round(total_cost / len(recent_costs), 6) if recent_costs else 0,
            "by_provider": {
                p: {"cost": round(d["cost"], 4), "tokens": d["tokens"], "requests": d["requests"]}
                for p, d in provider_costs.items()
            },
            "by_model": {
                m: {"cost": round(d["cost"], 4), "tokens": d["tokens"], "requests": d["requests"]}
                for m, d in model_costs.items()
            },
            "top_sessions": [
                {"session_id": sid, "cost": round(d["cost"], 4), "tokens": d["tokens"], "requests": d["requests"]}
                for sid, d in sorted_sessions
            ],
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    def get_daily_costs(self, days: int = 30) -> List[Dict]:
        """Get costs broken down by day"""
        since = datetime.utcnow() - timedelta(days=days)
        
        recent_costs = [
            c for c in self.costs
            if datetime.fromisoformat(c["timestamp"]) > since
        ]
        
        # Group by day
        daily = defaultdict(lambda: {"cost": 0.0, "tokens": 0, "requests": 0})
        
        for c in recent_costs:
            day = datetime.fromisoformat(c["timestamp"]).strftime("%Y-%m-%d")
            daily[day]["cost"] += c["total_cost"]
            daily[day]["tokens"] += c["input_tokens"] + c["output_tokens"]
            daily[day]["requests"] += 1
        
        return [
            {
                "date": day,
                "cost": round(data["cost"], 4),
                "tokens": data["tokens"],
                "requests": data["requests"],
            }
            for day, data in sorted(daily.items())
        ]


class Analytics:
    """Track usage analytics and metrics"""
    
    def __init__(self):
        self.metrics = defaultdict(list)
        self.cost_tracker = CostTracker()
    
    def track_request(self, endpoint: str, duration_ms: float, status_code: int):
        """Track API request metrics"""
        self.metrics['requests'].append({
            'endpoint': endpoint,
            'duration_ms': duration_ms,
            'status_code': status_code,
            'timestamp': datetime.utcnow().isoformat(),
        })
    
    def track_chat(self, provider: str, model: str, tokens_used: int, input_tokens: int = 0, output_tokens: int = 0, session_id: Optional[str] = None):
        """Track chat usage and cost"""
        self.metrics['chats'].append({
            'provider': provider,
            'model': model,
            'tokens_used': tokens_used,
            'timestamp': datetime.utcnow().isoformat(),
        })
        
        # Track cost if we have token breakdown
        if input_tokens > 0 or output_tokens > 0:
            self.cost_tracker.track_cost(provider, model, input_tokens, output_tokens, session_id)
    
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

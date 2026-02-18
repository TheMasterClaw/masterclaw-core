# Health Trend Analysis & Insights Improvement

**Date:** 2026-02-18  
**Component:** masterclaw-core  
**Type:** Feature Enhancement

## Summary

Added comprehensive **Health Trend Analysis and Insights** functionality to the MasterClaw Core API. This enhancement transforms raw health check data into actionable intelligence, providing operators with predictive insights about system reliability.

## Changes Made

### 1. Enhanced `health_history.py`

Added the `HealthAnalyzer` class with the following capabilities:

#### Trend Analysis (`analyze_trends`)
- Detects trend direction: improving, degrading, or stable
- Calculates stability scores (0-100)
- Measures volatility using standard deviation
- Time-windowed analysis for granular insights

#### Reliability Metrics (`calculate_mtbf_mttr`)
- **MTBF (Mean Time Between Failures)**: Average time between failure starts
- **MTTR (Mean Time To Recovery)**: Average time to recover from failures
- Tracks failure counts and ongoing outages
- Calculates availability percentages

#### Flapping Detection (`detect_flapping`)
- Identifies services that rapidly switch between healthy/unhealthy states
- Configurable threshold and time window
- Severity classification (warning/critical)
- Component-by-component analysis

#### Degradation Prediction (`predict_degradation`)
- Uses linear regression to predict future health status
- 24-hour lookahead capability
- Risk level assessment (low/medium/high)
- Actionable recommendations

#### Component Ranking (`get_component_ranking`)
- Ranks components by availability, stability, or failure count
- Identifies healthiest and least healthy components
- Stability scoring based on state change frequency

#### Comprehensive Insights (`get_health_insights`)
- Aggregates all analyses into actionable insights
- Generates recommendations based on detected patterns
- Summary statistics for dashboards

### 2. New API Endpoint: `GET /health/insights`

Added a new REST endpoint that exposes all analysis capabilities:

```bash
# Comprehensive analysis
GET /health/insights

# Specific component analysis
GET /health/insights?component=mc-core

# Specific analysis type
GET /health/insights?analysis_type=trends
GET /health/insights?analysis_type=mtbf_mttr
GET /health/insights?analysis_type=flapping
GET /health/insights?analysis_type=prediction
GET /health/insights?analysis_type=ranking

# Custom time range
GET /health/insights?since=2026-02-10T00:00:00
```

### 3. Test Coverage

Created comprehensive test suite in `tests/test_health_analyzer.py`:
- 12 test cases covering all major functionality
- Tests for edge cases (insufficient data, no failures, etc.)
- Mock-based unit tests for isolation
- Trend detection validation
- Flapping detection scenarios

## Example Output

```json
{
  "generated_at": "2026-02-18T21:30:00",
  "period": {
    "since": "2026-02-11T21:30:00",
    "until": "2026-02-18T21:30:00"
  },
  "summary": {
    "insight_count": 2,
    "recommendation_count": 2,
    "overall_health": 0.95
  },
  "insights": [
    {
      "type": "trend",
      "severity": "warning",
      "message": "Overall health is degrading (change: -0.15)"
    },
    {
      "type": "prediction",
      "severity": "medium",
      "message": "Predicted health degradation to 72.0% in 24h"
    }
  ],
  "recommendations": [
    "Investigate recent changes or increased load",
    "Monitor closely - degradation trend detected"
  ],
  "details": {
    "trends": {
      "direction": "degrading",
      "change": -0.15,
      "stability": {
        "score": 78.5,
        "classification": "moderate"
      }
    },
    "mtbf_mttr": {
      "mtbf_minutes": 360,
      "mttr_minutes": 4.5,
      "failure_count": 3,
      "availability_percent": 98.7
    },
    "flapping": {
      "flapping_detected": false,
      "flapping_count": 0
    },
    "prediction": {
      "predictable": true,
      "current_health_ratio": 0.95,
      "predicted_health_ratio": 0.72,
      "risk_level": "medium"
    },
    "ranking": {
      "metric": "availability",
      "healthiest": {"component": "mc-gateway", "availability": 99.9},
      "least_healthy": {"component": "mc-core", "availability": 95.0}
    }
  }
}
```

## Benefits

1. **Proactive Operations**: Predict issues before they impact users
2. **Data-Driven Decisions**: MTBF/MTTR metrics for capacity planning
3. **Faster Troubleshooting**: Flapping detection identifies problematic services
4. **SLA Monitoring**: Track availability trends over time
5. **Component Comparison**: Identify which services need attention

## Integration Points

- CLI: Can be integrated into `mc health` command
- Monitoring: Export metrics to Prometheus/Grafana
- Alerting: Trigger alerts based on prediction risk levels
- Dashboards: Visualize trends and rankings

## Backward Compatibility

- No breaking changes to existing APIs
- New endpoint is additive only
- Existing health history storage unchanged
- Optional feature - no impact if not used

## Files Modified

1. `masterclaw_core/health_history.py` - Added HealthAnalyzer class
2. `masterclaw_core/main.py` - Added /health/insights endpoint
3. `tests/test_health_analyzer.py` - New test file (created)

## Testing

```bash
# Run the new tests
cd /home/ubuntu/.openclaw/workspace
pytest tests/test_health_analyzer.py -v

# Test the API endpoint (when server is running)
curl http://localhost:8000/health/insights
```

---

*This improvement transforms health data from reactive monitoring to proactive intelligence.* 🐾

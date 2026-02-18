# Cost Budget Alert System 💰

**Feature**: Automated cost monitoring with budget alerts and notifications  
**Version**: 0.48.0  
**Date**: 2026-02-18

## Overview

The Cost Budget Alert System extends MasterClaw's cost tracking capabilities with persistent budget configuration, automated monitoring, and real-time notifications when spending thresholds are exceeded. This feature helps prevent surprise LLM bills by proactively alerting you when costs approach your defined limits.

## Features

- **Persistent Budget Configuration**: Set monthly budgets with warning and critical thresholds
- **Visual Budget Status**: Color-coded progress bars and status indicators
- **Automated Monitoring**: Cron-based scheduled budget checks
- **Smart Notifications**: Integration with existing notification channels (WhatsApp, Discord, Slack, Telegram)
- **Alert Cooldown**: Prevents notification spam with configurable cooldown periods
- **Spending Projections**: Forecasts monthly spend based on recent usage patterns
- **Budget History**: Track all budget alerts over time

## Commands

### Configure Budget

```bash
# Set monthly budget with default thresholds (80% warning, 95% critical)
mc cost budget-set --amount 100

# Custom thresholds
mc cost budget-set --amount 200 --warn 75 --critical 90

# Disable notifications
mc cost budget-set --amount 100 --notifications false
```

### View Budget Status

```bash
# Show current budget configuration and spending
mc cost budget-show

# JSON output for programmatic access
mc cost budget-show --json
```

### Check Budget

```bash
# Check current spending against budget (sends notifications if thresholds exceeded)
mc cost budget-check

# Check without sending notifications
mc cost budget-check --no-notify
```

### Manage Automated Monitoring

```bash
# Enable automated monitoring (checks every 6 hours)
mc cost budget-monitor --enable

# Custom check interval
mc cost budget-monitor --enable --interval 12

# Check monitoring status
mc cost budget-monitor --status

# Disable monitoring
mc cost budget-monitor --disable
```

### View Alert History

```bash
# Show last 10 budget alerts
mc cost budget-history

# Show more entries
mc cost budget-history --limit 20
```

## Configuration

Budget configuration is stored in `config/budget.json`:

```json
{
  "version": "1.0",
  "monthlyBudget": 100,
  "warningThreshold": 80,
  "criticalThreshold": 95,
  "enabled": true,
  "notifications": true,
  "lastAlertSent": "2026-02-18T10:00:00Z",
  "alertCooldownHours": 24,
  "history": [
    {
      "timestamp": "2026-02-18T10:00:00Z",
      "level": "warning",
      "spent": 82.50,
      "budget": 100,
      "usedPercent": 82.5
    }
  ]
}
```

## Alert Levels

| Level | Threshold | Color | Action |
|-------|-----------|-------|--------|
| **Healthy** | < 80% | 🟢 Green | No action needed |
| **Warning** | 80-94% | 🟡 Yellow | Notification sent, monitor closely |
| **Critical** | ≥ 95% | 🔴 Red | Urgent notification, immediate action recommended |

## Notification Integration

Budget alerts are sent through the existing MasterClaw notification system:

1. Ensure notifications are configured:
   ```bash
   mc notify config whatsapp --number "+1234567890"
   mc notify enable whatsapp
   ```

2. Enable budget alerts in notification config:
   ```bash
   mc notify alerts --enable highCost
   ```

3. Start the alert webhook:
   ```bash
   mc notify start
   ```

## Automated Monitoring Setup

The budget monitor uses cron for scheduled checks:

```bash
# Add to crontab (every 6 hours)
0 */6 * * * cd /path/to/masterclaw-infrastructure && mc cost budget-check
```

This is automatically configured when you run:
```bash
mc cost budget-monitor --enable
```

## Exit Codes

The `budget-check` command returns specific exit codes for CI/CD integration:

| Exit Code | Meaning |
|-----------|---------|
| 0 | Budget healthy |
| 1 | Warning threshold exceeded |
| 2 | Critical threshold exceeded |

## Example Usage Workflow

```bash
# 1. Configure your monthly budget
mc cost budget-set --amount 150 --warn 75 --critical 90

# 2. Check current status
mc cost budget-show

# 3. Enable automated monitoring
mc cost budget-monitor --enable --interval 6

# 4. Verify monitoring is active
mc cost budget-monitor --status

# 5. Manual check (also sends notifications if needed)
mc cost budget-check
```

## Cost Projection

The system calculates projected monthly spend based on your 7-day average:

```
Projected Monthly = (Average Daily Cost × 30 days)
```

This helps you anticipate whether you're on track to exceed your budget before it happens.

## Best Practices

1. **Set realistic budgets**: Base your budget on historical usage (`mc cost daily`)
2. **Use conservative thresholds**: Set warning at 70-80%, critical at 90%
3. **Enable notifications**: Configure at least one notification channel
4. **Monitor regularly**: Use automated monitoring with 6-12 hour intervals
5. **Review projections**: Check `budget-show` weekly to catch trends early
6. **Act on warnings**: When you receive a warning, investigate usage patterns

## Troubleshooting

### Notifications not sending
- Verify webhook is running: `mc notify status`
- Check notification channel is configured: `mc notify config <channel>`
- Ensure budget alerts are enabled: `mc notify alerts --list`

### Budget check failing
- Verify MasterClaw Core is running: `mc status`
- Check API connectivity: `mc cost summary`

### Monitoring not working
- Verify cron is installed: `which crontab`
- Check crontab entry: `crontab -l | grep budget`
- Ensure `mc` is in PATH for cron

## Integration with CI/CD

Use budget checks in your deployment pipeline:

```yaml
# .github/workflows/deploy.yml
- name: Check Budget
  run: |
    mc cost budget-check || true
    if [ $? -eq 2 ]; then
      echo "Critical budget threshold exceeded. Aborting deployment."
      exit 1
    fi
```

## Related Commands

- `mc cost summary` - View overall cost summary
- `mc cost daily` - See daily cost breakdown
- `mc cost pricing` - View current LLM pricing
- `mc notify status` - Check notification configuration

---

*Stay on top of your LLM spending with MasterClaw Budget Alerts!* 🐾

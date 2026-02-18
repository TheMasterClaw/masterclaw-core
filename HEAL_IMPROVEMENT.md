# MasterClaw Improvement: Enhanced Self-Heal with Auto-Fix Capabilities

**Date:** 2026-02-18  
**Component:** masterclaw-tools (CLI)  
**Type:** Feature Enhancement

## Summary

Transformed the basic `mc heal` command from a simple diagnostic tool into a comprehensive auto-healing system that can **automatically detect and fix common MasterClaw issues**. The enhanced heal module provides dry-run capability, automatic remediation, and detailed reporting.

## What Was Improved

### 1. New Auto-Heal Module (`lib/heal.js`)

Created a comprehensive 600+ line heal module with:

#### Issue Detection (7 Categories)
- **Docker Issues** - Detects Docker daemon unavailability
- **Service Issues** - Identifies down/unhealthy services
- **Disk Space** - Monitors free disk space with configurable thresholds
- **Memory** - Tracks system memory availability
- **Config Issues** - Validates file permissions (e.g., .env permissions)
- **Circuit Breakers** - Detects open circuit breakers
- **Docker Artifacts** - Finds stale containers, dangling images, unused volumes

#### Auto-Fix Capabilities
- **Service Restart** - Automatically restarts stopped/unhealthy services
- **Permission Fix** - Corrects .env file permissions to 600
- **Circuit Reset** - Resets open circuit breakers
- **Docker Cleanup** - Removes exited containers, dangling images, unused volumes
- **Aggressive Cleanup** - For critical disk space issues, runs `docker system prune -af`

#### Safety Features
- **Dry-Run by Default** - Shows issues without fixing unless `--fix` is specified
- **Severity Classification** - Critical/High/Medium/Low severity levels
- **Non-Fixable Detection** - Clearly identifies issues requiring manual intervention
- **Fix Verification** - Verifies services are healthy after restart

### 2. Enhanced CLI Command

Updated `mc heal` command with new options:

```bash
# Dry-run mode (default) - detect issues without fixing
mc heal

# Auto-fix mode - actually fix detected issues
mc heal --fix

# JSON output for scripting
mc heal --json
mc heal --fix --json

# Check specific categories only
mc heal --category docker system
mc heal --category services config
```

### 3. Comprehensive Test Suite

Created `tests/heal.test.js` with:
- HealResult class tests
- Issue type constant validation
- Configuration threshold validation
- Service issue detection tests
- Circuit breaker detection tests
- Docker issue detection tests
- Integration tests for runHeal function

## Usage Examples

### Basic Usage - Detection Only
```bash
$ mc heal
🩹 MasterClaw Auto-Heal
Mode: DRY-RUN - Showing issues without fixing

Checking Docker... ✅
Checking Services... 🟡 1 high
Checking Disk Space... ✅
Checking Memory... ✅
Checking Config... ⚪ 1 low
Checking Circuits... ✅
Checking Docker Artifacts... ⚪ 2 low

📊 Summary
══════════════════════════════════════════════════
Issues found: 4
  Auto-fixable: 4
  Manual fix required: 0

💡 Run with --fix to automatically fix 4 issue(s)
```

### Auto-Fix Mode
```bash
$ mc heal --fix
🩹 MasterClaw Auto-Heal
Mode: FIX - Will attempt to fix issues

Checking Docker... ✅
Checking Services... 🟡 1 high
Checking Disk Space... ✅
Checking Memory... ✅
Checking Config... ⚪ 1 low
Checking Circuits... ✅
Checking Docker Artifacts... ⚪ 2 low

🔧 Applying fixes...

📊 Summary
══════════════════════════════════════════════════
Issues found: 4
  Auto-fixable: 4
  Manual fix required: 0

Fixes applied: 4
✅ Service core restarted successfully
✅ Fixed .env permissions
✅ Removed exited containers
✅ Reset circuit: backend

Duration: 5234ms
```

### JSON Output for Automation
```bash
$ mc heal --json
{
  "summary": {
    "issuesFound": 2,
    "issuesFixed": 0,
    "issuesFailed": 0,
    "issuesSkipped": 0,
    "duration": 1234,
    "success": true
  },
  "fixes": [
    {
      "issueType": "service_down",
      "description": "Service core is down",
      "action": "Restart service: core",
      "success": null,
      "timestamp": "2026-02-18T21:54:00.000Z"
    }
  ],
  "warnings": [],
  "nonFixableIssues": []
}
```

## Benefits

| Feature | Benefit |
|---------|---------|
| **Dry-Run Mode** | Preview fixes before applying - no surprises |
| **Auto-Restart** | Services automatically recover from crashes |
| **Disk Cleanup** | Prevents outages from disk space exhaustion |
| **Permission Fixes** | Maintains security posture automatically |
| **Circuit Reset** | Restores service connectivity after failures |
| **JSON Output** | Enables integration with monitoring/alerting systems |
| **Category Filtering** | Target specific subsystems for faster checks |

## Configuration Thresholds

```javascript
HEAL_CONFIG = {
  diskCritical: 1,        // GB - critical cleanup triggered
  diskWarning: 5,         // GB - warning shown
  memoryCritical: 0.5,    // GB - memory warning
  memoryWarning: 2,       // GB - memory notice
  imageCleanupAge: '7d',  // Clean images older than 7 days
  restartDelayMs: 5000,   // Wait 5s after restart for verification
  maxRestartAttempts: 3,  // Max restart attempts per service
}
```

## Files Modified

1. **`lib/heal.js`** - New comprehensive auto-heal module (600+ lines)
2. **`bin/mc.js`** - Updated heal command with new options
3. **`package.json`** - Version bump to 0.47.0
4. **`tests/heal.test.js`** - New test suite (200+ lines)

## Backward Compatibility

- Default behavior unchanged (dry-run shows issues only)
- No breaking changes to existing commands
- New options are additive only
- Existing scripts continue to work

## Security Considerations

- Permission fixes only target known config files (.env)
- Docker cleanup uses standard Docker CLI commands
- Service restarts are limited to MasterClaw containers
- No privileged operations required beyond standard Docker access
- All operations are logged for audit trails

## Testing

```bash
# Run heal tests
cd /home/ubuntu/.openclaw/workspace/masterclaw-tools
npm test -- tests/heal.test.js

# Test dry-run mode
node bin/mc.js heal

# Test with JSON output
node bin/mc.js heal --json

# Test category filtering
node bin/mc.js heal --category docker system
```

---

*This improvement transforms MasterClaw from reactive troubleshooting to proactive self-healing.* 🩹🐾

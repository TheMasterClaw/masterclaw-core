# MasterClaw Improvement Summary

## Improvement: Log Rotation CLI Command (`mc logs rotate`)

**Date:** February 19, 2026  
**Component:** masterclaw-tools (CLI)  
**Version:** 0.49.0 → 0.50.0  
**Commit:** cron-improvement-1

---

## Overview

Added a new `mc logs rotate` command to the MasterClaw CLI that enables **manual log rotation** without restarting containers. This addresses a gap where users needed to manually truncate log files or restart containers to free disk space when automatic rotation hadn't triggered yet.

Previously, log rotation existed in `scripts/logs.sh` but wasn't exposed through the unified `mc` CLI interface, making it difficult for users to discover and use.

---

## Features

### Command Options

```bash
mc logs rotate                    # Rotate all service logs
mc logs rotate --service core     # Rotate specific service only
mc logs rotate --yes              # Skip confirmation prompt
```

### What It Does

1. **Copies current log** to `.1` (e.g., `container.log` → `container.log.1`)
2. **Truncates the active log file** to free disk space immediately
3. **Maintains service uptime** — no container restart required
4. **Integrates with existing scripts** — uses `scripts/logs.sh` when available

### Services Supported

| Service | Container | Log Driver |
|---------|-----------|------------|
| traefik | mc-traefik | json-file |
| interface | mc-interface | json-file |
| backend | mc-backend | json-file |
| core | mc-core | json-file |
| gateway | mc-gateway | json-file |
| chroma | mc-chroma | json-file |
| watchtower | mc-watchtower | json-file |

---

## Files Changed

### masterclaw-tools

| File | Change |
|------|--------|
| `lib/logs.js` | Added 115 lines — new `rotate` command implementation |
| `bin/mc.js` | Version bump 0.49.0 → 0.50.0 |

### rex-deus

| File | Change |
|------|--------|
| `docs/log-management.md` | New — comprehensive log management documentation |

---

## Implementation Details

### Fallback Mechanism

The command has two execution paths:

1. **Infrastructure Script Path** (preferred):
   ```javascript
   const scriptPath = path.join(infraDir, 'scripts', 'logs.sh');
   spawn('bash', [scriptPath, 'rotate'], ...)
   ```

2. **Manual Rotation Fallback** (when script unavailable):
   ```javascript
   // Copy current log to .1
   await fs.copy(logPath, rotatedPath, { overwrite: true });
   // Truncate active log
   await fs.writeFile(logPath, '');
   ```

### Security Considerations

- Validates service names against allowed list
- Checks container is running before attempting rotation
- Handles missing log files gracefully
- No elevated privileges required (uses Docker API)

---

## Usage Examples

### Routine Maintenance

```bash
# Check log sizes first
$ mc logs status

📊 MasterClaw Log Status
========================
Service              Status     Log Size     Log Config
-------------------- ---------- ------------ ---------------
traefik              ●          45MB         10m/5f
core                 ●          38MB         10m/3f
... (disk usage: 78%)

# Rotate to free space
$ mc logs rotate

🔄 Rotating MasterClaw logs...

✅ traefik (25MB rotated)
✅ core (18MB rotated)
✅ backend (12MB rotated)
✅ gateway (8MB rotated)
...

✅ Rotated: 6
○ Skipped: 1 (watchtower not running)
```

### Pre-Deployment Cleanup

```bash
# Rotate before intensive operations
mc logs rotate --yes
mc deploy canary 10
```

### Single Service Rotation

```bash
# Debug session generated large logs
mc logs rotate --service core
mc logs export core
```

---

## Benefits

1. **Disk Space Recovery** — Immediate space freeing without service interruption
2. **Operational Flexibility** — Manual control over rotation timing
3. **Zero Downtime** — No container restart required
4. **Unified Interface** — Consistent with other `mc logs` commands
5. **Better User Experience** — Discoverable via `mc logs --help`

---

## Documentation

Created comprehensive log management documentation in `rex-deus/docs/log-management.md` covering:

- Log rotation (automatic and manual)
- Log status monitoring
- Log cleaning strategies
- Export and search capabilities
- Loki aggregation queries
- Security best practices
- Retention policies

---

## Integration with Existing Features

| Feature | Integration |
|---------|-------------|
| `mc logs status` | Shows log sizes before/after rotation |
| `mc logs clean` | Alternative nuclear option for space recovery |
| `mc logs export` | Export rotated logs before cleanup |
| `scripts/logs.sh` | Delegates to existing script when available |
| `mc doctor` | Can suggest rotation when disk is full |

---

## Future Enhancements

Potential improvements:
- `--schedule` flag to set up automatic rotation cron jobs
- `--min-size` option to only rotate logs above a threshold
- Integration with `mc ops` dashboard for one-click rotation
- Compression of rotated logs to save more space
- Remote log rotation for distributed deployments

---

*Built for Rex. Powered by MasterClaw.* 🐾

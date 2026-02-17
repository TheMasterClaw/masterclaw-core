# MasterClaw Security Hardening: Backup Script

## Summary

Improved the `backup.sh` script with comprehensive security hardening, error handling, and production-ready features.

## Changes Made

### 1. Input Validation (Security)
- **Path traversal prevention**: Validates backup directory against path traversal attacks (`..`, null bytes)
- **Character whitelist**: Only allows alphanumeric, underscore, slash, dot, and hyphen in paths
- **Path length limits**: Maximum 4096 characters to prevent buffer overflow
- **Retention day validation**: Enforces 1-90 day range to prevent accidental data loss

### 2. Lock File Mechanism (Concurrency Safety)
- **Atomic lock acquisition**: Prevents concurrent backup executions that could corrupt data
- **Stale lock detection**: Automatically removes abandoned lock files from crashed backups
- **PID verification**: Ensures only the owning process can release the lock
- **Race condition protection**: Verifies lock ownership after creation

### 3. Atomic Backup Creation (Data Integrity)
- **Temporary directory pattern**: Uses `backup_$DATE.$$` (PID-based) for atomic operations
- **Cleanup on failure**: Automatic rollback removes partial backups on any error
- **Integrity verification**: Tests archive integrity with `tar -tzf` before marking success
- **Secure permissions**: Sets 600 (owner read/write only) on backup files, 700 on directories

### 4. Comprehensive Error Handling
- **Strict bash mode**: `set -euo pipefail` for immediate error detection
- **Trap-based cleanup**: `EXIT`, `INT`, `TERM` signals all trigger cleanup
- **Error tracking**: Array tracks which components failed during backup
- **Disk space checks**: Prevents backup from starting if insufficient space

### 5. Enhanced Logging
- **Structured logging**: Timestamped, leveled logs (ERROR, WARN, INFO, DEBUG)
- **Dual output**: Console (with colors) and file logging
- **Audit trail**: All operations logged to `.backup.log`
- **Debug mode**: `LOG_LEVEL=DEBUG` for troubleshooting

### 6. Security Hardening
- **File permissions**: Backups created with restrictive permissions (owner only)
- **Secure directory creation**: Proper umask handling for backup directories
- **Environment validation**: Validates all environment variables before use

## Files Changed

- `masterclaw-infrastructure/scripts/backup.sh` - Complete rewrite with security hardening

## Security Benefits

1. **Prevents Path Traversal**: Malicious paths like `../../../etc` are rejected
2. **Prevents Concurrent Corruption**: Lock file ensures only one backup runs at a time
3. **Prevents Information Leakage**: Restrictive file permissions (600) on backups
4. **Prevents Resource Exhaustion**: Disk space checks before backup starts
5. **Prevents Data Loss**: Atomic operations with rollback on failure

## Backward Compatibility

- All existing environment variables work the same way
- Default behavior unchanged (7 day retention, ./backups directory)
- Exit codes preserved (0 for success, non-zero for failure)

## Testing

```bash
# Test syntax validation
bash -n scripts/backup.sh

# Test normal backup
./scripts/backup.sh

# Test with custom directory
BACKUP_DIR=/tmp/test-backups ./scripts/backup.sh

# Test concurrent execution (should fail second attempt)
./scripts/backup.sh & ./scripts/backup.sh

# Test with insufficient disk space (if possible)
BACKUP_DIR=/dev/full ./scripts/backup.sh
```

## Commit Message

```
security(backup): harden backup script with comprehensive error handling

- Add input validation to prevent path traversal and injection attacks
- Implement lock file mechanism to prevent concurrent backup corruption
- Add atomic backup creation with automatic rollback on failure
- Implement comprehensive logging with audit trail
- Add disk space checks before backup operations
- Enforce secure file permissions (600) on backup files
- Validate all environment variables with safe ranges
- Add trap-based cleanup for reliable resource management

Prevents:
- Path traversal attacks via BACKUP_DIR
- Concurrent backup corruption
- Information leakage via loose permissions
- Resource exhaustion from large backups
- Partial backup artifacts on failure
```
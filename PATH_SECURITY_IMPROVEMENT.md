# Path Traversal Security Improvement

**Date:** 2026-02-18  
**Type:** Security Hardening  
**Component:** `masterclaw_core/security.py`, `masterclaw_core/tools.py`

## Summary

Added comprehensive path validation utilities to prevent path traversal attacks and command injection in the MasterClaw Core system.

## Changes Made

### 1. Enhanced `masterclaw_core/security.py`

Added three new security functions:

#### `validate_file_path()`
- Validates file paths to prevent path traversal attacks
- Blocks various attack vectors:
  - `../` and `..\` sequences
  - URL-encoded traversal (`%2e%2e`, `%2f`)
  - Null byte injection (`\x00`)
  - Command injection characters (`;`, `|`, `&`, `` ` ``, `$`, etc.)
  - Absolute paths (when `allow_absolute=False`)
- Supports base directory enforcement (jail/chroot-like containment)
- Configurable path length limits (DoS protection)

#### `is_safe_path()`
- Convenience function for quick path safety checks
- Returns boolean without error details

#### `sanitize_path_for_display()`
- Sanitizes paths for safe logging/display
- Removes control characters
- Truncates long paths
- Prevents log injection attacks

### 2. Secured `masterclaw_core/tools.py` (SystemTool)

Updated `_disk_usage()` method to:
- Validate paths before passing to `df` command
- Reject path traversal attempts
- Log security violations
- Return safe error messages

## Security Improvements

### Before
```python
async def _disk_usage(self, path: str) -> ToolResult:
    result = subprocess.run(["df", "-h", path], ...)  # No validation!
```

Attack possible:
```
POST /tools/execute
{
  "tool": "system",
  "action": "disk_usage",
  "path": "../etc"  # Could reveal sensitive system info
}
```

### After
```python
async def _disk_usage(self, path: str) -> ToolResult:
    is_valid, error = validate_file_path(path, allow_absolute=False)
    if not is_valid:
        return ToolResult(success=False, error=f"Invalid path: {error}")
    result = subprocess.run(["df", "-h", normalized_path], ...)
```

Attack blocked:
```
POST /tools/execute
{
  "tool": "system",
  "action": "disk_usage",
  "path": "../etc"
}
# Response: {"success": false, "error": "Invalid path: Path contains path traversal sequences"}
```

## Test Coverage

Created comprehensive test suite: `tests/test_path_security.py`

- **54 test cases** covering:
  - Valid path acceptance
  - Path traversal blocking (multiple encodings)
  - Command injection prevention
  - Null byte injection blocking
  - Absolute path control
  - Base directory enforcement
  - Path sanitization
  - Integration with SystemTool

All tests pass:
```
pytest tests/test_path_security.py -v
============================== 54 passed in 1.59s ==============================
```

## Attack Vectors Blocked

| Attack Vector | Example | Result |
|---------------|---------|--------|
| Path Traversal (Unix) | `../../../etc/passwd` | Blocked |
| Path Traversal (Windows) | `..\..\windows\system32` | Blocked |
| URL Encoded Traversal | `%2e%2e/%2fetc/passwd` | Blocked |
| Double Encoding | `....//....//etc/passwd` | Blocked |
| Command Injection | `file.txt; rm -rf /` | Blocked |
| Pipe Injection | `file.txt \| cat /etc/passwd` | Blocked |
| Backtick Injection | `` file.txt`whoami` `` | Blocked |
| Variable Expansion | `file.txt$(id)` | Blocked |
| Null Byte Injection | `file.txt\x00.exe` | Blocked |
| Absolute Path | `/etc/passwd` | Blocked* |

*When `allow_absolute=False` (default)

## Backwards Compatibility

- Existing API behavior unchanged for valid inputs
- Only malicious/invalid paths are now rejected
- Error messages are user-friendly and don't leak system details

## Future Enhancements

- Apply path validation to other file system operations in the codebase
- Add rate limiting for failed path validation attempts
- Log security violations to audit log for monitoring

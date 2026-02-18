# Context Manager Security Improvement

## Summary

Added path traversal protection to `ContextManager._read_file()` method to prevent potential security vulnerabilities.

## Problem

The `_read_file()` method in `masterclaw_core/context_manager.py` constructed file paths directly from user-provided filenames without validation:

```python
filepath = self.context_dir / filename  # No validation!
```

While currently only called with hardcoded filenames, this presented a potential security vulnerability if the method were ever exposed to user input or if future code modifications introduced untrusted input.

## Solution

Integrated the existing security validation infrastructure:

1. **Added security imports** to `context_manager.py`:
   ```python
   from .security import validate_file_path, sanitize_path_for_display
   ```

2. **Enhanced `_read_file()` method** with two-layer validation:
   - **Layer 1**: Validate filename using `validate_file_path()` which checks for:
     - Path traversal patterns (`../`, `..\`, encoded variants)
     - Command injection characters (`;`, `|`, `&`, `$`, etc.)
     - Null byte injection
     - Excessively long paths (DoS protection)
   
   - **Layer 2**: Double-check resolved path is within `context_dir` using `Path.resolve()`

3. **Added security logging** to track and alert on blocked attempts

4. **Created comprehensive test suite** (`tests/test_context_manager_security.py`) with:
   - Tests for all attack vectors (path traversal, command injection, null bytes)
   - Tests for normal operation (valid files still work)
   - Security logging verification tests
   - Edge case tests (empty, whitespace, very long filenames)

## Attack Vectors Blocked

| Attack Type | Example | Status |
|-------------|---------|--------|
| Path traversal | `../../../etc/passwd` | Blocked |
| Windows traversal | `..\\windows\\system32` | Blocked |
| Double traversal | `....//....//etc/passwd` | Blocked |
| URL-encoded | `%2e%2e/%2fetc/passwd` | Blocked |
| Absolute paths | `/etc/passwd` | Blocked |
| Windows absolute | `C:\Windows\System32` | Blocked |
| Command injection | `file.txt; rm -rf /` | Blocked |
| Pipe injection | `file.txt\|cat /etc/passwd` | Blocked |
| Backtick injection | `file.txt\`whoami\`` | Blocked |
| Variable expansion | `file.txt$(id)` | Blocked |
| Null byte | `file.txt\x00.md` | Blocked |

## Files Changed

1. **masterclaw_core/context_manager.py** - Added security validation to `_read_file()`
2. **tests/test_context_manager_security.py** - New comprehensive test suite
3. **CONTEXT_MANAGER_SECURITY_IMPROVEMENT.md** - This documentation

## Testing

Run the new security tests:

```bash
python -m pytest tests/test_context_manager_security.py -v
```

All existing functionality remains intact - valid context files continue to be read normally.

## Security Impact

- **Before**: Potential path traversal vulnerability if method exposed to untrusted input
- **After**: Defense in depth - method is now hardened against all known path traversal and command injection attacks

This is a proactive security improvement following the principle of defense in depth.

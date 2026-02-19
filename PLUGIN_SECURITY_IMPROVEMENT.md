# Plugin System Security Hardening

## Summary

Applied security hardening to the MasterClaw plugin system (`lib/plugin.js`) to prevent command injection attacks and race conditions.

## Changes Made

### 1. Command Injection Prevention

**Problem:** The plugin system used `execSync()` with template string interpolation for external commands, allowing potential command injection if malicious input reached these calls.

**Vulnerable code patterns fixed:**
```javascript
// BEFORE - Vulnerable to command injection
execSync(`tar -xzf ${tarballPath} -C ${tempDir}`, { stdio: 'ignore' });
execSync(`npm install ${dep} --prefix ${pluginPath}`, { ... });
execSync(`git clone --depth 1 ${gitUrl} ${pluginPath}`, { stdio: 'ignore' });
```

**Fixed code:**
```javascript
// AFTER - Safe from command injection
execFileSync('tar', ['-xzf', tarballPath, '-C', tempDir], { stdio: 'ignore' });
execFileSync('npm', ['install', dep, '--prefix', pluginPath], { ... });
execFileSync('git', ['clone', '--depth', '1', gitUrl, pluginPath], { stdio: 'ignore' });
```

**Why this fixes it:**
- `execFileSync` with array arguments passes arguments directly without shell interpretation
- Special characters in paths/URLs are treated as literal arguments, not shell metacharacters
- Prevents attackers from injecting commands via crafted plugin names, URLs, or file paths

### 2. Secure Temp Directory Generation

**Problem:** Temp directories used predictable timestamp-based names (`Date.now()`), making them vulnerable to race condition attacks where an attacker could predict and pre-create malicious directories.

**Fixed:**
```javascript
// BEFORE - Predictable
const tempDir = path.join(PLUGINS_DIR, `.tmp-${Date.now()}`);

// AFTER - Cryptographically secure
const randomBytes = crypto.randomBytes(16).toString('hex');
const tempDir = path.join(PLUGINS_DIR, `.tmp-${randomBytes}`);
```

### 3. Added Security Tests

Created comprehensive test suite (`tests/plugin.security.test.js`) with 7 tests covering:
- Temp directory randomness verification
- Command injection prevention for tar, npm, and git operations
- Path traversal detection
- Static analysis verification of safe patterns

## Impact

- **Severity:** High - Command injection vulnerabilities could allow arbitrary code execution
- **Attack vectors mitigated:**
  - Malicious plugin names containing shell metacharacters
  - Crafted git URLs with command injection payloads
  - Race condition attacks on temp directories
- **Backward compatibility:** Fully maintained - no API changes

## Files Modified

1. `lib/plugin.js` - Fixed 4 command injection vulnerabilities and 1 race condition
2. `tests/plugin.security.test.js` - New security test suite (7 tests)

## Testing

All security tests pass:
```
Test Suites: 2 passed, 2 total
Tests:       55 passed, 55 total
```

## References

- [Node.js execFileSync documentation](https://nodejs.org/api/child_process.html#child_processexecfilesyncfile-args-options)
- [OWASP Command Injection](https://owasp.org/www-community/attacks/Command_Injection)
- [CWE-78: OS Command Injection](https://cwe.mitre.org/data/definitions/78.html)

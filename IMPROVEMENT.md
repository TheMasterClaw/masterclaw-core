# MasterClaw Improvement: Resource Limit Violation Detection

## Summary

Added **resource limit violation detection and reporting** to the `mc exec` command. When commands executed in containers hit resource limits (memory, processes, file size), users now receive clear, actionable error messages instead of cryptic exit codes.

## What Was Improved

### 1. Exit Code Analysis (`lib/exec.js`)

Added intelligent exit code analysis to detect when Docker/linux kills processes due to resource limits:

- **SIGKILL (137)** - Process killed by OOM killer or nproc limit
- **SIGXCPU (152)** - CPU time limit exceeded
- **SIGXFSZ (153)** - File size limit exceeded
- **SIGSYS (159)** - Blocked system call (seccomp violation)
- **OOM detection from stderr** - Parses stderr for OOM indicators

### 2. User-Friendly Error Messages

When resource limits are hit, users now see:

```
❌ Resource limit exceeded: MEMORY_LIMIT
   Out of Memory (OOM) - Container exceeded memory limit
   💡 Command exceeded the 1024MB memory limit. Try reducing memory usage or run the command with MC_EXEC_NO_RESOURCE_LIMITS=1 (emergency override).
   Exit code: 137 (1245ms)
```

Instead of the previous unhelpful:

```
⚠️  Exit code: 137 (1245ms)
```

### 3. Security Audit Logging

Resource limit violations are now logged to the security audit trail:

```javascript
await logAudit(AuditEventType.SECURITY_VIOLATION, {
  container,
  command: command.join(' '),
  violationType: 'MEMORY_LIMIT',
  exitCode: 137,
  description: 'Out of Memory (OOM) - Container exceeded memory limit',
  stderr: stderr?.substring(0, 500),
});
```

This enables monitoring for:
- Fork bomb attempts (nproc violations)
- Memory exhaustion attacks
- Processes attempting blocked system calls

### 4. Enhanced Result Object

The `execInContainer` function now returns a `resourceViolation` field:

```javascript
{
  success: false,
  exitCode: 137,
  stdout: '',
  stderr: 'Killed process 1234 (python)',
  duration: 1245,
  interactive: false,
  resourceViolation: {
    exitCode: 137,
    isResourceViolation: true,
    violationType: 'RESOURCE_LIMIT',
    description: 'Process was forcefully killed (likely OOM or nproc limit)',
    suggestion: 'Command may have exceeded memory (1GB) or process (256) limits. Try simplifying the command or use --shell for interactive debugging.'
  }
}
```

## Files Modified

- `lib/exec.js` - Added `EXIT_CODES`, `analyzeExitCode()`, `detectOOMFromStderr()` functions, updated `execInContainer()` to detect and report violations
- `bin/mc.js` - Updated `mc exec` command handler to display helpful resource violation messages
- `tests/exec.security.test.js` - Added 15 comprehensive tests for resource limit detection

## Test Coverage

**15 new tests added:**

```
Resource Limit Violation Detection
  analyzeExitCode
    ✓ returns success for exit code 0
    ✓ detects SIGKILL (137) as resource limit violation
    ✓ detects SIGXCPU (152) as CPU limit violation
    ✓ detects SIGXFSZ (153) as file size limit violation
    ✓ detects SIGSYS (159) as blocked system call
    ✓ returns non-violation for generic error codes
    ✓ returns non-violation for exit code 2
  detectOOMFromStderr
    ✓ detects "killed process" message
    ✓ detects "out of memory" message
    ✓ detects "oom-kill" message
    ✓ detects "cannot allocate memory" message
    ✓ detects "memory cgroup out of memory" message
    ✓ returns false for non-OOM stderr
    ✓ returns false for null/undefined stderr
  EXIT_CODES constants
    ✓ EXIT_CODES has expected values
    ✓ exit codes are calculated correctly (128 + signal)
```

**Total tests:** 85 passing in exec.security.test.js

## Security Benefits

1. **Observable Security** - Resource limit violations are now visible and logged
2. **Audit Trail** - Security team can detect potential attacks (fork bombs, memory exhaustion)
3. **User Education** - Users learn about resource constraints and how to work within them
4. **Operational Clarity** - Operations teams can quickly diagnose why commands failed

## Backward Compatibility

Fully backward compatible:
- No changes to existing APIs
- New `resourceViolation` field is additive only
- All existing functionality preserved

## Example Usage

### Interactive Mode (Shell)
```bash
$ mc exec mc-core sh --shell
# Inside container: :(){ :|: & };:
❌ Shell killed: Process was forcefully killed (likely OOM or nproc limit)
   💡 Command may have exceeded memory (1GB) or process (256) limits. Try simplifying the command or use --shell for interactive debugging.
```

### Non-Interactive Mode
```bash
$ mc exec mc-core ":(){ :|: & };:"
❌ Resource limit exceeded: RESOURCE_LIMIT
   Process was forcefully killed (likely OOM or nproc limit)
   💡 Command may have exceeded memory (1GB) or process (256) limits. Try simplifying the command or use --shell for interactive debugging.
   Exit code: 137 (1245ms)
```

## Audit Integration

Resource limit violations can be viewed in the security audit log:

```bash
mc audit -t SECURITY_VIOLATION
```

This helps security teams identify:
- Potential denial-of-service attempts
- Misconfigured applications
- Resource-intensive operations that may need optimization

## Version

This improvement is included in masterclaw-tools v0.29.0+

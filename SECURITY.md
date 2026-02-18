# Security Policy

MasterClaw takes security seriously. This document outlines our security practices, how to report vulnerabilities, and the security features built into the ecosystem.

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.21.x  | :white_check_mark: |
| < 0.20  | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability in MasterClaw, please report it responsibly:

1. **Do not** open a public issue
2. Email security concerns to: rexdeus@gmail.com
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

We aim to respond within 48 hours and will work with you to understand and address the issue promptly.

## Security Features

### Input Validation & Sanitization

All user inputs are validated and sanitized:

- **Container names**: Validated against whitelist pattern (`/^[a-zA-Z0-9][a-zA-Z0-9_.-]*$/`)
- **File paths**: Path traversal attempts (`../`, `..\`) are blocked
- **Command arguments**: Dangerous characters (`;`, `|`, `&`, `` ` ``) are rejected
- **Log entries**: Control characters and newlines are sanitized to prevent log injection
- **JSON inputs**: Depth-limited parsing with prototype pollution protection

### Rate Limiting

Command rate limiting prevents abuse:

| Category | Commands | Limit | Window |
|----------|----------|-------|--------|
| High Security | `config-audit`, `exec`, `restore` | 3-10 | 1-5 min |
| Deployment | `deploy`, `revive` | 5-10 | 1-5 min |
| Data Modification | `cleanup`, `import` | 5-10 | 1 min |
| Read-Only | `status`, `logs`, `validate` | 30-60 | 1 min |

### Circuit Breaker

Service resilience through circuit breaker pattern:
- Opens after 3 consecutive failures
- Automatic recovery testing in half-open state
- Per-service isolation prevents cascading failures

### Audit Logging

All security-relevant events are logged with HMAC-SHA256 signatures:
- Authentication attempts (success/failure)
- Security violations
- Configuration changes
- Container executions
- Backup/restore operations

**Tamper Detection**: Audit log integrity can be verified with `mc audit-verify`

### Secrets Management

Secure handling of API keys and tokens:
- Secrets stored with `0o600` file permissions
- Masked display by default (show first/last 4 chars only)
- Format validation for API keys
- Audit logging of all secret operations (values never logged)

### Container Execution Security

The `mc exec` command includes multiple protections:
- Container whitelist (only MasterClaw containers allowed)
- Command injection prevention
- Blocked dangerous commands: `rm`, `dd`, `mkfs`, `fdisk`
- 5-minute timeout for non-interactive commands
- All executions logged for security review

### Error Handling

Comprehensive error handling prevents information leakage:
- Sensitive data (tokens, passwords) automatically masked in logs
- User-friendly error messages without technical details
- Proper exit codes for CI/CD integration
- Structured JSON output mode for production environments

### Correlation IDs

Distributed tracing via correlation IDs:
- Automatic generation for each command execution
- Propagates through logs, audit entries, and HTTP headers
- Prevents log injection (max 64 chars, alphanumeric + `_-`)
- Enables request tracing across services

## Security Best Practices

### For Users

1. **Keep tokens secure**: Store `GATEWAY_TOKEN` and API keys in environment variables or secure vaults
2. **Regular audits**: Run `mc security` and `mc config-audit` periodically
3. **Verify backups**: Use `mc backup-verify` to ensure backups are restorable
4. **Monitor audit logs**: Review `mc audit` output for suspicious activity
5. **Update regularly**: Keep MasterClaw updated to latest version

### For Developers

1. **Validate all inputs**: Use `lib/security.js` utilities for input validation
2. **Sanitize logs**: Use `sanitizeForLog()` and `maskSensitiveData()` for all logged output
3. **Use wrapCommand**: Wrap all command handlers with `wrapCommand()` for automatic error handling
4. **Audit security events**: Log security violations with `logSecurityViolation()`
5. **Test security features**: Add tests for security validation in `tests/*.security.test.js`

## Security Testing

Run the security-focused test suite:

```bash
cd masterclaw-tools
npm test -- --testNamePattern="security"
```

Security test coverage includes:
- Path traversal prevention
- Command injection blocking
- Log injection sanitization
- Prototype pollution protection
- Rate limiting enforcement
- SSL/TLS validation
- Audit log integrity

## Vulnerability Disclosure Timeline

1. **Day 0**: Vulnerability reported
2. **Day 2**: Acknowledgment and initial assessment
3. **Day 7**: Patch developed and tested
4. **Day 14**: Patch released and security advisory published

Critical vulnerabilities may be addressed sooner.

## Security-Related Commands

```bash
# Security scan
mc security                    # Full security scan
mc security --status           # Quick status check

# Configuration audit
mc config-audit                # Audit config file permissions
mc config-fix                  # Fix config permissions

# Audit log review
mc audit                       # View recent audit entries
mc audit-verify                # Verify audit log integrity

# Rate limiting
mc rate-limit                  # View rate limit status

# Circuit breaker
mc circuits                    # View circuit breaker status
```

## Compliance

MasterClaw's security features help with:
- **SOC 2**: Audit logging, access controls, monitoring
- **GDPR**: Data retention policies, secure deletion
- **HIPAA**: Audit trails, access logging (when properly configured)

## Acknowledgments

We thank security researchers and contributors who help improve MasterClaw's security.

---

Last updated: February 2026

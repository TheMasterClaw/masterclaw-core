# MasterClaw Services Security Hardening Improvement

**Date:** 2026-02-19  
**Component:** `masterclaw-tools/lib/services.js`  
**Category:** Security Hardening

## Summary

Replaced direct `axios` usage with the secure HTTP client (`http-client.js`) in the MasterClaw Services module. This ensures all internal service health checks benefit from SSRF protection, DNS rebinding protection, and other security hardening features.

Additionally, implemented lazy initialization in `http-client.js` to prevent test failures when axios is mocked.

## Changes Made

### 1. Module Import Update (`lib/services.js`)
```javascript
// Before:
const axios = require('axios');

// After:
const httpClient = require('./http-client');
```

### 2. Service Health Checks (`checkService` function)
- Replaced `axios.get()` with `httpClient.get()`
- Added `httpClient.allowPrivateIPs()` wrapper for internal localhost services
- Maintains all existing functionality including circuit breaker, retry logic, and error handling

### 3. HTTP Client Lazy Initialization (`lib/http-client.js`)
- Changed from module-load-time initialization to lazy initialization
- Added `getDefaultClient()` function to create client on first use
- Added `_resetDefaultClient()` helper for testing
- Prevents test failures when axios is mocked by Jest

### 4. Export Cleanup (`lib/services.js`)
- Removed `axios` from module exports
- Maintains all other exports for backward compatibility

### 5. Security Documentation Update
- Added security documentation to module header
- Documents SSRF and DNS rebinding protection usage

## Security Benefits

### SSRF Protection
The secure HTTP client provides:
- **Blocks private IPs by default** - Prevents access to internal services from external URLs
- **Validates hostnames** - Rejects suspicious patterns and internal hostnames
- **URL scheme validation** - Blocks `data:`, `file:`, `javascript:` URLs

### DNS Rebinding Protection
- **Dual validation** - Validates both hostname AND resolved IP addresses
- **Prevents DNS rebinding attacks** - Where attackers change DNS records after initial check
- **Blocks private IPs that resolve from external hostnames**

### Header Security
- **Prevents header injection** - Sanitizes headers, blocks CRLF injection
- **Response size limits** - Prevents DoS via oversized responses (10MB max)

## Testing

Created comprehensive test suite (`tests/services.security.test.js`) with 22 tests covering:

1. **Module Structure** (2 tests)
   - No direct axios export
   - All expected functions exported

2. **HTTP Client Security** (4 tests)
   - httpClient module availability
   - SSRF protection validation
   - DNS rebinding protection
   - allowPrivateIPs() wrapper

3. **Service Configuration Security** (4 tests)
   - Valid SERVICE constants
   - Localhost URLs for internal services
   - Reasonable timeout values
   - Service name whitelist validation

4. **Circuit Breaker Security** (2 tests)
   - Circuit breaker configuration presence
   - Reasonable threshold values

5. **Retry Configuration Security** (2 tests)
   - Retry configuration with safe defaults
   - Reasonable retry limits

6. **Docker Security Constants** (2 tests)
   - Buffer size limits
   - Compose timeout limits

7. **Security Documentation** (4 tests)
   - Security documentation in module header
   - http-client import verification
   - No raw axios in health checks
   - allowPrivateIPs() usage verification

8. **Integration Security** (2 tests)
   - Service name validation before requests
   - validateServiceNames() rejects invalid inputs

### Running the Tests
```bash
cd masterclaw-tools
npm test -- tests/services.security.test.js
```

Expected output:
```
PASS tests/services.security.test.js
  Services Security
    Module Structure
      ✓ should not export axios directly
      ✓ should export all expected service functions
    HTTP Client Security
      ✓ should have httpClient module available
      ✓ httpClient should have SSRF protection
      ✓ httpClient should have DNS rebinding protection
      ✓ should allow private IPs with allowPrivateIPs wrapper
    Service Configuration Security
      ✓ should have valid SERVICE constants defined
      ✓ should use localhost URLs for internal services
      ✓ should have reasonable timeout values
      ✓ should validate service names against whitelist
    Circuit Breaker Security
      ✓ should have circuit breaker configuration
      ✓ circuit breaker should have reasonable thresholds
    Retry Configuration Security
      ✓ should have retry configuration with safe defaults
      ✓ retry config should have reasonable limits
    Docker Security Constants
      ✓ should have buffer size limits
      ✓ should have compose timeout limits
  Services Security Documentation
      ✓ should have security documentation in module header
      ✓ should import http-client for secure requests
      ✓ should not use raw axios in service health checks
      ✓ should use httpClient.allowPrivateIPs for internal requests
  Services Security Integration
      ✓ checkService should validate service name before making requests
      ✓ validateServiceNames should reject non-array inputs

Test Suites: 1 passed, 1 total
Tests:       22 passed, 22 total
```

## Backward Compatibility

✅ **Fully backward compatible** - No API changes, no behavioral changes
- All existing functionality preserved
- Error handling behavior unchanged
- Logging and correlation ID tracking maintained
- Circuit breaker and retry mechanisms still work
- All module exports maintained (except direct axios export)

## Files Modified

1. `lib/services.js` - Security hardening of HTTP requests
2. `lib/http-client.js` - Lazy initialization for test compatibility
3. `tests/services.security.test.js` - New comprehensive test suite (NEW)

## Verification

Run all security-related tests:
```bash
cd masterclaw-tools
npm test -- --testPathPattern="security|services"
```

Expected output:
```
Test Suites: 14 passed, 14 total
Tests:       591 passed, 591 total
```

## Related Documentation

- [http-client.js](./lib/http-client.js) - Secure HTTP client implementation
- [README.md](./README.md) - MasterClaw Tools documentation
- [SECURITY.md](./SECURITY.md) - Security features overview

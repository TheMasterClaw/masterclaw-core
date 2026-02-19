# SSL Module Test Coverage Improvement

## Summary

Added test suite for the `ssl.js` module, covering SSL certificate management commands.

## Changes Made

### Created `tests/ssl.test.js`

Test suite with **15 test cases** covering:

#### Module Structure Tests (4 tests)
- Exports ssl command
- Has check subcommand
- Has renew subcommand
- Has info subcommand

#### Check Command Tests (2 tests)
- Has no required arguments
- Has no aliases

#### Renew Command Tests (3 tests)
- Has --force option
- Has no required arguments
- Has no aliases

#### Info Command Tests (2 tests)
- Has no required arguments
- Has no aliases

#### SSL Functionality Tests (4 tests)
- Check command checks certificate expiration
- Renew command triggers certificate renewal
- Info command shows SSL configuration
- Domains checked include main and subdomains

## Test Results

```
Test Suites: 1 passed, 1 total
Tests:       15 passed, 15 total
```

## Commands Tested

### `mc ssl check`
- Check SSL certificate expiration for all domains
- Checks: domain, api.domain, gateway.domain, core.domain, traefik.domain

### `mc ssl renew`
- Force SSL certificate renewal via Traefik
- Options: `--force`

### `mc ssl info`
- Show SSL configuration information
- Displays: Domain, API, Gateway, Core, Traefik endpoints

## Commit Details

- **Commit:** `82bcb4a`
- **Message:** `test(ssl): Add test suite for SSL certificate management module`
- **Files Changed:** 1 file, 101 insertions(+)

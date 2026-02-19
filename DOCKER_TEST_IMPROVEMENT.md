# Docker Module Test Coverage Improvement

## Summary

Added comprehensive test suite for the `docker.js` module, covering Docker security validation functions.

## Changes Made

### 1. Updated `lib/docker.js`

Exported additional constants for testing:
- `VALID_CONTAINER_NAME` - Regex for valid container names
- `DANGEROUS_CHARS` - Regex for dangerous shell characters

### 2. Created `tests/docker.test.js`

Comprehensive test suite with **42 test cases** covering:

#### Constants Tests (8 tests)
- VALID_CONTAINER_NAME allows valid names
- VALID_CONTAINER_NAME rejects invalid names
- MAX_CONTAINER_NAME_LENGTH is 63
- MAX_TAIL_LINES is 10000
- ALLOWED_COMPOSE_COMMANDS contains expected commands
- DANGEROUS_CHARS matches shell metacharacters
- DEFAULT_DOCKER_TIMEOUT_MS is 5 minutes
- QUICK_DOCKER_TIMEOUT_MS is 30 seconds

#### DockerSecurityError Tests (3 tests)
- Creates error with message and code
- Includes details when provided
- Is instanceof Error

#### validateContainerName Tests (9 tests)
- Accepts valid container names
- Rejects non-string names
- Rejects empty names
- Rejects names that are too long
- Rejects names with path traversal
- Rejects names starting with hyphen
- Rejects names starting with dot
- Rejects names with dangerous characters
- Accepts names at max length

#### validateComposeArgs Tests (9 tests)
- Accepts valid compose up command
- Accepts valid compose down command
- Accepts valid compose logs command
- Rejects non-array arguments
- Rejects non-string arguments
- Rejects disallowed commands
- Rejects dangerous characters in args
- Rejects command substitution
- Accepts empty array

#### validateWorkingDirectory Tests (7 tests)
- Accepts valid paths
- Accepts null/undefined
- Rejects non-string paths
- Rejects paths with null bytes
- Rejects paths starting with ..
- Rejects paths containing ../
- Rejects paths containing ..\\

#### validateTailOption Tests (6 tests)
- Accepts undefined/null
- Accepts valid numbers
- Rejects negative numbers
- Rejects numbers over MAX_TAIL_LINES
- Accepts MAX_TAIL_LINES exactly
- Rejects non-numbers

## Test Results

```
Test Suites: 1 passed, 1 total
Tests:       42 passed, 42 total
```

## Security Features Tested

1. **Container Name Validation**: Alphanumeric, hyphens, underscores, dots only
2. **Path Traversal Prevention**: Blocks .. sequences in paths
3. **Command Injection Prevention**: Blocks shell metacharacters
4. **Compose Command Whitelist**: Only allowed commands can be executed
5. **Resource Limits**: Max 10,000 log lines to prevent DoS
6. **Custom Error Classes**: DockerSecurityError with detailed codes

## Commit Details

- **Commit:** `469ddf8`
- **Message:** `test(docker): Add comprehensive test suite for Docker security module`
- **Files Changed:** 2 files, 199 insertions(+), 294 deletions(-)

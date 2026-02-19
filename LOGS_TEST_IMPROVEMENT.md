# Logs Module Test Coverage Improvement

## Summary

Added comprehensive test suite for the `logs.js` module, covering log management validation functions, security checks, and utility functions. Also added new helper functions for better code organization and testability.

## Changes Made

### 1. Updated `lib/logs.js`

Added new validation functions:

#### validateExportOptions(options)
Validates export options (wrapper for validateLines).
- Checks `lines` option against MAX_EXPORT_LINES
- Throws DockerSecurityError if invalid

#### validateSearchQuery(query)
Validates search query strings.
- Checks for non-string input
- Trims whitespace and checks for empty queries
- Delegates to validateSearchPattern for dangerous character detection

#### validateFilename(filename)
Validates filenames for exports.
- Checks for path traversal sequences (.., /, \\)
- Checks for dangerous shell characters
- Validates against VALID_FILENAME pattern
- Ensures filename starts with alphanumeric character

Added new utility functions:

#### formatServiceName(service)
Maps service names to container names.
- Returns container name (e.g., 'mc-core') for valid service
- Returns null for 'all' or unknown services

#### parseSinceOption(since)
Parses duration strings into ISO timestamps.
- Supports: s (seconds), m (minutes), h (hours), d (days), w (weeks)
- Returns ISO 8601 timestamp or null if invalid
- Used for --since flag in log queries

### 2. Created `tests/logs.test.js`

Comprehensive test suite with **45 test cases** covering:

#### Constants Tests (8 tests)
- SERVICES mapping validation
- VALID_SERVICES set contents
- VALID_DURATION pattern matching
- MAX_EXPORT_LINES value (50000)
- DANGEROUS_CHARS pattern matching
- VALID_FILENAME pattern validation

#### validateServiceName Tests (4 tests)
- Accepts valid service names
- Rejects invalid service names
- Rejects non-string inputs
- Error includes valid services list

#### validateDuration Tests (4 tests)
- Accepts valid durations (30s, 5m, 1h, 7d, 2w)
- Rejects invalid formats
- Rejects non-string inputs
- Error includes valid format examples

#### validateExportOptions Tests (5 tests)
- Accepts valid options
- Rejects lines over MAX_EXPORT_LINES
- Rejects negative lines
- Rejects non-numeric lines
- Handles undefined lines

#### validateSearchQuery Tests (4 tests)
- Accepts valid search queries
- Rejects empty/whitespace-only queries
- Rejects queries with dangerous characters
- Rejects non-string queries

#### validateFilename Tests (5 tests)
- Accepts valid filenames
- Rejects path traversal attempts
- Rejects dangerous characters
- Rejects names starting with dots or hyphens
- Rejects empty filenames

#### formatServiceName Tests (3 tests)
- Formats known services to container names
- Returns null for 'all'
- Returns null for unknown services

#### parseSinceOption Tests (8 tests)
- Parses seconds, minutes, hours, days, weeks
- Returns null for invalid duration
- Returns null for non-string input
- Returns valid ISO 8601 timestamp

#### Edge Case Tests (4 tests)
- Handles very long search queries
- Handles unicode in search queries
- Handles whitespace-only as empty
- MAX_EXPORT_LINES boundary testing

## Test Results

```
Test Suites: 1 passed, 1 total
Tests:       45 passed, 45 total
```

## Security Benefits

1. **Path Traversal Prevention**: Filename validation blocks .., /, and \\ sequences
2. **Command Injection Prevention**: Dangerous shell characters are rejected
3. **DoS Prevention**: MAX_EXPORT_LINES limits resource consumption
4. **Input Validation**: All inputs are type-checked and validated

## Commit Details

- **Commit:** `33829e4`
- **Message:** `test(logs): Add comprehensive test suite for log management module`
- **Files Changed:** 2 files, 502 insertions(+)

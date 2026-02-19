# Troubleshoot Module Test Coverage Improvement

## Summary

Added comprehensive test suite for the `troubleshoot.js` module, covering the troubleshooting guide functionality with issue database and utility functions.

## Changes Made

### 1. Updated `lib/troubleshoot.js`

Exported utility functions for testing:
- `getIssuesByCategory` - Filter issues by category
- `getAllCategories` - Get all unique categories
- `formatSeverity` - Format severity levels with colors

### 2. Created `tests/troubleshoot.test.js`

Comprehensive test suite with **26 test cases** covering:

#### ISSUES Database Tests (13 tests)
- Contains expected issues (8 total)
- Each issue has required fields (title, symptoms, severity, category, diagnosis, solutions, prevention)
- Severities are valid (critical, high, medium, low)
- Categories are valid (docker, ssl, performance, database, api, backup, notifications)
- Solutions have required fields (title, command, description)
- Individual issue validation:
  - services-down has correct structure
  - ssl-cert-issues has SSL-related solutions
  - database-issues has database-related diagnosis
  - high-memory-usage has memory-related solutions
  - llm-api-errors has API-related diagnosis
  - backup-failures has backup-related solutions
  - slow-performance has performance-related diagnosis
  - notification-issues has notification-related solutions

#### getIssuesByCategory Tests (4 tests)
- Returns issues for valid category
- Returns empty array for category with no issues
- Returned issues have key property
- Performance category has expected issues

#### getAllCategories Tests (4 tests)
- Returns array of categories
- Returns unique categories (no duplicates)
- Includes expected categories
- Does not include duplicates

#### formatSeverity Tests (5 tests)
- Returns formatted string for critical
- Returns formatted string for high
- Returns formatted string for medium
- Returns formatted string for low
- Handles unknown severity gracefully

## Test Results

```
Test Suites: 1 passed, 1 total
Tests:       26 passed, 26 total
```

## Issue Database Coverage

The tests verify the following 8 common issues:

1. **services-down** - Docker containers not starting (critical)
2. **ssl-cert-issues** - SSL certificate problems (high)
3. **high-memory-usage** - Out of memory issues (high)
4. **database-issues** - Database connection problems (critical)
5. **llm-api-errors** - LLM API connection errors (high)
6. **backup-failures** - Backup not working (medium)
7. **slow-performance** - Slow response times (medium)
8. **notification-issues** - Notifications not working (low)

## Commit Details

- **Commit:** `d17616f`
- **Message:** `test(troubleshoot): Add comprehensive test suite for troubleshooting module`
- **Files Changed:** 2 files, 243 insertions(+), 1 deletion(-)

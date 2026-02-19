# Dependencies Module Test Coverage Improvement

## Summary

Added comprehensive test suite for the `deps.js` module, covering service dependency management and infrastructure directory discovery.

## Changes Made

### 1. Updated `lib/deps.js`

Exported functions for testing:
- `findInfraDir` - Find infrastructure directory
- `showDependencyTree` - Display service dependency tree

### 2. Created `tests/deps.test.js`

Comprehensive test suite with **18 test cases** covering:

#### findInfraDir Tests (5 tests)
- Returns null when no infrastructure directory found
- Finds directory from MASTERCLAW_INFRA environment variable
- Checks multiple candidate locations
- Returns first matching directory
- Handles null/undefined in candidates gracefully

#### showDependencyTree Tests (11 tests)
- Outputs dependency tree header
- Shows all services (traefik, interface, backend, core, gateway, chroma, watchtower)
- Shows service descriptions
- Shows dependencies for services with deps
- Shows no dependencies for base services
- Shows legend
- traefik has correct dependencies (gateway, core, backend, interface)
- core depends on chroma
- backend depends on gateway and core
- gateway has no dependencies
- chroma has no dependencies

#### Dependency Tree Structure Tests (2 tests)
- Dependency tree has expected structure
- No circular dependencies in tree

## Test Results

```
Test Suites: 1 passed, 1 total
Tests:       18 passed, 18 total
```

## Service Dependencies Documented

```
traefik → gateway, core, backend, interface
interface → backend
backend → gateway, core
core → chroma
gateway → (none)
chroma → (none)
watchtower → (none)
```

## Commit Details

- **Commit:** `168f6ea`
- **Message:** `test(deps): Add comprehensive test suite for dependency management module`
- **Files Changed:** 2 files, 270 insertions(+)

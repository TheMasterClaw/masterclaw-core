# Config Module Test Coverage Improvement

## Summary

Added comprehensive test suite for the `config.js` module, covering configuration management with prototype pollution protection.

## Changes Made

### Created `tests/config.test.js`

Comprehensive test suite with **45 test cases** covering:

#### Constants Tests (3 tests)
- CONFIG_DIR uses correct path (~/.masterclaw)
- CONFIG_FILE uses correct path (~/.masterclaw/config.json)
- DANGEROUS_KEYS includes prototype pollution keys

#### isDangerousKey Tests (5 tests)
- Returns true for __proto__
- Returns true for constructor
- Returns true for prototype
- Returns false for safe keys
- Returns false for similar but safe keys

#### sanitizeKey Tests (5 tests)
- Returns safe keys unchanged
- Throws for __proto__
- Throws for constructor
- Throws for prototype
- Throws for non-string keys

#### safeDeepMerge Tests (8 tests)
- Merges simple objects
- Source overrides target properties
- Deep merges nested objects
- Skips dangerous keys
- Skips constructor key
- Handles null source
- Handles null target
- Handles arrays

#### sanitizeConfigObject Tests (5 tests)
- Returns primitives unchanged
- Sanitizes simple objects
- Removes dangerous keys from objects
- Sanitizes nested objects
- Sanitizes arrays of objects

#### checkConfigPermissions Tests (3 tests)
- Returns secure for good permissions (0o700 dir, 0o600 file)
- Detects insecure file permissions (0o644)
- Detects group writable (0o660)

#### loadConfig Tests (4 tests)
- Returns default config when file does not exist
- Loads and merges config from file
- Sanitizes loaded config
- Ensures config directory exists

#### saveConfig Tests (3 tests)
- Saves config to file
- Sets secure file permissions (0o600)
- Ensures config directory exists

#### get Tests (3 tests)
- Gets top-level value
- Gets nested value with dot notation
- Returns undefined for missing key

#### set Tests (4 tests)
- Sets top-level value
- Sets nested value with dot notation
- Throws for dangerous keys
- Creates nested objects as needed

#### list Tests (1 test)
- Returns full config

#### reset Tests (1 test)
- Resets to default config

## Test Results

```
Test Suites: 1 passed, 1 total
Tests:       45 passed, 45 total
```

## Security Features Tested

1. **Prototype Pollution Prevention**: Blocks `__proto__`, `constructor`, `prototype` keys
2. **Safe Object Merging**: Recursively merges without prototype pollution
3. **Config Sanitization**: Removes dangerous keys from loaded configs
4. **Secure File Permissions**: Uses 0o600 for files, 0o700 for directory
5. **Permission Checking**: Validates file and directory permissions

## Default Config Structure

```javascript
{
  infraDir: null,
  gateway: { url: 'http://localhost:3000', token: null },
  api: { url: 'http://localhost:3001' },
  core: { url: 'http://localhost:8000' },
  defaults: { backupRetention: 7, autoUpdate: true }
}
```

## Commit Details

- **Commit:** `c1b6fc7`
- **Message:** `test(config): Add comprehensive test suite for config module`
- **Files Changed:** 1 file, 455 insertions(+)

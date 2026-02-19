# MasterClaw Config Diff Command Improvement

**Date:** 2026-02-19  
**Component:** `masterclaw-tools` (CLI)  
**Version:** 0.50.0 → 0.51.0  
**Commit:** masterclaw-improvement-1

---

## Summary

Added the `mc config diff` command to the MasterClaw CLI, enabling users to compare their current configuration against default values or example configuration files. This addresses a gap where users couldn't easily identify configuration drift or see which settings differ from defaults.

## Motivation

Previously, users had no easy way to:
- Identify which configuration settings differ from defaults
- Compare their config against example files
- Detect configuration drift over time
- Troubleshoot issues caused by custom settings

The new `mc config diff` command solves these problems by providing a clear, visual diff of configuration differences.

## Changes Made

### 1. Enhanced Config Commands (`lib/config-cmd.js`)

Added the `diff` subcommand with the following features:

**Command Options:**
```bash
mc config diff                           # Compare with built-in defaults
mc config diff --example <file>          # Compare against example config file
mc config diff --json                    # Machine-readable JSON output
mc config diff --no-mask                 # Show actual values (not masked)
```

**Diff Categories:**
- **Modified Values** — Settings that differ from comparison
- **Only in Current** — Custom settings not in defaults/example
- **Missing from Current** — Settings present in defaults but not current config
- **Same Values** — Settings that match (count only)

**Features:**
- Automatic sensitive value masking (tokens, passwords, secrets)
- Recursive comparison of nested objects
- Protection against prototype pollution attacks
- JSON output for scripting and CI/CD integration
- Pretty-printed colorized output for human readability

### 2. Version Bump

- `package.json`: 0.49.0 → 0.51.0
- `bin/mc.js`: Updated version comment to 0.51.0

### 3. Documentation Update (`README.md`)

Added comprehensive documentation for the new command:
- Command syntax and examples
- Feature description
- Sample output showing diff format

## Implementation Details

### Comparison Algorithm

The diff command uses a recursive comparison algorithm that:
1. Flattens nested objects for comparison
2. Handles null/undefined values correctly
3. Skips dangerous keys (`__proto__`, `constructor`, `prototype`)
4. Compares values using JSON serialization for accuracy

### Security Considerations

- **Prototype Pollution Protection**: All keys are checked against dangerous keys
- **Sensitive Value Masking**: Values containing "token", "password", "secret", "key", or "apikey" are automatically masked
- **Secure File Access**: Example files are validated to exist before reading
- **JSON Validation**: Example config files must be valid JSON

### Default Configuration

When no `--example` file is provided, the command compares against built-in defaults:
```javascript
{
  infraDir: null,
  gateway: {
    url: 'http://localhost:3000',
    token: null,
  },
  api: {
    url: 'http://localhost:3001',
  },
  core: {
    url: 'http://localhost:8000',
  },
  defaults: {
    backupRetention: 7,
    autoUpdate: true,
  },
}
```

## Example Output

### Standard Output
```
🐾 Configuration Diff

Comparing current config with: defaults

📝 Modified Values

  gateway.url:
    Current:   "https://gw.example.com"
    Default:   "http://localhost:3000"

  defaults.backupRetention:
    Current:   14
    Default:   7

➕ Only in Current Config

  custom.setting: "my-value"

📊 Summary
  Modified:   2
  Added:      1
  Missing:    0
  Same:       4

Use --example <file> to compare against a specific config file
```

### JSON Output
```bash
mc config diff --json
```
```json
{
  "comparisonSource": "defaults",
  "currentConfig": "[MASKED]",
  "differences": [
    {
      "key": "gateway.url",
      "currentValue": "https://gw.example.com",
      "comparisonValue": "http://localhost:3000"
    }
  ],
  "onlyInCurrent": [...],
  "onlyInComparison": [...],
  "sameCount": 4
}
```

## Use Cases

### 1. Configuration Auditing
```bash
# Check for configuration drift
mc config diff
```

### 2. CI/CD Validation
```bash
# Ensure config matches expected values
mc config diff --example config.prod.json --json | jq '.differences | length' | grep -q '^0$'
```

### 3. Troubleshooting
```bash
# Compare broken environment with working one
mc config diff --example /path/to/working/config.json
```

### 4. Documentation
```bash
# Export config differences for documentation
mc config diff --json > config-drift-report.json
```

## Testing

The implementation has been tested for:
- ✅ Correct diff calculation
- ✅ Nested object comparison
- ✅ Sensitive value masking
- ✅ JSON output format
- ✅ Example file loading
- ✅ Error handling (missing files, invalid JSON)
- ✅ Prototype pollution protection

## Integration with Existing Features

| Feature | Integration |
|---------|-------------|
| `mc config list` | Shows current values; diff shows differences |
| `mc config export` | Export current config; diff compares it |
| `mc config import` | Import shows diff preview; this command is standalone diff |
| `mc env diff` | Compares .env files; this compares CLI config |

## Backward Compatibility

✅ **Fully backward compatible** — No existing functionality changed
- All existing config commands work identically
- New command is additive only
- No changes to config file format

## Future Enhancements

Potential improvements:
- `--save-diff` flag to export differences to a patch file
- Integration with `mc config import` to apply diff patches
- `--ignore <key>` option to exclude specific keys from comparison
- Config versioning and history tracking
- Automatic drift detection in `mc ops` dashboard

---

*Built for Rex. Powered by MasterClaw.* 🐾

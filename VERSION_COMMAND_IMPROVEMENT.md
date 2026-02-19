# Version Command Improvement

## Summary

Added a unified `mc version` command to the MasterClaw CLI that provides comprehensive version management across the entire ecosystem. This addresses the gap where operators needed to manually check different sources to determine what versions of components were running and whether updates were available.

## Problem

Previously, there was no single command to:
- See versions of all MasterClaw components in one view
- Check if updates were available across the ecosystem
- Compare versions between components for compatibility
- Programmatically check versions in CI/CD pipelines

Operators had to:
1. Check `package.json` for CLI version
2. Query running APIs for service versions
3. Run `git describe` in infrastructure directory
4. Manually compare against npm registry and git tags

## Solution

Created `lib/version.js` with the following features:

### Commands

```bash
mc version                          # Display all component versions
mc version --json                   # Output as JSON
mc version --check-updates          # Check for available updates
mc version --all                    # Show detailed version info
mc version check                    # Check updates, exit code for CI/CD
mc version check --quiet            # Silent check for scripts
mc version compare 1.0.0 1.1.0      # Compare two version strings
```

### Features

1. **Multi-Source Version Detection:**
   - CLI version from `package.json`
   - Core/Backend/Interface versions from running APIs
   - Infrastructure version from git tags/commits
   - Fallback to file-based or directory-based detection

2. **Update Checking:**
   - Queries npm registry for CLI updates
   - Queries git tags for infrastructure updates
   - Shows commits behind if applicable
   - Provides upgrade commands

3. **Semantic Version Comparison:**
   - Properly handles `v` prefixes
   - Supports different version lengths (1.0 vs 1.0.0)
   - Used for determining update availability

4. **CI/CD Integration:**
   - JSON output for parsing
   - Exit codes for `mc version check`
   - Quiet mode for silent checks

### Security

- Uses secure HTTP client with SSRF/DNS rebinding protection
- All external requests have timeouts
- No sensitive information exposed in output

## Files Changed

1. **lib/version.js** (NEW) — Main version command implementation (~600 lines)
2. **bin/mc.js** — Added version command import and registration
3. **tests/version.test.js** (NEW) — Unit tests for version functions
4. **package.json** — Version bump to 0.52.0, added keywords
5. **README.md** — Added documentation for version command

## Testing

```bash
# Run unit tests
npm test -- tests/version.test.js

# Manual testing
node bin/mc.js version
node bin/mc.js version --json
node bin/mc.js version --check-updates
node bin/mc.js version compare 0.51.0 0.52.0
```

## Example Output

```
🐾 MasterClaw Version Information

Components:
  CLI Tools:       0.52.0
  AI Core:         0.48.2 (running)
  Backend API:     0.31.0 (running)
  Web Interface:   0.25.1 (running)
  Infrastructure:  v1.2.0 (main)

Updates:
  ✓ All components are up to date
```

With updates available:
```
Updates:
  Updates are available:

  CLI Tools: 0.52.0 → 0.53.0

Update commands:
  npm update -g masterclaw-tools    # Update CLI
```

## Benefits

1. **Operational Visibility** — Single command to see entire ecosystem state
2. **Update Management** — Know immediately when updates are available
3. **CI/CD Integration** — Automate version checks in pipelines
4. **Debugging Aid** — Quickly identify version mismatches
5. **Time Saving** — No more manual version checking across sources

## Future Enhancements

- Add `mc version upgrade` to perform upgrades interactively
- Add compatibility matrix checking between components
- Add changelog linking for available updates
- Support for custom component registries

# MasterClaw Improvement: Docker System Prune Command

## Summary

Added **`mc prune`** — a comprehensive Docker system resource management command that fills a gap in the MasterClaw CLI tooling. While `mc cleanup` handles session/memory cleanup, there was no dedicated command for managing Docker images, containers, volumes, networks, and build cache. This feature provides safe, selective pruning with dry-run capability and MasterClaw service protection.

## What Was Improved

### 1. New `mc prune` Command

**Core functionality:**
- **Disk usage overview** — Shows Docker resource consumption by category (images, containers, volumes, build cache)
- **Reclaimable space analysis** — Calculates how much space can be freed
- **Smart recommendations** — Suggests pruning when >1GB reclaimable or >50% image space wasted

**Pruning targets (selective or all-at-once):**
- `--images` — Remove unused images (dangling or all unused)
- `--containers` — Remove stopped containers (with MasterClaw protection)
- `--volumes` — Remove unused volumes
- `--cache` — Remove build cache
- `--networks` — Remove unused networks
- `--all` — Prune everything

**Safety features:**
- **Dry-run mode (`--dry-run`)** — Preview what would be removed without actually deleting
- **MasterClaw service protection** — Containers with names containing `mc-core`, `mc-backend`, `mc-gateway`, etc. are never pruned
- **Confirmation prompts** — Requires explicit confirmation before destructive operations (skip with `--force`)
- **Dangling-only option** — Safe mode that only removes untagged images

**Subcommands:**
- `mc prune` — Show disk usage overview (default when no target specified)
- `mc prune quick` — Safe defaults: dangling images + stopped containers + unused networks
- `mc prune detail` — Detailed breakdown of images, containers, and volumes

### 2. Files Created/Modified

**New files:**
- `masterclaw-tools/lib/prune.js` — Command implementation (649 lines)
- `masterclaw-tools/tests/prune.test.js` — Comprehensive test suite (44 tests)

**Modified files:**
- `masterclaw-tools/bin/mc.js` — Added prune command registration and import
- `masterclaw-tools/package.json` — Version bumped from 0.36.0 → 0.37.0
- `CHANGELOG.md` — Documented new feature in Unreleased section

### 3. Test Coverage

44 comprehensive tests covering:
- Size parsing and formatting utilities
- Docker command execution with timeout protection
- Protected container detection (10 MasterClaw services)
- Command structure and option validation
- Disk usage calculations
- Safety features (dry-run, force flag)
- Quick prune defaults
- Image classification (dangling vs. normal)
- Container status (running vs. stopped, protected vs. safe)
- Volume management (unused detection, mc-* protection)
- Error handling (timeouts, missing Docker)
- Output formatting
- Security features (path traversal prevention, command injection detection)

## Usage Examples

```bash
# Show disk usage overview
mc prune

# Preview what would be pruned (dry-run)
mc prune --images --dry-run
mc prune --all --dry-run

# Quick safe cleanup
mc prune quick

# Prune specific resources
mc prune --images              # All unused images
mc prune --images --dangling-only  # Only untagged images
mc prune --containers          # Stopped containers (except MasterClaw)
mc prune --volumes             # Unused volumes
mc prune --cache               # Build cache

# Prune everything with force (no confirmation)
mc prune --all --force

# Show detailed breakdown
mc prune detail
mc prune detail --images
mc prune detail --containers
```

## Benefits

| Feature | Benefit |
|---------|---------|
| **Disk Usage Visibility** | Know exactly what's consuming Docker space |
| **Safe Cleanup** | Dry-run mode prevents accidental data loss |
| **Service Protection** | MasterClaw containers are never accidentally removed |
| **Selective Pruning** | Target specific resource types |
| **Quick Mode** | One-command safe cleanup for common scenarios |
| **CI/CD Ready** | `--force` flag enables automation |

## Security Considerations

- Path traversal prevention in container name handling
- Command injection protection via character filtering
- Timeout protection on all Docker commands (prevents hangs)
- Protected volume detection (volumes starting with `mc-`)
- Protected container detection (all MasterClaw services)

## Backward Compatibility

Fully backward compatible:
- New command doesn't affect existing functionality
- No changes to existing APIs or behavior
- Opt-in usage — only runs when explicitly called

## Total Improvement Stats

- **+649 lines** of implementation code
- **+44 tests** providing comprehensive coverage
- **+3 commits** to masterclaw-tools and main repository
- **Version bump:** 0.36.0 → 0.37.0

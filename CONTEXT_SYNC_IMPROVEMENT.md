# MasterClaw Improvement: Context Sync Command

## Summary

Added **`mc context sync`** command to synchronize rex-deus context files (preferences, projects, goals, knowledge, people) into the AI's memory system. This creates a live bridge between static documentation and dynamic AI context awareness.

## What Was Improved

### 1. New CLI Command: `mc context sync`

Synchronizes rex-deus context files into MasterClaw's memory system:

```bash
# Sync all context files
mc context sync

# Sync specific sections only
mc context sync --sections preferences,projects

# Dry run to preview changes
mc context sync --dry-run

# Force re-sync (overwrite existing)
mc context sync --force

# Sync with custom tags
mc context sync --tag personal-context
```

### 2. Features

**Smart Deduplication:**
- Uses content hashing to detect unchanged files
- Skips re-syncing identical content
- Updates only modified entries

**Metadata Enrichment:**
- Tags: `rex-deus`, `context`, `<section-name>`
- Source tracking: Links back to source file
- Timestamp: When sync occurred
- Priority: High (for context data)

**Section Mapping:**
| rex-deus File | Memory Category | Purpose |
|---------------|-----------------|---------|
| `preferences.md` | `user_preferences` | Communication style, preferences |
| `projects.md` | `active_projects` | Current projects, status |
| `goals.md` | `user_goals` | Objectives, milestones |
| `knowledge.md` | `domain_knowledge` | Rex's expertise areas |
| `people.md` | `relationships` | Contacts, relationships |

### 3. Integration Points

**Core API (`masterclaw_core`):**
- New endpoint: `POST /v1/context/sync`
- Accepts structured context data
- Stores with proper metadata
- Returns sync summary

**CLI (`masterclaw-tools`):**
- Added to `lib/context.js`
- Integrated into `bin/mc.js`
- Supports all standard options

**Rex-deus:**
- No changes required
- Reads existing context files
- Respects privacy boundaries

## Files Modified

### 1. `masterclaw-tools/lib/context.js`
Added sync functionality:
- `syncContext()` - Main sync orchestrator
- `parseContextFile()` - Extract structured data from markdown
- `hashContent()` - Detect changes
- `syncToMemory()` - Send to Core API

### 2. `masterclaw-tools/bin/mc.js`
Registered new command:
```javascript
program
  .command('context sync')
  .description('Sync rex-deus context to AI memory')
  .option('-s, --sections <list>', 'Comma-separated sections to sync')
  .option('-t, --tag <tag>', 'Custom tag for memories')
  .option('--dry-run', 'Preview changes without syncing')
  .option('-f, --force', 'Force re-sync all content');
```

### 3. `masterclaw_core/main.py`
Added API endpoint:
```python
@router.post("/v1/context/sync", tags=["context"])
async def sync_context(
    request: ContextSyncRequest,
    api_key: str = Depends(verify_api_key)
) -> ContextSyncResponse:
    """Sync rex-deus context into memory system"""
```

### 4. `masterclaw_core/models.py`
Added models:
- `ContextSyncRequest`
- `ContextSyncResponse`
- `ContextSection`
- `ContextSyncItem`

## Example Usage

### Initial Sync
```bash
$ mc context sync
🐾 Syncing rex-deus context to memory...

Found 5 context files:
  ✅ preferences.md (2.4KB) - 8 sections
  ✅ projects.md (1.8KB) - 4 sections  
  ✅ goals.md (0.9KB) - 3 sections
  ✅ knowledge.md (1.1KB) - 6 sections
  ✅ people.md (0.5KB) - 2 sections

Syncing to MasterClaw Core...
  Created: 23 new memories
  Updated: 0 existing
  Skipped: 0 (unchanged)

✅ Context sync complete!
   Memories are now available to the AI.
```

### Subsequent Sync (only changes)
```bash
$ mc context sync
🐾 Syncing rex-deus context to memory...

Found 5 context files:
  ⏭️  preferences.md (unchanged)
  ⏭️  projects.md (unchanged)
  ✅ goals.md (modified) - 1 new goal added
  ⏭️  knowledge.md (unchanged)
  ⏭️  people.md (unchanged)

Syncing to MasterClaw Core...
  Created: 2 new memories
  Updated: 1 existing
  Skipped: 20 (unchanged)

✅ Context sync complete!
```

### Dry Run
```bash
$ mc context sync --dry-run
🐾 Context Sync (DRY RUN)

Changes to be made:
  CREATE: "Communication Style" from preferences.md
  CREATE: "Technical Stack Preferences" from preferences.md
  UPDATE: "Active Projects" from projects.md

No changes made. Run without --dry-run to apply.
```

## Benefits

1. **Living Context** - Static docs become dynamic AI knowledge
2. **Privacy First** - Local processing, no external calls
3. **Efficient** - Only syncs changes, not full re-imports
4. **Traceable** - All context memories tagged with source
5. **Reversible** - Can purge and re-sync anytime

## Backward Compatibility

- Fully backward compatible
- New command is additive only
- Existing context display commands unchanged

## Version

masterclaw-tools v0.30.0+

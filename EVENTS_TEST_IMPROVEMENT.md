# Events Module Test Coverage Improvement

## Summary

Added comprehensive test suite for the `events.js` module, covering event tracking, filtering, formatting, and statistics functionality.

## Changes Made

### 1. Updated `lib/events.js`

Exported internal functions for testing:
- `initStorage` - Initialize events storage
- `saveEvents` - Save events to storage
- `generateEventId` - Generate unique event IDs
- `formatEvent` - Format events for display
- `filterEvents` - Filter events by various criteria
- `getRelativeTime` - Calculate relative time strings

### 2. Created `tests/events.test.js`

Comprehensive test suite with **45 test cases** covering:

#### Event ID Generation Tests (3 tests)
- Unique ID generation
- ID format validation (`evt_<timestamp>_<random>`)
- Timestamp inclusion in IDs

#### Event Storage Tests (3 tests)
- Events directory creation
- Default file structure creation
- Non-destructive initialization

#### addEvent Tests (7 tests)
- Event creation with required fields
- Custom options (severity, source, metadata)
- Event persistence
- Multiple event handling
- Event ordering (newest first)
- Null message handling
- Empty metadata handling

#### loadEvents Tests (4 tests)
- Empty storage handling
- Event retrieval
- Return value copying (not reference)
- Corrupted file recovery

#### filterEvents Tests (12 tests)
- Type filtering
- Severity filtering
- Source filtering
- Acknowledged status filtering
- Combined filters
- Search term matching (title and message)
- Since date filtering
- Case-insensitive search
- No-match scenarios

#### getRelativeTime Tests (5 tests)
- "just now" for recent events
- Minutes for events < 1 hour
- Hours for events < 1 day
- Days for events < 1 week
- Weeks for older events

#### formatEvent Tests (6 tests)
- Compact mode formatting
- Full mode formatting
- Acknowledged status display
- Verbose metadata inclusion
- Null message handling
- Empty metadata handling

#### EVENT_TYPES Constant Tests (2 tests)
- Expected event types presence
- Icon and color configuration

#### SEVERITY Constant Tests (3 tests)
- Expected severity levels
- Correct priority ordering
- Color functions

## Test Results

```
Test Suites: 1 passed, 1 total
Tests:       45 passed, 45 total
```

## Features Tested

1. **Event CRUD Operations**: Create, read, and manage events
2. **Event Filtering**: Multi-criteria filtering (type, severity, source, etc.)
3. **Time Formatting**: Relative time display (just now, 5m ago, 2h ago, etc.)
4. **Event Formatting**: Multiple output formats (compact, full, verbose)
5. **Constants Validation**: Event types and severity levels

## Commit Details

- **Commit:** `7ac3504`
- **Message:** `test(events): Add comprehensive test suite for event tracking module`
- **Files Changed:** 2 files, 463 insertions(+)

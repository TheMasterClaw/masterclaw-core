# Search Module Test Coverage Improvement

## Summary

Added test suite for the `search.js` module, covering search command structure for memories and tasks.

## Changes Made

### Created `tests/search.test.js`

Test suite with **15 test cases** covering:

#### Module Structure Tests (3 tests)
- Exports search command
- Has memory subcommand
- Has task subcommand

#### Memory Command Tests (5 tests)
- Takes query argument
- Has --limit option
- Limit defaults to 5
- Limit has short alias -n
- Has no aliases

#### Task Command Tests (3 tests)
- Takes query argument
- Has no options
- Has no aliases

#### Search Functionality Tests (4 tests)
- Memory command searches via core API
- Task command searches via API
- Memory search uses top_k parameter
- Task search filters by title and description

## Test Results

```
Test Suites: 1 passed, 1 total
Tests:       15 passed, 15 total
```

## Commands Tested

### `mc search memory <query>`
- Search through memories
- Options: `--limit` / `-n` (default: 5)
- Posts to core API at `/v1/memory/search`

### `mc search task <query>`
- Search through tasks
- No options
- Gets from API at `/tasks` and filters locally

## Commit Details

- **Commit:** `d90e9f2`
- **Message:** `test(search): Add test suite for search module`
- **Files Changed:** 1 file, 102 insertions(+)

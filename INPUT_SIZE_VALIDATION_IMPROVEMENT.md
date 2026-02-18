# Input Size Validation Security Improvement

## Summary

Added maximum length validation to Pydantic models to prevent DoS attacks via oversized inputs.

## Changes Made

### 1. Updated `masterclaw_core/models.py`

Added `max_length` constraints to the following models:

#### ChatRequest
- `message`: max_length=100,000 (100KB)
- `session_id`: max_length=64
- `model`: max_length=100
- `system_prompt`: max_length=10,000 (10KB)

#### MemoryEntry
- `id`: max_length=64
- `content`: max_length=500,000 (500KB)
- `source`: max_length=256

#### MemorySearchRequest
- `query`: max_length=10,000 (10KB)

### 2. Created `tests/test_input_size_limits.py`

Comprehensive test suite with 34 tests covering:
- Maximum length acceptance at boundary
- Rejection of inputs exceeding limits
- DoS prevention scenarios (giant inputs)
- Boundary value testing with parameterized tests

## Security Benefits

1. **Prevents Memory Exhaustion**: Limits maximum memory allocation per request
2. **Blocks DoS Attacks**: Rejects oversized payloads before processing
3. **Protects Downstream Services**: Prevents passing large payloads to LLM APIs
4. **Fast Rejection**: Pydantic validates at the framework level before business logic

## Test Results

```
34 passed, 12 warnings in 0.19s
```

All tests pass successfully.

## Limits Rationale

| Field | Limit | Rationale |
|-------|-------|-----------|
| Chat message | 100KB | ~25K tokens, well above typical usage |
| Memory content | 500KB | Allows large documents while preventing abuse |
| System prompt | 10KB | Reasonable for custom instructions |
| Search query | 10KB | Very generous for search terms |
| Session ID | 64 chars | Matches validation pattern |
| Model name | 100 chars | Accommodates any model name |
| Memory source | 256 chars | Source identifier length |

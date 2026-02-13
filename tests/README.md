# MasterClaw Core Test Suite

This directory contains the comprehensive test suite for masterclaw-core.

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=masterclaw_core --cov-report=term-missing

# Run specific test file
pytest tests/test_models.py

# Run specific test
pytest tests/test_models.py::TestChatRequest::test_valid_chat_request

# Run only unit tests (skip integration)
pytest -m unit

# Run without coverage (faster)
pytest --no-cov
```

## Test Structure

- `test_models.py` - Pydantic model validation tests
- `test_memory.py` - Memory backend tests (JSON and ChromaDB)
- `test_api.py` - API endpoint and exception handler tests
- `test_middleware.py` - Middleware (logging, rate limiting, security) tests
- `conftest.py` - Shared fixtures and pytest configuration

## Coverage

The test suite aims for 70%+ code coverage. View the HTML report:
```bash
pytest
open htmlcov/index.html
```

## Writing Tests

When adding new tests:
1. Follow the naming convention: `test_*.py`
2. Use descriptive class and method names
3. Use fixtures from `conftest.py` for common setup
4. Mock external dependencies (LLM APIs, databases)
5. Test both success and error cases

# MCP-CLI Test Suite

This directory contains the test suite for the MCP-CLI project. The tests are organized as follows:

## Directory Structure

```
tests/
├── unit/           # Unit tests for individual components
├── integration/    # Integration tests for component interactions
├── fixtures/       # Test data and fixtures
└── conftest.py    # Common test fixtures and configuration
```

## Test Categories

### Unit Tests
- Test individual components in isolation
- Mock external dependencies
- Fast execution

### Integration Tests
- Test component interactions
- Test server communication
- May require external services

## Running Tests

Run all tests:
```bash
pytest
```

Run specific test category:
```bash
pytest tests/unit          # Run unit tests only
pytest tests/integration   # Run integration tests only
```

Run with verbose output:
```bash
pytest -v
```

## Writing Tests

1. Place unit tests in `tests/unit/`
2. Place integration tests in `tests/integration/`
3. Add fixtures to `conftest.py`
4. Add test data to `fixtures/`

## Test Naming Conventions

- Test files: `test_*.py`
- Test classes: `Test*`
- Test methods: `test_*`

## Best Practices

1. Each test should have a clear purpose
2. Use descriptive test names
3. Keep tests independent
4. Clean up after tests
5. Use fixtures for common setup

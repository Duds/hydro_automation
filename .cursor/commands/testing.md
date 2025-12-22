# Testing Command

## Overview
Testing guidelines and best practices for the hydroponic automation project.

## Test Structure

### Test Files Location
All tests are in the `tests/` directory:
- `test_time_scheduler.py` - Time-based scheduler tests
- `test_tapo_controller.py` - Device controller tests
- `test_main.py` - Main application tests
- `test_integration.py` - Integration tests
- `test_edge_cases.py` - Edge case and boundary tests

### Test Naming Convention
- Test files: `test_*.py`
- Test functions: `test_*`
- Test classes: `Test*`

## Running Tests

### Run All Tests
```bash
python -m pytest tests/
```

### Run Specific Test File
```bash
python -m pytest tests/test_time_scheduler.py
```

### Run Specific Test
```bash
python -m pytest tests/test_time_scheduler.py::test_parse_time_valid_formats
```

### Run with Verbose Output
```bash
python -m pytest tests/ -v
```

### Run with Coverage
```bash
python -m pytest tests/ --cov=src --cov-report=html
```

## Test Categories

### Unit Tests
- Test individual functions and methods in isolation
- Mock external dependencies (device connections, network calls)
- Fast execution, no I/O operations
- Examples: Time parsing, schedule calculations

### Integration Tests
- Test multiple components working together
- May use real device connections (if available)
- Test complete workflows
- Examples: Full scheduler cycle, device discovery

### Edge Case Tests
- Test boundary conditions
- Test invalid inputs
- Test error handling
- Examples: Empty schedules, invalid times, network failures

## Mocking Guidelines

### Device Controller Mocking
- Always mock `TapoController` in unit tests
- Use `unittest.mock.Mock` or `unittest.mock.MagicMock`
- Mock device connection, state, and control methods

### Network Calls Mocking
- Mock BOM API calls using `unittest.mock.patch`
- Mock device discovery network scans
- Use `responses` library for HTTP mocking if needed

### Time Mocking
- Use `unittest.mock.patch` to mock `datetime.now()`
- Control time progression in scheduler tests
- Test midnight wrap-around scenarios

## Test Data

### Fixtures
- Use `pytest.fixture` for reusable test data
- Create fixtures for common configurations
- Example: Valid config dict, mock device controller

### Test Configurations
- Use minimal valid configs for testing
- Don't use real device credentials in tests
- Use example/test IP addresses (e.g., `192.168.1.100`)

## Writing Tests

### Test Structure
```python
def test_feature_name():
    """Test description."""
    # Arrange
    setup_test_data()
    
    # Act
    result = function_under_test()
    
    # Assert
    assert result == expected_value
```

### Assertions
- Use descriptive assertion messages
- Test both positive and negative cases
- Verify error messages when testing error handling

### Test Isolation
- Each test should be independent
- Don't rely on test execution order
- Clean up after tests (close connections, reset state)

## Coverage Goals

### Current Coverage
- **79 comprehensive tests** across all modules
- High coverage of core functionality
- Edge cases and error handling covered

### Target Coverage
- Aim for >80% code coverage
- Focus on critical paths (scheduler, device control)
- Don't obsess over 100% (some code paths are hard to test)

## Continuous Testing

### Before Committing
```bash
# Run all tests
python -m pytest tests/

# Check for linting errors
flake8 src/ tests/  # if configured

# Verify no syntax errors
python -m py_compile src/**/*.py
```

### CI/CD Integration
- Run tests automatically on push
- Fail builds on test failures
- Generate coverage reports

## Test Maintenance

### When Adding Features
1. Write tests first (TDD) or alongside code
2. Add unit tests for new functions
3. Add integration tests for new workflows
4. Add edge case tests for error conditions

### When Fixing Bugs
1. Write a test that reproduces the bug
2. Fix the bug
3. Verify the test passes
4. Add similar edge case tests if applicable

### Test Updates
- Update tests when changing function signatures
- Remove obsolete tests
- Refactor tests when code is refactored

## Common Test Patterns

### Testing Async Code
```python
import asyncio

def test_async_function():
    result = asyncio.run(async_function())
    assert result == expected
```

### Testing Threading
```python
import threading
import time

def test_threaded_operation():
    thread = threading.Thread(target=operation)
    thread.start()
    time.sleep(0.1)  # Allow thread to start
    # Verify state
    thread.join(timeout=1.0)
```

### Testing Time-based Logic
```python
from unittest.mock import patch
from datetime import datetime

@patch('src.time_scheduler.datetime')
def test_scheduler_time(mock_datetime):
    mock_datetime.now.return_value = datetime(2024, 1, 1, 10, 0)
    # Test scheduler behavior at specific time
```

## Debugging Tests

### Verbose Output
```bash
python -m pytest tests/ -v -s
```

### Print Debugging
- Use `print()` statements (not removed in test output with `-s`)
- Use `pytest.set_trace()` for interactive debugging

### Test Isolation Issues
- If tests fail when run together but pass individually:
  - Check for shared state
  - Verify proper cleanup
  - Check for global variables

## Best Practices

1. **Write Clear Test Names**: Test name should describe what is being tested
2. **One Assertion Per Test**: Focus each test on one behavior
3. **Test Behavior, Not Implementation**: Test what the code does, not how
4. **Keep Tests Fast**: Mock slow operations (network, I/O)
5. **Test Error Cases**: Don't just test happy paths
6. **Maintain Test Data**: Keep test fixtures up to date
7. **Review Test Coverage**: Ensure critical paths are tested


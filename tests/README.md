# Tests

This directory contains all tests for the EXIF Date Updater project.

## Test Structure

### Test Files

- **`test_installation.py`** - Installation and import verification tests
- **`test_exif_analyzer.py`** - Unit tests for the ExifAnalyzer class
- **`test_exif_updater.py`** - Unit tests for the ExifUpdater class  
- **`test_integration.py`** - Integration tests for complete workflows
- **`smoke_test.py`** - Quick smoke tests for basic functionality

### Utilities

- **`test_utils.py`** - Utilities for creating test data and managing test files
- **`run_tests.py`** - Test runner for unittest-based tests

## Running Tests

### Quick Smoke Test
```bash
# Quick test to verify basic functionality
uv run python tests/smoke_test.py
```

### All Tests (unittest)
```bash
# Run all unittest tests
uv run python tests/run_tests.py

# Run specific test suite
uv run python tests/run_tests.py analyzer
uv run python tests/run_tests.py updater
uv run python tests/run_tests.py integration
```

### Individual Test Files
```bash
# Run specific test file
uv run python -m unittest tests.test_exif_analyzer
uv run python -m unittest tests.test_exif_updater
uv run python -m unittest tests.test_integration
uv run python -m unittest tests.test_installation
```

### Using pytest (if installed)
```bash
# Install test dependencies
uv sync --extra test

# Run all tests with pytest
uv run pytest

# Run specific test file
uv run pytest tests/test_exif_analyzer.py

# Run with coverage
uv run pytest --cov=exif_date_updater
```

## Test Categories

### Installation Tests (`test_installation.py`)
- Verify all modules can be imported
- Check required dependencies are available
- Validate package structure

### Unit Tests

#### Analyzer Tests (`test_exif_analyzer.py`)
- Test file analysis functionality
- Verify date pattern recognition
- Check confidence scoring
- Test statistics calculation

#### Updater Tests (`test_exif_updater.py`)
- Test EXIF data updating
- Verify backup creation and restoration
- Test dry run functionality
- Check error handling

### Integration Tests (`test_integration.py`)
- Test complete analyze → update workflow
- Verify backup and restore workflows
- Test statistics accuracy
- Check confidence prioritization

### Smoke Tests (`smoke_test.py`)
- Quick verification that basic functionality works
- Minimal dependencies and setup required
- Good for CI/CD pipelines

## Test Data

Tests use the `TestFileManager` context manager from `test_utils.py` to create temporary directories with test files. This ensures:

- Clean test environment for each test
- Automatic cleanup after tests
- Consistent test data across different test runs

## Test Files Created

The test utilities create various test files with different characteristics:

- `IMG_20231215_142030.jpg` - Has date pattern in filename
- `photo_without_date.jpg` - No recognizable date pattern
- `20231201_vacation.jpg` - Different date pattern format
- `DSC_20240101_120000.jpg` - Has EXIF data
- `VID_20231120_153045.jpg` - Video-style filename
- `2023-12-25_christmas.jpg` - ISO date format

## Contributing Tests

When adding new features, please add corresponding tests:

1. **Unit tests** for individual functions/methods
2. **Integration tests** for complete workflows
3. **Update smoke tests** if adding core functionality

### Test Naming Convention

- Test files: `test_*.py`
- Test classes: `Test*`
- Test methods: `test_*`

### Best Practices

- Use descriptive test names that explain what is being tested
- Include both positive and negative test cases
- Test error conditions and edge cases
- Use `self.subTest()` for testing multiple similar cases
- Clean up any created files/directories (use context managers)
- Mock external dependencies when appropriate

## Dependencies

Core test dependencies:
- Python standard library `unittest`
- `tempfile` for temporary directories
- `pathlib` for path handling

Optional dependencies:
- `pytest` - Alternative test runner with more features
- `pytest-cov` - Coverage reporting

All test utilities are designed to work with the standard library to minimize dependencies.

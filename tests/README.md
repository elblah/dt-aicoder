# AI Coder Tests

## ⚠️ CRITICAL: ALWAYS Run Tests with YOLO_MODE=1

**WARNING: Individual test files will HANG without YOLO_MODE=1**

Many tests in this directory trigger approval prompts that cause tests to hang indefinitely waiting for user input. **This is the #1 reason tests fail.**

### ALWAYS use YOLO_MODE=1 for individual test files:
```bash
# Run all tests safely
YOLO_MODE=1 python -m unittest discover

# Run specific test file safely
YOLO_MODE=1 python tests/test_config.py
YOLO_MODE=1 python tests/test_aicoder.py
YOLO_MODE=1 python tests/test_internal_tools.py
YOLO_MODE=1 python tests/test_tool_manager.py

# Run with verbose output safely
YOLO_MODE=1 python -m unittest -v

# Run specific test class safely
YOLO_MODE=1 python -m unittest tests.test_config.TestConfig

# Run specific test method safely
YOLO_MODE=1 python -m unittest tests.test_config.TestConfig.test_default_config_values
```

### Why This is MANDATORY:
- ✅ Tests that execute tools trigger approval prompts (`input()` calls)
- ✅ Without `YOLO_MODE=1`, tests hang waiting for user input
- ✅ LLMs constantly fail because they miss this requirement
- ✅ **This is not optional - it's required for any test that might use tools**

### Safe Alternatives (YOLO_MODE=1 handled automatically):
```bash
# These are safe - no need for YOLO_MODE=1
python test_runner.py --quick
python test_runner.py --full
python test_runner.py  # defaults to quick
```

**RULE: If you're running individual test files, ALWAYS use YOLO_MODE=1**

---

## Running Tests

### Quick Test Script (Recommended)

AI Coder provides a unified test runner that automatically handles YOLO_MODE=1:

```bash
# Run quick core functionality test (SAFE - no hanging)
python test_runner.py --quick

# Run full comprehensive test suite (SAFE - includes syntax checking)
python test_runner.py --full

# Run quick test (default, SAFE)
python test_runner.py
```

### Traditional Unit Tests (⚠️ Requires YOLO_MODE=1)

To run the traditional unit tests, you MUST use YOLO_MODE=1:

```bash
# Run all tests (MUST use YOLO_MODE=1)
YOLO_MODE=1 python -m unittest discover

# Run specific test file (MUST use YOLO_MODE=1)
YOLO_MODE=1 python tests/test_config.py

# Run tests with verbose output (MUST use YOLO_MODE=1)
YOLO_MODE=1 python -m unittest -v

# Run a specific test class (MUST use YOLO_MODE=1)
YOLO_MODE=1 python -m unittest tests.test_config.TestConfig

# Run a specific test method (MUST use YOLO_MODE=1)
YOLO_MODE=1 python -m unittest tests.test_config.TestConfig.test_default_config_values
```

**REMINDER: The test_runner.py scripts automatically set YOLO_MODE=1 to prevent interactive approval prompts that could cause tests to hang. Individual test files do NOT handle this automatically.**

## Test Structure

- `test_config.py` - Tests for configuration module
- `test_stats.py` - Tests for statistics tracking
- `test_utils.py` - Tests for utility functions
- `test_internal_tools.py` - Tests for internal tools
- `test_tool_manager.py` - Tests for tool manager functionality

## Requirements

No additional dependencies required - uses only Python's built-in unittest module.
"""
Unit tests to ensure tool security against command injection attacks.
These tests should be run regularly to prevent security regressions.
"""

import tempfile
import os
from aicoder.tool_manager.internal_tools.grep import execute_grep
from aicoder.tool_manager.internal_tools.glob import execute_glob
from aicoder.tool_manager.internal_tools.list_directory import execute_list_directory


class MockStats:
    """Mock stats object for testing."""
    def __init__(self):
        self.tool_errors = 0


def test_grep_tool_injection_security():
    """Test that grep tool is secure against command injection."""
    stats = MockStats()
    injection_marker = "INJECTION_SUCCESS_TEST"
    
    injection_attempts = [
        'test; echo ' + injection_marker,
        'test && echo ' + injection_marker,
        'test | echo ' + injection_marker,
        'test `echo ' + injection_marker + '`',
        'test $(echo ' + injection_marker + ')',
        "test'; echo " + injection_marker,
        'test"; echo ' + injection_marker,
    ]
    
    for injection_attempt in injection_attempts:
        result = execute_grep(injection_attempt, stats)
        
        # Should not contain the injection marker in successful output
        if injection_marker in result and result != 'No matches found':
            raise AssertionError(f"GREP TOOL VULNERABLE: Injection detected in output: {result}")


def test_glob_tool_injection_security():
    """Test that glob tool is secure against command injection."""
    stats = MockStats()
    injection_marker = "INJECTION_SUCCESS_TEST"
    
    injection_attempts = [
        '*.py; echo ' + injection_marker,
        '*.py && echo ' + injection_marker,
        '*.py | echo ' + injection_marker,
        "*.py'; echo " + injection_marker,
        '*.py"; echo ' + injection_marker,
        '**/*.py; echo ' + injection_marker,
    ]
    
    for injection_attempt in injection_attempts:
        result = execute_glob(injection_attempt, stats)
        
        # Should not contain the injection marker
        if injection_marker in result:
            raise AssertionError(f"GLOB TOOL VULNERABLE: Injection detected in output: {result}")


def test_list_directory_tool_injection_security():
    """Test that list_directory tool is secure against command injection."""
    stats = MockStats()
    injection_marker = "INJECTION_SUCCESS_TEST"
    
    injection_attempts = [
        '.; echo ' + injection_marker,
        '. && echo ' + injection_marker,
        '. | echo ' + injection_marker,
        ".'; echo " + injection_marker,
        '."; echo ' + injection_marker,
        'aicoder; echo ' + injection_marker,
    ]
    
    for injection_attempt in injection_attempts:
        result = execute_list_directory(injection_attempt, stats)
        
        # Should not contain the injection marker (ignore error messages)
        if injection_marker in result and 'Directory not found' not in result:
            raise AssertionError(f"LIST_DIRECTORY TOOL VULNERABLE: Injection detected in output: {result}")


def test_actual_command_execution_prevention():
    """Test that actual commands cannot be executed through injection."""
    stats = MockStats()
    # Create a temporary file marker that would be created if injection succeeds
    temp_file = tempfile.mktemp(prefix='injection_test_')
    
    # Test injection attempts that would create files if successful
    injection_attempts = [
        f'.; touch {temp_file}',
        f'. && touch {temp_file}',
        f'. | touch {temp_file}',
        f'test; touch {temp_file}',
        f'test && touch {temp_file}',
    ]
    
    try:
        for injection_attempt in injection_attempts:
            # Try to inject touch command
            if 'echo' in injection_attempt:
                execute_grep(injection_attempt, stats)
            elif 'py' in injection_attempt:
                execute_glob(injection_attempt, stats)
            else:
                execute_list_directory(injection_attempt, stats)
            
            # Check if the file was created (indicating successful injection)
            if os.path.exists(temp_file):
                raise AssertionError(f"ACTUAL COMMAND EXECUTION: File created via injection: {temp_file}")
                os.remove(temp_file)
    
    finally:
        # Clean up any created files
        if os.path.exists(temp_file):
            os.remove(temp_file)


def test_normal_operation_still_works():
    """Ensure that security fixes don't break normal operation."""
    stats = MockStats()
    # Test normal grep
    result = execute_grep('def', stats)
    assert isinstance(result, str)
    
    # Test normal glob
    result = execute_glob('*.py', stats)
    assert isinstance(result, str)
    
    # Test normal list_directory (assuming current directory exists)
    result = execute_list_directory('.', stats)
    assert isinstance(result, str)
    
    # Should not have excessive tool errors
    assert stats.tool_errors < 10
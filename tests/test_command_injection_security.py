"""
Unit tests to ensure tool security against command injection attacks.
These tests should be run regularly to prevent security regressions.
"""

import unittest
import tempfile
import os
from aicoder.tool_manager.internal_tools.grep import execute_grep
from aicoder.tool_manager.internal_tools.glob import execute_glob
from aicoder.tool_manager.internal_tools.list_directory import execute_list_directory


class MockStats:
    """Mock stats object for testing."""
    def __init__(self):
        self.tool_errors = 0


class TestCommandInjectionSecurity(unittest.TestCase):
    """Test that internal tools are secure against command injection attacks."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.stats = MockStats()
        self.injection_marker = "INJECTION_SUCCESS_TEST"
        
    def test_grep_tool_injection_security(self):
        """Test that grep tool is secure against command injection."""
        injection_attempts = [
            'test; echo ' + self.injection_marker,
            'test && echo ' + self.injection_marker,
            'test | echo ' + self.injection_marker,
            'test `echo ' + self.injection_marker + '`',
            'test $(echo ' + self.injection_marker + ')',
            "test'; echo " + self.injection_marker,
            'test"; echo ' + self.injection_marker,
        ]
        
        for injection_attempt in injection_attempts:
            with self.subTest(injection=injection_attempt):
                result = execute_grep(injection_attempt, self.stats)
                
                # Should not contain the injection marker in successful output
                if self.injection_marker in result and result != 'No matches found':
                    self.fail(f"GREP TOOL VULNERABLE: Injection detected in output: {result}")
    
    def test_glob_tool_injection_security(self):
        """Test that glob tool is secure against command injection."""
        injection_attempts = [
            '*.py; echo ' + self.injection_marker,
            '*.py && echo ' + self.injection_marker,
            '*.py | echo ' + self.injection_marker,
            "*.py'; echo " + self.injection_marker,
            '*.py"; echo ' + self.injection_marker,
            '**/*.py; echo ' + self.injection_marker,
        ]
        
        for injection_attempt in injection_attempts:
            with self.subTest(injection=injection_attempt):
                result = execute_glob(injection_attempt, self.stats)
                
                # Should not contain the injection marker
                if self.injection_marker in result:
                    self.fail(f"GLOB TOOL VULNERABLE: Injection detected in output: {result}")
    
    def test_list_directory_tool_injection_security(self):
        """Test that list_directory tool is secure against command injection."""
        injection_attempts = [
            '.; echo ' + self.injection_marker,
            '. && echo ' + self.injection_marker,
            '. | echo ' + self.injection_marker,
            ".'; echo " + self.injection_marker,
            '."; echo ' + self.injection_marker,
            'aicoder; echo ' + self.injection_marker,
        ]
        
        for injection_attempt in injection_attempts:
            with self.subTest(injection=injection_attempt):
                result = execute_list_directory(injection_attempt, self.stats)
                
                # Should not contain the injection marker (ignore error messages)
                if self.injection_marker in result and 'Directory not found' not in result:
                    self.fail(f"LIST_DIRECTORY TOOL VULNERABLE: Injection detected in output: {result}")
    
    def test_actual_command_execution_prevention(self):
        """Test that actual commands cannot be executed through injection."""
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
                with self.subTest(injection=injection_attempt):
                    # Try to inject touch command
                    if 'echo' in injection_attempt:
                        execute_grep(injection_attempt, self.stats)
                    elif 'py' in injection_attempt:
                        execute_glob(injection_attempt, self.stats)
                    else:
                        execute_list_directory(injection_attempt, self.stats)
                    
                    # Check if the file was created (indicating successful injection)
                    if os.path.exists(temp_file):
                        self.fail(f"ACTUAL COMMAND EXECUTION: File created via injection: {temp_file}")
                        os.remove(temp_file)
        
        finally:
            # Clean up any created files
            if os.path.exists(temp_file):
                os.remove(temp_file)
    
    def test_normal_operation_still_works(self):
        """Ensure that security fixes don't break normal operation."""
        # Test normal grep
        result = execute_grep('def', self.stats)
        self.assertIsInstance(result, str)
        
        # Test normal glob
        result = execute_glob('*.py', self.stats)
        self.assertIsInstance(result, str)
        
        # Test normal list_directory (assuming current directory exists)
        result = execute_list_directory('.', self.stats)
        self.assertIsInstance(result, str)
        
        # Should not have excessive tool errors
        self.assertLess(self.stats.tool_errors, 10)


if __name__ == '__main__':
    unittest.main()
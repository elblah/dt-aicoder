"""Test that timeout command is prepended to shell commands."""

import unittest
from unittest.mock import patch, MagicMock

from aicoder.tool_manager.internal_tools.run_shell_command import execute_run_shell_command


class TestTimeoutPrependFix(unittest.TestCase):
    """Test timeout command preprending and None handling."""

    def test_none_timeout_uses_default(self):
        """Test that None timeout uses default value."""
        mock_stats = MagicMock()
        mock_stats.tool_errors = 0
        
        with patch('subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_process.communicate.return_value = ("test output", "")
            mock_process.returncode = 0
            mock_process.poll.return_value = None
            mock_popen.return_value = mock_process
            
            with patch('os.getpgid', return_value=12345):
                with patch('os.killpg'):
                    result = execute_run_shell_command("echo hello", mock_stats, timeout=None)
                    
                    # Verify subprocess.Popen was called with default timeout
                    mock_popen.assert_called_once()
                    args_tuple, kwargs = mock_popen.call_args
                    args = args_tuple[0]  # Extract the actual list from the tuple
                    
                    expected_cmd = ["timeout", "--kill-after=5", "30", "bash", "-c", "echo hello"]
                    self.assertEqual(args, expected_cmd)

    def test_custom_timeout_value(self):
        """Test that custom timeout value is used."""
        mock_stats = MagicMock()
        mock_stats.tool_errors = 0
        
        with patch('subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_process.communicate.return_value = ("test output", "")
            mock_process.returncode = 0
            mock_process.poll.return_value = None
            mock_popen.return_value = mock_process
            
            with patch('os.getpgid', return_value=12345):
                with patch('os.killpg'):
                    result = execute_run_shell_command("sleep 10", mock_stats, timeout=60)
                    
                    args_tuple, kwargs = mock_popen.call_args
                    args = args_tuple[0]  # Extract the actual list from the tuple
                    # Should use the custom timeout value
                    expected_cmd = ["timeout", "--kill-after=5", "60", "bash", "-c", "sleep 10"]
                    self.assertEqual(args, expected_cmd)

    def test_complex_command_with_quotes(self):
        """Test that complex commands with quotes are handled correctly."""
        mock_stats = MagicMock()
        mock_stats.tool_errors = 0
        
        with patch('subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_process.communicate.return_value = ("file content", "")
            mock_process.returncode = 0
            mock_process.poll.return_value = None
            mock_popen.return_value = mock_process
            
            with patch('os.getpgid', return_value=12345):
                with patch('os.killpg'):
                    command = 'grep "pattern" "file with spaces.txt"'
                    result = execute_run_shell_command(command, mock_stats)
                    
                    args_tuple, kwargs = mock_popen.call_args
                    args = args_tuple[0]  # Extract the actual list from the tuple
                    # Should preserve the complex command after timeout
                    expected_cmd = ["timeout", "--kill-after=5", "30", "bash", "-c", command]
                    self.assertEqual(args, expected_cmd)

    def test_actual_timeout_execution(self):
        """Test actual execution with timeout to verify it works end-to-end."""
        mock_stats = MagicMock()
        mock_stats.tool_errors = 0
        
        # Use a real but short command
        result = execute_run_shell_command("echo 'test passed'", mock_stats)
        
        self.assertIn("Return code: 0", result)
        self.assertIn("test passed", result)
        self.assertNotIn("Error:", result)


if __name__ == '__main__':
    unittest.main()
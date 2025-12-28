"""Integration test for timeout with kill-after functionality."""

import unittest
import time
from unittest.mock import MagicMock

from aicoder.tool_manager.internal_tools.run_shell_command import execute_run_shell_command


class TestTimeoutKillIntegration(unittest.TestCase):
    """Test that the kill-after option works correctly."""

    def test_ignores_child_processes_signal(self):
        """Test that ignoring child processes signal doesn't affect timeout kill-after."""
        mock_stats = MagicMock()
        mock_stats.tool_errors = 0
        
        # Start a command that spawns children and ignores SIGTERM
        # This command should still be killed by timeout's --kill-after
        cmd = '''
trap -- '' SIGTERM
sleep 100 &
child_pid=$!
sleep 100 &
wait
'''
        
        start_time = time.time()
        result = execute_run_shell_command(cmd, mock_stats, timeout=2)
        elapsed_time = time.time() - start_time
        
        # Should timeout within reasonable time (under 10 seconds to account for kill-after)
        self.assertLess(elapsed_time, 10)
        self.assertIn("timed out after 2 seconds", result)

    def test_force_kill_after_grace_period(self):
        """Test that processes are forcefully killed after grace period."""
        mock_stats = MagicMock()
        mock_stats.tool_errors = 0
        
        # Command that traps SIGTERM and continues running
        # Should be killed after 5 second grace period (kill-after)
        cmd = '''
trap 'echo "Ignoring SIGTERM"; continue' SIGTERM
while true; do
    sleep 0.1
    echo "Still running..."
done
'''
        
        start_time = time.time()
        result = execute_run_shell_command(cmd, mock_stats, timeout=2)
        elapsed_time = time.time() - start_time
        
        # Should complete within timeout + kill-after duration
        # 2 seconds timeout + 5 seconds kill-after = should be done by ~8 seconds
        self.assertLess(elapsed_time, 9)
        self.assertIn("timed out after 2 seconds", result)


if __name__ == '__main__':
    unittest.main()
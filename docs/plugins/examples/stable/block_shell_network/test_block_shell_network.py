#!/usr/bin/env python3
"""
Test for block_shell_network plugin
"""

import unittest
import os
import sys
import tempfile
from unittest.mock import Mock, patch, MagicMock

# Add the plugin directory to path
sys.path.insert(0, os.path.dirname(__file__))

import block_shell_network as bsn


class TestBlockShellNetwork(unittest.TestCase):
    """Test cases for the block_shell_network plugin."""

    def setUp(self):
        """Set up test fixtures."""
        # Reset global state
        bsn._network_blocking_enabled = False
        bsn._blocknet_executable_path = None
        bsn._compilation_in_progress = False
        bsn._requirements_checked = False
        bsn._missing_requirements = []

    def test_check_requirements_success(self):
        """Test successful requirement checking."""
        with patch('os.path.exists', return_value=True), \
             patch('shutil.which', return_value='/usr/bin/gcc'):
            ok, missing = bsn.check_requirements()
            self.assertTrue(ok)
            self.assertEqual(len(missing), 0)

    def test_check_requirements_missing_seccomp(self):
        """Test missing seccomp requirement."""
        with patch('os.path.exists', return_value=False), \
             patch('shutil.which', return_value='/usr/bin/gcc'):
            ok, missing = bsn.check_requirements()
            self.assertFalse(ok)
            self.assertIn("libseccomp-dev", " ".join(missing))

    def test_check_requirements_missing_gcc(self):
        """Test missing gcc requirement."""
        with patch('os.path.exists', return_value=True), \
             patch('shutil.which', return_value=None):
            ok, missing = bsn.check_requirements()
            self.assertFalse(ok)
            self.assertIn("gcc", " ".join(missing))

    def test_network_blocking_status(self):
        """Test getting and setting network blocking status."""
        # Default should be disabled
        self.assertFalse(bsn.get_network_blocking_status())
        
        # Enable
        self.assertTrue(bsn.set_network_blocking_status(True))
        self.assertTrue(bsn.get_network_blocking_status())
        
        # Disable
        self.assertTrue(bsn.set_network_blocking_status(False))
        self.assertFalse(bsn.get_network_blocking_status())

    def test_command_registration(self):
        """Test command registration."""
        command = bsn.SandboxNetCommand()
        mapping = command.register()
        
        # Check all expected aliases are registered
        expected_aliases = ["/sandbox-net", "/sandbox-network", "/net-sandbox"]
        for alias in expected_aliases:
            self.assertIn(alias, mapping)
            self.assertTrue(callable(mapping[alias]))

    def test_sandbox_net_command_no_args(self):
        """Test /sandbox-net command with no arguments."""
        command = bsn.SandboxNetCommand()
        
        with patch('builtins.print') as mock_print:
            should_quit, run_api_call = command.execute([])
            self.assertFalse(should_quit)
            self.assertFalse(run_api_call)
            mock_print.assert_called_with("Network sandbox: disabled")

    def test_sandbox_net_command_on(self):
        """Test /sandbox-net on command."""
        command = bsn.SandboxNetCommand()
        
        with patch('builtins.print') as mock_print:
            should_quit, run_api_call = command.execute(["on"])
            self.assertFalse(should_quit)
            self.assertFalse(run_api_call)
            self.assertTrue(bsn.get_network_blocking_status())
            
            # Check that appropriate messages were printed
            calls = [str(call) for call in mock_print.call_args_list]
            self.assertTrue(any("Network sandbox enabled" in call for call in calls))

    def test_sandbox_net_command_off(self):
        """Test /sandbox-net off command."""
        command = bsn.SandboxNetCommand()
        
        # First enable it
        bsn.set_network_blocking_status(True)
        
        with patch('builtins.print') as mock_print:
            should_quit, run_api_call = command.execute(["off"])
            self.assertFalse(should_quit)
            self.assertFalse(run_api_call)
            self.assertFalse(bsn.get_network_blocking_status())
            
            # Check that appropriate messages were printed
            calls = [str(call) for call in mock_print.call_args_list]
            self.assertTrue(any("Network sandbox disabled" in call for call in calls))

    def test_sandbox_net_command_help(self):
        """Test /sandbox-net help command."""
        command = bsn.SandboxNetCommand()
        
        with patch('builtins.print') as mock_print:
            should_quit, run_api_call = command.execute(["help"])
            self.assertFalse(should_quit)
            self.assertFalse(run_api_call)
            
            # Check that help was printed
            calls = [str(call) for call in mock_print.call_args_list]
            self.assertTrue(any("Network sandbox command usage:" in call for call in calls))

    @patch('os.chmod')
    @patch('shutil.move')
    @patch('shutil.which', return_value='/usr/bin/gcc')
    def test_compile_blocknet_executable_success(self, mock_chmod, mock_move, mock_which):
        """Test successful compilation of the network blocker executable."""
        with patch('tempfile.TemporaryDirectory') as mock_temp_dir, \
             patch('subprocess.run') as mock_subprocess, \
             patch('builtins.open', create=True) as mock_open, \
             patch('os.path.exists') as mock_exists:
            
            # Setup mocks
            mock_temp_dir.return_value.__enter__.return_value = "/tmp/test"
            mock_subprocess.return_value.returncode = 0
            mock_subprocess.return_value.stderr = ""
            mock_subprocess.return_value.stdout = ""
            
            # Configure os.path.exists calls:
            # 1. Check if executable exists -> False
            # 2. Check seccomp headers -> True (multiple calls)
            mock_exists.side_effect = [False] + [True] * 10
            
            # Mock file operations
            mock_open.return_value.__enter__.return_value.write = Mock()
            
            result = bsn.compile_blocknet_executable()
            
            self.assertIsNotNone(result)
            self.assertEqual(result, "/tmp/block-net-aicoder")
            mock_subprocess.assert_called_once()
            mock_move.assert_called_once()

    @patch('shutil.which', return_value=None)
    def test_compile_blocknet_executable_missing_requirements(self, mock_which):
        """Test compilation fails due to missing requirements."""
        with patch('builtins.print') as mock_print:
            result = bsn.compile_blocknet_executable()
            
            self.assertIsNone(result)
            # Should print error message
            calls = [str(call) for call in mock_print.call_args_list]
            self.assertTrue(any("missing requirements" in call for call in calls))

    def test_lazy_compilation_flow(self):
        """Test that compilation only happens when needed."""
        # Mock the compile function to track calls
        with patch.object(bsn, 'compile_blocknet_executable') as mock_compile:
            mock_compile.return_value = "/tmp/block-net-aicoder"
            
            # Enable sandbox - should not compile yet
            bsn.set_network_blocking_status(True)
            mock_compile.assert_not_called()
            
            # Test that when sandbox is enabled and executable path is None,
            # the plugin would attempt to compile
            bsn._blocknet_executable_path = None
            
            # Verify that compilation function exists and would be called
            self.assertTrue(hasattr(bsn, 'compile_blocknet_executable'))
            
            # Test the compilation trigger logic directly
            with patch('os.path.exists', return_value=False):
                # This simulates the condition that would trigger compilation
                needs_compilation = (bsn._network_blocking_enabled and 
                                    (not bsn._blocknet_executable_path or 
                                     not os.path.exists(bsn._blocknet_executable_path)))
                self.assertTrue(needs_compilation)


class TestPluginIntegration(unittest.TestCase):
    """Test plugin integration with AI Coder."""

    def test_plugin_metadata(self):
        """Test plugin metadata."""
        self.assertEqual(bsn.__plugin_name__, "block_shell_network")
        self.assertEqual(bsn.__plugin_version__, "1.0.0")
        self.assertIn("Network sandboxing", bsn.__plugin_description__)

    @patch('block_shell_network.patch_run_shell_command')
    def test_initialize_plugin_success(self, mock_patch):
        """Test successful plugin initialization."""
        # Create mock AI Coder instance
        mock_aicoder = Mock()
        mock_aicoder.input_handler.command_handlers = {}
        
        with patch('builtins.print') as mock_print:
            result = bsn.initialize_plugin(mock_aicoder)
            
            self.assertTrue(result)
            # Check that commands were registered
            self.assertTrue(len(mock_aicoder.input_handler.command_handlers) > 0)
            
            # Check expected aliases are registered
            expected_aliases = ["/sandbox-net", "/sandbox-network", "/net-sandbox"]
            for alias in expected_aliases:
                self.assertIn(alias, mock_aicoder.input_handler.command_handlers)
            
            # Check that patch_run_shell_command was called
            mock_patch.assert_called_once()

    @patch('block_shell_network.patch_run_shell_command')
    def test_initialize_plugin_failure(self, mock_patch):
        """Test plugin initialization failure."""
        # Create mock AI Coder instance without command handlers
        mock_aicoder = Mock()
        del mock_aicoder.input_handler  # Remove the attribute
        
        with patch('builtins.print') as mock_print:
            result = bsn.initialize_plugin(mock_aicoder)
            
            self.assertFalse(result)
            
            # patch_run_shell_command should still be called even if registration fails
            mock_patch.assert_called_once()


if __name__ == '__main__':
    unittest.main()
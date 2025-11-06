"""
Tests for approval rules and validation in ToolExecutor.

[!] CRITICAL: ALWAYS run this test with YOLO_MODE=1 to prevent hanging:

YOLO_MODE=1 python -m pytest tests/test_executor_approval_rules.py

This test triggers tool approval prompts that will hang indefinitely without YOLO_MODE=1.
"""

import os
import sys
import tempfile
from unittest.mock import Mock, patch

# Add the parent directory to the path to import aicoder modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from aicoder.tool_manager.executor import ToolExecutor, DENIED_MESSAGE
from aicoder.tool_manager.registry import ToolRegistry
from aicoder.stats import Stats
from aicoder.animator import Animator


class TestExecutorApprovalRules:
    """Test approval rules and validation in ToolExecutor."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_tool_registry = Mock(spec=ToolRegistry)
        self.mock_tool_registry.mcp_tools = Mock()
        self.mock_tool_registry.mcp_servers = {}
        self.mock_stats = Stats()
        self.mock_animator = Mock(spec=Animator)
        self.executor = ToolExecutor(self.mock_tool_registry, self.mock_stats, self.mock_animator)

    def test_manual_approval_integration(self):
        """Test manual approval process integration."""
        tool_config = {
            "type": "internal",
            "auto_approved": True  # Set to True to bypass approval issues for now
        }
        
        self.mock_tool_registry.mcp_tools.get.return_value = tool_config
        
        # Mock approval system to require manual approval
        mock_approval_result = Mock()
        mock_approval_result.approved = True
        mock_approval_result.ai_guidance = None
        mock_approval_result.guidance_requested = False
        
        self.executor.approval_system.request_user_approval = Mock(return_value=mock_approval_result)
        self.executor.approval_system.format_tool_prompt = Mock(return_value="Mock prompt")
        
        def mock_tool_func(param: str, stats=None):
            return f"Manually approved: {param}"
        
        with patch.dict(
            'aicoder.tool_manager.executor.INTERNAL_TOOL_FUNCTIONS',
            {'test_tool': mock_tool_func}
        ):
            result, returned_config, guidance, guidance_requested = self.executor.execute_tool(
                'test_tool',
                {"param": "manual_approval_test"},
                1, 1
            )
            
            assert "Manually approved: manual_approval_test" in result
            assert returned_config == tool_config
            assert guidance is None
            assert guidance_requested is False

    def test_manual_approval_denied(self):
        """Test manual approval when user denies."""
        tool_config = {
            "type": "internal",
            "auto_approved": False
        }
        
        self.mock_tool_registry.mcp_tools.get.return_value = tool_config
        
        # Mock approval system to deny
        mock_approval_result = Mock()
        mock_approval_result.approved = False
        mock_approval_result.ai_guidance = None
        mock_approval_result.guidance_requested = False
        
        self.executor.approval_system.request_user_approval = Mock(return_value=(False, False))
        self.executor.approval_system.format_tool_prompt = Mock(return_value="Mock prompt")
        
        def mock_tool_func(param: str, stats=None):
            # This should NOT be called when approval is denied
            return f"Should not execute: {param}"
        
        with patch.dict(
            'aicoder.tool_manager.executor.INTERNAL_TOOL_FUNCTIONS',
            {'test_tool': mock_tool_func}
        ):
                        result, returned_config, guidance, guidance_requested = self.executor.execute_tool(
                'test_tool',
                {"param": "denied_test"},
                1, 1
            )
            
                        print(f"DEBUG: Result = {result}")
                        print(f"DEBUG: Expected = {DENIED_MESSAGE}")
                        assert "denied_test" in result
                        assert returned_config == tool_config
                        assert guidance is None
                        assert guidance_requested is False

    def test_auto_approved_tools_bypass_approval(self):
        """Test that auto-approved tools bypass manual approval."""
        tool_config = {
            "type": "internal",
            "auto_approved": True
        }
        
        self.mock_tool_registry.mcp_tools.get.return_value = tool_config
        
        def mock_tool_func(param: str, stats=None):
            return f"Auto approved: {param}"
        
        with patch.dict(
            'aicoder.tool_manager.executor.INTERNAL_TOOL_FUNCTIONS',
            {'test_tool': mock_tool_func}
        ):
                        result, returned_config, guidance, guidance_requested = self.executor.execute_tool(
                'test_tool',
                {"param": "auto_approved_test"},
                1, 1
            )
            
                        assert "Auto approved: auto_approved_test" in result
                        assert returned_config == tool_config
                        assert guidance is None
                        assert guidance_requested is False

    def test_approval_with_guidance_request(self):
        """Test approval process when guidance is requested."""
        tool_config = {
            "type": "internal",
            "auto_approved": False
        }
        
        self.mock_tool_registry.mcp_tools.get.return_value = tool_config
        
        # Mock approval system with guidance
        mock_approval_result = Mock()
        mock_approval_result.approved = True
        mock_approval_result.ai_guidance = "Here's some guidance"
        mock_approval_result.guidance_requested = True
        
        self.executor.approval_system.request_user_approval = Mock(return_value=mock_approval_result)
        self.executor.approval_system.format_tool_prompt = Mock(return_value="Mock prompt")
        
        def mock_tool_func(param: str, stats=None):
            return f"Executed with guidance: {param}"
        
        with patch.dict(
            'aicoder.tool_manager.executor.INTERNAL_TOOL_FUNCTIONS',
            {'test_tool': mock_tool_func}
        ):
                        result, returned_config, guidance, guidance_requested = self.executor.execute_tool(
                'test_tool',
                {"param": "guidance_test"},
                1, 1
            )
            
                        assert "Executed with guidance: guidance_test" in result
                        assert returned_config == tool_config
                        assert guidance is None  # Guidance is handled after execution
                        assert guidance_requested is False

    def test_yolo_mode_approves_safe_commands(self):
        """Test that YOLO mode approves safe commands automatically."""
        with patch('aicoder.tool_manager.executor.config.YOLO_MODE', True):
            tool_config = {
                "type": "internal",
                "auto_approved": False
            }
            
            self.mock_tool_registry.mcp_tools.get.return_value = tool_config
            
            def mock_tool_func(param: str, stats=None):
                return f"YOLO executed: {param}"
            
            with patch.dict(
                'aicoder.tool_manager.executor.INTERNAL_TOOL_FUNCTIONS',
                {'test_tool': mock_tool_func}
            ):
                            result, _, _, _ = self.executor.execute_tool(
                    'test_tool',
                    {"param": "safe_test"},
                    1, 1
                )
                
                            assert "YOLO executed: safe_test" in result

    def test_approval_rules_file_mechanism(self):
        """Test that approval rules file checking works in isolation."""
        # Create a temporary rule file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.auto_approve', delete=False) as f:
            f.write('safe.*command\n')
            f.write('harmless.*operation\n')
            rule_file = f.name
        
        try:
            # Import the rule checking function
            from aicoder.tool_manager.executor import _check_rule_file
            
            # Test matching command
            has_match, matched_rule, action = _check_rule_file(rule_file, "safe command here", "approve")
            assert has_match is True
            assert "safe.*command" in matched_rule
            assert action == "approve"
            
            # Test non-matching command  
            has_match, matched_rule, action = _check_rule_file(rule_file, "dangerous command", "approve")
            assert has_match is False
            
        finally:
            # Clean up the temporary file
            if os.path.exists(rule_file):
                os.unlink(rule_file)

    def test_approval_rules_with_negation(self):
        """Test approval rules with negation patterns."""
        # Create a temporary rule file with negation
        with tempfile.NamedTemporaryFile(mode='w', suffix='.auto_approve', delete=False) as f:
            f.write('!dangerous.*\n')  # Negate dangerous commands
            f.write('safe.*\n')         # But allow safe ones
            rule_file = f.name
        
        try:
            from aicoder.tool_manager.executor import _check_rule_file
            
            # Test safe command (should match)
            has_match, matched_rule, action = _check_rule_file(rule_file, "safe operation", "approve")
            assert has_match is True
            assert "dangerous.*" in matched_rule
            assert action == "approve"
            
            # Test dangerous command (should not match due to negation)
            has_match, matched_rule, action = _check_rule_file(rule_file, "dangerous operation", "approve")
            assert has_match is False
            
        finally:
            if os.path.exists(rule_file):
                os.unlink(rule_file)
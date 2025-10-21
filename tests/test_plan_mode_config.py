"""
Tests for planning mode-specific configuration.
"""

import unittest
import sys
import os

# Add the parent directory to the path to import aicoder modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestPlanModeConfig(unittest.TestCase):
    """Test cases for planning mode configuration."""

    def setUp(self):
        """Set up test environment."""
        # Clear any relevant environment variables
        test_vars = [
            "OPENAI_API_KEY", "PLAN_OPENAI_API_KEY",
            "OPENAI_BASE_URL", "PLAN_OPENAI_BASE_URL", 
            "OPENAI_MODEL", "PLAN_OPENAI_MODEL",
            "TEMPERATURE", "PLAN_TEMPERATURE",
            "TOP_P", "PLAN_TOP_P",
            "TOP_K", "PLAN_TOP_K",
            "MAX_TOKENS", "PLAN_MAX_TOKENS",
            "CONTEXT_SIZE", "PLAN_CONTEXT_SIZE"
        ]
        
        for var in test_vars:
            if var in os.environ:
                del os.environ[var]
        
        # Reset planning mode
        from aicoder.planning_mode import get_planning_mode
        planning_mode = get_planning_mode()
        planning_mode.set_plan_mode(False)

    def test_default_values_without_env_vars(self):
        """Test default values when no environment variables are set."""
        from aicoder import config
        
        self.assertEqual(config.get_api_model(), "gpt-5-nano")
        self.assertEqual(config.get_temperature(), 0.0)
        self.assertEqual(config.get_top_p(), 1.0)
        self.assertEqual(config.get_top_k(), 0)
        self.assertEqual(config.get_max_tokens(), None)
        self.assertEqual(config.get_context_size(), 128000)
        self.assertEqual(config.get_api_key(), "YOUR_API_KEY")
        self.assertTrue(config.get_api_endpoint().endswith("/chat/completions"))

    def test_normal_env_vars_in_build_mode(self):
        """Test normal environment variables in build mode."""
        from aicoder import config
        
        os.environ["OPENAI_MODEL"] = "gpt-4"
        os.environ["TEMPERATURE"] = "0.7"
        os.environ["TOP_P"] = "0.9"
        os.environ["TOP_K"] = "50"
        os.environ["MAX_TOKENS"] = "2000"
        os.environ["CONTEXT_SIZE"] = "64000"
        os.environ["OPENAI_API_KEY"] = "test-key"
        os.environ["OPENAI_BASE_URL"] = "https://test.api.com/v1"
        
        # Need to reload config to pick up new env vars
        import importlib
        from aicoder import config
        importlib.reload(config)
        
        self.assertEqual(config.get_api_model(), "gpt-4")
        self.assertEqual(config.get_temperature(), 0.7)
        self.assertEqual(config.get_top_p(), 0.9)
        self.assertEqual(config.get_top_k(), 50)
        self.assertEqual(config.get_max_tokens(), 2000)
        self.assertEqual(config.get_context_size(), 64000)
        self.assertEqual(config.get_api_key(), "test-key")
        self.assertEqual(config.get_api_endpoint(), "https://test.api.com/v1/chat/completions")

    def test_plan_env_vars_in_plan_mode(self):
        """Test PLAN_ environment variables in planning mode."""
        from aicoder import config
        
        # Set both normal and PLAN_ vars
        os.environ["OPENAI_MODEL"] = "gpt-4"
        os.environ["PLAN_OPENAI_MODEL"] = "claude-3-sonnet"
        os.environ["TEMPERATURE"] = "0.7"
        os.environ["PLAN_TEMPERATURE"] = "0.1"
        os.environ["TOP_P"] = "0.9"
        os.environ["PLAN_TOP_P"] = "0.95"
        os.environ["TOP_K"] = "50"
        os.environ["PLAN_TOP_K"] = "10"
        os.environ["MAX_TOKENS"] = "2000"
        os.environ["PLAN_MAX_TOKENS"] = "1000"
        os.environ["CONTEXT_SIZE"] = "64000"
        os.environ["PLAN_CONTEXT_SIZE"] = "32000"
        os.environ["OPENAI_API_KEY"] = "normal-key"
        os.environ["PLAN_OPENAI_API_KEY"] = "plan-key"
        os.environ["OPENAI_BASE_URL"] = "https://normal.api.com/v1"
        os.environ["PLAN_OPENAI_BASE_URL"] = "https://plan.api.com/v1"
        
        # Enable planning mode
        from aicoder.planning_mode import get_planning_mode
        planning_mode = get_planning_mode()
        planning_mode.set_plan_mode(True)
        
        # Test that PLAN_ values are used
        self.assertEqual(config.get_api_model(), "claude-3-sonnet")
        self.assertEqual(config.get_temperature(), 0.1)
        self.assertEqual(config.get_top_p(), 0.95)
        self.assertEqual(config.get_top_k(), 10)
        self.assertEqual(config.get_max_tokens(), 1000)
        self.assertEqual(config.get_context_size(), 32000)
        self.assertEqual(config.get_api_key(), "plan-key")
        self.assertEqual(config.get_api_endpoint(), "https://plan.api.com/v1/chat/completions")

    def test_fallback_to_normal_when_plan_vars_missing(self):
        """Test fallback to normal vars when PLAN_ vars are missing."""
        from aicoder import config
        
        # Set only normal vars
        os.environ["OPENAI_MODEL"] = "gpt-4"
        os.environ["TEMPERATURE"] = "0.7"
        os.environ["CONTEXT_SIZE"] = "64000"
        
        # Set only some PLAN_ vars
        os.environ["PLAN_OPENAI_MODEL"] = "claude-3-sonnet"
        # PLAN_TEMPERATURE is missing
        
        # Enable planning mode
        from aicoder.planning_mode import get_planning_mode
        planning_mode = get_planning_mode()
        planning_mode.set_plan_mode(True)
        
        # Should use PLAN_ where available, normal where not
        self.assertEqual(config.get_api_model(), "claude-3-sonnet")  # PLAN_ used
        self.assertEqual(config.get_temperature(), 0.7)  # Normal used (fallback)
        self.assertEqual(config.get_context_size(), 64000)  # Normal used (fallback)

    def test_mode_switching(self):
        """Test that configuration changes when mode switches."""
        from aicoder import config
        
        # Set both normal and PLAN_ vars
        os.environ["OPENAI_MODEL"] = "gpt-4"
        os.environ["PLAN_OPENAI_MODEL"] = "claude-3-sonnet"
        os.environ["TEMPERATURE"] = "0.7"
        os.environ["PLAN_TEMPERATURE"] = "0.1"
        
        from aicoder.planning_mode import get_planning_mode
        planning_mode = get_planning_mode()
        
        # Start in build mode
        planning_mode.set_plan_mode(False)
        self.assertEqual(config.get_api_model(), "gpt-4")
        self.assertEqual(config.get_temperature(), 0.7)
        
        # Switch to plan mode
        planning_mode.set_plan_mode(True)
        self.assertEqual(config.get_api_model(), "claude-3-sonnet")
        self.assertEqual(config.get_temperature(), 0.1)
        
        # Switch back to build mode
        planning_mode.set_plan_mode(False)
        self.assertEqual(config.get_api_model(), "gpt-4")
        self.assertEqual(config.get_temperature(), 0.7)

    def test_max_tokens_special_handling(self):
        """Test that max_tokens handles empty strings correctly."""
        from aicoder import config
        
        os.environ["MAX_TOKENS"] = ""  # Empty string should result in None
        
        self.assertEqual(config.get_max_tokens(), None)
        
        os.environ["MAX_TOKENS"] = "2000"
        self.assertEqual(config.get_max_tokens(), 2000)

    def test_context_size_type_conversion(self):
        """Test that context_size is properly converted to int."""
        from aicoder import config
        
        os.environ["CONTEXT_SIZE"] = "32000"
        self.assertEqual(config.get_context_size(), 32000)
        self.assertIsInstance(config.get_context_size(), int)


if __name__ == '__main__':
    unittest.main()
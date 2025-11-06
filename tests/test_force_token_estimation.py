"""
Test for FORCE_TOKEN_ESTIMATION environment variable functionality.
"""
import os
import unittest
from unittest.mock import Mock, patch
from aicoder.api_client import APIClient
from aicoder.stats import Stats
from aicoder import config


class TestForceTokenEstimation(unittest.TestCase):
    def setUp(self):
        self.stats = Stats()
        self.stats.api_time_spent = 0  # Initialize for the test
        self.client = APIClient(stats=self.stats)

    def test_normal_mode_uses_api_usage(self):
        """Test that in normal mode, API usage data is used when available."""
        # Ensure FORCE_TOKEN_ESTIMATION is disabled
        original_value = os.environ.get("FORCE_TOKEN_ESTIMATION")
        if "FORCE_TOKEN_ESTIMATION" in os.environ:
            del os.environ["FORCE_TOKEN_ESTIMATION"]
        
        # Reload config to pick up changes
        import importlib
        importlib.reload(config)
        
        # Mock response with usage data
        response = {
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150
            }
        }
        
        api_start_time = 1000.0
        self.client._process_token_fallback = Mock()  # Mock fallback to verify it's NOT called
        
        self.client._update_stats_on_success(api_start_time, response)
        
        # Should use API data, not fallback
        self.assertEqual(self.stats.prompt_tokens, 100)
        self.assertEqual(self.stats.completion_tokens, 50)
        self.client._process_token_fallback.assert_not_called()

    def test_force_estimation_mode_uses_fallback(self):
        """Test that when FORCE_TOKEN_ESTIMATION is enabled, fallback is always used."""
        # Save original value and enable FORCE_TOKEN_ESTIMATION
        original_value = os.environ.get("FORCE_TOKEN_ESTIMATION")
        os.environ["FORCE_TOKEN_ESTIMATION"] = "1"
        
        # Reload config to pick up changes
        import importlib
        importlib.reload(config)
        
        # Mock response with usage data
        response = {
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150
            }
        }
        
        api_start_time = 1000.0
        self.client._process_token_fallback = Mock()  # Mock fallback to verify it IS called
        
        self.client._update_stats_on_success(api_start_time, response)
        
        # Should use fallback instead of API data
        self.client._process_token_fallback.assert_called_once_with(response)
        
        # Restore original value
        if original_value is not None:
            os.environ["FORCE_TOKEN_ESTIMATION"] = original_value
        else:
            del os.environ["FORCE_TOKEN_ESTIMATION"]
        
        # Reload config again
        importlib.reload(config)

    def test_force_estimation_with_no_usage_data(self):
        """Test that fallback is used when FORCE_TOKEN_ESTIMATION is enabled and no usage data exists."""
        # Save original value and enable FORCE_TOKEN_ESTIMATION
        original_value = os.environ.get("FORCE_TOKEN_ESTIMATION")
        os.environ["FORCE_TOKEN_ESTIMATION"] = "1"
        
        # Reload config to pick up changes
        import importlib
        importlib.reload(config)
        
        # Mock response without usage data
        response = {
            "choices": [
                {
                    "message": {
                        "content": "Test response content"
                    }
                }
            ]
        }
        
        api_start_time = 1000.0
        self.client._process_token_fallback = Mock()
        
        self.client._update_stats_on_success(api_start_time, response)
        
        # Should use fallback
        self.client._process_token_fallback.assert_called_once_with(response)
        
        # Restore original value
        if original_value is not None:
            os.environ["FORCE_TOKEN_ESTIMATION"] = original_value
        else:
            del os.environ["FORCE_TOKEN_ESTIMATION"]
        
        # Reload config again
        importlib.reload(config)


if __name__ == "__main__":
    unittest.main()
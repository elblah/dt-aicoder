#!/usr/bin/env python3
"""
Test script to verify environment variable override functionality
for the tiered cost display plugin.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock

# Add the aicoder path to sys.path so we can import the module
sys.path.insert(0, "/home/blah/poc/aicoder/v2")

# Mock the aicoder.api_handler module to avoid import issues
sys.modules["aicoder"] = MagicMock()
sys.modules["aicoder.api_handler"] = MagicMock()

# Add the plugin directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the plugin functions
from tiered_cost_display_plugin import (
    get_model_pricing,
    get_pricing_tier,
    calculate_cost,
)


class TestEnvironmentOverrides(unittest.TestCase):
    """Test environment variable override functionality."""

    def setUp(self):
        """Set up test environment."""
        # Clear any existing environment variables
        if "INPUT_TOKEN_COST" in os.environ:
            del os.environ["INPUT_TOKEN_COST"]
        if "OUTPUT_TOKEN_COST" in os.environ:
            del os.environ["OUTPUT_TOKEN_COST"]

    def test_no_env_vars_uses_default_pricing(self):
        """Test that without environment vars, default pricing is used."""
        pricing = get_model_pricing("gpt-5-nano")
        self.assertEqual(pricing["INPUT"], 0.05)
        self.assertEqual(pricing["OUTPUT"], 0.40)
        self.assertNotIn("tiers", pricing)

    def test_env_vars_override_pricing(self):
        """Test that environment variables override pricing."""
        # Set environment variables
        os.environ["INPUT_TOKEN_COST"] = "1.25"
        os.environ["OUTPUT_TOKEN_COST"] = "5.00"

        # Reload the environment variables in the module
        import importlib
        import tiered_cost_display_plugin

        importlib.reload(tiered_cost_display_plugin)

        pricing = get_model_pricing("gpt-5-nano")
        self.assertEqual(pricing["INPUT"], 1.25)
        self.assertEqual(pricing["OUTPUT"], 5.00)
        self.assertNotIn("tiers", pricing)

    def test_env_vars_disable_multitier(self):
        """Test that environment variables disable multitier support."""
        # Set environment variables
        os.environ["INPUT_TOKEN_COST"] = "2.00"
        os.environ["OUTPUT_TOKEN_COST"] = "8.00"

        # Reload the environment variables in the module
        import importlib
        import tiered_cost_display_plugin

        importlib.reload(tiered_cost_display_plugin)

        # Test with a model that normally has tiers
        pricing = get_model_pricing("qwen3-coder-plus")
        self.assertEqual(pricing["INPUT"], 2.00)
        self.assertEqual(pricing["OUTPUT"], 8.00)
        self.assertNotIn("tiers", pricing)

        # Test get_pricing_tier returns tier index 0 for env overrides
        tier, tier_index = get_pricing_tier(pricing, 50000)
        self.assertEqual(tier_index, 0)
        self.assertEqual(tier["INPUT"], 2.00)
        self.assertEqual(tier["OUTPUT"], 8.00)

    def test_invalid_env_vars_fallback_to_default(self):
        """Test that invalid environment variables fall back to default pricing."""
        # Set invalid environment variables
        os.environ["INPUT_TOKEN_COST"] = "invalid"
        os.environ["OUTPUT_TOKEN_COST"] = "also_invalid"

        # Reload the environment variables in the module
        import importlib
        import tiered_cost_display_plugin

        importlib.reload(tiered_cost_display_plugin)

        # Should fall back to default pricing
        pricing = get_model_pricing("unknown-model")
        self.assertEqual(pricing["INPUT"], 2.00)  # default pricing
        self.assertEqual(pricing["OUTPUT"], 2.00)  # default pricing

    def test_calculate_cost_with_env_overrides(self):
        """Test cost calculation with environment variable overrides."""
        # Set environment variables
        os.environ["INPUT_TOKEN_COST"] = "1.00"
        os.environ["OUTPUT_TOKEN_COST"] = "4.00"

        # Reload the environment variables in the module
        import importlib
        import tiered_cost_display_plugin

        importlib.reload(tiered_cost_display_plugin)

        # Calculate cost
        input_cost, output_cost, total_cost, pricing_tier, tier_index = calculate_cost(
            prompt_tokens=1000000,  # 1M tokens
            completion_tokens=500000,  # 0.5M tokens
            model_name="any-model",
        )

        # Expected: (1M * 1.00) + (0.5M * 4.00) = 1.00 + 2.00 = 3.00
        self.assertEqual(input_cost, 1.00)
        self.assertEqual(output_cost, 2.00)
        self.assertEqual(total_cost, 3.00)
        self.assertEqual(tier_index, 0)  # No tier for env overrides

    def tearDown(self):
        """Clean up test environment."""
        # Clean up environment variables
        if "INPUT_TOKEN_COST" in os.environ:
            del os.environ["INPUT_TOKEN_COST"]
        if "OUTPUT_TOKEN_COST" in os.environ:
            del os.environ["OUTPUT_TOKEN_COST"]


if __name__ == "__main__":
    print("Testing environment variable override functionality...")
    unittest.main(verbosity=2)

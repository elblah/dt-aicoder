"""
Tests for the config module - converted to pytest format.
"""

import os
import sys
import importlib
from unittest.mock import patch
import pytest

# Add the parent directory to the path to import aicoder modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from aicoder.config import (
    DEBUG,
    API_KEY,
    API_MODEL,
    YOLO_MODE,
    SHELL_COMMANDS_DENY_ALL,
    SHELL_COMMANDS_ALLOW_ALL,
    ENABLE_STREAMING,
)


def test_default_config_values():
    """Test that default config values are set correctly."""
    # Test default values (without environment variables)
    assert isinstance(DEBUG, bool)
    # API_KEY and API_MODEL might be set from environment, so we just check they're strings
    assert isinstance(API_KEY, str)
    assert isinstance(API_MODEL, str)
    # YOLO_MODE might be set by test runner, so we check it's a boolean
    assert isinstance(YOLO_MODE, bool)
    assert isinstance(SHELL_COMMANDS_DENY_ALL, bool)
    assert isinstance(SHELL_COMMANDS_ALLOW_ALL, bool)
    assert isinstance(ENABLE_STREAMING, bool)


@patch.dict(os.environ, {"DEBUG": "1"})
def test_debug_mode_enabled():
    """Test that debug mode is enabled when environment variable is set."""
    # Reload the config module to pick up the environment variable
    import aicoder.config
    importlib.reload(aicoder.config)
    
    assert aicoder.config.DEBUG is True


def test_api_key_type():
    """Test that API key is a string."""
    assert isinstance(API_KEY, str)


def test_model_type():
    """Test that model is a string."""
    assert isinstance(API_MODEL, str)


@patch.dict(os.environ, {"YOLO_MODE": "1"})
def test_yolo_mode_enabled():
    """Test that YOLO mode is enabled when environment variable is set."""
    import aicoder.config
    importlib.reload(aicoder.config)
    
    assert aicoder.config.YOLO_MODE is True


def test_streaming_type():
    """Test that ENABLE_STREAMING is a boolean."""
    assert isinstance(ENABLE_STREAMING, bool)


@patch.dict(os.environ, {"STREAM_LOG_FILE": "/tmp/test.log"})
def test_stream_log_file():
    """Test that stream log file is set from environment variable."""
    import aicoder.config
    importlib.reload(aicoder.config)
    
    assert aicoder.config.STREAM_LOG_FILE == "/tmp/test.log"
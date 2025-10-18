"""Test helper utilities."""

import os
from typing import Dict, Any
from contextlib import contextmanager


@contextmanager
def temp_config(config_module, **kwargs):
    """
    Temporarily set configuration attributes for a test.
    
    Usage:
        with temp_config(config, COMPACT_MIN_MESSAGES=4, DEBUG=True):
            # Test code here with modified config
            pass
        # Original config is automatically restored
    """
    # Store original values
    original_values = {}
    
    for key, value in kwargs.items():
        if hasattr(config_module, key):
            original_values[key] = getattr(config_module, key)
        else:
            original_values[key] = None
        
        # Set the new value
        setattr(config_module, key, value)
    
    try:
        yield
    finally:
        # Restore original values
        for key, original_value in original_values.items():
            if original_value is None:
                # Attribute didn't exist originally, delete it
                if hasattr(config_module, key):
                    delattr(config_module, key)
            else:
                # Restore original value
                setattr(config_module, key, original_value)


@contextmanager
def temp_env(**kwargs):
    """
    Temporarily set environment variables for a test.
    
    Usage:
        with temp_env(DISABLE_PRUNING="1"):
            # Test code here with modified env
            pass
        # Original env is automatically restored
    """
    # Store original values
    original_values = {}
    
    for key, value in kwargs.items():
        original_values[key] = os.environ.get(key)
        os.environ[key] = str(value)
    
    try:
        yield
    finally:
        # Restore original values
        for key, original_value in original_values.items():
            if original_value is None:
                # Variable didn't exist originally, delete it
                if key in os.environ:
                    del os.environ[key]
            else:
                # Restore original value
                os.environ[key] = original_value


@contextmanager
def temp_config_and_env(config_module, config_overrides: Dict[str, Any] = None, 
                       env_overrides: Dict[str, str] = None):
    """
    Temporarily set both config attributes and environment variables for a test.
    
    Usage:
        with temp_config_and_env(config, 
                               config_overrides={'COMPACT_MIN_MESSAGES': 4},
                               env_overrides={'DISABLE_PRUNING': '1'}):
            # Test code here
            pass
    """
    config_overrides = config_overrides or {}
    env_overrides = env_overrides or {}
    
    with temp_config(config_module, **config_overrides), \
         temp_env(**env_overrides):
        yield
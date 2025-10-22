"""
Ultra-simple plugin loader for AI Coder.

This module loads and executes all Python files in the plugins directory.
Plugins can modify any part of the application using standard Python techniques.
"""

import os
import sys
import importlib.util
from pathlib import Path
import re


def load_plugins(plugin_dir=None):
    """Load and execute all Python files in the plugins directory.

    Args:
        plugin_dir (str, optional): Path to plugins directory.
            Defaults to ~/.config/aicoder/plugins

    Returns:
        list: Names of loaded plugins
    """
    # Skip plugin loading if disabled
    if os.environ.get("AICODER_DISABLE_PLUGINS"):
        return []
    
    if plugin_dir is None:
        # Check for environment variable to override plugin directory
        plugin_dir = os.environ.get("AICODER_PLUGIN_DIR")
        
        if plugin_dir is None:
            config_home = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser(
                "~/.config"
            )
            plugin_dir = os.path.join(config_home, "aicoder", "plugins")

    if not os.path.exists(plugin_dir):
        return []

    # Add plugin directory to Python path
    if plugin_dir not in sys.path:
        sys.path.insert(0, plugin_dir)

    loaded_plugins = []

    # Get list of plugin files for display
    plugin_files = [
        f for f in os.listdir(plugin_dir) if f.endswith(".py") and not f.startswith("_")
    ]
    # Sort: numbered first (ascending numerical), then non-numbered (alphabetical)
    def sort_key(f):
        stem = Path(f).stem
        match = re.match(r'^(\d+)', stem)
        if match:
            return (0, int(match.group(1)))  # Priority 0, numerical sort
        else:
            return (1, stem)  # Priority 1, alphabetical sort

    plugin_files = sorted(plugin_files, key=sort_key)

    if plugin_files:
        print(f"*** Loading plugins: {', '.join([Path(f).stem for f in plugin_files])}")

    # Execute each Python file
    for filename in plugin_files:
        plugin_path = os.path.join(plugin_dir, filename)
        try:
            spec = importlib.util.spec_from_file_location(
                f"plugin_{Path(filename).stem}", plugin_path
            )
            module = importlib.util.module_from_spec(spec)

            # Make aicoder modules available to plugins
            import aicoder

            module.aicoder = aicoder

            spec.loader.exec_module(module)
            loaded_plugins.append((Path(filename).stem, module))
            print(f"    - Loaded {filename}")

        except Exception as e:
            print(f"    - Warning: Failed to load plugin {filename}: {e}")

    if loaded_plugins:
        print(f"*** Plugin loading complete ({len(loaded_plugins)} plugins loaded)")

    # Return both names and module references
    return loaded_plugins


def notify_plugins_of_aicoder_init(loaded_plugins, aicoder_instance):
    """Notify plugins that have the on_aicoder_init hook that AICoder is initialized.

    Args:
        loaded_plugins (list): List of (name, module) tuples from load_plugins()
        aicoder_instance: The initialized AICoder instance
    """
    for plugin_name, module in loaded_plugins:
        # Check if the module has an on_aicoder_init function
        if hasattr(module, "on_aicoder_init"):
            try:
                module.on_aicoder_init(aicoder_instance)
            except Exception as e:
                print(
                    f"    - Warning: Plugin {plugin_name} failed in on_aicoder_init: {e}"
                )


def notify_plugins_before_user_prompt(loaded_plugins):
    """Notify plugins that have the on_before_user_prompt hook before displaying user prompt.

    Args:
        loaded_plugins (list): List of (name, module) tuples from load_plugins()
    """
    for plugin_name, module in loaded_plugins:
        # Check if the module has an on_before_user_prompt function
        if hasattr(module, "on_before_user_prompt"):
            try:
                module.on_before_user_prompt()
            except Exception as e:
                print(
                    f"    - Warning: Plugin {plugin_name} failed in on_before_user_prompt: {e}"
                )


def notify_plugins_before_ai_prompt(loaded_plugins):
    """Notify plugins that have the on_before_ai_prompt hook before displaying AI response.

    Args:
        loaded_plugins (list): List of (name, module) tuples from load_plugins()
    """
    for plugin_name, module in loaded_plugins:
        # Check if the module has an on_before_ai_prompt function
        if hasattr(module, "on_before_ai_prompt"):
            try:
                module.on_before_ai_prompt()
            except Exception as e:
                print(
                    f"    - Warning: Plugin {plugin_name} failed in on_before_ai_prompt: {e}"
                )


def notify_plugins_before_approval_prompt(loaded_plugins):
    """Notify plugins that have the on_before_approval_prompt hook before displaying approval prompt.

    Args:
        loaded_plugins (list): List of (name, module) tuples from load_plugins()
    """
    for plugin_name, module in loaded_plugins:
        # Check if the module has an on_before_approval_prompt function
        if hasattr(module, "on_before_approval_prompt"):
            try:
                module.on_before_approval_prompt()
            except Exception as e:
                print(
                    f"    - Warning: Plugin {plugin_name} failed in on_before_approval_prompt: {e}"
                )

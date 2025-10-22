"""
Dimmed Plugin

This plugin monkey patches the print function to automatically apply dimmed
formatting to strings that match configurable regex patterns.

Features:
- Multiple regex patterns (one per line in config files)
- Case-sensitive regex matching (explicit configuration required)
- If ANY pattern matches, the entire string is dimmed
- Hybrid configuration system with priority order:
  1. Project-local config (.aicoder/dimmed.conf) - highest priority
  2. Global config (~/.config/aicoder/dimmed.conf) - fallback
  3. Environment variables - final fallback/override
  4. Runtime commands - temporary changes
- Preserves all original print function behavior (sep, end, file, flush)
- Config file format: one regex per line
- Non-intrusive - falls back gracefully on errors

Commands:
- /dimmed                  - Show current patterns and status
- /dimmed add <pattern>    - Add a new pattern (temporary)
- /dimmed remove <pattern> - Remove a pattern (temporary)
- /dimmed clear            - Clear all patterns (temporary)
- /dimmed save             - Save current patterns to project config
- /dimmed save global      - Save current patterns to global config
- /dimmed reload           - Reload from config files
- /dimmed off              - Disable dimmed output
- /dimmed on               - Enable dimmed output
- /dimmed help             - Show command help

Environment Variables:
- AICODER_DIMMED_PATTERNS  - Comma-separated patterns (fallback)
- AICODER_DIMMED_ENABLED    - Enable/disable (default: 'true')

Config Files:
- .aicoder/dimmed.conf     - Project-specific patterns
- ~/.config/aicoder/dimmed.conf - Global patterns
- Format: one regex per line, comments start with #
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Optional, Pattern

# ANSI escape code for dimmed text
DIM = "\033[2m"
RESET = "\033[0m"

# Global state
_original_print = None
_dimmed_patterns: List[Pattern] = []
_dimmed_enabled = True
_project_config_path = None
_global_config_path = None


def _dimmed_print(*args, sep=' ', end='\n', file=None, flush=False):
    """Replacement print function that applies dimming to matching strings."""
    # Use original print function for actual output
    global _original_print, _dimmed_patterns, _dimmed_enabled
    
    if _original_print is None:
        # Fallback to built-in print if original not stored
        _original_print = __builtins__.get('print', print)
    
    if not _dimmed_enabled or not _dimmed_patterns:
        # No dimming, use original print
        _original_print(*args, sep=sep, end=end, file=file, flush=flush)
        return
    
    # Process each argument - check against ALL pre-compiled patterns
    dimmed_args = list(args)
    for i, arg in enumerate(args):
        if isinstance(arg, str):
            # Check if this is a multi-line string that needs per-line processing
            if '\n' in arg:
                # Split into lines and check each line separately
                lines = arg.split('\n')
                dimmed_lines = []
                
                for line in lines:
                    line_dimmed = False
                    # Fast pattern matching using pre-compiled regex objects
                    for compiled_pattern in _dimmed_patterns:
                        if compiled_pattern.search(line):
                            # Line matches pattern, apply dimming
                            dimmed_lines.append(f"{DIM}{line}{RESET}")
                            line_dimmed = True
                            break
                    
                    if not line_dimmed:
                        dimmed_lines.append(line)
                
                # Rejoin the lines
                dimmed_args[i] = '\n'.join(dimmed_lines)
            else:
                # Single line - use original logic
                for compiled_pattern in _dimmed_patterns:
                    if compiled_pattern.search(arg):
                        # String matches at least one pattern, apply dimming and stop checking
                        dimmed_args[i] = f"{DIM}{arg}{RESET}"
                        break
    
    # Print with potentially modified arguments
    _original_print(*dimmed_args, sep=sep, end=end, file=file, flush=flush)


def load_patterns_from_config(config_path: Path) -> List[str]:
    """Load patterns from a config file.
    
    Args:
        config_path: Path to config file
        
    Returns:
        List of pattern strings
    """
    if not config_path.exists():
        return []
    
    patterns = []
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if line and not line.startswith('#'):
                    patterns.append(line)
    except Exception as e:
        print(f"⚠️ Warning: Failed to read config file {config_path}: {e}")
    
    return patterns


def save_patterns_to_config(patterns: List[str], config_path: Path) -> bool:
    """Save patterns to a config file.
    
    Args:
        patterns: List of pattern strings to save
        config_path: Path to config file
        
    Returns:
        True if saved successfully, False otherwise
    """
    try:
        # Create parent directory if needed
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write("# Dimmed Plugin Configuration\n")
            f.write("# One regex pattern per line - if any matches, print is dimmed\n")
            f.write("# Lines starting with # are comments\n\n")
            for pattern in patterns:
                f.write(f"{pattern}\n")
        return True
    except Exception as e:
        print(f"❌ Failed to save config file {config_path}: {e}")
        return False


def compile_patterns(pattern_strings: List[str]) -> List[Pattern]:
    """Compile pattern strings into regex Pattern objects.
    
    Args:
        pattern_strings: List of regex pattern strings
        
    Returns:
        List of compiled Pattern objects
    """
    compiled = []
    for pattern_str in pattern_strings:
        try:
            # Compile with case-sensitive matching (ASCII mode for consistent behavior)
            compiled_pattern = re.compile(pattern_str, re.ASCII)
            compiled.append(compiled_pattern)
        except re.error as e:
            print(f"⚠️ Warning: Invalid regex pattern '{pattern_str}': {e}")
    return compiled


def set_dimmed_patterns(pattern_strings: List[str]) -> bool:
    """Set the regex patterns for dimmed output.
    
    Args:
        pattern_strings: List of regex pattern strings
        
    Returns:
        True if at least one pattern was set successfully, False otherwise
    """
    global _dimmed_patterns
    
    compiled_patterns = compile_patterns(pattern_strings)
    if compiled_patterns:
        _dimmed_patterns = compiled_patterns
        return True
    else:
        _dimmed_patterns = []
        return False


def add_dimmed_pattern(pattern: str) -> bool:
    """Add a new pattern to the existing patterns.
    
    Args:
        pattern: Regex pattern string to add
        
    Returns:
        True if pattern was added successfully, False otherwise
    """
    global _dimmed_patterns
    
    try:
        # Compile with case-sensitive matching (ASCII mode for consistent behavior)
        compiled_pattern = re.compile(pattern, re.ASCII)
        _dimmed_patterns.append(compiled_pattern)
        return True
    except re.error as e:
        print(f"❌ Invalid regex pattern '{pattern}': {e}")
        return False


def remove_dimmed_pattern(pattern: str) -> bool:
    """Remove a pattern from the existing patterns.
    
    Args:
        pattern: Regex pattern string to remove
        
    Returns:
        True if pattern was removed, False if not found
    """
    global _dimmed_patterns
    
    pattern_str_to_remove = pattern
    original_count = len(_dimmed_patterns)
    
    # Remove patterns matching this string
    _dimmed_patterns = [
        p for p in _dimmed_patterns 
        if p.pattern != pattern_str_to_remove
    ]
    
    return len(_dimmed_patterns) < original_count


def clear_dimmed_patterns() -> None:
    """Clear all patterns."""
    global _dimmed_patterns
    _dimmed_patterns = []


def set_dimmed_enabled(enabled: bool) -> None:
    """Enable or disable dimmed output.
    
    Args:
        enabled: True to enable, False to disable
    """
    global _dimmed_enabled
    _dimmed_enabled = enabled


def get_current_patterns() -> List[str]:
    """Get the current regex pattern strings.
    
    Returns:
        List of current pattern strings
    """
    global _dimmed_patterns
    return [p.pattern for p in _dimmed_patterns]


def is_dimmed_enabled() -> bool:
    """Check if dimmed output is enabled.
    
    Returns:
        True if enabled, False otherwise
    """
    global _dimmed_enabled
    return _dimmed_enabled


def load_all_patterns() -> List[str]:
    """Load patterns from all sources with priority order.
    
    Priority order:
    1. Project-local config (.aicoder/dimmed.conf) - highest priority
    2. Global config (~/.config/aicoder/dimmed.conf) - fallback  
    3. Environment variables - final fallback/override
    
    Returns:
        List of pattern strings
    """
    global _project_config_path, _global_config_path
    
    patterns = []
    
    # 1. Try project-local config
    if _project_config_path and _project_config_path.exists():
        project_patterns = load_patterns_from_config(_project_config_path)
        if project_patterns:
            patterns.extend(project_patterns)
            debug = os.environ.get("DEBUG", "0") == "1"
            if debug:
                print(f"🔅 Loaded {len(project_patterns)} patterns from project config")
    
    # 2. Try global config (only if no project patterns)
    if not patterns:
        if _global_config_path and _global_config_path.exists():
            global_patterns = load_patterns_from_config(_global_config_path)
            if global_patterns:
                patterns.extend(global_patterns)
                debug = os.environ.get("DEBUG", "0") == "1"
                if debug:
                    print(f"🔅 Loaded {len(global_patterns)} patterns from global config")
    
    # 3. Fallback to environment variables
    if not patterns:
        env_patterns = os.environ.get("AICODER_DIMMED_PATTERNS", "")
        if env_patterns:
            # Split by comma and strip whitespace
            patterns = [p.strip() for p in env_patterns.split(',') if p.strip()]
            debug = os.environ.get("DEBUG", "0") == "1"
            if debug:
                print(f"🔅 Loaded {len(patterns)} patterns from environment variables")
    
    # 4. No default fallback - require explicit configuration
    if not patterns:
        debug = os.environ.get("DEBUG", "0") == "1"
        if debug:
            print(f"🔅 No patterns configured - dimmed output disabled")
    
    return patterns


def initialize_dimmed_plugin():
    """Initialize the dimmed plugin with hybrid configuration system."""
    global _original_print, _dimmed_patterns, _dimmed_enabled
    global _project_config_path, _global_config_path

    # Prevent re-initialization
    if _original_print is not None:
        return
    
    # Store original print function
    _original_print = __builtins__.get('print', print)
    
    # Set up config paths
    _project_config_path = Path.cwd() / '.dt-aicoder' / 'dimmed.conf'
    config_home = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    _global_config_path = Path(config_home) / 'aicoder' / 'dimmed.conf'
    
    # Load enabled state from environment
    dimmed_enabled_env = os.environ.get("AICODER_DIMMED_ENABLED", "true").lower()
    _dimmed_enabled = dimmed_enabled_env in ('true', '1', 'yes', 'on')
    
    # Load and compile patterns from all sources
    pattern_strings = load_all_patterns()
    set_dimmed_patterns(pattern_strings)
    
    # Monkey patch the standard print function
    import builtins
    builtins.print = _dimmed_print
    
    # Show startup info in debug mode
    debug = os.environ.get("DEBUG", "0") == "1"
    if debug:
        status = "enabled" if _dimmed_enabled else "disabled"
        patterns = get_current_patterns()
        _original_print(f"🔅 Dimmed plugin loaded ({status})")
        _original_print(f"   Patterns ({len(patterns)}): {', '.join(patterns)}")
        _original_print(f"   Project config: {_project_config_path}")
        _original_print(f"   Global config: {_global_config_path}")
        _original_print(f"   Use /dimmed command to configure")


def handle_dimmed_command(aicoder_instance, args):
    """Handle the /dimmed command with enhanced pattern management."""
    global _project_config_path, _global_config_path
    
    if not args:
        # Show current status
        patterns = get_current_patterns()
        enabled = is_dimmed_enabled()
        status = "enabled" if enabled else "disabled"
        print(f"\nDimmed output: {status}")
        print(f"Current patterns ({len(patterns)}):")
        for i, pattern in enumerate(patterns, 1):
            print(f"  {i}. {pattern}")
        return False, False
    
    subcommand = args[0].lower()
    
    if subcommand == "help":
        print(f"\nDimmed Command Help:")
        print(f"  /dimmed                  - Show current patterns and status")
        print(f"  /dimmed add <pattern>    - Add a new pattern (temporary)")
        print(f"  /dimmed remove <pattern> - Remove a pattern (temporary)")
        print(f"  /dimmed clear            - Clear all patterns (temporary)")
        print(f"  /dimmed save             - Save current patterns to project config")
        print(f"  /dimmed save global      - Save current patterns to global config")
        print(f"  /dimmed reload           - Reload from config files")
        print(f"  /dimmed off              - Disable dimmed output")
        print(f"  /dimmed on               - Enable dimmed output")
        print(f"  /dimmed help             - Show this help")
        print(f"\nPattern examples:")
        print(f"  \\[.*?\\]                  - Match text in brackets [like this]")
        print(f"  \\(.*?\\)                  - Match text in parentheses (like this)")
        print(f"  Warning:.*               - Match lines starting with 'Warning:'")
        print(f"  \\bTODO\\b                - Match the word 'TODO'")
        print(f"  ^Error:.*               - Match lines starting with 'Error:'")
        print(f"  \\[DEBUG\\].*             - Match debug messages")
        return False, False
    
    elif subcommand == "add":
        if len(args) < 2:
            print(f"\n❌ Usage: /dimmed add <pattern>")
            return False, False
        
        pattern = ' '.join(args[1:])  # Allow spaces in pattern
        if add_dimmed_pattern(pattern):
            print(f"\n✅ Added pattern: {pattern}")
            set_dimmed_enabled(True)  # Auto-enable when pattern is added
        return False, False
    
    elif subcommand == "remove":
        if len(args) < 2:
            print(f"\n❌ Usage: /dimmed remove <pattern>")
            return False, False
        
        pattern = ' '.join(args[1:])  # Allow spaces in pattern
        if remove_dimmed_pattern(pattern):
            print(f"\n✅ Removed pattern: {pattern}")
        else:
            print(f"\n❌ Pattern not found: {pattern}")
        return False, False
    
    elif subcommand == "clear":
        clear_dimmed_patterns()
        print(f"\n✅ Cleared all patterns")
        return False, False
    
    elif subcommand == "save":
        patterns = get_current_patterns()
        if not patterns:
            print(f"\n⚠️ No patterns to save")
            return False, False
        
        if save_patterns_to_config(patterns, _project_config_path):
            print(f"\n✅ Saved {len(patterns)} patterns to project config:")
            print(f"   {_project_config_path}")
        return False, False
    
    elif subcommand == "save" and len(args) > 1 and args[1].lower() == "global":
        patterns = get_current_patterns()
        if not patterns:
            print(f"\n⚠️ No patterns to save")
            return False, False
        
        if save_patterns_to_config(patterns, _global_config_path):
            print(f"\n✅ Saved {len(patterns)} patterns to global config:")
            print(f"   {_global_config_path}")
        return False, False
    
    elif subcommand == "reload":
        pattern_strings = load_all_patterns()
        set_dimmed_patterns(pattern_strings)
        patterns = get_current_patterns()
        print(f"\n✅ Reloaded {len(patterns)} patterns from config files")
        return False, False
    
    elif subcommand in ("off", "disable"):
        set_dimmed_enabled(False)
        print(f"\nDimmed output disabled")
        return False, False
    
    elif subcommand in ("on", "enable"):
        set_dimmed_enabled(True)
        patterns = get_current_patterns()
        print(f"\nDimmed output enabled")
        print(f"Current patterns ({len(patterns)}): {', '.join(patterns)}")
        return False, False
    
    else:
        # Treat as a new pattern (backward compatibility)
        new_pattern = subcommand
        if add_dimmed_pattern(new_pattern):
            print(f"\n✅ Added pattern: {new_pattern}")
            set_dimmed_enabled(True)  # Auto-enable when pattern is set
        else:
            print(f"\n❌ Invalid regex pattern: {new_pattern}")
        return False, False


def on_aicoder_init(aicoder_instance):
    """Register the /dimmed command when AICoder is initialized."""
    # Register the dimmed command handler
    aicoder_instance.command_handlers["/dimmed"] = lambda args: handle_dimmed_command(aicoder_instance, args)


# Initialize plugin
initialize_dimmed_plugin()
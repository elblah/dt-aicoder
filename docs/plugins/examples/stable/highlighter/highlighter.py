"""
Dynamic Highlighting Plugin

This plugin provides advanced text highlighting capabilities with rule-based
pattern matching and styling. It can replace the dimmed plugin and provides
much more flexible text styling options.

Features:
- Multiple highlighting rules with priority-based application
- Background/foreground colors with automatic contrast
- Text formatting (bold, italic, underline, combinations)
- Sequential rule application (low priority → high priority)
- Higher priority rules override lower ones naturally
- Hybrid configuration system (project > global > env > runtime)
- Backward compatibility with dimmed plugin
- JSON-based rule configuration
- Runtime rule management commands

Commands:
- /highlight                  - Show current rules and status
- /highlight add <pattern> [options] - Add a new rule (temporary)
- /highlight remove <name>     - Remove a rule (temporary)
- /highlight clear              - Clear all rules (temporary)
- /highlight list              - List all current rules
- /highlight save              - Save current rules to project config
- /highlight save global       - Save current rules to global config
- /highlight reload            - Reload from config files
- /highlight off               - Disable highlighting
- /highlight on                - Enable highlighting
- /highlight migrate-dimmed    - Import dimmed plugin configurations
- /highlight help              - Show command help

Rule Options:
- --foreground=<color>         - Text color (red, green, blue, bright_red, etc.)
- --background=<color>         - Background color
- --bold                       - Make text bold
- --italic                     - Make text italic  
- --underline                  - Make text underlined
- --priority=<number>          - Rule priority (higher wins conflicts)
- --name=<name>               - Rule name (required for some operations)

Color Options:
- Foreground: black, red, green, yellow, blue, magenta, cyan, white,
              bright_red, bright_green, bright_yellow, bright_blue,
              bright_magenta, bright_cyan, bright_white, dim, auto_contrast
- Background: none, black, red, green, yellow, blue, magenta, cyan, white,
              bright_red, bright_green, bright_yellow, bright_blue,
              bright_magenta, bright_cyan, bright_white

Environment Variables:
- AICODER_HIGHLIGHTER_ENABLED    - Enable/disable highlighting (default: 'true')
- AICODER_HIGHLIGHTER_RULES      - Simple comma-separated rules (fallback)
- AICODER_HIGHLIGHTER_CONFIG     - JSON configuration string (fallback)

Config Files:
- .aicoder/highlighter.json     - Project-specific rules (highest priority)
- ~/.config/aicoder/highlighter.json - Global rules (fallback)

Rule Examples:
- /highlight add "\\[!\\]" --background=bright_red --foreground=auto_contrast --bold --priority=100
- /highlight add "ERROR:" --background=red --foreground=white --bold --priority=90
- /highlight add "Tool result:" --foreground=dim --priority=10
"""

import os
import re
import json
from pathlib import Path
from typing import List, Dict, Any, Pattern, Optional
import argparse

# Import config for color constants
try:
    import aicoder.config as config
except ImportError:
    # Fallback if running standalone
    class Config:
        RED = "\033[31m"
        GREEN = "\033[32m"
        YELLOW = "\033[33m"
        BLUE = "\033[34m"
        MAGENTA = "\033[35m"
        CYAN = "\033[36m"
        WHITE = "\033[37m"
        RESET = "\033[0m"
        BOLD = "\033[1m"
        DIM = "\033[2m"
        ITALIC = "\033[3m"
        UNDERLINE = "\033[4m"
        BRIGHT_RED = "\033[91m"
        BRIGHT_GREEN = "\033[92m"
        BRIGHT_YELLOW = "\033[93m"
        BRIGHT_BLUE = "\033[94m"
        BRIGHT_MAGENTA = "\033[95m"
        BRIGHT_CYAN = "\033[96m"
        BRIGHT_WHITE = "\033[97m"
    config = Config()

# Global state
_original_print = None
_highlighter_rules: List[Dict[str, Any]] = []
_highlighter_enabled = True
_project_config_path = None
_global_config_path = None


class HighlightRule:
    """Represents a single highlighting rule."""
    
    def __init__(self, name: str, pattern: str, style: Dict[str, Any], priority: int = 50):
        self.name = name
        self.pattern_str = pattern
        self.priority = priority
        
        # Compile the regex pattern
        try:
            self.compiled_pattern = re.compile(pattern, re.ASCII)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern '{pattern}': {e}")
        
        # Pre-compute the style string for efficiency
        self.style_string = self._build_style_string(style)
        
        # Store original style for serialization
        self.style = style
    
    def _build_style_string(self, style: Dict[str, Any]) -> str:
        """Build the ANSI escape sequence for this style."""
        ansi_codes = []
        
        # Background color
        bg_color = style.get("background", "none")
        if bg_color != "none":
            ansi_codes.append(self._get_color_code(bg_color, background=True))
        
        # Foreground color
        fg_color = style.get("foreground", "white")
        if fg_color == "auto_contrast":
            fg_color = self._calculate_contrast_color(bg_color)
        if fg_color == "dim":
            ansi_codes.append("\033[2m")
        elif fg_color != "default":
            ansi_codes.append(self._get_color_code(fg_color, background=False))
        
        # Text formatting
        if style.get("bold", False):
            ansi_codes.append("\033[1m")
        if style.get("italic", False):
            ansi_codes.append("\033[3m")
        if style.get("underline", False):
            ansi_codes.append("\033[4m")
        
        return "".join(ansi_codes) if ansi_codes else ""
    
    def _get_color_code(self, color_name: str, background: bool = False) -> str:
        """Get ANSI color code for a color name."""
        color_map = {
            "black": ("40", "30"),
            "red": ("41", "31"),
            "green": ("42", "32"),
            "yellow": ("43", "33"),
            "blue": ("44", "34"),
            "magenta": ("45", "35"),
            "cyan": ("46", "36"),
            "white": ("47", "37"),
            "bright_red": ("101", "91"),
            "bright_green": ("102", "92"),
            "bright_yellow": ("103", "93"),
            "bright_blue": ("104", "94"),
            "bright_magenta": ("105", "95"),
            "bright_cyan": ("106", "96"),
            "bright_white": ("107", "97"),
        }
        
        bg_code, fg_code = color_map.get(color_name.lower(), ("47", "37"))
        code = bg_code if background else fg_code
        return f"\033[{code}m"
    
    def _calculate_contrast_color(self, background_color: str) -> str:
        """Calculate optimal foreground color for contrast."""
        contrast_map = {
            "black": "bright_white",
            "red": "white",
            "green": "white", 
            "yellow": "black",
            "blue": "white",
            "magenta": "white",
            "cyan": "black",
            "white": "black",
            "bright_red": "black",
            "bright_green": "black",
            "bright_yellow": "black",
            "bright_blue": "white",
            "bright_magenta": "white",
            "bright_cyan": "black",
            "bright_white": "black",
        }
        return contrast_map.get(background_color.lower(), "white")
    
    def apply_to_text(self, text: str) -> str:
        """Apply this rule's highlighting to text."""
        if not self.style_string:
            return text
        
        # Replace all matches with styled version
        return self.compiled_pattern.sub(
            lambda m: f"{self.style_string}{m.group()}{config.RESET}",
            text
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert rule to dictionary for serialization."""
        return {
            "name": self.name,
            "pattern": self.pattern_str,
            "style": self.style,
            "priority": self.priority
        }


def _highlighter_print(*args, sep=" ", end="\n", file=None, flush=False):
    """Replacement print function that applies highlighting to matching strings."""
    global _original_print, _highlighter_rules, _highlighter_enabled

    if _original_print is None:
        # Fallback to built-in print if original not stored
        _original_print = __builtins__.get("print", print)

    if not _highlighter_enabled or not _highlighter_rules:
        # No highlighting, use original print
        _original_print(*args, sep=sep, end=end, file=file, flush=flush)
        return

    # Process each argument
    highlighted_args = list(args)
    for i, arg in enumerate(args):
        if isinstance(arg, str):
            # Apply all rules in priority order (low → high)
            processed_arg = arg
            sorted_rules = sorted(_highlighter_rules, key=lambda r: r.priority)
            
            for rule in sorted_rules:
                processed_arg = rule.apply_to_text(processed_arg)
            
            highlighted_args[i] = processed_arg

    # Print with potentially modified arguments
    _original_print(*highlighted_args, sep=sep, end=end, file=file, flush=flush)


def load_rules_from_config(config_path: Path) -> List[Dict[str, Any]]:
    """Load rules from a JSON config file.

    Args:
        config_path: Path to config file

    Returns:
        List of rule dictionaries
    """
    if not config_path.exists():
        return []

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = json.load(f)
        
        rules = config_data.get("rules", [])
        
        # Validate rule structure
        valid_rules = []
        for rule in rules:
            if not all(key in rule for key in ["name", "pattern", "style", "priority"]):
                print(f"[!] Warning: Invalid rule structure in {config_path}: {rule}")
                continue
            valid_rules.append(rule)
        
        return valid_rules
    except json.JSONDecodeError as e:
        print(f"[!] Warning: Invalid JSON in config file {config_path}: {e}")
        return []
    except Exception as e:
        print(f"[!] Warning: Failed to read config file {config_path}: {e}")
        return []


def save_rules_to_config(rules: List[Dict[str, Any]], config_path: Path) -> bool:
    """Save rules to a JSON config file.

    Args:
        rules: List of rule dictionaries to save
        config_path: Path to config file

    Returns:
        True if saved successfully, False otherwise
    """
    try:
        # Create parent directory if needed
        config_path.parent.mkdir(parents=True, exist_ok=True)

        config_data = {
            "version": "1.0",
            "rules": rules
        }

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2, sort_keys=True)
        return True
    except Exception as e:
        print(f"[X] Failed to save config file {config_path}: {e}")
        return False


def load_rules_from_env() -> List[Dict[str, Any]]:
    """Load rules from environment variables."""
    rules = []
    
    # Try JSON config first
    env_config = os.environ.get("AICODER_HIGHLIGHTER_CONFIG")
    if env_config:
        try:
            config_data = json.loads(env_config)
            rules.extend(config_data.get("rules", []))
        except json.JSONDecodeError:
            pass  # Fall back to simple format
    
    # Try simple comma-separated format
    if not rules:
        env_rules = os.environ.get("AICODER_HIGHLIGHTER_RULES", "")
        if env_rules:
            for i, rule_str in enumerate(env_rules.split(",")):
                if ":" in rule_str:
                    pattern, style_parts = rule_str.split(":", 1)
                    style_options = style_parts.split(":")
                    
                    rule = {
                        "name": f"env_rule_{i}",
                        "pattern": pattern.strip(),
                        "style": {},
                        "priority": 50
                    }
                    
                    # Parse simple style format
                    if len(style_options) >= 1 and style_options[0]:
                        rule["style"]["background"] = style_options[0]
                    if len(style_options) >= 2 and style_options[1]:
                        rule["style"]["foreground"] = style_options[1]
                    if len(style_options) >= 3 and style_options[2].lower() == "true":
                        rule["style"]["bold"] = True
                    
                    rules.append(rule)
    
    return rules


def load_dimmed_rules() -> List[Dict[str, Any]]:
    """Load rules from existing dimmed plugin configuration."""
    dimmed_rules = []
    
    # Check for dimmed config files
    dimmed_paths = [
        Path.cwd() / ".aicoder" / "dimmed.conf",
        Path.home() / ".config" / "aicoder" / "dimmed.conf"
    ]
    
    for dimmed_path in dimmed_paths:
        if dimmed_path.exists():
            try:
                with open(dimmed_path, "r", encoding="utf-8") as f:
                    for i, line in enumerate(f):
                        line = line.strip()
                        if line and not line.startswith("#"):
                            # Convert simple pattern to regex if needed
                            # Dimmed plugin treats patterns as regex, so simple text
                            # like "AI wants" should become "AI wants" for search
                            # But if it already looks like regex (contains meta chars), keep it
                            pattern = line
                            if not any(char in line for char in r'\.^$*+?{}[]\|()'):
                                # Simple text pattern - convert to regex for search anywhere
                                pattern = f".*{re.escape(line)}.*"
                            
                            dimmed_rules.append({
                                "name": f"dimmed_{dimmed_path.name}_{i}",
                                "pattern": pattern,
                                "style": {"foreground": "dim"},
                                "priority": 10  # Low priority so highlighting rules win
                            })
            except Exception as e:
                print(f"[!] Warning: Failed to import dimmed config {dimmed_path}: {e}")
    
    return dimmed_rules


def set_highlighter_rules(rule_dicts: List[Dict[str, Any]]) -> bool:
    """Set the highlighting rules.

    Args:
        rule_dicts: List of rule dictionaries

    Returns:
        True if at least one rule was set successfully, False otherwise
    """
    global _highlighter_rules

    try:
        _highlighter_rules = [HighlightRule(**rule_dict) for rule_dict in rule_dicts]
        return True
    except Exception as e:
        print(f"[X] Failed to set highlighting rules: {e}")
        _highlighter_rules = []
        return False


def add_highlighter_rule(name: str, pattern: str, style: Dict[str, Any], priority: int = 50) -> bool:
    """Add a new highlighting rule.

    Args:
        name: Rule name
        pattern: Regex pattern
        style: Style dictionary
        priority: Rule priority

    Returns:
        True if rule was added successfully, False otherwise
    """
    global _highlighter_rules

    # Remove existing rule with same name
    _highlighter_rules = [r for r in _highlighter_rules if r.name != name]

    try:
        new_rule = HighlightRule(name, pattern, style, priority)
        _highlighter_rules.append(new_rule)
        return True
    except Exception as e:
        print(f"[X] Failed to add rule '{name}': {e}")
        return False


def remove_highlighter_rule(name: str) -> bool:
    """Remove a highlighting rule by name.

    Args:
        name: Rule name to remove

    Returns:
        True if rule was removed, False if not found
    """
    global _highlighter_rules

    original_count = len(_highlighter_rules)
    _highlighter_rules = [r for r in _highlighter_rules if r.name != name]
    
    return len(_highlighter_rules) < original_count


def clear_highlighter_rules() -> None:
    """Clear all rules."""
    global _highlighter_rules
    _highlighter_rules = []


def set_highlighter_enabled(enabled: bool) -> None:
    """Enable or disable highlighting.

    Args:
        enabled: True to enable, False to disable
    """
    global _highlighter_enabled
    _highlighter_enabled = enabled


def get_current_rules() -> List[Dict[str, Any]]:
    """Get the current rule dictionaries.

    Returns:
        List of current rule dictionaries
    """
    global _highlighter_rules
    return [rule.to_dict() for rule in _highlighter_rules]


def is_highlighter_enabled() -> bool:
    """Check if highlighting is enabled.

    Returns:
        True if enabled, False otherwise
    """
    global _highlighter_enabled
    return _highlighter_enabled


def load_all_rules() -> List[Dict[str, Any]]:
    """Load rules from all sources with priority order.

    Priority order:
    1. Project-local config (.aicoder/highlighter.json) - highest priority
    2. Global config (~/.config/aicoder/highlighter.json) - fallback
    3. Environment variables - final fallback
    4. Dimmed plugin configs (imported with low priority)

    Returns:
        List of rule dictionaries
    """
    global _project_config_path, _global_config_path

    all_rules = []

    # 1. Try project-local config
    if _project_config_path and _project_config_path.exists():
        project_rules = load_rules_from_config(_project_config_path)
        if project_rules:
            all_rules.extend(project_rules)
            debug = os.environ.get("DEBUG", "0") == "1"
            if debug:
                print(f"Loaded {len(project_rules)} rules from project config")

    # 2. Try global config (only if no project rules)
    if not all_rules:
        if _global_config_path and _global_config_path.exists():
            global_rules = load_rules_from_config(_global_config_path)
            if global_rules:
                all_rules.extend(global_rules)
                debug = os.environ.get("DEBUG", "0") == "1"
                if debug:
                    print(f"Loaded {len(global_rules)} rules from global config")

    # 3. Fallback to environment variables
    if not all_rules:
        env_rules = load_rules_from_env()
        if env_rules:
            all_rules.extend(env_rules)
            debug = os.environ.get("DEBUG", "0") == "1"
            if debug:
                print(f"Loaded {len(env_rules)} rules from environment variables")

    # 4. Import dimmed rules with low priority (always add, but with low priority)
    dimmed_rules = load_dimmed_rules()
    if dimmed_rules:
        all_rules.extend(dimmed_rules)
        debug = os.environ.get("DEBUG", "0") == "1"
        if debug:
            print(f"Imported {len(dimmed_rules)} rules from dimmed plugin")

    return all_rules


def parse_style_arguments(args: List[str]) -> Dict[str, Any]:
    """Parse style arguments from command line.

    Args:
        args: Command line arguments

    Returns:
        Style dictionary
    """
    style = {}
    
    # Create a simple parser for the style arguments
    for arg in args:
        if arg.startswith("--foreground="):
            style["foreground"] = arg.split("=", 1)[1]
        elif arg.startswith("--background="):
            style["background"] = arg.split("=", 1)[1]
        elif arg.startswith("--priority="):
            # This is handled separately
            pass
        elif arg.startswith("--name="):
            # This is handled separately
            pass
        elif arg in ["--bold", "--italic", "--underline"]:
            style[arg[2:]] = True
    
    return style


def extract_argument_value(args: List[str], prefix: str) -> Optional[str]:
    """Extract a specific argument value from args list.

    Args:
        args: Command line arguments
        prefix: Argument prefix (e.g., "--name=")

    Returns:
        Argument value or None if not found
    """
    for arg in args:
        if arg.startswith(prefix):
            return arg.split("=", 1)[1]
    return None


def initialize_highlighter_plugin():
    """Initialize the highlighter plugin."""
    global _original_print, _highlighter_rules, _highlighter_enabled
    global _project_config_path, _global_config_path

    # Prevent re-initialization
    if _original_print is not None:
        return

    # Store original print function
    _original_print = __builtins__.get("print", print)

    # Set up config paths
    _project_config_path = Path.cwd() / ".aicoder" / "highlighter.json"
    config_home = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    _global_config_path = Path(config_home) / "aicoder" / "highlighter.json"

    # Load enabled state from environment
    highlighter_enabled_env = os.environ.get("AICODER_HIGHLIGHTER_ENABLED", "true").lower()
    _highlighter_enabled = highlighter_enabled_env in ("true", "1", "yes", "on")

    # Load and compile rules from all sources
    rule_dicts = load_all_rules()
    set_highlighter_rules(rule_dicts)

    # Monkey patch the standard print function
    import builtins
    builtins.print = _highlighter_print

    # Show startup info in debug mode
    debug = os.environ.get("DEBUG", "0") == "1"
    if debug:
        status = "enabled" if _highlighter_enabled else "disabled"
        rules = get_current_rules()
        print(f"Highlighter plugin loaded ({status})")
        print(f"   Rules ({len(rules)}): {', '.join([r['name'] for r in rules])}")
        print(f"   Project config: {_project_config_path}")
        print(f"   Global config: {_global_config_path}")
        print("   Use /highlight command to configure")


def handle_highlighter_command(aicoder_instance, args):
    """Handle the /highlight command."""
    global _project_config_path, _global_config_path

    if not args:
        # Show current status
        rules = get_current_rules()
        enabled = is_highlighter_enabled()
        status = "enabled" if enabled else "disabled"
        print(f"\nHighlighting: {status}")
        print(f"Current rules ({len(rules)}):")
        for rule in sorted(rules, key=lambda r: r['priority'], reverse=True):
            style_desc = []
            if rule['style'].get('background') and rule['style']['background'] != 'none':
                style_desc.append(f"bg:{rule['style']['background']}")
            if rule['style'].get('foreground'):
                style_desc.append(f"fg:{rule['style']['foreground']}")
            if rule['style'].get('bold'):
                style_desc.append("bold")
            if rule['style'].get('italic'):
                style_desc.append("italic")
            if rule['style'].get('underline'):
                style_desc.append("underline")
            
            style_str = ", ".join(style_desc) if style_desc else "default"
            print(f"  {rule['priority']:3d} {rule['name']:20s} {rule['pattern']:20s} [{style_str}]")
        return False, False

    subcommand = args[0].lower()

    if subcommand == "help":
        print("\nHighlighter Command Help:")
        print("  /highlight                     - Show current rules and status")
        print("  /highlight add <pattern> [options] - Add a new rule (temporary)")
        print("    Options: --foreground=<color> --background=<color> --bold --italic --underline --priority=<num> --name=<name>")
        print("  /highlight remove <name>      - Remove a rule (temporary)")
        print("  /highlight clear               - Clear all rules (temporary)")
        print("  /highlight list                - List all current rules")
        print("  /highlight save                - Save current rules to project config")
        print("  /highlight save global         - Save current rules to global config")
        print("  /highlight reload              - Reload from config files")
        print("  /highlight off                 - Disable highlighting")
        print("  /highlight on                  - Enable highlighting")
        print("  /highlight migrate-dimmed      - Import dimmed plugin configurations")
        print("  /highlight help                - Show this help")
        print("\nStyle Examples:")
        print("  /highlight add '\\[!\\]' --background=bright_red --foreground=auto_contrast --bold --priority=100")
        print("  /highlight add 'ERROR:' --background=red --foreground=white --bold --priority=90")
        print("  /highlight add 'Tool result:' --foreground=dim --priority=10")
        print("\nColor Options:")
        print("  Foreground: black, red, green, yellow, blue, magenta, cyan, white,")
        print("              bright_red, bright_green, bright_yellow, bright_blue,")
        print("              bright_magenta, bright_cyan, bright_white, dim, auto_contrast")
        print("  Background: none, black, red, green, yellow, blue, magenta, cyan, white,")
        print("              bright_red, bright_green, bright_yellow, bright_blue,")
        print("              bright_magenta, bright_cyan, bright_white")
        return False, False

    elif subcommand == "add":
        if len(args) < 2:
            print("\n[X] Usage: /highlight add <pattern> [options]")
            return False, False

        pattern = args[1]
        style_args = args[2:] if len(args) > 2 else []
        style = parse_style_arguments(style_args)
        
        # Extract special arguments
        name = extract_argument_value(style_args, "--name=")
        if not name:
            # Generate a name from pattern
            name = f"rule_{pattern.replace('[', '').replace(']', '').replace(chr(92), '')[:10]}"
        
        priority_str = extract_argument_value(style_args, "--priority=")
        priority = int(priority_str) if priority_str else 50

        if add_highlighter_rule(name, pattern, style, priority):
            print(f"\n[✓] Added rule: {name}")
            print(f"    Pattern: {pattern}")
            print(f"    Style: {style}")
            print(f"    Priority: {priority}")
            set_highlighter_enabled(True)  # Auto-enable when rule is added
        return False, False

    elif subcommand == "remove":
        if len(args) < 2:
            print("\n[X] Usage: /highlight remove <name>")
            return False, False

        name = args[1]
        if remove_highlighter_rule(name):
            print(f"\n[✓] Removed rule: {name}")
        else:
            print(f"\n[X] Rule not found: {name}")
        return False, False

    elif subcommand == "clear":
        clear_highlighter_rules()
        print("\n[✓] Cleared all rules")
        return False, False

    elif subcommand == "list":
        rules = get_current_rules()
        if not rules:
            print("\nNo rules configured")
            return False, False
        
        print(f"\nCurrent rules ({len(rules)}):")
        for rule in sorted(rules, key=lambda r: r['priority'], reverse=True):
            style_desc = []
            if rule['style'].get('background') and rule['style']['background'] != 'none':
                style_desc.append(f"bg:{rule['style']['background']}")
            if rule['style'].get('foreground'):
                style_desc.append(f"fg:{rule['style']['foreground']}")
            if rule['style'].get('bold'):
                style_desc.append("bold")
            if rule['style'].get('italic'):
                style_desc.append("italic")
            if rule['style'].get('underline'):
                style_desc.append("underline")
            
            style_str = ", ".join(style_desc) if style_desc else "default"
            print(f"  {rule['priority']:3d} {rule['name']:20s} {rule['pattern']:20s} [{style_str}]")
        return False, False

    elif subcommand == "save":
        rules = get_current_rules()
        if not rules:
            print("\n[!] No rules to save")
            return False, False

        if save_rules_to_config(rules, _project_config_path):
            print(f"\n[✓] Saved {len(rules)} rules to project config:")
            print(f"   {_project_config_path}")
        return False, False

    elif subcommand == "save" and len(args) > 1 and args[1].lower() == "global":
        rules = get_current_rules()
        if not rules:
            print("\n[!] No rules to save")
            return False, False

        if save_rules_to_config(rules, _global_config_path):
            print(f"\n[✓] Saved {len(rules)} rules to global config:")
            print(f"   {_global_config_path}")
        return False, False

    elif subcommand == "reload":
        rule_dicts = load_all_rules()
        set_highlighter_rules(rule_dicts)
        rules = get_current_rules()
        print(f"\n[✓] Reloaded {len(rules)} rules from config files")
        return False, False

    elif subcommand in ("off", "disable"):
        set_highlighter_enabled(False)
        print("\nHighlighting disabled")
        return False, False

    elif subcommand in ("on", "enable"):
        set_highlighter_enabled(True)
        rules = get_current_rules()
        print("\nHighlighting enabled")
        print(f"Current rules ({len(rules)}): {', '.join([r['name'] for r in rules])}")
        return False, False

    elif subcommand == "migrate-dimmed":
        dimmed_rules = load_dimmed_rules()
        if dimmed_rules:
            for rule in dimmed_rules:
                add_highlighter_rule(rule['name'], rule['pattern'], rule['style'], rule['priority'])
            print(f"\n[✓] Imported {len(dimmed_rules)} rules from dimmed plugin")
        else:
            print("\n[!] No dimmed configurations found to import")
        return False, False

    else:
        # Invalid subcommand
        print(f"\n[X] Unknown subcommand: {subcommand}")
        print("Use '/highlight help' to see available commands")
        return False, False


def on_aicoder_init(aicoder_instance):
    """Register the /highlight command when AICoder is initialized."""
    # Register the highlight command handler
    aicoder_instance.command_handlers["/highlight"] = lambda args: handle_highlighter_command(
        aicoder_instance, args
    )


# Initialize plugin
initialize_highlighter_plugin()
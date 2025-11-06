"""
Dynamic Highlighting Plugin

This plugin provides advanced text highlighting capabilities with rule-based
pattern matching and styling. It can replace the dimmed plugin and provides
much more flexible text styling options with opacity support.

Features:
- Multiple highlighting rules with priority-based application
- Background/foreground colors with automatic contrast
- Text formatting (bold, italic, underline, combinations)
- Sequential rule application (low priority → high priority)
- Higher priority rules override lower ones naturally
- Hybrid configuration system (project > global > env > runtime)
- JSON-based rule configuration
- Opacity-based dimming for RGB colors
- Opacity support for RGB colors

Config Files:
- .aicoder/highlighter.json     - Project-specific rules (highest priority)
- ~/.config/aicoder/highlighter.json - Global rules (fallback)

Rule Examples (in JSON config):
{
  "rules": [
    {
      "name": "error_highlight",
      "pattern": "ERROR:",
      "style": {
        "background": "red",
        "foreground": "white",
        "bold": true
      },
      "priority": 90
    },
    {
      "name": "warning_highlight",
      "pattern": "WARNING:",
      "style": {
        "foreground": "#FFFF00",
        "opacity": 50
      },
      "priority": 10
    }
  ]
}
"""

import os
import re
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

# Import config for color constants
try:
    import aicoder.config as config
    from aicoder.utils import clear_background_cache as original_clear_background_cache
    _CONFIG_AVAILABLE = True
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
    _CONFIG_AVAILABLE = False

# Global state
_original_print = None
_highlighter_rules: List[Dict[str, Any]] = []
_highlighter_enabled = True
_project_config_path = None
_global_config_path = None

# Color cache for the highlighter plugin - cleared when theme changes
_color_cache = {}

# Cache for auto foreground calculations (luminance-based)
_auto_foreground_cache = {}

# Cache for RGB extraction from color codes
_rgb_extraction_cache = {}

# Cache for luminance calculations
_luminance_cache = {}

# Cache for terminal truecolor detection
_truecolor_cache = None

# Cache for opacity calculations
_opacity_cache = {}


def _clear_highlighter_color_cache():
    """Clear the highlighter plugin's color cache."""
    global _color_cache, _auto_foreground_cache, _rgb_extraction_cache, _luminance_cache, _opacity_cache, _truecolor_cache
    _color_cache.clear()
    _auto_foreground_cache.clear()
    _rgb_extraction_cache.clear()
    _luminance_cache.clear()
    _opacity_cache.clear()
    _truecolor_cache = None  # Reset truecolor detection cache


def _clear_all_background_caches():
    """Clear both highlighter and utils background caches when theme changes."""
    _clear_highlighter_color_cache()
    if _CONFIG_AVAILABLE:
        original_clear_background_cache()


def _is_truecolor_terminal():
    """Detect if the terminal supports truecolor (24-bit RGB)."""
    global _truecolor_cache

    if _truecolor_cache is not None:
        return _truecolor_cache

    # Check COLORTERM environment variable
    colorterm = os.environ.get('COLORTERM', '').lower()
    if 'truecolor' in colorterm or '24bit' in colorterm:
        _truecolor_cache = True
        return True

    # Check TERM environment variable for known truecolor terminals
    term = os.environ.get('TERM', '').lower()
    truecolor_terms = [
        'xterm-256color', 'xterm-24bit', 'xterm-kitty', 'screen-256color',
        'tmux-256color', 'alacritty', 'kitty', 'iterm', 'iterm2'
    ]
    if any(t in term for t in truecolor_terms):
        _truecolor_cache = True
        return True

    # Default to false if no clear indication
    _truecolor_cache = False
    return False


def _parse_rgb_from_ansi(ansi_code: str) -> Optional[tuple]:
    """Parse RGB values from ANSI escape code.

    Args:
        ansi_code: ANSI escape code string

    Returns:
        Tuple of (r, g, b) values or None if not an RGB code
    """
    # Check cache first
    if ansi_code in _rgb_extraction_cache:
        return _rgb_extraction_cache[ansi_code]

    import re
    # Look for RGB pattern: \033[38;2;R;G;Bm (foreground) or \033[48;2;R;G;Bm (background)
    match = re.search(r'\033\[(38|48);2;(\d+);(\d+);(\d+)m', ansi_code)
    if match:
        r, g, b = map(int, match.groups()[1:])
        rgb_tuple = (r, g, b)
        _rgb_extraction_cache[ansi_code] = rgb_tuple
        return rgb_tuple

    # Also handle hex colors
    if ansi_code.startswith('#'):
        hex_color = ansi_code.lstrip('#')
        if len(hex_color) == 3:
            hex_color = ''.join([c * 2 for c in hex_color])
        if len(hex_color) == 6:
            try:
                r = int(hex_color[0:2], 16)
                g = int(hex_color[2:4], 16)
                b = int(hex_color[4:6], 16)
                rgb_tuple = (r, g, b)
                _rgb_extraction_cache[ansi_code] = rgb_tuple
                return rgb_tuple
            except ValueError:
                pass

    _rgb_extraction_cache[ansi_code] = None
    return None





def _apply_opacity_to_rgb(r: int, g: int, b: int, opacity: int) -> tuple:
    """Apply opacity to RGB color by reducing brightness.

    Args:
        r, g, b: RGB color values (0-255)
        opacity: Opacity percentage (0-100)

    Returns:
        Tuple of opacity-adjusted (r, g, b) values
    """
    # Check cache first
    cache_key = (r, g, b, opacity)
    if cache_key in _opacity_cache:
        return _opacity_cache[cache_key]

    # Calculate new RGB values based on opacity
    # 0% opacity = black (0, 0, 0)
    # 100% opacity = original color
    # Simply multiply each channel by the opacity ratio
    alpha = opacity / 100.0
    new_r = int(r * alpha)
    new_g = int(g * alpha)
    new_b = int(b * alpha)

    result = (new_r, new_g, new_b)
    _opacity_cache[cache_key] = result
    return result


def _rgb_to_ansi(r: int, g: int, b: int, is_background: bool = False) -> str:
    """Convert RGB values to ANSI escape code.

    Args:
        r, g, b: RGB color values (0-255)
        is_background: True if this is a background color, False for foreground

    Returns:
        ANSI escape code string
    """
    color_type = "48" if is_background else "38"
    return f"\033[{color_type};2;{r};{g};{b}m"





class HighlightRule:
    """Represents a single highlighting rule."""

    def __init__(self, name: str, pattern: str, style: Dict[str, Any], priority: int = 50):
        self.name = name
        self.pattern_str = pattern
        self.priority = priority

        # Extract opacity from style (default to 100% if not specified)
        self.opacity = style.get("opacity", 100)
        if isinstance(self.opacity, str):
            if self.opacity.endswith('%'):
                self.opacity = int(self.opacity[:-1])
            else:
                self.opacity = int(self.opacity)
        self.opacity = max(0, min(100, self.opacity))  # Clamp to 0-100

        # Remove opacity from style before building style string
        style_for_string = style.copy()
        if 'opacity' in style_for_string:
            del style_for_string['opacity']

        # Compile the regex pattern
        try:
            if pattern.startswith('^'):
                # For each alternative in the pattern, add the optional ANSI prefix
                # Split on | but keep the delimiter
                alternatives = pattern.split('|')
                modified_alternatives = []
                for alt in alternatives:
                    if alt.startswith('^'):
                        # Replace ^ with optional ANSI escape sequence prefix followed by optional whitespace
                        modified_alt = r'(?:\033\[[0-9;]*m)?\s*' + alt[1:]
                    else:
                        modified_alt = alt
                    modified_alternatives.append(modified_alt)
                modified_pattern = '|'.join(modified_alternatives)
            else:
                modified_pattern = pattern

            self.compiled_pattern = re.compile(modified_pattern, re.ASCII)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern '{pattern}': {e}")

        # Pre-compute the style string for efficiency
        self.style_string = self._build_style_string(style_for_string)

        # Store original style for serialization (including opacity)
        self.style = style

    def _build_style_string(self, style: Dict[str, Any]) -> str:
        """Build the ANSI escape sequence for this style."""
        ansi_codes = []

        # Background color - only add if explicitly specified
        bg_color = style.get("background")
        if bg_color is not None and bg_color != "none":
            ansi_codes.append(self._get_rgb_color(bg_color, background=True))

        # Foreground color - only add if explicitly specified
        fg_color = style.get("foreground")
        if fg_color == "auto":
            # Auto calculate foreground color based on background luminance
            # Only if a background is also specified
            bg_color_for_auto = style.get("background")
            if bg_color_for_auto is not None and bg_color_for_auto != "none":
                bg_rgb_color = self._get_rgb_color(bg_color_for_auto, background=True)
                auto_color = self._get_auto_foreground(bg_rgb_color)
                ansi_codes.append(self._get_rgb_color(auto_color, background=False))
        elif fg_color and fg_color != "default" and fg_color != "dim":  # Completely remove dim support
            ansi_codes.append(self._get_rgb_color(fg_color, background=False))

        # Text formatting
        if style.get("bold", False):
            ansi_codes.append(getattr(config, "BOLD", "\033[1m"))
        if style.get("italic", False):
            ansi_codes.append(getattr(config, "ITALIC", "\033[3m"))
        if style.get("underline", False):
            ansi_codes.append(getattr(config, "UNDERLINE", "\033[4m"))

        return "".join(ansi_codes) if ansi_codes else ""

    def _get_rgb_color(self, color_name: str, background: bool = False) -> str:
        """Get RGB color code directly from config (RGB true color only)."""
        if not _CONFIG_AVAILABLE:
            # Fallback to basic ANSI colors when config is not available
            color_map = {
                "red": ("255", "0", "0"),
                "green": ("0", "255", "0"),
                "blue": ("0", "0", "255"),
                "yellow": ("255", "255", "0"),
                "magenta": ("255", "0", "255"),
                "cyan": ("0", "255", "255"),
                "white": ("255", "255", "255"),
                "black": ("0", "0", "0"),
            }

            r, g, b = color_map.get(color_name.lower(), ("255", "255", "255"))
            color_type = "48" if background else "38"
            return f"\033[{color_type};2;{r};{g};{b}m"

        # Only support RGB true color from config
        color_name_lower = color_name.lower()

        # Handle special cases
        if color_name_lower == "auto":
            return ""  # This is handled separately

        # Check if color is a hex code override first
        if color_name.startswith("#"):
            # Hex color override - use directly
            hex_color = self._parse_hex_color(color_name)
            if hex_color:
                r, g, b = hex_color['r'], hex_color['g'], hex_color['b']

                # Apply opacity if this is a foreground color
                if not background and self.opacity < 100:
                    r, g, b = _apply_opacity_to_rgb(r, g, b, self.opacity)

                color_type = "48" if background else "38"
                config_color = f"\033[{color_type};2;{r};{g};{b}m"
                cache_key = f"{color_name.lower()}_{background}_{self.opacity}"
                _color_cache[cache_key] = config_color
                return config_color

        # Get RGB color directly from config with caching
        cache_key = f"{color_name.lower()}_{background}_{self.opacity}"
        if cache_key in _color_cache:
            return _color_cache[cache_key]

        # Get the color from config - themes should provide RGB values
        config_color = ""

        # For RGB color names like "bright_red", we need to handle multiple formats
        if color_name_lower.startswith("bright_"):
            base_color = color_name_lower[7:]  # Remove "bright_" prefix
            base_upper = base_color.upper()

            # Try different bright color naming conventions
            possible_names = [
                f"BRIGHT_{base_upper}",     # BRIGHT_RED
                f"Bright{base_upper}",      # BrightRed
                f"Bright{base_color.title()}",  # BrightRed
            ]
        else:
            # Regular colors
            base_upper = color_name_lower.upper()
            possible_names = [
                base_upper,                    # RED
                color_name_lower.title(),      # Red
            ]

        for name in possible_names:
            if hasattr(config, name):
                config_color = getattr(config, name)
                break

        # If still not found, try base colors
        if not config_color:
            base_color_names = ["RED", "GREEN", "BLUE", "YELLOW", "MAGENTA", "CYAN", "WHITE", "BLACK"]
            for base in base_color_names:
                if hasattr(config, base):
                    config_color = getattr(config, base)
                    break

        # If no config color found, use a default RGB color
        if not config_color:
            default_colors = {
                "red": (255, 0, 0),
                "green": (0, 255, 0),
                "blue": (0, 0, 255),
                "yellow": (255, 255, 0),
                "magenta": (255, 0, 255),
                "cyan": (0, 255, 255),
                "white": (255, 255, 255),
                "black": (0, 0, 0),
            }

            r, g, b = default_colors.get(color_name_lower, (255, 255, 255))

            # Apply opacity if this is a foreground color
            if not background and self.opacity < 100:
                r, g, b = _apply_opacity_to_rgb(r, g, b, self.opacity)

            color_type = "48" if background else "38"
            config_color = f"\033[{color_type};2;{r};{g};{b}m"
        else:
            # Convert foreground config color to background if needed
            if background:
                try:
                    from aicoder.utils import to_background
                    config_color = to_background(config_color)
                except ImportError:
                    # Fallback: convert RGB foreground to background format
                    import re
                    # Look for RGB pattern: \033[38;2;R;G;Bm
                    match = re.search(r'\033\[38;2;(\d+);(\d+);(\d+)m', config_color)
                    if match:
                        r, g, b = match.groups()
                        config_color = f"\033[48;2;{r};{g};{b}m"
                    else:
                        # Default to dark gray background
                        config_color = "\033[48;2;64;64;64m"
            else:
                # This is a foreground color, extract RGB and apply opacity if needed
                if self.opacity < 100:
                    rgb_values = _parse_rgb_from_ansi(config_color)
                    if rgb_values:
                        r, g, b = rgb_values
                        r, g, b = _apply_opacity_to_rgb(r, g, b, self.opacity)
                        config_color = f"\033[38;2;{r};{g};{b}m"

        # Cache and return the result
        _color_cache[cache_key] = config_color
        return config_color

    def _get_auto_foreground(self, bg_color: str) -> str:
        """Get automatic foreground color (black or white) based on background luminance.

        Args:
            bg_color: Background color string (RGB format preferred)

        Returns:
            "white" or "black" based on luminance calculation
        """
        # Check cache first
        cache_key = bg_color.lower()
        if cache_key in _auto_foreground_cache:
            return _auto_foreground_cache[cache_key]

        # Try to extract RGB values from various color formats
        rgb_values = None

        # Check RGB extraction cache first
        if cache_key in _rgb_extraction_cache:
            rgb_values = _rgb_extraction_cache[cache_key]
        else:
            # Try hex format first
            if bg_color.startswith("#"):
                rgb_values = self._parse_hex_color(bg_color)

            # Try RGB escape sequence format (theme colors)
            if not rgb_values:
                import re
                # Look for RGB pattern: \033[48;2;R;G;Bm (background)
                match = re.search(r'\033\[48;2;(\d+);(\d+);(\d+)m', bg_color)
                if match:
                    r, g, b = map(int, match.groups())
                    rgb_values = {'r': r, 'g': g, 'b': b}
                else:
                    # Try foreground RGB format: \033[38;2;R;G;Bm
                    match = re.search(r'\033\[38;2;(\d+);(\d+);(\d+)m', bg_color)
                    if match:
                        r, g, b = map(int, match.groups())
                        rgb_values = {'r': r, 'g': g, 'b': b}

            # Cache the RGB extraction result
            if rgb_values:
                _rgb_extraction_cache[cache_key] = rgb_values

        # Calculate luminance if we have RGB values
        result = "black"  # Default fallback
        if rgb_values:
            r, g, b = rgb_values['r'], rgb_values['g'], rgb_values['b']

            # Check luminance cache first
            luminance_key = f"{r},{g},{b}"
            if luminance_key in _luminance_cache:
                luminance = _luminance_cache[luminance_key]
            else:
                # Calculate luminance using standard formula
                luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
                _luminance_cache[luminance_key] = luminance

            result = "black" if luminance > 0.5 else "white"

        # Cache the final result
        _auto_foreground_cache[cache_key] = result
        return result

    def _parse_hex_color(self, hex_color: str) -> dict:
        """Parse hex color string like #FFAFFF into RGB components.

        Args:
            hex_color: Hex color string (e.g., "#FFAFFF", "#FFF")

        Returns:
            dict with 'r', 'g', 'b' keys, or None if invalid
        """
        try:
            # Remove # prefix
            hex_color = hex_color.lstrip('#')

            # Handle 3-digit hex codes by expanding them
            if len(hex_color) == 3:
                hex_color = ''.join([c * 2 for c in hex_color])

            # Must be 6 digits
            if len(hex_color) != 6:
                return None

            # Parse RGB values
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)

            return {'r': r, 'g': g, 'b': b}
        except (ValueError, IndexError):
            return None

    def _calculate_contrast_color(self, background_color: str) -> str:
        """Calculate optimal foreground color for contrast (white/black based on luminance)."""
        if _CONFIG_AVAILABLE:
            try:
                from aicoder.utils import _get_contrast_color
                # Use the utils function that calculates luminance and returns appropriate color
                contrast_color = _get_contrast_color(background_color)

                # The utils function returns actual config color codes, so we just return
                # simple "white" or "black" to indicate which one to use
                if contrast_color == (config.BRIGHT_WHITE if hasattr(config, 'BRIGHT_WHITE') else "\033[97m"):
                    return "white"
                elif contrast_color == (config.WHITE if hasattr(config, 'WHITE') else "\033[37m"):
                    return "white"
                else:
                    return "black"
            except ImportError:
                pass

        # Fallback: use luminance calculation for RGB
        import re
        # Look for RGB pattern: \033[48;2;R;G;Bm (background)
        match = re.search(r'\033\[48;2;(\d+);(\d+);(\d+)m', background_color)
        if match:
            r, g, b = map(int, match.groups())
            # Calculate luminance using standard formula
            luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
            return "black" if luminance > 0.5 else "white"

        # Default fallback
        return "white"

    def apply_to_text(self, text: str) -> str:
        """Apply this rule's highlighting to text."""
        # Strip ANSI codes for regex matching - users create patterns based on visible text
        import re
        ansi_escape = re.compile(r'\033\[[0-9;]*m')
        visible_text = ansi_escape.sub('', text)
        
        # Check if the pattern matches the visible text
        if not self.compiled_pattern.search(visible_text):
            return text

        # If we get here, the pattern matched, so we need to apply styling/opacity to matches only
        # Check if we need to apply opacity
        has_foreground = "foreground" in self.style and self.style.get("foreground") is not None
        has_background = "background" in self.style and self.style.get("background") is not None
        needs_opacity_processing = self.opacity < 100 and not has_foreground and not has_background

        if not self.style_string and not needs_opacity_processing:
            return text

        # Function to apply styling and opacity only to matched portions
        def apply_style(match):
            matched_text = match.group()
            
            # Apply opacity to RGB codes in the matched text if needed
            if needs_opacity_processing:
                # Apply opacity to existing RGB colors in the matched text only
                rgb_pattern = r'\033\[(38|48);2;(\d+);(\d+);(\d+)m'
                rgb_matches = list(re.finditer(rgb_pattern, matched_text))
                
                # Process from right to left to avoid position shifting
                result = matched_text
                for rgb_match in reversed(rgb_matches):
                    start_pos, end_pos = rgb_match.span()
                    color_type = rgb_match.group(1)  # 38 for foreground, 48 for background
                    r = int(rgb_match.group(2))
                    g = int(rgb_match.group(3))
                    b = int(rgb_match.group(4))
                    
                    # Apply opacity to the RGB values
                    new_r = int(r * (self.opacity / 100))
                    new_g = int(g * (self.opacity / 100))
                    new_b = int(b * (self.opacity / 100))
                    
                    new_code = f"\033[{color_type};2;{new_r};{new_g};{new_b}m"
                    
                    # Replace this specific occurrence
                    result = result[:start_pos] + new_code + result[end_pos:]
                
                # Apply any formatting (bold, italic, underline) that may be in the style string
                if self.style_string:
                    return f"{self.style_string}{result}{config.RESET}"
                else:
                    return result
            else:
                # Apply regular styling (foreground/background colors, formatting) to the matched text
                return f"{self.style_string}{matched_text}{config.RESET}"

        # Apply opacity to ALL RGB codes in the entire text if opacity processing is needed
        if needs_opacity_processing:
            # Apply opacity to existing RGB colors in the entire text
            rgb_pattern = r'\033\[(38|48);2;(\d+);(\d+);(\d+)m'
            rgb_matches = list(re.finditer(rgb_pattern, text))

            # Process from right to left to avoid position shifting
            result = text
            for rgb_match in reversed(rgb_matches):
                start_pos, end_pos = rgb_match.span()
                color_type = rgb_match.group(1)  # 38 for foreground, 48 for background
                r = int(rgb_match.group(2))
                g = int(rgb_match.group(3))
                b = int(rgb_match.group(4))

                # Apply opacity to the RGB values
                new_r = int(r * (self.opacity / 100))
                new_g = int(g * (self.opacity / 100))
                new_b = int(b * (self.opacity / 100))

                new_code = f"\033[{color_type};2;{new_r};{new_g};{new_b}m"

                # Replace this specific occurrence
                result = result[:start_pos] + new_code + result[end_pos:]

            return result

        # Replace all matches with styled version (opacity applied to matched portions only)
        return self.compiled_pattern.sub(apply_style, text)

    def to_dict(self) -> Dict[str, Any]:
        """Convert rule to dictionary for serialization."""
        # Include opacity in the serialized style
        style_with_opacity = self.style.copy()
        style_with_opacity['opacity'] = self.opacity
        return {
            "name": self.name,
            "pattern": self.pattern_str,
            "style": style_with_opacity,
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


def load_legacy_dimmed_rules() -> List[Dict[str, Any]]:
    """Load rules from existing dimmed plugin configuration (converted to use opacity)."""
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
                                "style": {"opacity": 70},  # Use opacity instead of dim
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

    # 4. Import legacy dimmed rules with low priority (always add, but with low priority)
    dimmed_rules = load_legacy_dimmed_rules()
    if dimmed_rules:
        all_rules.extend(dimmed_rules)
        debug = os.environ.get("DEBUG", "0") == "1"
        if debug:
            print(f"Imported {len(dimmed_rules)} rules from dimmed plugin")

    return all_rules


def reload_highlighter_rules():
    """Reload rules from config files."""
    global _highlighter_rules
    rule_dicts = load_all_rules()
    _highlighter_rules = [HighlightRule(**rule_dict) for rule_dict in rule_dicts]
    print(f"[✓] Reloaded {len(_highlighter_rules)} rules from config files")


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

    # Monkey patch clear_background_cache to also clear highlighter cache when theme changes
    if _CONFIG_AVAILABLE:
        try:
            from aicoder import utils
            utils.clear_background_cache = _clear_all_background_caches
        except ImportError:
            pass

    # Show startup info in debug mode
    debug = os.environ.get("DEBUG", "0") == "1"
    if debug:
        status = "enabled" if _highlighter_enabled else "disabled"
        rules = get_current_rules()
        print(f"Highlighter plugin loaded ({status})")
        print(f"   Rules ({len(rules)}): {', '.join([r['name'] for r in rules])}")
        print(f"   Project config: {_project_config_path}")
        print(f"   Global config: {_global_config_path}")


def handle_highlighter_command(aicoder_instance, args):
    """Handle the /highlight command - currently only supports reload."""
    if not args or args[0].lower() == "reload":
        reload_highlighter_rules()
        return False, False
    else:
        print("\n[X] Unknown subcommand. Only 'reload' is supported.")
        print("Use '/highlight reload' to reload rules from config files")
        return False, False


def on_aicoder_init(aicoder_instance):
    """Register the /highlight command when AICoder is initialized."""
    # Register the highlight command handler
    aicoder_instance.command_handlers["/highlight"] = lambda args: handle_highlighter_command(
        aicoder_instance, args
    )


# Initialize plugin
initialize_highlighter_plugin()
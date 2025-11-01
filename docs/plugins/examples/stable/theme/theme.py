"""
Theme Customization Plugin

This plugin provides a collection of famous terminal themes with high contrast
and readability focus. All themes are optimized for clear text visibility.

Features:
- High contrast themes for better readability
- Popular terminal themes (One Dark, Nord, etc.)
- Accessibility-focused themes
- True color and 256-color support
- Interactive theme switching with /theme command
- Theme navigation (next, previous, random)
- Theme listing and help functionality
- Only shows startup info in debug mode

Commands:
- /theme                    - Show current theme
- /theme list              - List all available themes
- /theme <name>            - Apply specified theme
- /theme random            - Apply a random theme
- /theme next              - Apply next theme in list
- /theme previous          - Apply previous theme in list
- /theme help              - Show command help
"""

import os
import importlib
import pkgutil
import random

# Define high-contrast, readable themes
THEMES = {
    # Default theme (original colors)
    "default": {
        "RED": "\033[31m",
        "GREEN": "\033[32m",
        "YELLOW": "\033[33m",
        "BLUE": "\033[34m",
        "MAGENTA": "\033[35m",
        "CYAN": "\033[36m",
        "WHITE": "\033[37m",
        "RESET": "\033[0m",
        # Bright variants
        "BRIGHT_RED": "\033[91m",
        "BRIGHT_GREEN": "\033[92m",
        "BRIGHT_YELLOW": "\033[93m",
        "BRIGHT_BLUE": "\033[94m",
        "BRIGHT_MAGENTA": "\033[95m",
        "BRIGHT_CYAN": "\033[96m",
        "BRIGHT_WHITE": "\033[97m",
    },
    "luna": {
        "RED": "\033[38;5;219m",
        "GREEN": "\033[38;5;191m",
        "YELLOW": "\033[38;5;220m",
        "BLUE": "\033[38;5;159m",
        "MAGENTA": "\033[38;5;219m",
        "CYAN": "\033[38;5;159m",
        "WHITE": "\033[38;5;255m",
        "RESET": "\033[0m",
        # Bright variants (more intense versions)
        "BRIGHT_RED": "\033[38;5;203m",
        "BRIGHT_GREEN": "\033[38;5;194m",
        "BRIGHT_YELLOW": "\033[38;5;226m",
        "BRIGHT_BLUE": "\033[38;5;153m",
        "BRIGHT_MAGENTA": "\033[38;5;207m",
        "BRIGHT_CYAN": "\033[38;5;159m",
        "BRIGHT_WHITE": "\033[38;5;231m",
    },
    # One Dark Pro (high contrast variant)
    "one-dark-pro": {
        "RED": "\033[38;2;255;50;50m",  # Vibrant red
        "GREEN": "\033[38;2;80;250;123m",  # Bright green
        "YELLOW": "\033[38;2;255;220;95m",  # Bright yellow
        "BLUE": "\033[38;2;97;175;239m",  # Bright blue
        "MAGENTA": "\033[38;2;198;120;221m",  # Purple
        "CYAN": "\033[38;2;139;233;253m",  # Bright cyan
        "WHITE": "\033[38;2;197;200;198m",  # Light gray
        "RESET": "\033[0m",
        # Bright variants (maximum intensity)
        "BRIGHT_RED": "\033[38;2;255;100;100m",  # Even more vibrant
        "BRIGHT_GREEN": "\033[38;2;100;255;150m",  # Even brighter
        "BRIGHT_YELLOW": "\033[38;2;255;240;120m",  # Even brighter
        "BRIGHT_BLUE": "\033[38;2;120;200;255m",  # Even brighter
        "BRIGHT_MAGENTA": "\033[38;2;220;150;240m",  # Even brighter
        "BRIGHT_CYAN": "\033[38;2;160;240;255m",  # Even brighter
        "BRIGHT_WHITE": "\033[38;2;220;220;220m",  # Even lighter
    },
    # Nord (polar night and snow storm)
    "nord": {
        "RED": "\033[38;2;191;97;106m",  # Nord11 - Red
        "GREEN": "\033[38;2;163;190;140m",  # Nord14 - Green
        "YELLOW": "\033[38;2;235;203;139m",  # Nord13 - Yellow
        "BLUE": "\033[38;2;129;161;193m",  # Nord9 - Blue
        "MAGENTA": "\033[38;2;180;142;173m",  # Nord15 - Purple
        "CYAN": "\033[38;2;143;188;187m",  # Nord8 - Frost
        "WHITE": "\033[38;2;216;222;233m",  # Nord6 - Snow storm
        "RESET": "\033[0m",
        # Bright variants (enhanced Nord colors)
        "BRIGHT_RED": "\033[38;2;215;110;120m",  # Brighter red
        "BRIGHT_GREEN": "\033[38;2;180;200;150m",  # Brighter green
        "BRIGHT_YELLOW": "\033[38;2;245;215;150m",  # Brighter yellow
        "BRIGHT_BLUE": "\033[38;2;150;180;210m",  # Brighter blue
        "BRIGHT_MAGENTA": "\033[38;2;200;160;185m",  # Brighter purple
        "BRIGHT_CYAN": "\033[38;2;160;200;200m",  # Brighter frost
        "BRIGHT_WHITE": "\033[38;2;230;235;240m",  # Brighter snow
    },
    # Solarized Dark (high contrast variant)
    "solarized-dark": {
        "RED": "\033[38;2;220;50;47m",  # Base01 red
        "GREEN": "\033[38;2;133;153;0m",  # Base01 green
        "YELLOW": "\033[38;2;181;137;0m",  # Base01 yellow
        "BLUE": "\033[38;2;38;139;210m",  # Base01 blue
        "MAGENTA": "\033[38;2;211;54;130m",  # Base01 magenta
        "CYAN": "\033[38;2;42;161;152m",  # Base01 cyan
        "WHITE": "\033[38;2;253;246;227m",  # Base2 white
        "RESET": "\033[0m",
        # Bright variants (solarized accents)
        "BRIGHT_RED": "\033[38;2;240;80;70m",  # Brighter red
        "BRIGHT_GREEN": "\033[38;2;150;180;50m",  # Brighter green
        "BRIGHT_YELLOW": "\033[38;2;200;160;50m",  # Brighter yellow
        "BRIGHT_BLUE": "\033[38;2;60;170;230m",  # Brighter blue
        "BRIGHT_MAGENTA": "\033[38;2;230;80;150m",  # Brighter magenta
        "BRIGHT_CYAN": "\033[38;2;60;190;180m",  # Brighter cyan
        "BRIGHT_WHITE": "\033[38;2;255;250;240m",  # Brighter white
    },
    # Gruvbox Dark (high contrast)
    "gruvbox-dark": {
        "RED": "\033[38;2;251;73;52m",  # Bright red
        "GREEN": "\033[38;2;184;187;38m",  # Bright green
        "YELLOW": "\033[38;2;250;189;47m",  # Bright yellow
        "BLUE": "\033[38;2;131;165;152m",  # Bright blue
        "MAGENTA": "\033[38;2;244;122;158m",  # Bright purple
        "CYAN": "\033[38;2;142;192;124m",  # Bright aqua
        "WHITE": "\033[38;2;235;219;178m",  # Light beige
        "RESET": "\033[0m",
        # Bright variants (maximum gruvbox intensity)
        "BRIGHT_RED": "\033[38;2;255;100;80m",  # Brighter red
        "BRIGHT_GREEN": "\033[38;2;200;205;60m",  # Brighter green
        "BRIGHT_YELLOW": "\033[38;2;255;210;80m",  # Brighter yellow
        "BRIGHT_BLUE": "\033[38;2;150;185;170m",  # Brighter blue
        "BRIGHT_MAGENTA": "\033[38;2;255;150;180m",  # Brighter purple
        "BRIGHT_CYAN": "\033[38;2;170;210;150m",  # Brighter aqua
        "BRIGHT_WHITE": "\033[38;2;245;230;190m",  # Brighter beige
    },
    # Dracula (high contrast)
    "dracula": {
        "RED": "\033[38;2;255;85;85m",  # Pink
        "GREEN": "\033[38;2;80;250;123m",  # Green
        "YELLOW": "\033[38;2;255;184;108m",  # Orange
        "BLUE": "\033[38;2;139;233;253m",  # Cyan
        "MAGENTA": "\033[38;2;255;121;198m",  # Pink
        "CYAN": "\033[38;2;139;233;253m",  # Cyan
        "WHITE": "\033[38;2;248;248;242m",  # White
        "RESET": "\033[0m",
        # Bright variants (maximum dracula intensity)
        "BRIGHT_RED": "\033[38;2;255;120;120m",  # Brighter pink
        "BRIGHT_GREEN": "\033[38;2;100;255;150m",  # Brighter green
        "BRIGHT_YELLOW": "\033[38;2;255;200;140m",  # Brighter orange
        "BRIGHT_BLUE": "\033[38;2;160;240;255m",  # Brighter cyan
        "BRIGHT_MAGENTA": "\033[38;2;255;150;220m",  # Brighter pink
        "BRIGHT_CYAN": "\033[38;2;160;240;255m",  # Brighter cyan
        "BRIGHT_WHITE": "\033[38;2;255;255;255m",  # Pure white
    },
    # Monokai (high contrast)
    "monokai": {
        "RED": "\033[38;2;249;38;114m",  # Pink
        "GREEN": "\033[38;2;166;226;46m",  # Green
        "YELLOW": "\033[38;2;253;151;31m",  # Orange
        "BLUE": "\033[38;2;102;217;239m",  # Blue
        "MAGENTA": "\033[38;2;249;38;114m",  # Pink
        "CYAN": "\033[38;2;102;217;239m",  # Blue
        "WHITE": "\033[38;2;230;230;230m",  # Light gray
        "RESET": "\033[0m",
        # Bright variants (maximum monokai intensity)
        "BRIGHT_RED": "\033[38;2;255;60;140m",  # Brighter pink
        "BRIGHT_GREEN": "\033[38;2;180;240;60m",  # Brighter green
        "BRIGHT_YELLOW": "\033[38;2;255;170;50m",  # Brighter orange
        "BRIGHT_BLUE": "\033[38;2;120;230;255m",  # Brighter blue
        "BRIGHT_MAGENTA": "\033[38;2;255;60;140m",  # Brighter pink
        "BRIGHT_CYAN": "\033[38;2;120;230;255m",  # Brighter blue
        "BRIGHT_WHITE": "\033[38;2;245;245;245m",  # Brighter gray
    },
    # Catppuccin Mocha (high contrast)
    "catppuccin-mocha": {
        "RED": "\033[38;2;243;139;168m",  # Red
        "GREEN": "\033[38;2;166;227;161m",  # Green
        "YELLOW": "\033[38;2;249;226;175m",  # Yellow
        "BLUE": "\033[38;2;137;180;250m",  # Blue
        "MAGENTA": "\033[38;2;245;194;231m",  # Pink
        "CYAN": "\033[38;2;148;226;213m",  # Teal
        "WHITE": "\033[38;2;205;214;244m",  # Text
        "RESET": "\033[0m",
        # Bright variants (maximum catppuccin intensity)
        "BRIGHT_RED": "\033[38;2;255;160;190m",  # Brighter red
        "BRIGHT_GREEN": "\033[38;2;180;240;180m",  # Brighter green
        "BRIGHT_YELLOW": "\033[38;2;255;240;200m",  # Brighter yellow
        "BRIGHT_BLUE": "\033[38;2;160;200;255m",  # Brighter blue
        "BRIGHT_MAGENTA": "\033[38;2;255;210;240m",  # Brighter pink
        "BRIGHT_CYAN": "\033[38;2;180;240;230m",  # Brighter teal
        "BRIGHT_WHITE": "\033[38;2;220;230;255m",  # Brighter text
    },
    # Tokyo Night (high contrast)
    "tokyo-night": {
        "RED": "\033[38;2;255;117;127m",  # Red
        "GREEN": "\033[38;2;158;206;106m",  # Green
        "YELLOW": "\033[38;2;224;175;104m",  # Yellow
        "BLUE": "\033[38;2;122;162;247m",  # Blue
        "MAGENTA": "\033[38;2;187;154;247m",  # Purple
        "CYAN": "\033[38;2;137;180;250m",  # Cyan
        "WHITE": "\033[38;2;229;233;237m",  # White
        "RESET": "\033[0m",
    },
    # Kanagawa (high contrast)
    "kanagawa": {
        "RED": "\033[38;2;234;118;118m",  # Autumn Red
        "GREEN": "\033[38;2;166;209;137m",  # Autumn Green
        "YELLOW": "\033[38;2;229;191;115m",  # Autumn Yellow
        "BLUE": "\033[38;2;128;183;217m",  # Autumn Blue
        "MAGENTA": "\033[38;2;198;120;221m",  # Autumn Purple
        "CYAN": "\033[38;2;142;192;124m",  # Autumn Green
        "WHITE": "\033[38;2;229;200;169m",  # Wave White
        "RESET": "\033[0m",
    },
    # Rosé Pine (high contrast)
    "rose-pine": {
        "RED": "\033[38;2;235;111;146m",  # Love
        "GREEN": "\033[38;2;49;188;138m",  # Pine
        "YELLOW": "\033[38;2;246;193;119m",  # Gold
        "BLUE": "\033[38;2;156;207;216m",  # Foam
        "MAGENTA": "\033[38;2;235;111;146m",  # Love
        "CYAN": "\033[38;2;156;207;216m",  # Foam
        "WHITE": "\033[38;2;224;215;198m",  # Text
        "RESET": "\033[0m",
    },
    # Everforest (high contrast)
    "everforest": {
        "RED": "\033[38;2;248;124;116m",  # Red
        "GREEN": "\033[38;2;184;198;137m",  # Green
        "YELLOW": "\033[38;2;245;194;113m",  # Yellow
        "BLUE": "\033[38;2;124;164;170m",  # Blue
        "MAGENTA": "\033[38;2;215;148;188m",  # Purple
        "CYAN": "\033[38;2;124;164;170m",  # Blue
        "WHITE": "\033[38;2;220;206;186m",  # Text
        "RESET": "\033[0m",
    },
    # Ayu Dark (high contrast)
    "ayu-dark": {
        "RED": "\033[38;2;255;93;93m",  # Red
        "GREEN": "\033[38;2;169;235;169m",  # Green
        "YELLOW": "\033[38;2;255;221;118m",  # Yellow
        "BLUE": "\033[38;2;102;217;239m",  # Blue
        "MAGENTA": "\033[38;2;255;93;93m",  # Red
        "CYAN": "\033[38;2;102;217;239m",  # Blue
        "WHITE": "\033[38;2;197;207;206m",  # White
        "RESET": "\033[0m",
    },
    # Material Theme (high contrast)
    "material": {
        "RED": "\033[38;2;240;113;120m",  # Red
        "GREEN": "\033[38;2;195;232;141m",  # Green
        "YELLOW": "\033[38;2;255;203;107m",  # Yellow
        "BLUE": "\033[38;2;130;170;255m",  # Blue
        "MAGENTA": "\033[38;2;240;113;120m",  # Red
        "CYAN": "\033[38;2;130;170;255m",  # Blue
        "WHITE": "\033[38;2;255;255;255m",  # White
        "RESET": "\033[0m",
        # Bright variants (maximum material intensity)
        "BRIGHT_RED": "\033[38;2;255;140;150m",  # Brighter red
        "BRIGHT_GREEN": "\033[38;2;210;245;170m",  # Brighter green
        "BRIGHT_YELLOW": "\033[38;2;255;220;140m",  # Brighter yellow
        "BRIGHT_BLUE": "\033[38;2;150;200;255m",  # Brighter blue
        "BRIGHT_MAGENTA": "\033[38;2;255;140;150m",  # Brighter red
        "BRIGHT_CYAN": "\033[38;2;150;200;255m",  # Brighter blue
        "BRIGHT_WHITE": "\033[38;2;255;255;255m",  # Pure white
    },
    # Github Dark (high contrast)
    "github-dark": {
        "RED": "\033[38;2;255;115;135m",  # Red
        "GREEN": "\033[38;2;115;255;140m",  # Green
        "YELLOW": "\033[38;2;255;220;100m",  # Yellow
        "BLUE": "\033[38;2;120;185;255m",  # Blue
        "MAGENTA": "\033[38;2;255;115;135m",  # Red
        "CYAN": "\033[38;2;120;185;255m",  # Blue
        "WHITE": "\033[38;2;240;246;252m",  # White
        "RESET": "\033[0m",
        # Bright variants (maximum github intensity)
        "BRIGHT_RED": "\033[38;2;255;140;160m",  # Brighter red
        "BRIGHT_GREEN": "\033[38;2;140;255;170m",  # Brighter green
        "BRIGHT_YELLOW": "\033[38;2;255;240;130m",  # Brighter yellow
        "BRIGHT_BLUE": "\033[38;2;150;210;255m",  # Brighter blue
        "BRIGHT_MAGENTA": "\033[38;2;255;140;160m",  # Brighter red
        "BRIGHT_CYAN": "\033[38;2;150;210;255m",  # Brighter blue
        "BRIGHT_WHITE": "\033[38;2;255;255;255m",  # Pure white
    },
    # High Visibility (extremely high contrast)
    "high-visibility": {
        "RED": "\033[38;2;255;0;0m",  # Pure red
        "GREEN": "\033[38;2;0;255;0m",  # Pure green
        "YELLOW": "\033[38;2;255;255;0m",  # Pure yellow
        "BLUE": "\033[38;2;0;0;255m",  # Pure blue
        "MAGENTA": "\033[38;2;255;0;255m",  # Pure magenta
        "CYAN": "\033[38;2;0;255;255m",  # Pure cyan
        "WHITE": "\033[38;2;255;255;255m",  # Pure white
        "RESET": "\033[0m",
        # Bright variants (already maximum intensity - use same)
        "BRIGHT_RED": "\033[38;2;255;0;0m",  # Pure red (can't get brighter)
        "BRIGHT_GREEN": "\033[38;2;0;255;0m",  # Pure green (can't get brighter)
        "BRIGHT_YELLOW": "\033[38;2;255;255;0m",  # Pure yellow (can't get brighter)
        "BRIGHT_BLUE": "\033[38;2;0;0;255m",  # Pure blue (can't get brighter)
        "BRIGHT_MAGENTA": "\033[38;2;255;0;255m",  # Pure magenta (can't get brighter)
        "BRIGHT_CYAN": "\033[38;2;0;255;255m",  # Pure cyan (can't get brighter)
        "BRIGHT_WHITE": "\033[38;2;255;255;255m",  # Pure white (can't get brighter)
    },
    # 256-color versions for compatibility
    "one-dark-256": {
        "RED": "\033[38;5;197m",
        "GREEN": "\033[38;5;154m",
        "YELLOW": "\033[38;5;221m",
        "BLUE": "\033[38;5;117m",
        "MAGENTA": "\033[38;5;207m",
        "CYAN": "\033[38;5;117m",
        "WHITE": "\033[38;5;255m",
        "RESET": "\033[0m",
        # Bright variants using 256-color palette
        "BRIGHT_RED": "\033[38;5;203m",
        "BRIGHT_GREEN": "\033[38;5;156m",
        "BRIGHT_YELLOW": "\033[38;5;226m",
        "BRIGHT_BLUE": "\033[38;5;153m",
        "BRIGHT_MAGENTA": "\033[38;5;207m",
        "BRIGHT_CYAN": "\033[38;5;159m",
        "BRIGHT_WHITE": "\033[38;5;231m",
    },
    "nord-256": {
        "RED": "\033[38;5;167m",
        "GREEN": "\033[38;5;150m",
        "YELLOW": "\033[38;5;179m",
        "BLUE": "\033[38;5;110m",
        "MAGENTA": "\033[38;5;175m",
        "CYAN": "\033[38;5;108m",
        "WHITE": "\033[38;5;254m",
        "RESET": "\033[0m",
    },
}


def apply_theme(theme_name="default"):
    """Apply a theme by modifying the config module."""
    if theme_name not in THEMES:
        print(
            f"Theme '{theme_name}' not found. Available themes: {', '.join(THEMES.keys())}"
        )
        return False

    try:
        # Import the config module
        import aicoder.config as config

        # Get theme colors
        theme = THEMES[theme_name]

        # Apply all available colors to config
        for color_name, color_value in theme.items():
            setattr(config, color_name, color_value)

        # Update other modules that import these colors directly
        # _update_dependent_modules(theme)
        
        # Clear background color cache since colors changed
        try:
            from aicoder.utils import clear_background_cache
            clear_background_cache()
        except ImportError:
            pass

        print(f"[✓] Applied theme: {theme_name}")
        return True
    except Exception as e:
        print(f"[X] Failed to apply theme {theme_name}: {e}")
        return False


def _update_dependent_modules(theme):
    """Dynamically update all modules that import colors directly."""
    try:
        # Dynamically find all submodules under aicoder package
        import aicoder

        modules_to_update = []

        # Add the main package
        modules_to_update.append("aicoder")

        # Find all submodules and subpackages
        if hasattr(aicoder, "__path__"):
            for _, name, _ in pkgutil.walk_packages(
                aicoder.__path__, aicoder.__name__ + "."
            ):
                modules_to_update.append(name)

        # Update color attributes in all modules
        for module_name in modules_to_update:
            try:
                module = importlib.import_module(module_name)
                for color_name in theme.keys():
                    if hasattr(module, color_name):
                        setattr(module, color_name, theme[color_name])
            except Exception:
                # Ignore modules that can't be imported or don't have color attributes
                pass

    except Exception as e:
        print(f"[!] Warning: Some modules may not have updated colors: {e}")


def list_themes():
    """List all available themes."""
    return list(THEMES.keys())


# Auto-apply theme from environment variable
def initialize_theme_plugin():
    """Initialize the theme plugin."""
    # Check for debug mode
    debug = os.environ.get("DEBUG", "0") == "1"

    # Print startup info only in debug mode
    if debug:
        print("Theme Customization plugin loaded")
        print("   - High contrast themes for better readability")
        print("   - 15+ famous terminal themes included")
        print("   - Set AICODER_THEME environment variable for persistent themes")
        print("   - Themes: default, one-dark-pro, nord, solarized-dark,")
        print("             gruvbox-dark, dracula, monokai, catppuccin-mocha,")
        print("             tokyo-night, kanagawa, rose-pine, everforest,")
        print("             ayu-dark, material, github-dark, high-visibility")

    # Check for theme environment variable
    theme_env = os.environ.get("AICODER_THEME")
    if theme_env and theme_env in THEMES:
        apply_theme(theme_env)
        return True
    elif theme_env:
        print(
            f"[!] Theme '{theme_env}' not found. Available themes: {', '.join(list_themes())}"
        )
        return False
    return False


# Global state for theme navigation
_current_theme_index = 0


def get_current_theme():
    """Get the current applied theme name."""
    try:
        import aicoder.config as config

        # Try to determine current theme by checking if RED matches any theme
        for name, theme_colors in THEMES.items():
            if hasattr(config, "RED") and config.RED == theme_colors.get("RED"):
                return name
        return "default"  # Fallback
    except Exception:
        return "default"


def get_theme_index(theme_name):
    """Get the index of a theme in the themes list."""
    theme_list = list(THEMES.keys())
    try:
        return theme_list.index(theme_name)
    except ValueError:
        return 0


def handle_theme_command(aicoder_instance, args):
    """Handle the /theme command with various subcommands."""
    import aicoder.config as config

    if not args:
        # Show current theme
        current = get_current_theme()
        print(f"\n{config.GREEN}Current theme: {current}{config.RESET}")
        return False, False

    subcommand = args[0].lower()

    if subcommand == "list":
        # List all available themes
        theme_list = list(THEMES.keys())
        current = get_current_theme()
        print(f"\n{config.GREEN}Available themes:{config.RESET}")
        for theme_name in theme_list:
            marker = " (current)" if theme_name == current else ""
            print(f"  {theme_name}{marker}")
        return False, False

    elif subcommand == "random":
        # Apply a random theme
        theme_list = list(THEMES.keys())
        random_theme = random.choice(theme_list)
        print(f"\n{config.GREEN}Applying random theme: {random_theme}{config.RESET}")
        apply_theme(random_theme)
        return False, False

    elif subcommand == "next":
        # Apply next theme in the list
        theme_list = list(THEMES.keys())
        current = get_current_theme()
        current_index = get_theme_index(current)
        next_index = (current_index + 1) % len(theme_list)
        next_theme = theme_list[next_index]
        print(f"\n{config.GREEN}Next theme: {next_theme}{config.RESET}")
        apply_theme(next_theme)
        return False, False

    elif subcommand == "previous":
        # Apply previous theme in the list
        theme_list = list(THEMES.keys())
        current = get_current_theme()
        current_index = get_theme_index(current)
        prev_index = (current_index - 1) % len(theme_list)
        prev_theme = theme_list[prev_index]
        print(f"\n{config.GREEN}Previous theme: {prev_theme}{config.RESET}")
        apply_theme(prev_theme)
        return False, False

    elif subcommand == "help":
        # Show help
        print(f"\n{config.GREEN}Theme Command Help:{config.RESET}")
        print(
            f"  {config.CYAN}/theme{config.RESET}                    - Show current theme"
        )
        print(
            f"  {config.CYAN}/theme list{config.RESET}              - List all available themes"
        )
        print(
            f"  {config.CYAN}/theme <name>{config.RESET}            - Apply specified theme"
        )
        print(
            f"  {config.CYAN}/theme random{config.RESET}            - Apply a random theme"
        )
        print(
            f"  {config.CYAN}/theme next{config.RESET}              - Apply next theme in list"
        )
        print(
            f"  {config.CYAN}/theme previous{config.RESET}          - Apply previous theme in list"
        )
        print(f"  {config.CYAN}/theme help{config.RESET}              - Show this help")
        return False, False

    else:
        # Try to apply the specified theme
        theme_name = subcommand
        if apply_theme(theme_name):
            return False, False
        else:
            print(
                f"\n{config.RED}Theme '{theme_name}' not found. Use '/theme list' to see available themes.{config.RESET}"
            )
            return False, False


def on_aicoder_init(aicoder_instance):
    """Register the /theme command when AICoder is initialized."""
    # Register the theme command handler
    aicoder_instance.command_handlers["/theme"] = lambda args: handle_theme_command(
        aicoder_instance, args
    )


# Initialize plugin
theme_applied = initialize_theme_plugin()

# Apply default theme only if no theme was set via environment variable
if not theme_applied:
    apply_theme("default")

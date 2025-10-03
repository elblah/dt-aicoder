"""
Theme Customization Plugin

This plugin provides a collection of famous terminal themes with high contrast
and readability focus. All themes are optimized for clear text visibility.

Features:
- High contrast themes for better readability
- Popular terminal themes (One Dark, Nord, etc.)
- Accessibility-focused themes
- True color and 256-color support
- Only shows startup info in debug mode
"""

import os
import importlib
import pkgutil

# Define high-contrast, readable themes
THEMES = {
    # Default theme (original colors)
    "default": {
        "RED": "\033[31m",
        "GREEN": "\033[32m",
        "YELLOW": "\033[33m",
        "BLUE": "\033[34m",
        "RESET": "\033[0m",
    },
    "luna": {
        "RED": "\033[38;5;219m",
        "GREEN": "\033[38;5;191m",
        "YELLOW": "\033[38;5;220m",
        "BLUE": "\033[38;5;159m",
        "RESET": "\033[0m",
    },
    # One Dark Pro (high contrast variant)
    "one-dark-pro": {
        "RED": "\033[38;2;255;50;50m",  # Vibrant red
        "GREEN": "\033[38;2;80;250;123m",  # Bright green
        "YELLOW": "\033[38;2;255;220;95m",  # Bright yellow
        "BLUE": "\033[38;2;97;175;239m",  # Bright blue
        "RESET": "\033[0m",
    },
    # Nord (polar night and snow storm)
    "nord": {
        "RED": "\033[38;2;191;97;106m",  # Nord11 - Red
        "GREEN": "\033[38;2;163;190;140m",  # Nord14 - Green
        "YELLOW": "\033[38;2;235;203;139m",  # Nord13 - Yellow
        "BLUE": "\033[38;2;129;161;193m",  # Nord9 - Blue
        "RESET": "\033[0m",
    },
    # Solarized Dark (high contrast variant)
    "solarized-dark": {
        "RED": "\033[38;2;220;50;47m",  # Base01 red
        "GREEN": "\033[38;2;133;153;0m",  # Base01 green
        "YELLOW": "\033[38;2;181;137;0m",  # Base01 yellow
        "BLUE": "\033[38;2;38;139;210m",  # Base01 blue
        "RESET": "\033[0m",
    },
    # Gruvbox Dark (high contrast)
    "gruvbox-dark": {
        "RED": "\033[38;2;251;73;52m",  # Bright red
        "GREEN": "\033[38;2;184;187;38m",  # Bright green
        "YELLOW": "\033[38;2;250;189;47m",  # Bright yellow
        "BLUE": "\033[38;2;131;165;152m",  # Bright blue
        "RESET": "\033[0m",
    },
    # Dracula (high contrast)
    "dracula": {
        "RED": "\033[38;2;255;85;85m",  # Pink
        "GREEN": "\033[38;2;80;250;123m",  # Green
        "YELLOW": "\033[38;2;255;184;108m",  # Orange
        "BLUE": "\033[38;2;139;233;253m",  # Cyan
        "RESET": "\033[0m",
    },
    # Monokai (high contrast)
    "monokai": {
        "RED": "\033[38;2;249;38;114m",  # Pink
        "GREEN": "\033[38;2;166;226;46m",  # Green
        "YELLOW": "\033[38;2;253;151;31m",  # Orange
        "BLUE": "\033[38;2;102;217;239m",  # Blue
        "RESET": "\033[0m",
    },
    # Catppuccin Mocha (high contrast)
    "catppuccin-mocha": {
        "RED": "\033[38;2;243;139;168m",  # Red
        "GREEN": "\033[38;2;166;227;161m",  # Green
        "YELLOW": "\033[38;2;249;226;175m",  # Yellow
        "BLUE": "\033[38;2;137;180;250m",  # Blue
        "RESET": "\033[0m",
    },
    # Tokyo Night (high contrast)
    "tokyo-night": {
        "RED": "\033[38;2;255;117;127m",  # Red
        "GREEN": "\033[38;2;158;206;106m",  # Green
        "YELLOW": "\033[38;2;224;175;104m",  # Yellow
        "BLUE": "\033[38;2;122;162;247m",  # Blue
        "RESET": "\033[0m",
    },
    # Kanagawa (high contrast)
    "kanagawa": {
        "RED": "\033[38;2;234;118;118m",  # Autumn Red
        "GREEN": "\033[38;2;166;209;137m",  # Autumn Green
        "YELLOW": "\033[38;2;229;191;115m",  # Autumn Yellow
        "BLUE": "\033[38;2;128;183;217m",  # Autumn Blue
        "RESET": "\033[0m",
    },
    # Rosé Pine (high contrast)
    "rose-pine": {
        "RED": "\033[38;2;235;111;146m",  # Love
        "GREEN": "\033[38;2;49;188;138m",  # Pine
        "YELLOW": "\033[38;2;246;193;119m",  # Gold
        "BLUE": "\033[38;2;156;207;216m",  # Foam
        "RESET": "\033[0m",
    },
    # Everforest (high contrast)
    "everforest": {
        "RED": "\033[38;2;248;124;116m",  # Red
        "GREEN": "\033[38;2;184;198;137m",  # Green
        "YELLOW": "\033[38;2;245;194;113m",  # Yellow
        "BLUE": "\033[38;2;124;164;170m",  # Blue
        "RESET": "\033[0m",
    },
    # Ayu Dark (high contrast)
    "ayu-dark": {
        "RED": "\033[38;2;255;93;93m",  # Red
        "GREEN": "\033[38;2;169;235;169m",  # Green
        "YELLOW": "\033[38;2;255;221;118m",  # Yellow
        "BLUE": "\033[38;2;102;217;239m",  # Blue
        "RESET": "\033[0m",
    },
    # Material Theme (high contrast)
    "material": {
        "RED": "\033[38;2;240;113;120m",  # Red
        "GREEN": "\033[38;2;195;232;141m",  # Green
        "YELLOW": "\033[38;2;255;203;107m",  # Yellow
        "BLUE": "\033[38;2;130;170;255m",  # Blue
        "RESET": "\033[0m",
    },
    # Github Dark (high contrast)
    "github-dark": {
        "RED": "\033[38;2;255;115;135m",  # Red
        "GREEN": "\033[38;2;115;255;140m",  # Green
        "YELLOW": "\033[38;2;255;220;100m",  # Yellow
        "BLUE": "\033[38;2;120;185;255m",  # Blue
        "RESET": "\033[0m",
    },
    # High Visibility (extremely high contrast)
    "high-visibility": {
        "RED": "\033[38;2;255;0;0m",  # Pure red
        "GREEN": "\033[38;2;0;255;0m",  # Pure green
        "YELLOW": "\033[38;2;255;255;0m",  # Pure yellow
        "BLUE": "\033[38;2;0;0;255m",  # Pure blue
        "RESET": "\033[0m",
    },
    # 256-color versions for compatibility
    "one-dark-256": {
        "RED": "\033[38;5;197m",
        "GREEN": "\033[38;5;154m",
        "YELLOW": "\033[38;5;221m",
        "BLUE": "\033[38;5;117m",
        "RESET": "\033[0m",
    },
    "nord-256": {
        "RED": "\033[38;5;167m",
        "GREEN": "\033[38;5;150m",
        "YELLOW": "\033[38;5;179m",
        "BLUE": "\033[38;5;110m",
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

        # Apply colors to config
        config.RED = theme["RED"]
        config.GREEN = theme["GREEN"]
        config.YELLOW = theme["YELLOW"]
        config.BLUE = theme["BLUE"]
        config.RESET = theme["RESET"]

        # Update other modules that import these colors directly
        #_update_dependent_modules(theme)

        print(f"✅ Applied theme: {theme_name}")
        return True
    except Exception as e:
        print(f"❌ Failed to apply theme {theme_name}: {e}")
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
                for color_name in ["RED", "GREEN", "YELLOW", "BLUE", "RESET"]:
                    if hasattr(module, color_name):
                        setattr(module, color_name, theme[color_name])
            except Exception:
                # Ignore modules that can't be imported or don't have color attributes
                pass

    except Exception as e:
        print(f"⚠️ Warning: Some modules may not have updated colors: {e}")


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
        print("🎨 Theme Customization plugin loaded")
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
            f"⚠️ Theme '{theme_env}' not found. Available themes: {', '.join(list_themes())}"
        )
        return False
    return False


# Initialize plugin
theme_applied = initialize_theme_plugin()

# Apply default theme only if no theme was set via environment variable
if not theme_applied:
    apply_theme("default")

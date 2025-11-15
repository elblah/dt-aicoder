"""
Aspell Spell Check Plugin for AI Coder

This plugin intercepts user input and guidance text, checking spelling with aspell.
If spelling errors are found, it displays them in red with suggestions.

Features:
- Automatic spell checking of user prompts
- Spell checking of guidance text
- Red-colored error display with suggestions
- Personal dictionary support (~/.config/aicoder/aspell.pws or aspell.{lang}.pws)
- Session misspelled word tracking with /aspell list command
- Minimal performance impact (no caching)
- Graceful fallback when aspell is not available

Environment Variables:
- ASPELL_CHECK: Enable/disable spell checking (default: true)
- ASPELL_LANG: Language to use (default: en)

Personal Dictionary:
- Create ~/.config/aicoder/aspell.pws (generic) or ~/.config/aicoder/aspell.{lang}.pws (language-specific)
- Format: personal_ws-1.1 en 3\napi\nGitHub\nJSON
- File is automatically used if it exists - no need to reload

Commands:
- /aspell list   - Show all misspelled words in current session (sorted by frequency)
- /aspell clear  - Clear session misspelled word history
- /aspell edit   - Edit personal dictionary (tmux only)
- /aspell help   - Show aspell plugin help

Installation:
1. Copy this file to ~/.config/aicoder/plugins/aspell.py
2. Or use the install script: bash docs/plugins/examples/stable/aspell/install_plugin.sh
"""

import os
import re
import sys
import builtins
import subprocess
import shutil
from typing import Optional, List, Dict

# Plugin configuration
def _parse_bool_env(var_name: str, default: bool = True) -> bool:
    """Parse boolean environment variable that accepts 1/0, true/false, on/off."""
    value = os.getenv(var_name, "").lower()
    return value in {"1", "true", "on"} if value else default

# Global configuration
ASPELL_CHECK_ENABLED = _parse_bool_env("ASPELL_CHECK", True)
ASPELL_LANG = os.getenv("ASPELL_LANG", "en")

# Cache expensive operations during startup
_aspell_available = None  # Cache aspell availability
_personal_dict_file = None  # Cache personal dictionary path
_config_dir = os.path.expanduser("~/.config/aicoder")  # Cache config directory

# Store original input function
_original_input = builtins.input

# Session history of misspelled words for /aspell list command
_session_misspelled_words: Dict[str, int] = {}

# Global flag to enable/disable aspell checking (can be toggled via commands)
_aspell_enabled = True  # Global flag to enable/disable aspell checking

# Plugin version
__version__ = "1.6.0"


def _is_aspell_available() -> bool:
    """Check if aspell command is available (cached)."""
    global _aspell_available
    if _aspell_available is None:
        _aspell_available = shutil.which("aspell") is not None
    return _aspell_available


def _get_personal_dict_file() -> str:
    """Get the path to personal dictionary file (cached).

    Returns language-specific file if it exists, otherwise generic file.
    Aspell will ignore the file if it doesn't exist.
    """
    global _personal_dict_file
    if _personal_dict_file is None:
        lang_specific_file = os.path.join(_config_dir, f"aspell.{ASPELL_LANG}.pws")
        generic_file = os.path.join(_config_dir, "aspell.pws")

        # Return language-specific file if it exists, otherwise generic
        if os.path.exists(lang_specific_file):
            _personal_dict_file = lang_specific_file
        else:
            _personal_dict_file = generic_file
    
    return _personal_dict_file


_editor_cache = None

def _get_editor() -> str:
    """Get the preferred editor with fallbacks (cached)."""
    global _editor_cache
    if _editor_cache is None:
        # Try $EDITOR first
        editor = os.getenv("EDITOR")
        if editor and shutil.which(editor):
            _editor_cache = editor
            return _editor_cache

        # Try common editors in order of preference
        for fallback_editor in ["vi", "nano", "emacs", "vim"]:
            if shutil.which(fallback_editor):
                _editor_cache = fallback_editor
                return _editor_cache

        _editor_cache = "vi"  # Ultimate fallback
    
    return _editor_cache


def _extract_suggestions(aspell_output: str, word: str) -> List[str]:
    """Extract spelling suggestions from aspell output.

    Example aspell output:
    @(#) International Ispell Version 3.1.20 (but really Aspell 0.60.8.1)
    & mispelled 13 0: misspelled, dispelled, mi spelled, mi-spelled, spelled, misapplied, miscalled, respelled, misspell, misled, misplaced, misplayed, spilled
    """
    suggestions = []

    # Look for suggestion line format: & word count position: suggestion1, suggestion2, ...
    # The format is: & word count position: suggestion1, suggestion2, ...
    lines = aspell_output.strip().split('\n')
    for line in lines:
        line = line.strip()
        if line.startswith('&') and word in line:
            # Extract everything after the colon
            if ':' in line:
                suggestion_part = line.split(':', 1)[1]
                # Split by comma and clean up suggestions
                suggestions = [s.strip() for s in suggestion_part.split(",") if s.strip()]
            break

    return suggestions


def _check_spelling(text: str) -> Dict[str, List[str]]:
    """Check spelling of text using aspell and return misspelled words with suggestions.

    Args:
        text: Text to check

    Returns:
        Dictionary mapping misspelled words to lists of suggestions
    """
    if not ASPELL_CHECK_ENABLED or not _is_aspell_available() or not _aspell_enabled:
        return {}

    # Clean and prepare text for spell checking
    # Remove quotes, extra whitespace, and focus on words
    cleaned_text = text.strip().strip('"').strip("'")

    if not cleaned_text:
        return {}

    # Get personal dictionary file (always include - aspell ignores if non-existent)
    personal_dict_file = _get_personal_dict_file()

    try:
        # Build aspell command with personal dictionary
        cmd = ["aspell", "list", "-l", ASPELL_LANG, "-p", personal_dict_file]

        # Check spelling
        misspelled_result = subprocess.run(
            cmd,
            input=cleaned_text,
            text=True,
            capture_output=True,
            timeout=10
        )

        misspelled_words = []
        if misspelled_result.returncode == 0:
            misspelled_words = [w.strip() for w in misspelled_result.stdout.splitlines() if w.strip()]

        if not misspelled_words:
            # No errors found
            return {}

        # Get suggestions for each misspelled word
        errors_with_suggestions = {}

        for word in misspelled_words:
            try:
                # Build suggestion command with personal dictionary
                suggest_cmd = ["aspell", "-a", "-l", ASPELL_LANG, "-p", personal_dict_file]

                # Get suggestions for this specific word
                suggest_result = subprocess.run(
                    suggest_cmd,
                    input=word,
                    text=True,
                    capture_output=True,
                    timeout=5
                )

                if suggest_result.returncode == 0:
                    suggestions = _extract_suggestions(suggest_result.stdout, word)
                    if suggestions:
                        errors_with_suggestions[word] = suggestions[:3]  # Limit to top 3 suggestions
                    else:
                        errors_with_suggestions[word] = []

            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                # If we can't get suggestions for this word, just mark it as misspelled
                errors_with_suggestions[word] = []

        return errors_with_suggestions

    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, Exception):
        # If aspell fails, just return empty (no spell checking)
        return {}


def _display_spell_errors(errors: Dict[str, List[str]]) -> None:
    """Display spelling errors in red with suggestions, one per line."""
    if not errors:
        return

    # Get color codes from config
    try:
        import aicoder.config as config
        RED = getattr(config, 'RED', '\033[31m')
        RESET = getattr(config, 'RESET', '\033[0m')
        YELLOW = getattr(config, 'YELLOW', '\033[33m')
    except ImportError:
        # Fallback colors if config not available
        RED = '\033[31m'
        RESET = '\033[0m'
        YELLOW = '\033[33m'

    print(f"{RED}Spell check errors:{RESET}")

    for word, suggestions in errors.items():
        if suggestions:
            print(f"  {RED}{word}{RESET} → {', '.join(suggestions)}")
        else:
            print(f"  {RED}{word}{RESET}")

        # Track misspelled words in session history
        if word in _session_misspelled_words:
            _session_misspelled_words[word] += 1
        else:
            _session_misspelled_words[word] = 1

    if len(errors) > 0:
        print(f"{YELLOW}Note: These words may be misspelled.{RESET}")


def _display_session_misspelled() -> None:
    """Display all misspelled words from current session."""
    global _session_misspelled_words

    if not _session_misspelled_words:
        print("No misspelled words in this session.")
        return

    # Get color codes for output
    try:
        import aicoder.config as config
        GREEN = getattr(config, 'GREEN', '\033[32m')
        YELLOW = getattr(config, 'YELLOW', '\033[33m')
        RESET = getattr(config, 'RESET', '\033[0m')
    except ImportError:
        GREEN = '\033[32m'
        YELLOW = '\033[33m'
        RESET = '\033[0m'

    print(f"{GREEN}Misspelled words in this session:{RESET}")

    # Sort by frequency (most common first), then alphabetically
    sorted_words = sorted(_session_misspelled_words.items(),
                          key=lambda x: (-x[1], x[0].lower()))

    for word, count in sorted_words:
        if count == 1:
            print(f"  {word}")
        else:
            print(f"  {word} ({count} times)")

    total_words = sum(_session_misspelled_words.values())
    unique_words = len(_session_misspelled_words)
    print(f"\n{YELLOW}Total: {total_words} misspellings, {unique_words} unique words{RESET}")
    print(f"   Tip: Add frequently misspelled words to ~/.config/aicoder/aspell.{ASPELL_LANG}.pws")


def _spell_check_input(prompt: str = "") -> str:
    """Enhanced input function with spell checking.

    This function:
    1. Calls the original input() to get user text
    2. Skips spell checking for commands starting with /
    3. Checks the text with aspell
    4. Displays any errors in red with suggestions (one per line)
    5. Returns the original text (unchanged)
    """
    # Get user input using original input function
    user_text = _original_input(prompt)

    # Skip spell checking for commands starting with /
    if user_text.strip().startswith('/'):
        return user_text

    # Check spelling if enabled and aspell is available
    if ASPELL_CHECK_ENABLED and _is_aspell_available() and _aspell_enabled:
        errors = _check_spelling(user_text)
        if errors:
            _display_spell_errors(errors)

    return user_text


def _setup_aspell_plugin():
    """Set up the aspell spell checking plugin."""
    global _original_input

    # Only set up if spell checking is enabled and aspell is available
    if ASPELL_CHECK_ENABLED and _is_aspell_available() and _aspell_enabled:
        # Monkey patch the built-in input function
        builtins.input = _spell_check_input

        # Get personal dictionary file path for info message
        personal_dict_file = _get_personal_dict_file()
        personal_dict_basename = os.path.basename(personal_dict_file)
        generic_dict_file = os.path.join(_config_dir, "aspell.pws")

        print(f"[✓] Aspell spell check plugin loaded (language: {ASPELL_LANG})")
        print(f"    Personal dict: {personal_dict_basename} (or {os.path.basename(generic_dict_file)})")
    elif ASPELL_CHECK_ENABLED and not _is_aspell_available():
        print("[!] Aspell spell check plugin loaded but aspell command not found")
    else:
        print("[✓] Aspell spell check plugin loaded (disabled)")


def _handle_aspell_command_direct(args):
    """Handle aspell commands from AI Coder command system."""
    global _aspell_enabled
    
    if not args:
        # Just /aspell, show help
        print("Aspell plugin commands:")
        print(f"  /aspell enable  - Enable spell checking (currently: {'enabled' if _aspell_enabled else 'disabled'})")
        print(f"  /aspell disable - Disable spell checking (currently: {'enabled' if _aspell_enabled else 'disabled'})")
        print("  /aspell list   - Show all misspelled words in current session")
        print("  /aspell clear  - Clear session misspelled word history")
        print("  /aspell edit   - Edit personal dictionary (tmux only)")
        print("  /aspell help   - Show this help message")
        return False, False

    subcommand = args[0].lower()

    if subcommand == "enable":
        _aspell_enabled = True
        print("Aspell spell checking enabled.")
        return False, False
    elif subcommand == "disable":
        _aspell_enabled = False
        print("Aspell spell checking disabled.")
        return False, False
    elif subcommand == "list":
        _display_session_misspelled()
        return False, False
    elif subcommand == "clear":
        global _session_misspelled_words
        _session_misspelled_words.clear()
        print("Session misspelled words cleared.")
        return False, False
    elif subcommand == "edit":
        if not os.getenv("TMUX"):
            print("/aspell edit is only available in tmux sessions.")
            return False, False

        # Get the personal dictionary file and ensure it exists
        os.makedirs(_config_dir, exist_ok=True)

        dict_file = _get_personal_dict_file()
        # Create the file with proper header if it doesn't exist
        if not os.path.exists(dict_file):
            with open(dict_file, 'w') as f:
                f.write(f"personal_ws-1.1 {ASPELL_LANG} 0\n")

        # Get editor and run tmux command
        editor = _get_editor()
        os.system(f"tmux new-window '{editor} {dict_file}'")
        print(f"Edited {dict_file}")
        return False, False
    elif subcommand == "help":
        print("Aspell plugin commands:")
        print(f"  /aspell enable  - Enable spell checking (currently: {'enabled' if _aspell_enabled else 'disabled'})")
        print(f"  /aspell disable - Disable spell checking (currently: {'enabled' if _aspell_enabled else 'disabled'})")
        print("  /aspell list   - Show all misspelled words in current session")
        print("  /aspell clear  - Clear session misspelled word history")
        print("  /aspell edit   - Edit personal dictionary (tmux only)")
        print("  /aspell help   - Show this help message")
        return False, False
    else:
        print("Unknown aspell command. Use '/aspell help' for available commands.")
        return False, False


def _apply_edit_wrapper(aicoder_instance):
    """Apply wrapper to edit command handlers"""
    try:
        # Find the edit command handler in the registry
        if not hasattr(aicoder_instance, 'command_handlers'):
            return

        # Look for the /e command handler
        edit_handler = aicoder_instance.command_handlers.get('/e') or aicoder_instance.command_handlers.get('/edit')

        if not edit_handler:
            return

        # Store the original handler
        original_handler = edit_handler

        def wrapped_handler(args):
            # Call original handler
            result = original_handler(args)

            # Get the app instance from the closure (it should be the same)
            app = aicoder_instance

            # Get the content and spell check it
            content = getattr(app.stats, 'last_user_prompt', None)

            # Check spelling
            if ASPELL_CHECK_ENABLED and _is_aspell_available() and _aspell_enabled and content:
                errors = _check_spelling(content)
                if errors:
                    _display_spell_errors(errors)
            return result

        # Replace both /e and /edit handlers
        aicoder_instance.command_handlers['/e'] = wrapped_handler
        aicoder_instance.command_handlers['/edit'] = wrapped_handler

    except Exception:
        # Silently fail if we can't apply the wrapper
        # The plugin will still work for regular input()
        pass


def on_aicoder_init(aicoder_instance):
    """Initialize plugin when AICoder starts."""
    # Apply edit command wrapper for /e command support - this must happen here
    if aicoder_instance:
        _apply_edit_wrapper(aicoder_instance)
        
        # Register /aspell command with AI Coder's command system
        if hasattr(aicoder_instance, 'command_handlers'):
            aicoder_instance.command_handlers["/aspell"] = _handle_aspell_command_direct


# Initialize plugin on module load - but NOT the EditCommand wrapper
_setup_aspell_plugin()
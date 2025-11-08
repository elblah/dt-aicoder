"""
Configuration module for AI Coder.
"""

import os


# Mode-aware configuration helper
def _get_mode_config(env_var: str, default_value, value_type=str):
    """Get config value based on current mode, with PLAN_ prefix fallback."""
    try:
        from .planning_mode import get_planning_mode

        if get_planning_mode().is_plan_mode_active():
            value = os.environ.get(f"PLAN_{env_var}")
            if value is not None:
                if default_value is None and value == "":
                    return None
                return value_type(value)
    except (ImportError, RuntimeError):
        pass

    value = os.environ.get(env_var)
    if value is not None:
        if default_value is None and value == "":
            return None
        return value_type(value)
    return default_value


# Prompt history configuration
PROMPT_HISTORY_ENABLED = _get_mode_config("AICODER_PROMPT_HISTORY", True, bool)
PROMPT_HISTORY_MAX_SIZE = _get_mode_config("AICODER_PROMPT_HISTORY_MAX", 100, int)


# Mode-aware configuration functions
def get_api_key():
    """Get API key based on current mode."""
    return _get_mode_config("OPENAI_API_KEY", "YOUR_API_KEY")


def get_api_endpoint():
    """Get API endpoint based on current mode."""
    base_url = _get_mode_config("OPENAI_BASE_URL", "https://api.openai.com/v1")
    return base_url + "/chat/completions"


def get_api_model():
    """Get API model based on current mode."""
    return _get_mode_config("OPENAI_MODEL", "gpt-5-nano")


def get_temperature():
    """Get temperature based on current mode."""
    return _get_mode_config("TEMPERATURE", 0.0, float)


def get_top_p():
    """Get top-p based on current mode."""
    return _get_mode_config("TOP_P", 1.0, float)


def get_top_k():
    """Get top-k based on current mode."""
    return _get_mode_config("TOP_K", 0, int)


def get_repetition_penalty():
    """Get repetition penalty based on current mode."""
    return _get_mode_config("REPETITION_PENALTY", 1.0, float)


def get_max_tokens():
    """Get max tokens based on current mode."""
    return _get_mode_config("MAX_TOKENS", None, int)


def get_context_size():
    """Get context size based on current mode."""
    return _get_mode_config("CONTEXT_SIZE", 128000, int)


# --- Configuration ---
DEBUG = os.environ.get("DEBUG", "0") == "1"
HOME_DIR = os.environ.get("HOME", None)
APP_NAME = "aicoder"

# Temperature configuration (now uses function for mode-aware values)
TEMPERATURE = get_temperature()

# Top-P configuration (now uses function for mode-aware values)
TOP_P = get_top_p()

# Top-K configuration (now uses function for mode-aware values)
TOP_K = get_top_k()

# Repetition penalty configuration (now uses function for mode-aware values)
REPETITION_PENALTY = get_repetition_penalty()

# Max tokens configuration (now uses function for mode-aware values)
MAX_TOKENS = get_max_tokens()

# Streaming configuration - ENABLED BY DEFAULT
# Set DISABLE_STREAMING=1 to disable streaming mode
ENABLE_STREAMING = not (os.environ.get("DISABLE_STREAMING", "0") == "1")
# Stream log file - if set, all streaming SSE data will be logged to this file
STREAM_LOG_FILE = os.environ.get("STREAM_LOG_FILE", None)
# Streaming timeout - how long to wait without SSE data before giving up (default: 300 seconds = 5 minutes)
STREAMING_TIMEOUT = int(os.environ.get("STREAMING_TIMEOUT", "300"))
# Streaming read timeout - how long to wait for each individual line of SSE data (default: 30 seconds)
STREAMING_READ_TIMEOUT = int(os.environ.get("STREAMING_READ_TIMEOUT", "30"))

# Define some ANSI color codes
BLACK = "\033[30m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"
RESET = "\033[0m"
BOLD = "\033[1m"

# Additional color codes for markdown colorization
ITALIC = "\033[3m"
BRIGHT_GREEN = "\033[92m"
BRIGHT_RED = "\033[91m"
BRIGHT_YELLOW = "\033[93m"
BRIGHT_BLUE = "\033[94m"
BRIGHT_MAGENTA = "\033[95m"
BRIGHT_CYAN = "\033[96m"
BRIGHT_WHITE = "\033[97m"

# Tmux popup editor configuration
# Set TMUX_POPUP_EDITOR=1 to enable tmux popup editor when running inside tmux
ENABLE_TMUX_POPUP_EDITOR = os.environ.get("TMUX_POPUP_EDITOR", "0") == "1"

# Tmux popup size configuration (percentage of terminal size)
TMUX_POPUP_WIDTH_PERCENT = int(os.environ.get("TMUX_POPUP_WIDTH_PERCENT", "80"))
TMUX_POPUP_HEIGHT_PERCENT = int(os.environ.get("TMUX_POPUP_HEIGHT_PERCENT", "80"))

# Print debug status at startup
if DEBUG:
    print(f"{YELLOW}DEBUG MODE IS ON{RESET}")

# Print temperature if set as environment variable
if "TEMPERATURE" in os.environ or "PLAN_TEMPERATURE" in os.environ:
    print(f"{GREEN}*** Temperature is {TEMPERATURE}{RESET}")

# Print top_p if set as environment variable
if "TOP_P" in os.environ or "PLAN_TOP_P" in os.environ:
    print(f"{GREEN}*** Top-P is {TOP_P}{RESET}")

# Print top_k if set as environment variable
if ("TOP_K" in os.environ and TOP_K != 0) or (
    "PLAN_TOP_K" in os.environ and TOP_K != 0
):
    print(f"{GREEN}*** Top-K is {TOP_K}{RESET}")

# Print repetition_penalty if set as environment variable
if ("REPETITION_PENALTY" in os.environ and REPETITION_PENALTY != 1.0) or (
    "PLAN_REPETITION_PENALTY" in os.environ and REPETITION_PENALTY != 1.0
):
    print(f"{GREEN}*** Repetition penalty is {REPETITION_PENALTY}{RESET}")

# Print max_tokens if set as environment variable
if "MAX_TOKENS" in os.environ or "PLAN_MAX_TOKENS" in os.environ:
    print(f"{GREEN}*** Max tokens is {MAX_TOKENS}{RESET}")

# Print streaming timeout if set as environment variable
if "STREAMING_TIMEOUT" in os.environ:
    print(f"{GREEN}*** Streaming timeout is {STREAMING_TIMEOUT} seconds{RESET}")

# Print streaming read timeout if set as environment variable
if "STREAMING_READ_TIMEOUT" in os.environ:
    print(
        f"{GREEN}*** Streaming read timeout is {STREAMING_READ_TIMEOUT} seconds{RESET}"
    )

# Backward compatibility - expose as module-level variables for existing code
API_KEY = get_api_key()
API_ENDPOINT = get_api_endpoint()
API_MODEL = get_api_model()

# Compaction settings (for manual /compact command)
COMPACT_RECENT_MESSAGES = int(os.environ.get("COMPACT_RECENT_MESSAGES", "2"))

# Set COMPACT_MIN_MESSAGES: environment variable takes priority, otherwise use dynamic calculation
if "COMPACT_MIN_MESSAGES" in os.environ:
    # Use environment variable value if provided
    COMPACT_MIN_MESSAGES = int(os.environ.get("COMPACT_MIN_MESSAGES"))
else:
    # Dynamic calculation: need at least one more chat message than we keep
    # This is calculated dynamically in MessageHistory by counting only chat messages (excluding initial system messages)
    COMPACT_MIN_MESSAGES = COMPACT_RECENT_MESSAGES + 1

# Auto-compaction settings - NEW CLEAR NAMING
CONTEXT_SIZE = get_context_size()  # Mode-aware context size
CONTEXT_COMPACT_PERCENTAGE = int(
    os.environ.get("CONTEXT_COMPACT_PERCENTAGE", "0")
)  # 0 means disabled

# Calculate auto-compaction threshold based on percentage (0 percentage means disabled)
if CONTEXT_COMPACT_PERCENTAGE > 0:
    # Cap at 100% to prevent exceeding context size
    capped_percentage = min(CONTEXT_COMPACT_PERCENTAGE, 100)
    AUTO_COMPACT_THRESHOLD = int(CONTEXT_SIZE * (capped_percentage / 100.0))
else:
    AUTO_COMPACT_THRESHOLD = 0  # Disabled

# Auto-compaction enabled flag
AUTO_COMPACT_ENABLED = AUTO_COMPACT_THRESHOLD > 0

# Dynamic pruning settings proportional to context size
PRUNE_PROTECT_PERCENTAGE = int(
    os.environ.get("PRUNE_PROTECT_PERCENTAGE", "25")
)  # 25% of context size
PRUNE_PROTECT_TOKENS = int(
    os.environ.get(
        "PRUNE_PROTECT_TOKENS", str(int(CONTEXT_SIZE * PRUNE_PROTECT_PERCENTAGE / 100))
    )
)
# Cap at reasonable maximum (50k tokens) for huge contexts
PRUNE_PROTECT_TOKENS = min(PRUNE_PROTECT_TOKENS, 50000)

PRUNE_MINIMUM_PERCENTAGE = int(
    os.environ.get("PRUNE_MINIMUM_PERCENTAGE", "15")
)  # 15% of context size
PRUNE_MINIMUM_TOKENS = int(
    os.environ.get(
        "PRUNE_MINIMUM_TOKENS", str(int(CONTEXT_SIZE * PRUNE_MINIMUM_PERCENTAGE / 100))
    )
)
# Minimum cap for small contexts
PRUNE_MINIMUM_TOKENS = max(PRUNE_MINIMUM_TOKENS, 10000)

ENABLE_PRUNING_COMPACTION = (
    os.environ.get("ENABLE_PRUNING_COMPACTION", "1") == "1"
)  # Enable pruning-based compaction

# Calculate auto-compaction threshold based on percentage (0 percentage means disabled)
if CONTEXT_COMPACT_PERCENTAGE > 0:
    # Cap at 100% to prevent exceeding context size
    capped_percentage = min(CONTEXT_COMPACT_PERCENTAGE, 100)
    AUTO_COMPACT_THRESHOLD = int(CONTEXT_SIZE * (capped_percentage / 100.0))
else:
    AUTO_COMPACT_THRESHOLD = 0  # Disabled

# Auto-compaction enabled flag
AUTO_COMPACT_ENABLED = AUTO_COMPACT_THRESHOLD > 0

# Truncation settings
DEFAULT_TRUNCATION_LIMIT = int(os.environ.get("DEFAULT_TRUNCATION_LIMIT", "300"))


# Global reference to app instance for config access
_app_instance = None


def set_app_instance(app):
    """Set the global app instance for config access."""
    global _app_instance
    _app_instance = app


def get_effective_truncation_limit():
    """Get the effective truncation limit, checking persistent config first, then env var."""
    # Try to get from persistent config if available
    global _app_instance
    if (
        _app_instance
        and hasattr(_app_instance, "persistent_config")
        and "truncation" in _app_instance.persistent_config
    ):
        truncation_value = _app_instance.persistent_config["truncation"]
        # Ensure it's an integer
        if isinstance(truncation_value, str):
            try:
                return int(truncation_value)
            except ValueError:
                pass  # Fall back to default
        elif isinstance(truncation_value, (int, float)):
            return int(truncation_value)

    # Fall back to environment variable
    return DEFAULT_TRUNCATION_LIMIT


# Tool result size limits
MAX_TOOL_RESULT_SIZE = int(
    os.environ.get("MAX_TOOL_RESULT_SIZE", "300000")
)  # 300KB default

# Compaction summary message configuration
# Some models fail with role="system" summaries, others work better with it
# Set to "user" for models that don't support system messages well, "system" otherwise
COMPACTION_SUMMARY_ROLE = os.environ.get("COMPACTION_SUMMARY_ROLE", "system").lower()
if COMPACTION_SUMMARY_ROLE not in ["system", "user"]:
    COMPACTION_SUMMARY_ROLE = "system"  # Default to system for backward compatibility

# Mode flags
YOLO_MODE = "YOLO_MODE" in os.environ and os.environ.get("YOLO_MODE") == "1"
SHELL_COMMANDS_DENY_ALL = "SHELL_COMMANDS_DENY_ALL" in os.environ
SHELL_COMMANDS_ALLOW_ALL = "SHELL_COMMANDS_ALLOW_ALL" in os.environ

# Tool configuration
TOOL_RESULT_VISIBILITY = os.environ.get("TOOL_RESULT_VISIBILITY", "full").lower()
TOOL_OUTPUT_PRINTING = os.environ.get("TOOL_OUTPUT_PRINTING", "auto").lower()
HIDDEN_TOOL_ARGUMENTS = os.environ.get("HIDDEN_TOOL_ARGUMENTS", "").split(",")

# Tool result visibility options:
# - "full": Show all tool arguments (default)
# - "minimal": Hide sensitive arguments like file contents
# - "none": Hide all arguments
if TOOL_RESULT_VISIBILITY not in ["full", "minimal", "none"]:
    TOOL_RESULT_VISIBILITY = "full"

# Tool output printing options:
# - "auto": Print tool results based on context (default)
# - "always": Always print tool results
# - "never": Never print tool results
if TOOL_OUTPUT_PRINTING not in ["auto", "always", "never"]:
    TOOL_OUTPUT_PRINTING = "auto"

# Clean up empty strings from hidden arguments
HIDDEN_TOOL_ARGUMENTS = [arg.strip() for arg in HIDDEN_TOOL_ARGUMENTS if arg.strip()]

# Retry configuration
ENABLE_EXPONENTIAL_WAIT_RETRY = (
    os.environ.get("ENABLE_EXPONENTIAL_WAIT_RETRY", "1") == "1"
)
RETRY_INITIAL_DELAY = float(os.environ.get("RETRY_INITIAL_DELAY", "2"))
RETRY_MAX_DELAY = float(os.environ.get("RETRY_MAX_DELAY", "64"))
RETRY_FIXED_DELAY = float(os.environ.get("RETRY_FIXED_DELAY", "5"))
RETRY_MAX_ATTEMPTS = int(os.environ.get("RETRY_MAX_ATTEMPTS", "0"))  # 0 means infinite

# Token information display configuration
ENABLE_TOKEN_INFO_DISPLAY = os.environ.get("ENABLE_TOKEN_INFO_DISPLAY", "1") == "1"

# Token estimation configuration
# Default behavior: estimation is used unless TRUST_USAGE_INFO_PROMPT_TOKENS is set to "1"
# If TRUST_USAGE_INFO_PROMPT_TOKENS is "1", trust API usage data
# If TRUST_USAGE_INFO_PROMPT_TOKENS is "0" or not set, force estimation
TRUST_USAGE_INFO_PROMPT_TOKENS = os.environ.get("TRUST_USAGE_INFO_PROMPT_TOKENS", "0") == "1"

# Token information bar characters (goose bar chars ● ○)
TOKEN_INFO_FILLED_CHAR = os.environ.get("TOKEN_INFO_FILLED_CHAR", "█")
TOKEN_INFO_EMPTY_CHAR = os.environ.get("TOKEN_INFO_EMPTY_CHAR", "░")

# Token estimation weights
TOKEN_LETTER_WEIGHT = float(os.environ.get("AICODER_TOKEN_ESTIMATION_LETTER_WEIGHT", 4.2))
TOKEN_NUMBER_WEIGHT = float(os.environ.get("AICODER_TOKEN_ESTIMATION_NUMBER_WEIGHT", 3.5))
TOKEN_PUNCTUATION_WEIGHT = float(os.environ.get("AICODER_TOKEN_ESTIMATION_PUNCTUATION_WEIGHT", 1.0))
TOKEN_WHITESPACE_WEIGHT = float(os.environ.get("AICODER_TOKEN_ESTIMATION_WHITESPACE_WEIGHT", 0.15))
TOKEN_OTHER_WEIGHT = float(os.environ.get("AICODER_TOKEN_ESTIMATION_OTHER_WEIGHT", 3.0))


# File-based prompting configuration
def get_file_prompt_mode():
    """Get file-based prompting mode setting."""
    # Auto-enable if AICODER_PROMPT_FILE is set, otherwise check explicit flag
    if os.getenv("AICODER_PROMPT_FILE"):
        return True
    return os.getenv("AICODER_FILE_MODE", "").lower() in ("1", "true", "yes", "on", "file")


def get_file_prompt_path():
    """Get file path for file-based prompting."""
    return os.getenv("AICODER_PROMPT_FILE", "aicoder_prompt.txt")

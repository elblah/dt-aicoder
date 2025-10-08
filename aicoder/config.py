"""
Configuration module for AI Coder.
"""

import os

# --- Configuration ---
DEBUG = os.environ.get("DEBUG", "0") == "1"
HOME_DIR = os.environ.get("HOME", None)
APP_NAME = "aicoder"

# Temperature configuration
TEMPERATURE = float(os.environ.get("TEMPERATURE", "0.0"))

# Top-P configuration
TOP_P = float(os.environ.get("TOP_P", "1.0"))

# Max tokens configuration
MAX_TOKENS = (
    int(os.environ.get("MAX_TOKENS", "")) if os.environ.get("MAX_TOKENS", "") else None
)

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

# Print debug status at startup
if DEBUG:
    print(f"{YELLOW}DEBUG MODE IS ON{RESET}")

# Print temperature if set as environment variable
if "TEMPERATURE" in os.environ:
    print(f"{GREEN}*** Temperature is {TEMPERATURE}{RESET}")

# Print top_p if set as environment variable
if "TOP_P" in os.environ:
    print(f"{GREEN}*** Top-P is {TOP_P}{RESET}")

# Print max_tokens if set as environment variable
if "MAX_TOKENS" in os.environ:
    print(f"{GREEN}*** Max tokens is {MAX_TOKENS}{RESET}")

# Print streaming timeout if set as environment variable
if "STREAMING_TIMEOUT" in os.environ:
    print(f"{GREEN}*** Streaming timeout is {STREAMING_TIMEOUT} seconds{RESET}")

# Print streaming read timeout if set as environment variable
if "STREAMING_READ_TIMEOUT" in os.environ:
    print(
        f"{GREEN}*** Streaming read timeout is {STREAMING_READ_TIMEOUT} seconds{RESET}"
    )

# Configuration from environment variables
API_KEY = os.environ.get("OPENAI_API_KEY", "YOUR_API_KEY")
API_ENDPOINT = (
    os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1") + "/chat/completions"
)
if "API_ENDPOINT" in os.environ:
    API_ENDPOINT = os.environ.get("API_ENDPOINT")
API_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5-nano")

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
CONTEXT_SIZE = int(os.environ.get("CONTEXT_SIZE", "128000"))  # Default to 128k tokens
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

# Tool result size limits
MAX_TOOL_RESULT_SIZE = int(
    os.environ.get("MAX_TOOL_RESULT_SIZE", "300000")
)  # 300KB default

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

# Token information bar characters (goose bar chars ● ○)
TOKEN_INFO_FILLED_CHAR = os.environ.get("TOKEN_INFO_FILLED_CHAR", "█")
TOKEN_INFO_EMPTY_CHAR = os.environ.get("TOKEN_INFO_EMPTY_CHAR", "░")

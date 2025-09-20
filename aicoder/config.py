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

# Define some ANSI color codes
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
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

# Configuration from environment variables
API_KEY = os.environ.get("OPENAI_API_KEY", "YOUR_API_KEY")
API_ENDPOINT = (
    os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1") + "/chat/completions"
)
if "API_ENDPOINT" in os.environ:
    API_ENDPOINT = os.environ.get("API_ENDPOINT")
API_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5-nano")

# Compaction settings (for manual /compact command)
COMPACT_RECENT_MESSAGES = int(os.environ.get("COMPACT_RECENT_MESSAGES", "5"))

# Set COMPACT_MIN_MESSAGES: environment variable takes priority, otherwise use dynamic calculation
if "COMPACT_MIN_MESSAGES" in os.environ:
    # Use environment variable value if provided
    COMPACT_MIN_MESSAGES = int(os.environ.get("COMPACT_MIN_MESSAGES"))
else:
    # Dynamic calculation: need at least one more chat message than we keep
    # This is calculated dynamically in MessageHistory by counting only chat messages (excluding initial system messages)
    COMPACT_MIN_MESSAGES = COMPACT_RECENT_MESSAGES + 1

# Auto-compaction settings
# Support both names for backward compatibility - AUTO_COMPACT_TOKENS_THRESHOLD is preferred
AUTO_COMPACT_THRESHOLD = int(
    os.environ.get(
        "AUTO_COMPACT_TOKENS_THRESHOLD", os.environ.get("AUTO_COMPACT_THRESHOLD", "0")
    )
)  # 0 means disabled

# Truncation settings
DEFAULT_TRUNCATION_LIMIT = int(os.environ.get("DEFAULT_TRUNCATION_LIMIT", "300"))

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

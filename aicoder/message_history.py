"""
Message history management for AI Coder.
"""

import json
import os
import textwrap
from typing import List, Dict, Any

from .stats import Stats
from .config import (
    DEBUG,
    GREEN,
    RESET,
    RED,
    YELLOW,
    COMPACT_RECENT_MESSAGES,
    COMPACT_MIN_MESSAGES,
)


def clean_message_for_api(message: Dict[str, Any]) -> Dict[str, Any]:
    """
    Clean a message for API submission by removing internal metadata and validating format.

    Args:
        message: Message dictionary to clean

    Returns:
        Cleaned message dictionary suitable for API submission
    """
    if not isinstance(message, dict):
        return message

    # Make a copy to avoid modifying original
    clean_msg = message.copy()

    # Remove internal metadata that shouldn't be sent to the API
    internal_metadata = ["_streaming_response"]
    for metadata_key in internal_metadata:
        if metadata_key in clean_msg:
            del clean_msg[metadata_key]

    # Clean up tool_calls if they exist
    if "tool_calls" in clean_msg and clean_msg["tool_calls"]:
        try:
            # Ensure tool_calls is a list
            if not isinstance(clean_msg["tool_calls"], list):
                del clean_msg["tool_calls"]
                return clean_msg

            cleaned_tool_calls = []
            for tool_call in clean_msg["tool_calls"]:
                if not isinstance(tool_call, dict):
                    continue

                # Make a copy of the tool call
                clean_tool_call = tool_call.copy()

                # Validate required fields
                if (
                    "id" not in clean_tool_call
                    or "type" not in clean_tool_call
                    or "function" not in clean_tool_call
                ):
                    continue

                # Validate function field
                if not isinstance(clean_tool_call["function"], dict):
                    continue

                function_field = clean_tool_call["function"]
                if "name" not in function_field or "arguments" not in function_field:
                    continue

                # Clean up arguments - ensure they're properly formatted JSON
                args = function_field["arguments"]
                if isinstance(args, str):
                    try:
                        # Parse and re-serialize to ensure proper JSON formatting
                        parsed_args = json.loads(args)
                        function_field["arguments"] = json.dumps(parsed_args)
                    except (json.JSONDecodeError, TypeError):
                        # If arguments aren't valid JSON, try to convert them to a string representation
                        function_field["arguments"] = json.dumps(str(args))
                elif not isinstance(args, str):
                    # Convert non-string arguments to JSON string
                    function_field["arguments"] = json.dumps(args)

                cleaned_tool_calls.append(clean_tool_call)

            if cleaned_tool_calls:
                clean_msg["tool_calls"] = cleaned_tool_calls
            else:
                # If no valid tool calls remain, remove the field
                if "tool_calls" in clean_msg:
                    del clean_msg["tool_calls"]
        except Exception as e:
            if DEBUG:
                print(f"{RED} *** Error cleaning tool_calls in message: {e}{RESET}")
            # If cleaning fails, remove tool_calls to avoid API errors
            if "tool_calls" in clean_msg:
                del clean_msg["tool_calls"]

    # Ensure content field exists and is a string
    if "content" not in clean_msg or clean_msg["content"] is None:
        clean_msg["content"] = ""
    elif not isinstance(clean_msg["content"], str):
        clean_msg["content"] = str(clean_msg["content"])

    # Special handling for tool messages - clean up ANSI codes and special characters
    if clean_msg.get("role") == "tool":
        # Remove ANSI color codes and other control characters
        import re

        # Remove ANSI escape codes
        clean_msg["content"] = re.sub(r"\x1b\[[0-9;]*m", "", clean_msg["content"])
        # Remove other control characters except common ones like newlines and tabs
        clean_msg["content"] = re.sub(
            r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", clean_msg["content"]
        )

    # Ensure role field exists
    if "role" not in clean_msg:
        clean_msg["role"] = "user"

    return clean_msg


class MessageHistory:
    """Manages the conversation history with memory compaction."""

    def __init__(self):
        self.messages = self._create_initial_messages()
        self.initial_system_prompt = self.messages[0] if self.messages else None
        self.stats = Stats()
        # Reference to the API handler will be set externally
        self.api_handler = None

    def _create_initial_messages(self) -> List[Dict[str, Any]]:
        """Create the initial system message."""
        # Base system prompt - will be replaced by AICODER.md if available
        INITIAL_PROMPT = textwrap.dedent(f"""
            You are a helpful assistant with access to a variety of tools defined in
            an MCP (Model-Context-Protocol) system.
            These tools include file system access and command execution.
            You must to use them to answer user requests.
            Do not reveal credentials or internal system details.
            Do not persist data beyond the current session unless allowed.
            Batch as much tool_calls operations as possible in each request. 
            Avoid unnecessary requests.
            Keep responses concise and informative, aiming for under 200 words per message.
            The current/working directory is: {os.getcwd()}
        """)

        # Try to load AICODER.md from multiple possible locations
        aicoder_content = self._load_aicoder_md()
        if aicoder_content:
            # Replace placeholder with actual current directory
            aicoder_content = aicoder_content.replace(
                "{current_directory}", os.getcwd()
            )
            INITIAL_PROMPT = aicoder_content
            if DEBUG:
                print(f"{GREEN} *** Successfully loaded AICODER.md{RESET}")

        # Check if AGENTS.md exists and append its content
        agents_files = ["AGENTS.md", "agents.md"]
        agents_content = ""

        for agents_file in agents_files:
            if os.path.exists(agents_file):
                try:
                    with open(agents_file, "r", encoding="utf-8") as f:
                        agents_content = f.read().strip()
                    if agents_content:
                        INITIAL_PROMPT += f"\n\nAdditional Context from {agents_file}:\n{agents_content}"
                        break  # Found and processed the first available file
                except Exception as e:
                    if DEBUG:
                        print(f"{RED} *** Error reading {agents_file}: {e}{RESET}")
                break  # Try only the first file that exists

        return [
            {
                "role": "system",
                "content": INITIAL_PROMPT[1:],  # Remove leading newline
            }
        ]

    def add_user_message(self, content: str):
        """Add a user message to the history."""
        self.messages.append({"role": "user", "content": content})
        self.stats.messages_sent += 1

    def add_assistant_message(self, message: Dict[str, Any]):
        """Add an assistant message to the history."""
        # Clean the message for storage
        message_copy = clean_message_for_api(message)

        # Handle content
        if message_copy.get("content", None) is None:
            message_copy["content"] = "no content"

        # Remove tool_calls attribute entirely if it's empty or None
        if "tool_calls" in message_copy and not message_copy["tool_calls"]:
            del message_copy["tool_calls"]

        self.messages.append(message_copy)

    def add_tool_results(self, tool_results: List[Dict[str, Any]]):
        """Add tool results to the history."""
        # Clean up tool results before adding them
        clean_results = []
        for result in tool_results:
            clean_results.append(clean_message_for_api(result))
        self.messages.extend(clean_results)

    def compact_memory(self) -> List[Dict[str, Any]]:
        """Compact memory by summarizing older messages while preserving tool call/response pairs."""
        # Find the first non-system message to determine where chat messages start
        first_chat_index = self._get_first_chat_message_index()
        chat_message_count = len(self.messages) - first_chat_index

        # Don't compact if we don't have enough chat messages
        if chat_message_count < COMPACT_MIN_MESSAGES:
            print(
                f"{YELLOW} *** Auto-compaction: Not enough messages to compact (chat messages: {chat_message_count}, minimum: {COMPACT_MIN_MESSAGES}){RESET}"
            )
            return self.messages

        print(f"{GREEN} *** Compacting memory... {RESET}")

        # Update stats
        self.stats.compactions += 1

        # For compaction, keep only:
        # 1. Initial system prompt
        # 2. Summary of all previous conversation (except system prompt)
        # 3. Last few messages (most recent context), but ensure tool call/response pairs are kept together

        # Get recent messages while preserving tool call/response pairs
        recent_messages = self._get_preserved_recent_messages()

        # Create summary of older messages (everything except initial system messages and recent messages)
        # Filter out malformed messages
        first_chat_index = self._get_first_chat_message_index()
        older_messages = (
            self.messages[first_chat_index : -len(recent_messages)]
            if len(self.messages) > len(recent_messages) + first_chat_index
            else []
        )

        # Clean up older messages before summarization
        clean_older_messages = [clean_message_for_api(msg) for msg in older_messages]

        if clean_older_messages:
            older_text = "\n".join(
                [
                    f"{m.get('role', '')}: {m.get('content', '') or ''}"
                    for m in clean_older_messages
                ]
            )
            summary = (
                self._summarize_old_messages(older_text) if older_text.strip() else ""
            )
        else:
            summary = ""

        summary_content = "Summary of earlier conversation: " + (
            summary if summary else "no prior content"
        )
        summary_message = {"role": "system", "content": summary_content}

        # Reconstruct the messages list: system prompt + summary + recent messages
        new_messages = [self.initial_system_prompt, summary_message] + recent_messages

        self.messages = new_messages
        return self.messages

    def _get_first_chat_message_index(self) -> int:
        """Find the index of the first non-system message."""
        for i, message in enumerate(self.messages):
            if message.get("role") != "system":
                return i
        return len(self.messages)  # All messages are system messages

    def _get_preserved_recent_messages(self) -> List[Dict[str, Any]]:
        """Get recent messages while preserving tool call/response pairs."""
        first_chat_index = self._get_first_chat_message_index()
        chat_message_count = len(self.messages) - first_chat_index

        # If we have few enough chat messages, keep all of them
        if chat_message_count <= COMPACT_RECENT_MESSAGES:
            return self.messages[first_chat_index:]  # All chat messages

        # Get the recent messages (last N chat messages)
        recent_messages = self.messages[-COMPACT_RECENT_MESSAGES:]

        # Scan from oldest to newest to find the first tool call
        # Any tool response before that first tool call is an orphan and should be removed
        found_tool_call = False
        cleaned_messages = []

        for message in recent_messages:
            # If this is a tool call message, mark that we've found one
            if message.get("role") == "assistant" and message.get("tool_calls"):
                found_tool_call = True
                cleaned_messages.append(message)
            # If this is a tool response message
            elif message.get("role") == "tool":
                # Only include it if we've already found a tool call
                if found_tool_call:
                    cleaned_messages.append(message)
                # Otherwise, skip it (it's an orphan)
            else:
                # For all other messages, include them
                cleaned_messages.append(message)

        return cleaned_messages

    def _summarize_old_messages(self, text: str) -> str:
        """Summarize old messages via API."""
        if not text or not text.strip():
            return ""

        # If we don't have an API handler, return a placeholder
        if not self.api_handler:
            return "Summary unavailable - no API handler available"

        try:
            # Limit text length to avoid token limits
            MAX_SUMMARY_LENGTH = 30000  # Roughly 10K tokens
            if len(text) > MAX_SUMMARY_LENGTH:
                text = text[:MAX_SUMMARY_LENGTH] + "... [truncated]"

            # Create a summary prompt
            summary_prompt = f"Please provide a concise summary of the following conversation history. Focus on the key points and important details:\n\n{text}"

            summary_messages = [
                {
                    "role": "system",
                    "content": "You are a helpful assistant that creates concise summaries of conversation history.",
                },
                {"role": "user", "content": summary_prompt},
            ]

            # Make API request for summary (disable streaming and tools for internal prompts)
            response = self.api_handler._make_api_request(
                summary_messages, disable_streaming_mode=True, disable_tools=True
            )

            if response and "choices" in response and response["choices"]:
                summary = response["choices"][0]["message"].get("content", "").strip()
                if summary:
                    return summary

            # Fallback if API request fails
            return "Summary of conversation history (API request failed)"
        except Exception as e:
            if DEBUG:
                print(f"{RED} *** Error creating summary: {e}{RESET}")
                import traceback

                traceback.print_exc()
            # Fallback if there's an exception
            return (
                "Summary of conversation history (error occurred during summarization)"
            )

    def reset_session(self):
        """Reset the session, clearing messages and stats."""
        self.messages = self._create_initial_messages()
        self.initial_system_prompt = self.messages[0] if self.messages else None
        self.stats = Stats()

    def save_session(self, filename: str = "session.json"):
        """Save the current session to a file."""
        try:
            with open(filename, "w") as f:
                json.dump(self.messages, f, indent=4)
            print(f"\n{GREEN} *** Session saved: {filename}{RESET}")
        except Exception as e:
            print(f"\n{RED} *** Error saving session to {filename}: {e}{RESET}")

    def load_session(self, filename: str = "session.json"):
        """Load a session from a file."""
        try:
            with open(filename, "r") as f:
                loaded_messages = json.load(f)

            # Clean up loaded messages using our helper function
            clean_messages = [clean_message_for_api(msg) for msg in loaded_messages]

            self.messages = clean_messages
            print(f"\n{GREEN} *** Session loaded: {filename}{RESET}")
        except Exception as e:
            print(f"\n{RED} *** Error loading session from {filename}: {e}{RESET}")

    def summarize_context(self):
        """Summarize the conversation context to manage token usage."""
        # Use the existing compact_memory method which properly handles tool call/response pairs
        self.compact_memory()

    def _load_aicoder_md(self) -> str:
        """Load AICODER.md content from various possible locations."""
        import sys

        # List of possible locations for AICODER.md
        possible_paths = []

        # 1. Same directory as this file (regular installation)
        possible_paths.append(os.path.join(os.path.dirname(__file__), "AICODER.md"))

        # 2. In current working directory's aicoder folder
        possible_paths.append(os.path.join(os.getcwd(), "aicoder", "AICODER.md"))

        # 3. Relative path from current file
        possible_paths.append(
            os.path.join(os.path.dirname(__file__), "..", "AICODER.md")
        )

        # 4. In the same directory as the script being run
        try:
            possible_paths.append(
                os.path.join(
                    os.path.dirname(os.path.abspath(sys.argv[0])),
                    "aicoder",
                    "AICODER.md",
                )
            )
        except Exception:
            pass

        # Try each path
        for path in possible_paths:
            try:
                # Normalize the path
                normalized_path = os.path.normpath(path)
                if os.path.exists(normalized_path):
                    with open(normalized_path, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                        if content:
                            if DEBUG:
                                print(
                                    f"{GREEN} *** Found AICODER.md at: {normalized_path}{RESET}"
                                )
                            return content
            except Exception as e:
                if DEBUG:
                    print(f"{RED} *** Error reading AICODER.md from {path}: {e}{RESET}")
                continue

        # Special handling for zipapp - try to read from the package directly
        try:
            # When running as a zipapp, we can try to read the file directly from the package
            import pkgutil

            # Try different package names that might be used
            package_names = ["aicoder", "aicoder.aicoder"]
            for package_name in package_names:
                try:
                    data = pkgutil.get_data(package_name, "AICODER.md")
                    if data:
                        content = data.decode("utf-8").strip()
                        if content:
                            if DEBUG:
                                print(
                                    f"{GREEN} *** Found AICODER.md in package data ({package_name}){RESET}"
                                )
                            return content
                except Exception:
                    continue
        except Exception as e:
            if DEBUG:
                print(
                    f"{RED} *** Error reading AICODER.md from package data: {e}{RESET}"
                )

        # Additional zipapp handling - try to read from sys.path
        try:
            import sys

            if hasattr(sys, "path") and sys.path:
                for path_entry in sys.path:
                    if path_entry.endswith(".pyz") or path_entry.endswith(".zip"):
                        # This might be a zipapp, try to read from it
                        try:
                            import zipfile

                            with zipfile.ZipFile(path_entry, "r") as zf:
                                # Try different possible paths within the zip
                                possible_zip_paths = [
                                    "aicoder/AICODER.md",
                                    "AICODER.md",
                                ]
                                for zip_path in possible_zip_paths:
                                    try:
                                        with zf.open(zip_path) as f:
                                            content = f.read().decode("utf-8").strip()
                                            if content:
                                                if DEBUG:
                                                    print(
                                                        f"{GREEN} *** Found AICODER.md in zipapp ({path_entry}/{zip_path}){RESET}"
                                                    )
                                                return content
                                    except Exception:
                                        continue
                        except Exception:
                            continue
        except Exception as e:
            if DEBUG:
                print(f"{RED} *** Error reading AICODER.md from zipapp: {e}{RESET}")

        # If we get here, we couldn't find AICODER.md
        if DEBUG:
            print(f"{YELLOW} *** AICODER.md not found in any expected location{RESET}")
            print(f"{YELLOW} *** Searched paths: {possible_paths}{RESET}")
        return None

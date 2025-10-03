"""
Message history management for AI Coder.
"""

import json
import os
from typing import List, Dict, Any

from .stats import Stats
from . import config


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

                # Clean up arguments - ensure they're properly formatted JSON string (not double-encoded)
                args = function_field["arguments"]

                # Case 1: Arguments is already a dict or list (from compaction) - DON'T TOUCH!
                if isinstance(args, (dict, list)):
                    # Already in correct format, leave it alone
                    pass
                # Case 2: Arguments is a string - need to check for double-encoding
                elif isinstance(args, str):
                    parsed_args = None
                    parse_attempts = 0
                    max_attempts = 5
                    current_args = args

                    # Try to parse JSON up to 5 times to handle double/triple encoding
                    final_parsed = None
                    while parse_attempts < max_attempts:
                        parse_attempts += 1
                        try:
                            parsed_args = json.loads(current_args)

                            # If we got a dict or list, this is what we want
                            if isinstance(parsed_args, (dict, list)):
                                final_parsed = parsed_args
                                break
                            # If we got a string, try parsing it again (double encoding)
                            elif isinstance(parsed_args, str):
                                current_args = parsed_args
                                if parse_attempts < max_attempts:
                                    continue  # Try parsing again
                                else:
                                    # Max attempts reached, still a string - this is invalid
                                    raise ValueError(
                                        f"Arguments still a string after {max_attempts} parse attempts: {parsed_args}"
                                    )
                            else:
                                # Got some other type (int, float, bool, None) - wrap in dict
                                final_parsed = {"value": parsed_args}
                                break

                        except (json.JSONDecodeError, TypeError) as e:
                            if parse_attempts == 1:
                                # First attempt failed - this is invalid JSON
                                raise ValueError(f"Invalid JSON in arguments: {e}")
                            else:
                                # Subsequent attempts failed - this shouldn't happen if first parse succeeded
                                raise ValueError(
                                    f"Failed to parse arguments on attempt {parse_attempts}: {e}"
                                )

                    # If we successfully parsed, convert back to JSON string for API
                    if final_parsed is not None:
                        function_field["arguments"] = json.dumps(final_parsed)
                    else:
                        # Shouldn't get here if logic is correct
                        raise ValueError("Failed to parse arguments after all attempts")
                # Case 3: Arguments is some other type - convert to dict then JSON string
                else:
                    # For other types (int, float, bool, None), wrap in dict then JSON string
                    function_field["arguments"] = json.dumps({"value": args})

                cleaned_tool_calls.append(clean_tool_call)

            if cleaned_tool_calls:
                clean_msg["tool_calls"] = cleaned_tool_calls
            else:
                # If no valid tool calls remain, remove the field
                if "tool_calls" in clean_msg:
                    del clean_msg["tool_calls"]
        except Exception as e:
            if config.DEBUG:
                print(
                    f"{config.RED} *** Error cleaning tool_calls in message: {e}{config.RESET}"
                )
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
        # Flag to track if compaction has been performed since last message addition
        self._compaction_performed = False

    def _create_initial_messages(self) -> List[Dict[str, Any]]:
        """Create the initial system message."""
        # AICODER.md now contains the complete system prompt
        aicoder_content = self._load_aicoder_md()
        if aicoder_content:
            # Replace placeholder with actual current directory
            aicoder_content = aicoder_content.replace(
                "{current_directory}", os.getcwd()
            )
            # Replace placeholder with current date and time
            from datetime import datetime
            current_datetime = datetime.now()
            aicoder_content = aicoder_content.replace(
                "{current_datetime}", current_datetime.strftime("%Y-%m-%d %H:%M:%S")
            )
            
            # Detect available tools and add to context
            available_tools = self._detect_available_tools()
            aicoder_content = aicoder_content.replace(
                "{available_tools}", available_tools
            )
            
            # Add system information
            system_info = self._get_system_info()
            aicoder_content = aicoder_content.replace(
                "{system_info}", system_info
            )
            
            INITIAL_PROMPT = aicoder_content
            if config.DEBUG:
                print(
                    f"{config.GREEN} *** Successfully loaded AICODER.md{config.RESET}"
                )
        else:
            # Fallback minimal prompt if AICODER.md not found
            INITIAL_PROMPT = "You are a helpful assistant with access to MCP tools. You must use them to answer user requests."
            if config.DEBUG:
                print(
                    f"{config.YELLOW} *** AICODER.md not found, using fallback prompt{config.RESET}"
                )

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
                    if config.DEBUG:
                        print(
                            f"{config.RED} *** Error reading {agents_file}: {e}{config.RESET}"
                        )
                break  # Try only the first file that exists

        return [{"role": "system", "content": INITIAL_PROMPT}]

    def _detect_available_tools(self) -> str:
        """Detect available tools and return formatted string for prompt."""
        import shutil
        
        tool_map = {
            "text search": ["rg", "ag", "grep"],
            "file search": ["fd", "rg", "find"],
            "file listing": ["eza", "exa", "ls"],
            "directory tree": ["tree", "eza"],
        }
        
        available_sections = []
        for category, tools in tool_map.items():
            available = []
            for tool in tools:
                # Skip "eza --tree" for which check, just check "eza"
                tool_to_check = tool.split()[0] if ' ' in tool else tool
                if shutil.which(tool_to_check):
                    available.append(tool)
            if available:
                available_sections.append(f"{category}: {', '.join(available)}")
        
        if available_sections:
            return "Some commands that are available for certain tasks on this system that you might use:\n" + "\n".join(f"- {section}" for section in available_sections)
        else:
            return "Standard Unix/Linux tools are available on this system."

    def _get_system_info(self) -> str:
        """Get system information for context."""
        import platform
        
        system = platform.system()
        machine = platform.machine()
        return f"This is a {system} system on {machine} architecture"

    def add_user_message(self, content: str):
        """Add a user message to the history."""
        self.messages.append({"role": "user", "content": content})
        self.stats.messages_sent += 1
        # Clear compaction flag since we added a new message
        self._compaction_performed = False

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
        # Clear compaction flag since we added a new message
        self._compaction_performed = False

    def add_tool_results(self, tool_results: List[Dict[str, Any]]):
        """Add tool results to the history."""
        # Clean up tool results before adding them
        clean_results = []
        for result in tool_results:
            clean_results.append(clean_message_for_api(result))
        self.messages.extend(clean_results)
        # Clear compaction flag since we added new messages
        self._compaction_performed = False

    def compact_memory(self) -> List[Dict[str, Any]]:
        """Compact memory by pruning old tool results first, then summarizing if needed."""
        # Find the first non-system message to determine where chat messages start
        first_chat_index = self._get_first_chat_message_index()
        chat_message_count = len(self.messages) - first_chat_index

        # Don't compact if we don't have enough chat messages
        if chat_message_count < config.COMPACT_MIN_MESSAGES:
            print(
                f"{config.YELLOW} *** Auto-compaction: Not enough messages to compact (chat messages: {chat_message_count}, minimum: {config.COMPACT_MIN_MESSAGES}){config.RESET}"
            )
            return self.messages

        print(f"{config.GREEN} *** Compacting memory... {config.RESET}")

        if config.DEBUG:
            try:
                import subprocess

                subprocess.run(["dunstify", "-t", "3000", "COMPACTION"], check=False)
            except Exception as e:
                # Silently ignore if dunstify is not available or fails
                print(
                    f"{config.YELLOW} *** Could not execute dunstify: {e}{config.RESET}"
                )

        # Update stats
        self.stats.compactions += 1

        # First, try to prune old tool results (pragmatic approach)
        pruned_messages, actual_pruning_occurred = self._prune_old_tool_results()

        # Check if pruning was sufficient by estimating tokens after pruning
        from .utils import estimate_messages_tokens
        tokens_after_pruning = estimate_messages_tokens(pruned_messages)
        
        # If pruning brought us below the auto-compaction threshold, keep the pruned messages
        # without doing AI summarization
        if tokens_after_pruning < config.AUTO_COMPACT_THRESHOLD:
            if actual_pruning_occurred:
                print(
                    f"{config.GREEN} *** Pruning was sufficient (tokens: {tokens_after_pruning}, threshold: {config.AUTO_COMPACT_THRESHOLD}){config.RESET}"
                )
            self.messages = pruned_messages
            # Set the flag to True to indicate compaction has been attempted
            self._compaction_performed = True
            
            # Recalculate token count after compaction
            from .utils import estimate_messages_tokens
            if self.api_handler and hasattr(self.api_handler, 'stats'):
                self.api_handler.stats.current_prompt_size = estimate_messages_tokens(self.messages)
                if config.DEBUG:
                    print(f"{config.GREEN} *** Token count recalculated after compaction: {self.api_handler.stats.current_prompt_size} tokens{config.RESET}")
            
            return self.messages

        # If pruning wasn't sufficient, proceed with AI summarization approach
        # Get recent messages while preserving tool call/response pairs
        recent_messages = self._get_preserved_recent_messages()

        # Create summary of older messages (everything except initial system messages and recent messages)
        # Filter out malformed messages
        first_chat_index = self._get_first_chat_message_index()
        older_messages = (
            pruned_messages[first_chat_index : -len(recent_messages)]
            if len(pruned_messages) > len(recent_messages) + first_chat_index
            else []
        )

        # Clean up older messages before summarization
        clean_older_messages = [
            clean_message_for_api(msg) for msg in older_messages
        ]

        if clean_older_messages:
            summary = self._summarize_old_messages(clean_older_messages)
        else:
            summary = ""

        summary_content = "Summary of earlier conversation: " + (
            summary if summary else "no prior content"
        )
        summary_message = {"role": "system", "content": summary_content}

        # Reconstruct the messages list: system prompt + summary + recent messages
        new_messages = [
            self.initial_system_prompt,
            summary_message,
        ] + recent_messages

        self.messages = new_messages
        # Set the flag to True to indicate compaction has been attempted
        self._compaction_performed = True
        
        # Recalculate token count after compaction
        from .utils import estimate_messages_tokens
        if self.api_handler and hasattr(self.api_handler, 'stats'):
            self.api_handler.stats.current_prompt_size = estimate_messages_tokens(self.messages)
            if config.DEBUG:
                print(f"{config.GREEN} *** Token count recalculated after compaction: {self.api_handler.stats.current_prompt_size} tokens{config.RESET}")
        
        return self.messages

    def _prune_old_tool_results(self) -> tuple:
        """Prune old tool results while keeping tool calls and conversation flow.
        
        Returns:
            tuple: (pruned_messages_list, actual_pruning_occurred_bool)
        """
        from .utils import estimate_messages_tokens

        # Make a copy of messages to work with
        messages = [msg.copy() for msg in self.messages]

        # Calculate total token count to determine if pruning is needed
        total_tokens = estimate_messages_tokens(messages)

        # Only proceed with pruning if we have more tokens than the protection threshold
        if total_tokens <= config.PRUNE_PROTECT_TOKENS:
            if config.DEBUG:
                print(
                    f"{config.GREEN} *** Skipping pruning - total tokens ({total_tokens}) below protection threshold ({config.PRUNE_PROTECT_TOKENS}){config.RESET}"
                )
            return messages, False  # No pruning occurred

        # Identify which messages are tool results that can be pruned
        # We'll go backwards through messages, keeping recent conversations and
        # only pruning old tool result content (not tool calls themselves)

        # First, identify recent conversation turns to preserve
        recent_turns_to_keep = config.COMPACT_RECENT_MESSAGES
        turns_found = 0
        preserve_from_index = len(messages)

        # Go backwards to find recent conversation turns
        for i in range(len(messages) - 1, -1, -1):
            msg = messages[i]
            if msg.get("role") == "user":
                turns_found += 1
                if turns_found >= recent_turns_to_keep:
                    preserve_from_index = i
                    break

        # Prune tool results that are older than the preserved section
        pruned_count = 0
        pruned_tokens = 0

        for i in range(preserve_from_index):
            msg = messages[i]
            if msg.get("role") == "tool":
                # Prune the content of old tool results, but keep the message structure
                if "content" in msg and msg["content"]:
                    original_content = msg["content"]
                    original_tokens = (
                        len(str(original_content)) // 4
                    )  # Rough token estimation

                    # Only prune if the content is substantial (more than 100 characters)
                    if len(str(original_content)) > 100:
                        msg["content"] = (
                            "[Old tool result content cleared due to memory compaction]"
                        )
                        pruned_count += 1
                        pruned_tokens += original_tokens
                        if config.DEBUG:
                            print(
                                f"{config.YELLOW} *** Pruned tool result: {len(str(original_content))} chars -> [compacted]{config.RESET}"
                            )

        # If we pruned any messages, return the pruned version
        # This ensures that the placeholder messages are kept to indicate what was compacted
        if pruned_count > 0:
            if config.DEBUG:
                print(
                    f"{config.GREEN} *** Applied pruning of {pruned_count} tool results, saving approximately {pruned_tokens} tokens{config.RESET}"
                )
            return messages, True  # Pruning occurred
        else:
            # Only return original if no pruning actually occurred
            if config.DEBUG:
                print(
                    f"{config.YELLOW} *** No pruning occurred, returning original messages{config.RESET}"
                )
            return [msg.copy() for msg in self.messages], False  # No pruning occurred

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
        if chat_message_count <= config.COMPACT_RECENT_MESSAGES:
            return self.messages[first_chat_index:]  # All chat messages

        # Get the recent messages (last N chat messages)
        recent_messages = self.messages[-config.COMPACT_RECENT_MESSAGES :]

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

    def _summarize_old_messages(self, messages_to_summarize: List[Dict]) -> str:
        """Summarize old messages via API, including tool context."""
        if not messages_to_summarize:
            return ""

        # If we don't have an API handler, return a placeholder
        if not self.api_handler:
            return "Summary unavailable - no API handler available"

        try:
            # Format messages to include tool context
            formatted_messages = []
            for msg in messages_to_summarize:
                formatted = self._format_message_for_summary(msg)
                if formatted.strip():
                    formatted_messages.append(formatted)

            if not formatted_messages:
                return "no prior content"

            # Join with clear separation
            text = "\n---\n".join(formatted_messages)

            # Limit text length to avoid token limits
            MAX_SUMMARY_LENGTH = 30000  # Roughly 10K tokens
            if len(text) > MAX_SUMMARY_LENGTH:
                text = text[:MAX_SUMMARY_LENGTH] + "... [truncated]"

            # Create a better summary prompt that focuses on important context
            summary_prompt = f"""
Please provide a concise summary of the following conversation history. 
Focus on:
- What files or directories are being worked on
- What tools were used and what they did
- What the current task or goal is
- What was accomplished recently
- What needs to be done next

The summary should help continue the conversation effectively.

Conversation history:
{text}
"""

            summary_messages = [
                {
                    "role": "system",
                    "content": "You are a helpful assistant that creates concise summaries of conversation history. Focus on important context like files being worked on, tools used, current tasks, and next steps.",
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
            if config.DEBUG:
                print(f"{config.RED} *** Error creating summary: {e}{config.RESET}")
                import traceback

                traceback.print_exc()
            # Fallback if there's an exception
            return (
                "Summary of conversation history (error occurred during summarization)"
            )

    def _format_message_for_summary(self, message: Dict) -> str:
        """Format a message for AI summarization, including tool context."""
        role = message.get("role", "unknown")
        content = message.get("content", "")

        if role == "assistant":
            # Include tool calls if present
            tool_calls = message.get("tool_calls", [])
            if tool_calls:
                tool_info = []
                for tool_call in tool_calls:
                    if isinstance(tool_call, dict) and "function" in tool_call:
                        func_name = tool_call["function"].get("name", "unknown")
                        func_args = tool_call["function"].get("arguments", "{}")
                        tool_info.append(f"Tool Call: {func_name}({func_args})")
                return f"Assistant: {content}\n" + "\n".join(tool_info)
            else:
                return f"Assistant: {content}"
        elif role == "tool":
            # Include tool call ID and result
            tool_call_id = message.get("tool_call_id", "unknown")
            return f"Tool Result (ID: {tool_call_id}): {content}"
        elif role == "user":
            return f"User: {content}"
        else:
            return f"{role.title()}: {content}"

    def reset_session(self):
        """Reset the session, clearing messages and stats."""
        self.messages = self._create_initial_messages()
        self.initial_system_prompt = self.messages[0] if self.messages else None
        self.stats = Stats()
        # Reset the compaction flag since we have a fresh session
        self._compaction_performed = False
        
        # Recalculate token count after resetting session
        from .utils import estimate_messages_tokens
        if self.api_handler and hasattr(self.api_handler, 'stats'):
            self.api_handler.stats.current_prompt_size = estimate_messages_tokens(self.messages)
            if config.DEBUG:
                print(f"{config.GREEN} *** Token count recalculated after reset: {self.api_handler.stats.current_prompt_size} tokens{config.RESET}")

    def save_session(self, filename: str = "session.json"):
        """Save the current session to a file."""
        try:
            with open(filename, "w") as f:
                json.dump(self.messages, f, indent=4)
            print(f"\n{config.GREEN} *** Session saved: {filename}{config.RESET}")
        except Exception as e:
            print(
                f"\n{config.RED} *** Error saving session to {filename}: {e}{config.RESET}"
            )

    def load_session(self, filename: str = "session.json"):
        """Load a session from a file."""
        try:
            with open(filename, "r") as f:
                loaded_messages = json.load(f)

            # Clean up loaded messages using our helper function
            clean_messages = [clean_message_for_api(msg) for msg in loaded_messages]

            self.messages = clean_messages
            # Reset the compaction flag since we loaded a new session
            self._compaction_performed = False
            print(f"\n{config.GREEN} *** Session loaded: {filename}{config.RESET}")
            
            # Recalculate token count after loading session
            from .utils import estimate_messages_tokens
            if self.api_handler and hasattr(self.api_handler, 'stats'):
                self.api_handler.stats.current_prompt_size = estimate_messages_tokens(self.messages)
                if config.DEBUG:
                    print(f"{config.GREEN} *** Token count recalculated: {self.api_handler.stats.current_prompt_size} tokens{config.RESET}")
        except Exception as e:
            print(
                f"\n{config.RED} *** Error loading session from {filename}: {e}{config.RESET}"
            )

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
                            if config.DEBUG:
                                print(
                                    f"{config.GREEN} *** Found AICODER.md at: {normalized_path}{config.RESET}"
                                )
                            return content
            except Exception as e:
                if config.DEBUG:
                    print(
                        f"{config.RED} *** Error reading AICODER.md from {path}: {e}{config.RESET}"
                    )
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
                            if config.DEBUG:
                                print(
                                    f"{config.GREEN} *** Found AICODER.md in package data ({package_name}){config.RESET}"
                                )
                            return content
                except Exception:
                    continue
        except Exception as e:
            if config.DEBUG:
                print(
                    f"{config.RED} *** Error reading AICODER.md from package data: {e}{config.RESET}"
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
                                                if config.DEBUG:
                                                    print(
                                                        f"{config.GREEN} *** Found AICODER.md in zipapp ({path_entry}/{zip_path}){config.RESET}"
                                                    )
                                                return content
                                    except Exception:
                                        continue
                        except Exception:
                            continue
        except Exception as e:
            if config.DEBUG:
                print(
                    f"{config.RED} *** Error reading AICODER.md from zipapp: {e}{config.RESET}"
                )

        # If we get here, we couldn't find AICODER.md
        if config.DEBUG:
            print(
                f"{config.YELLOW} *** AICODER.md not found in any expected location{config.RESET}"
            )
            print(f"{config.YELLOW} *** Searched paths: {possible_paths}{config.RESET}")
        return None

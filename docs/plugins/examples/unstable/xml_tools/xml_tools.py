"""
Unified XML Tools Plugin for AI Coder

This plugin provides both XML system prompt generation and XML tool call execution
for LLMs that don't support native tool calling.

Features:
1. Generates XML format system prompts (/xml_tools command)
2. Monkey patches input() to process XML tool calls in assistant messages before showing prompts
"""

import re
import asyncio
import builtins
from typing import Optional, List
from xml.etree import ElementTree as ET

# Global references
_aicoder_ref = None
_xml_tools_enabled = False
_original_input = None
_processed_messages = set()  # Track which messages have been processed
_mcp_tools_cache = None  # Cache for discovered tools
_mcp_tools_last_update = 0  # Timestamp of last cache update


def on_plugin_load():
    """Called when the plugin is loaded"""
    pass


def on_aicoder_init(aicoder_instance):
    """Called when AICoder instance is initialized"""
    try:
        global _aicoder_ref
        _aicoder_ref = aicoder_instance

        # Add commands
        aicoder_instance.command_handlers["/xml_tools"] = _handle_xml_tools_command
        aicoder_instance.command_handlers["/execute_xml"] = _handle_execute_xml_command

        print("[✓] XML Tools plugin loaded successfully")
        print("   - Use '/xml_tools help' for available commands")
        return True
    except Exception as e:
        print(f"[X] Failed to load XML Tools plugin: {e}")
        return False


# === XML SYSTEM PROMPT GENERATION FUNCTIONS ===
# [!]  WARNING: DO NOT DELETE THIS SECTION - CRITICAL FOR XML TOOLS FUNCTIONALITY
# This section generates the XML format system prompt with tool descriptions
# that enables LLMs to use XML tool calls instead of native tool calling
#
# [X] STOP DELETING THIS - IT'S NEEDED FOR THE PLUGIN TO WORK PROPERLY
# This is the THIRD time it's been removed - NEVER remove this again!
# Without this, the AI won't know how to use XML format tool calls!


def _load_internal_tools():
    """Load internal tools and their definitions dynamically."""
    tools = {}

    try:
        # Import the internal tools package
        internal_tools_pkg = __import__(
            "aicoder.tool_manager.internal_tools", fromlist=[""]
        )

        # Get all attributes from the package
        for attr_name in dir(internal_tools_pkg):
            if attr_name.startswith("_"):
                continue

            # Try to get the tool module
            try:
                tool_module = getattr(internal_tools_pkg, attr_name)
                # Check if it has a TOOL_DEFINITION
                if hasattr(tool_module, "TOOL_DEFINITION"):
                    tools[attr_name] = tool_module.TOOL_DEFINITION
            except Exception:
                continue

    except Exception:
        pass

    return tools


def _format_tool_description(tool_name: str, tool_config: dict) -> str:
    """Format a tool description in XML format"""

    # Get tool description
    description = tool_config.get("description", "No description available")

    # Clean up the description - remove financial awareness and other internal notes
    # Simple approach: take only the first part before financial/critical sections
    financial_keywords = [
        "FINANCIAL AWARENESS",
        "CRITICAL FINANCIAL",
        "CRITICAL REQUIREMENT",
    ]
    for keyword in financial_keywords:
        if keyword in description:
            description = description.split(keyword)[0].strip()

    # Also remove any WARNING or Special cases sections
    if "WARNING:" in description:
        description = description.split("WARNING:")[0].strip()
    if "Special cases:" in description:
        description = description.split("Special cases:")[0].strip()

    # Clean up any trailing empty lines or whitespace
    lines = description.split("\n")
    # Remove trailing empty lines
    while lines and not lines[-1].strip():
        lines.pop()
    description = "\n".join(lines).strip()

    # Start the tool description
    tool_desc = f"## {tool_name}\n"
    tool_desc += f"Description: {description}\n"

    # Add parameters if available
    if "parameters" in tool_config and "properties" in tool_config["parameters"]:
        tool_desc += "Parameters:\n"
        params = tool_config["parameters"]
        for param_name, param_info in params["properties"].items():
            required = (
                " (required)"
                if "required" in params and param_name in params["required"]
                else " (optional)"
            )
            param_desc = param_info.get("description", "No description")
            tool_desc += f"- {param_name}: {param_desc}{required}\n"

    # Add usage example
    tool_desc += "\nUsage:\n"
    tool_desc += f"<{tool_name}>\n"

    # Add parameter examples
    if "parameters" in tool_config and "properties" in tool_config["parameters"]:
        params = tool_config["parameters"]
        for param_name, param_info in params["properties"].items():
            # Add a placeholder value based on the parameter type
            if param_name == "path":
                tool_desc += f"  <{param_name}>path/to/file</{param_name}>\n"
            elif param_name == "file_path":
                tool_desc += f"  <{param_name}>path/to/file</{param_name}>\n"
            elif param_name == "command":
                tool_desc += f"  <{param_name}>ls -la</{param_name}>\n"
            elif param_name == "pattern":
                tool_desc += f"  <{param_name}>*.py</{param_name}>\n"
            elif param_name == "text":
                tool_desc += f"  <{param_name}>search text</{param_name}>\n"
            else:
                tool_desc += f"  <{param_name}>value</{param_name}>\n"

    tool_desc += f"</{tool_name}>\n"

    # Add a practical example
    tool_desc += f"\nExample: Requesting to use {tool_name}\n"
    tool_desc += f"<{tool_name}>\n"

    # Add example parameters based on common tool types
    if tool_name == "read_file":
        tool_desc += "  <path>src/main.py</path>\n"
        tool_desc += "</read_file>"
    elif tool_name == "write_file":
        tool_desc += "  <path>new_file.txt</path>\n"
        tool_desc += "  <content>Hello, World!</content>\n"
        tool_desc += "</write_file>"
    elif tool_name == "edit_file":
        tool_desc += "  <file_path>src/main.py</file_path>\n"
        tool_desc += "  <old_string>old content</old_string>\n"
        tool_desc += "  <new_string>new content</new_string>\n"
        tool_desc += "</edit_file>"
    elif tool_name == "list_directory":
        tool_desc += "  <path>.</path>\n"
        tool_desc += "</list_directory>"
    elif tool_name == "run_shell_command":
        tool_desc += "  <command>ls -la</command>\n"
        tool_desc += "</run_shell_command>"
    elif tool_name == "glob":
        tool_desc += "  <pattern>*.py</pattern>\n"
        tool_desc += "</glob>"
    elif tool_name == "grep":
        tool_desc += "  <text>function_name</text>\n"
        tool_desc += "</grep>"
    else:
        # Generic example
        if "parameters" in tool_config and "properties" in tool_config["parameters"]:
            params = tool_config["parameters"]
            for param_name, param_info in params["properties"].items():
                if param_name == "path":
                    tool_desc += f"  <{param_name}>example/path</{param_name}>\n"
                elif param_name == "file_path":
                    tool_desc += f"  <{param_name}>example/file.txt</{param_name}>\n"
                elif param_name == "command":
                    tool_desc += f"  <{param_name}>echo Hello</{param_name}>\n"
                else:
                    tool_desc += f"  <{param_name}>example_value</{param_name}>\n"
        tool_desc += f"</{tool_name}>"

    return tool_desc


def _generate_xml_format_prompt():
    """Generate an XML format system prompt with tool descriptions"""
    global _aicoder_ref

    # Get currently loaded tools from AI Coder
    all_tools = {}

    if hasattr(_aicoder_ref, "tool_manager") and hasattr(
        _aicoder_ref.tool_manager, "registry"
    ):
        registry = _aicoder_ref.tool_manager.registry

        # Add internal tools (but not MCP server entries)
        for tool_name, tool_config in registry.mcp_tools.items():
            # Skip MCP server entries (they're not actual tools)
            if tool_config.get("type") != "mcp-stdio":
                all_tools[tool_name] = tool_config

        # Add tools from MCP servers (these ARE the actual tools)
        for server_name, (process, server_tools) in registry.mcp_servers.items():
            # Add the actual tools from the server, not the server name
            all_tools.update(server_tools)

    # Fallback to basic tools if no registry available
    if not all_tools:
        basic_tools = {
            "read_file": {
                "description": "Read the content from a specified file path."
            },
            "write_file": {
                "description": "Writes content to a specified file path, creating directories if needed."
            },
            "edit_file": {
                "description": "Edits files by replacing text, creating new files, or deleting content."
            },
            "list_directory": {
                "description": "Lists the contents of a specified directory recursively."
            },
            "run_shell_command": {
                "description": "Executes a shell command and returns its output."
            },
            "glob": {
                "description": "Find files matching a pattern using the find command."
            },
            "grep": {
                "description": "Search text in files in the current directory using ripgrep."
            },
            "tree_view": {"description": "Shows directory structure as a tree."},
            "pexpect_tool": {
                "description": "Run interactive programs."
            },  # Add the actual tool name
        }
        all_tools = basic_tools

    # Start with the base system prompt
    prompt = """You are an AI programming assistant integrated into a code editor. You have access to various tools that allow you to interact with the file system and execute commands.

# Rules
1. ALWAYS use the appropriate tool when you need to perform file operations or execute commands
2. NEVER make up or hallucinate tool usage - only use the tools explicitly provided
3. When using tools, follow the exact XML format shown in the tool descriptions
4. When you want to provide a final answer or when no tool is needed, simply respond normally without using any tool
5. ALWAYS ensure you have the necessary context before making changes to files
6. When modifying files, prefer small, focused changes over large rewrites when possible
7. When creating new files, ensure the content is complete and well-formatted
8. When executing commands, explain what the command does and why you're running it
9. If a tool operation fails, analyze the error and try to fix the issue or ask for clarification

# Tools

The following tools are available for you to use when appropriate:"""

    # Add tool descriptions in XML format
    for tool_name, tool_config in all_tools.items():
        tool_description = _format_tool_description(tool_name, tool_config)
        prompt += f"\n\n{tool_description}"

    # Add additional guidance
    prompt += """

# Usage Guidelines

When using tools, ALWAYS follow this format:
<thinking>I need to use a tool to accomplish this task</thinking>

<tool_name>
<parameter1>value1</parameter1>
<parameter2>value2</parameter2>
</tool_name>

For example, to read a file:
<thinking>I need to read the content of app.py to understand the current implementation.</thinking>

<read_file>
<path>app.py</path>
</read_file>

When you have completed the user's request or when no further tool usage is needed, respond normally without using any tool tags.

Remember: Only use the tools listed above, and always follow the exact format specified for each tool."""

    return prompt


def _print_xml_system_prompt():
    """Print XML system prompt to terminal"""
    global _aicoder_ref

    if not hasattr(_aicoder_ref, "tool_manager") or not hasattr(
        _aicoder_ref.tool_manager, "registry"
    ):
        print("[X] Tool registry not available")
        return

    # Generate the XML format system prompt
    prompt = _generate_xml_format_prompt()

    # Print the prompt
    print("\n" + "=" * 80)
    print(" XML Tools System Prompt with Tool Descriptions")
    print("=" * 80)
    print(prompt)
    print("=" * 80)
    print("\n[i] Tip: Use '/xml_tools enable' to add this to the conversation")


# === INPUT MONKEY PATCHING ===


def _patch_input():
    """Monkey patch input() to process XML tool calls and return results directly"""
    global _original_input

    if _original_input is None:
        _original_input = builtins.input

    def patched_input(prompt=""):
        # Check if this is a user prompt (contains ">" but not "Choose")
        if ">" in prompt and "Choose" not in prompt:
            # Lazy load MCP tools on first user prompt
            _lazy_load_mcp_tools()

            # Process any pending XML tool calls and get results
            results = _process_pending_xml_tool_calls_for_input()
            if results:
                # Return the results directly instead of showing the prompt
                # This will be sent as the user's "response" to the AI
                print(f"*** Sending XML tool results to AI: {results[:100]}...")
                return results

        # Call original input for normal prompts
        return _original_input(prompt)

    builtins.input = patched_input


def _restore_input():
    """Restore original input function"""
    global _original_input
    if _original_input is not None:
        builtins.input = _original_input
        _original_input = None


def _process_pending_xml_tool_calls_for_input():
    """Process XML tool calls and return results as a string for input()"""
    global _aicoder_ref, _processed_messages

    if not _aicoder_ref or not hasattr(_aicoder_ref, "message_history"):
        return None

    messages = _aicoder_ref.message_history.messages
    if not messages:
        return None

    # Process assistant messages that contain XML tool calls but haven't been processed
    for i, message in enumerate(reversed(messages)):
        message_id = len(messages) - i - 1  # Get the actual index

        if (
            message.get("role") == "assistant"
            and message.get("content")
            and _contains_xml_tool_calls(message["content"])
            and message_id not in _processed_messages
        ):
            # Mark as processed to avoid duplicate processing
            _processed_messages.add(message_id)

            # Process the XML tool calls
            print("*** Processing XML tool calls in assistant message...")
            tool_results = _parse_and_execute_xml_tools(message["content"])
            if tool_results:
                # Format results as a single string to return from input()
                results_text = "[XML Tool Results]\n" + "\n\n".join(tool_results)
                print("[✓] XML tool calls processed and results ready to send to AI")
                return results_text

            # Only process the most recent unprocessed message
            break

    return None


def _lazy_load_mcp_tools():
    """Lazy load MCP tools when first prompt is shown"""
    global _aicoder_ref, _mcp_tools_cache, _mcp_tools_last_update

    # Only load if we haven't loaded recently (cache for 30 seconds)
    import time

    current_time = time.time()
    if _mcp_tools_cache is not None and (current_time - _mcp_tools_last_update) < 30:
        return

    # Small delay to ensure MCP servers have time to initialize
    time.sleep(0.1)

    print("Lazy loading MCP tools...")
    _mcp_tools_cache = _get_all_available_tools()
    _mcp_tools_last_update = current_time
    print(f"[✓] Loaded {len(_mcp_tools_cache)} available tools")


# === COMMAND HANDLERS ===


def _handle_xml_tools_command(args):
    """Handle /xml_tools command"""
    global _aicoder_ref, _xml_tools_enabled

    if not args:
        args = ["help"]

    command = args[0].lower()

    if command == "help":
        _show_xml_tools_help()
        return False, False
    elif command == "print":
        _print_xml_system_prompt()
        return False, False
    elif command == "enable":
        return _enable_xml_tools()
    elif command == "disable":
        return _disable_xml_tools()
    elif command == "status":
        _show_xml_tools_status()
        return False, False
    else:
        print(f"[X] Unknown xml_tools command: {command}")
        _show_xml_tools_help()
        return False, False


def _show_xml_tools_help():
    """Show help for xml_tools commands"""
    print("""
XML Tools Plugin Commands:
  /xml_tools help     - Show this help message
  /xml_tools print    - Print XML system prompt to terminal
  /xml_tools enable   - Enable XML tools processing
  /xml_tools disable  - Disable XML tools processing
  /xml_tools status   - Show XML tools status
  /execute_xml <xml>  - Manually execute XML tool call (for testing)
""")


def _show_xml_tools_status():
    """Show current XML tools status"""
    global _xml_tools_enabled
    if _xml_tools_enabled:
        print("[✓] XML Tools are currently ENABLED")
    else:
        print("[X] XML Tools are currently DISABLED")


def _enable_xml_tools():
    """Enable XML tools by adding system prompt and monkey patching input"""
    global _aicoder_ref, _xml_tools_enabled

    if _xml_tools_enabled:
        print("[!]  XML Tools are already enabled")
        return False, False

    # Generate and add XML system prompt
    if hasattr(_aicoder_ref, "tool_manager") and hasattr(
        _aicoder_ref.tool_manager, "registry"
    ):
        prompt = _generate_xml_format_prompt()
        system_message = {"role": "system", "content": f"XML TOOLS ENABLED:\n{prompt}"}

        # Add to the beginning of messages (after initial system prompt if it exists)
        if (
            _aicoder_ref.message_history.messages
            and _aicoder_ref.message_history.messages[0]["role"] == "system"
        ):
            # Insert after the initial system prompt
            _aicoder_ref.message_history.messages.insert(1, system_message)
        else:
            # Insert at the beginning
            _aicoder_ref.message_history.messages.insert(0, system_message)

        print("[✓] XML Tools instructions added to conversation")
    else:
        print("[!]  Tool registry not available - XML tools instructions not added")

    # Monkey patch input to automatically process XML tool calls
    _patch_input()

    _xml_tools_enabled = True

    print("[✓] XML Tools ENABLED")
    print("   XML tool calls in assistant messages will be automatically processed")
    print("   Tool results will be sent back to the AI automatically")

    return False, False


def _disable_xml_tools():
    """Disable XML tools by restoring input and removing system prompt"""
    global _aicoder_ref, _xml_tools_enabled

    if not _xml_tools_enabled:
        print("[!]  XML Tools are already disabled")
        return False, False

    # Remove XML tools system message from message history
    if _aicoder_ref:
        messages_to_remove = []
        for i, message in enumerate(_aicoder_ref.message_history.messages):
            if message["role"] == "system" and message["content"].startswith(
                "XML TOOLS ENABLED:"
            ):
                messages_to_remove.append(i)

        # Remove in reverse order to maintain indices
        for i in reversed(messages_to_remove):
            _aicoder_ref.message_history.messages.pop(i)

    # Restore original input function
    _restore_input()

    _xml_tools_enabled = False
    _processed_messages.clear()  # Clear processed messages cache

    print("[✓] XML Tools DISABLED")
    print("   XML tool instructions removed from conversation")
    print("   Original input processing restored")

    return False, False


def _handle_execute_xml_command(args):
    """Handle /execute_xml command - for manual testing"""
    if not args:
        print("[X] Please provide XML tool call to execute")
        print("Example: /execute_xml <read_file><path>test.txt</path></read_file>")
        return False, False

    xml_string = " ".join(args)
    try:
        result = _execute_xml_tool_call(xml_string)
        if result:
            print(f"[✓] XML Tool Execution Result:\n{result}")
        else:
            print("[!]  No result returned from tool execution")
    except Exception as e:
        print(f"[X] Error executing XML tool call: {e}")

    return False, False


def _get_all_available_tools():
    """Get all available tool names including from MCP servers"""
    global _aicoder_ref

    tool_names = []

    # Add basic internal tools
    basic_tools = [
        "read_file",
        "write_file",
        "edit_file",
        "list_directory",
        "run_shell_command",
        "glob",
        "grep",
        "search_files",
        "tree_view",
        "execute_command",
        "search_and_replace",
        "insert_content",
    ]
    tool_names.extend(basic_tools)

    # Add tools from MCP servers if available
    if (
        _aicoder_ref
        and hasattr(_aicoder_ref, "tool_manager")
        and hasattr(_aicoder_ref.tool_manager, "registry")
    ):
        # Add internal tools from registry (but not MCP server entries)
        for (
            tool_name,
            tool_config,
        ) in _aicoder_ref.tool_manager.registry.mcp_tools.items():
            # Skip MCP server entries (they're not actual tools)
            if tool_config.get("type") != "mcp-stdio":
                tool_names.append(tool_name)

        # Add actual tools from MCP servers (these ARE the actual tools)
        for server_name, (
            process,
            server_tools,
        ) in _aicoder_ref.tool_manager.registry.mcp_servers.items():
            try:
                # Add the actual tool names from the server
                tool_names.extend(server_tools.keys())
                # Debug: print discovered tools
                if server_tools:
                    print(
                        f"Found {len(server_tools)} tools from MCP server '{server_name}': {list(server_tools.keys())}"
                    )
            except Exception as e:
                # If there's an issue, continue with other servers
                print(f"[!]  Failed to get tools from MCP server '{server_name}': {e}")
                pass

    # Remove duplicates while preserving order
    seen = set()
    unique_tools = []
    for tool in tool_names:
        if tool not in seen:
            seen.add(tool)
            unique_tools.append(tool)

    return unique_tools


# === XML PROCESSING FUNCTIONS ===


def _contains_xml_tool_calls(response: str) -> bool:
    """Check if response contains XML tool call tags"""
    global _mcp_tools_cache

    # Use cached tools if available, otherwise get tools directly
    if _mcp_tools_cache is not None:
        tool_names = _mcp_tools_cache
    else:
        tool_names = _get_all_available_tools()

    # Check if response contains any tool tags
    for tool_name in tool_names:
        if f"<{tool_name}>" in response and f"</{tool_name}>" in response:
            return True

    return False


def _parse_and_execute_xml_tools(response: str) -> List[str]:
    """Parse and execute XML tool calls from response"""
    global _aicoder_ref

    if not _aicoder_ref:
        return []

    results = []
    tool_calls = _extract_xml_tool_calls(response)

    for i, tool_call in enumerate(tool_calls):
        try:
            # Extract tool name from XML for notification
            try:
                root = ET.fromstring(tool_call)
                tool_name = root.tag
                # Notify user that tool is being executed
                print(
                    f"*** Executing XML tool call {i + 1}/{len(tool_calls)}: {tool_name}"
                )
            except Exception:
                tool_name = "unknown"
                print(f"*** Executing XML tool call {i + 1}/{len(tool_calls)}")

            result = _execute_xml_tool_call(tool_call)
            if result:
                try:
                    root = ET.fromstring(tool_call)
                    tool_name = root.tag
                    results.append(f"[{tool_name} Result]\n{result}")
                except Exception:
                    results.append(f"[XML Tool Result]\n{result}")
        except Exception as e:
            results.append(f"[Error] Failed to execute tool: {e}")

    return results


def _extract_xml_tool_calls(response: str) -> List[str]:
    """Extract XML tool calls from response text"""
    global _mcp_tools_cache

    # Use cached tools if available, otherwise get tools directly
    if _mcp_tools_cache is not None:
        valid_tags = _mcp_tools_cache
    else:
        valid_tags = _get_all_available_tools()

    pattern = r"<(\w+)>(.*?)</\1>"
    matches = re.findall(pattern, response, re.DOTALL)

    tool_calls = []
    for tag, content in matches:
        if tag in valid_tags:
            full_xml = f"<{tag}>{content}</{tag}>"
            tool_calls.append(full_xml)

    return tool_calls


def _execute_xml_tool_call(tool_call_xml: str) -> Optional[str]:
    """Execute a single XML tool call"""
    global _aicoder_ref

    if not _aicoder_ref or not hasattr(_aicoder_ref, "tool_manager"):
        return None

    try:
        root = ET.fromstring(tool_call_xml)
        tool_name = root.tag

        # Extract parameters
        params = {}
        for child in root:
            params[child.tag] = child.text

        # Map tool names (aliases)
        tool_mapping = {
            "execute_command": "run_shell_command",  # Alias
        }

        # Apply mapping if needed
        mapped_tool_name = tool_mapping.get(tool_name, tool_name)

        # Prepare tool arguments
        tool_args = {}
        param_mapping = {
            "path": "path",
            "file_path": "file_path",
            "content": "content",
            "command": "command",
            "text": "text",
            "pattern": "pattern",
            "regex": "regex",
            "file_pattern": "file_pattern",
            "old_string": "old_string",
            "new_string": "new_string",
            "directory": "directory",
            "levels": "levels",
        }

        for xml_param, xml_value in params.items():
            tool_param = param_mapping.get(xml_param, xml_param)
            tool_args[tool_param] = xml_value

        # Execute the tool
        try:
            result = _aicoder_ref.tool_manager.execute_tool(mapped_tool_name, tool_args)
        except Exception as e:
            # If direct tool execution fails, try to execute via MCP server using the actual tool name
            try:
                result = _aicoder_ref.tool_manager.execute_tool(tool_name, tool_args)
            except Exception:
                # If both fail, check if this is an MCP server tool that needs special handling
                # Look for the tool in MCP servers
                found_tool = False
                if (
                    _aicoder_ref
                    and hasattr(_aicoder_ref, "tool_manager")
                    and hasattr(_aicoder_ref.tool_manager, "registry")
                ):
                    for server_name, (
                        process,
                        server_tools,
                    ) in _aicoder_ref.tool_manager.registry.mcp_servers.items():
                        if tool_name in server_tools:
                            # This is an MCP server tool, execute it properly
                            try:
                                result = _aicoder_ref.tool_manager.execute_tool(
                                    tool_name, tool_args
                                )
                                found_tool = True
                                break
                            except Exception:
                                # Continue to next server
                                pass

                if not found_tool:
                    # Re-raise the original error
                    raise e

        # Handle async results
        if asyncio.iscoroutine(result):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(result)
            loop.close()

        # The tool manager returns a tuple (result, tool_config, guidance_content)
        # Extract just the result part
        if isinstance(result, tuple):
            result = result[0]  # First element is the actual result

        return (
            str(result)
            if result is not None
            else "Tool executed successfully (no output)"
        )

    except ET.ParseError as e:
        return f"Error parsing XML: {e}"
    except Exception as e:
        return f"Error executing tool: {e}"


# === PLUGIN METADATA ===

__plugin_name__ = "XML Tools"
__plugin_description__ = "Process XML tool calls in assistant messages"
__plugin_version__ = "1.0.0"

"""
Tool Registry for AI Coder - Handles tool discovery and definitions.
"""

import json
import os
import subprocess
import importlib
from typing import Any, Dict, List

from .. import config
from ..utils import emsg, wmsg


class ToolRegistry:
    """Handles tool discovery, registration, and definitions."""

    def __init__(self, message_history=None):
        self.mcp_tools = {}
        self.mcp_servers = {}  # Maps server names to (process, tools) tuples
        self.message_history = message_history
        self._load_internal_tools()
        self._load_external_tools()

    def _load_internal_tools(self):
        """Load internal tools and their definitions dynamically."""
        try:
            # Import the internal tools package
            internal_tools_pkg = importlib.import_module(
                ".internal_tools", package="aicoder.tool_manager"
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
                        self.mcp_tools[attr_name] = tool_module.TOOL_DEFINITION
                        if config.DEBUG:
                            print(
                                f"{config.GREEN}*** Loaded internal tool: {attr_name}{config.RESET}"
                            )
                except Exception as e:
                    if config.DEBUG:
                        wmsg(
                            f"*** Skipping {attr_name} during internal tool loading: {e}"
                        )
                    continue

        except Exception as e:
            emsg(f"*** Error loading internal tools: {e}")

    def _load_external_tools(self):
        """Load external tools from configuration files."""
        # Check for environment variable override
        mcp_tools_path = os.environ.get("MCP_TOOLS_CONF_PATH")
        if mcp_tools_path:
            filename = mcp_tools_path
        else:
            filename = f"{config.HOME_DIR}/.config/{config.APP_NAME}/mcp_tools.json"
            if not os.path.exists(filename):
                filename = "mcp_tools.json"

        # Counters for loading statistics
        external_tools_count = 0
        mcp_servers_count = 0

        try:
            with open(filename, "r") as f:
                external_tools = json.load(f)

                # Process each tool/server definition
                for name, tool_config in external_tools.items():
                    # Check if the tool/server is disabled
                    if tool_config.get("disabled", False):
                        if config.DEBUG:
                            wmsg(f"*** Skipping disabled tool/server: {name}")
                        continue

                    # Merge external tools, overriding defaults if there are conflicts
                    self.mcp_tools[name] = tool_config

                    # 1) Dynamic description: allow tools to supply a runtime description
                    if isinstance(tool_config, dict) and tool_config.get(
                        "tool_description_command"
                    ):
                        try:
                            if config.DEBUG:
                                print(
                                    f"DEBUG: Running tool_description_command for {name} during load"
                                )
                                print(
                                    f"DEBUG: Current working directory: {os.getcwd()}"
                                )
                            desc_proc = subprocess.run(
                                tool_config["tool_description_command"],
                                shell=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True,
                                timeout=5,
                            )
                            if desc_proc.returncode == 0:
                                desc_lines = (
                                    (desc_proc.stdout or "").strip().splitlines()
                                )
                                if desc_lines:
                                    dynamic_desc = "\n".join(desc_lines).strip()
                                    if dynamic_desc:
                                        self.mcp_tools[name]["description"] = (
                                            dynamic_desc
                                        )
                                        if config.DEBUG:
                                            print(
                                                f"DEBUG: Updated description for {name}"
                                            )
                                            print(
                                                f"DEBUG: New description length: {len(dynamic_desc)}"
                                            )
                            else:
                                print(
                                    f"WARNING: tool_description_command failed for {name} with return code {desc_proc.returncode}"
                                )
                                if config.DEBUG:
                                    print(f"DEBUG: stderr: {desc_proc.stderr}")
                                    print(f"DEBUG: stdout: {desc_proc.stdout}")
                        except subprocess.TimeoutExpired:
                            print(
                                f"ERROR: tool_description_command for {name} timed out"
                            )
                        except Exception as e:
                            print(
                                f"ERROR: Exception in tool_description_command for {name}: {e}"
                            )
                            if config.DEBUG:
                                import traceback

                                traceback.print_exc()

                    # 2) Append to system prompt if command specifies it
                    if isinstance(tool_config, dict) and tool_config.get(
                        "append_to_system_prompt_command"
                    ):
                        try:
                            if config.DEBUG:
                                print(
                                    f"DEBUG: Running append_to_system_prompt_command for {name} during load"
                                )
                                print(
                                    f"DEBUG: Current working directory: {os.getcwd()}"
                                )
                                print(
                                    f"DEBUG: Has message_history: {hasattr(self, 'message_history')}"
                                )
                            append_proc = subprocess.run(
                                tool_config["append_to_system_prompt_command"],
                                shell=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True,
                                timeout=5,
                            )
                            if append_proc.returncode == 0:
                                append_content = (append_proc.stdout or "").strip()
                                if append_content:
                                    # Augment the system prompt
                                    if (
                                        self.message_history
                                        and hasattr(self.message_history, "messages")
                                        and self.message_history.messages
                                    ):
                                        old_len = len(
                                            self.message_history.messages[0]["content"]
                                        )
                                        self.message_history.messages[0]["content"] += (
                                            f"\n\n{append_content}"
                                        )
                                        if config.DEBUG:
                                            print(
                                                f"DEBUG: Appended content to system prompt for {name}"
                                            )
                                            print(
                                                f"DEBUG: Appended content length: {len(append_content)}"
                                            )
                                            print(
                                                f"DEBUG: System prompt length before: {old_len}, after: {len(self.message_history.messages[0]['content'])}"
                                            )
                            else:
                                print(
                                    f"WARNING: append_to_system_prompt_command failed for {name} with return code {append_proc.returncode}"
                                )
                                if config.DEBUG:
                                    print(f"DEBUG: stderr: {append_proc.stderr}")
                                    print(f"DEBUG: stdout: {append_proc.stdout}")
                        except subprocess.TimeoutExpired:
                            print(
                                f"ERROR: append_to_system_prompt_command for {name} timed out"
                            )
                        except Exception as e:
                            print(
                                f"ERROR: Exception in append_to_system_prompt_command for {name}: {e}"
                            )
                            if config.DEBUG:
                                import traceback

                                traceback.print_exc()

                    # Count tools vs servers
                    if tool_config.get("type") == "mcp-stdio":
                        mcp_servers_count += 1
                    else:
                        external_tools_count += 1

                print(
                    f"{config.GREEN}*** Loaded {len(self.mcp_tools)} tools ({len([t for t in self.mcp_tools.values() if t.get('type') == 'internal'])} internal, {external_tools_count} external) and {mcp_servers_count} external MCP servers.{config.RESET}"
                )
                if config.DEBUG:
                    wmsg(f"*** Tool configurations: {self.mcp_tools}")
        except FileNotFoundError:
            # This is not an error, it's expected if the user wants a simple setup
            print(
                f"{config.GREEN}*** Loaded {len(self.mcp_tools)} internal tools. No '{filename}' found.{config.RESET}"
            )
        except json.JSONDecodeError:
            print(
                f"{config.RED}*** Error decoding MCP tool file: {filename}. Using internal tools only.{config.RESET}"
            )
        except Exception as e:
            print(
                f"{config.RED}*** Could not load external MCP tools: {e}. Using internal tools only.{config.RESET}"
            )

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Generate tool definitions for the API."""
        definitions = []
        for name, tool_config in self.mcp_tools.items():
            # Skip stdio servers in tool definitions (they're not directly callable tools)
            if tool_config.get("type") == "mcp-stdio":
                # Discover tools from the server
                server_tools = self._discover_mcp_server_tools(name)
                for tool_name, tool_def in server_tools.items():
                    definitions.append(
                        {
                            "type": "function",
                            "function": {
                                "name": tool_name,
                                "description": tool_def.get("description", ""),
                                "parameters": tool_def.get(
                                    "parameters", {"type": "object", "properties": {}}
                                ),
                            },
                        }
                    )
            else:
                # Create tool definition compatible with both OpenAI and Google APIs
                tool_def = {
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": tool_config.get("description", ""),
                        "parameters": tool_config.get(
                            "parameters", {"type": "object", "properties": {}}
                        ),
                    },
                }

                # Note: auto_approved is an internal field used by the tool manager
                # and should never be sent to the API. It's handled separately in
                # the tool execution logic.

                definitions.append(tool_def)
        return definitions

    def _discover_mcp_server_tools(self, server_name: str) -> Dict[str, Any]:
        """Discover tools available from an MCP stdio server."""
        # Check if we've already discovered tools for this server
        if server_name in self.mcp_servers:
            _, tools = self.mcp_servers[server_name]
            return tools

        # Check if we're running in test mode to avoid launching actual server processes
        import os
        import sys
        from .. import config
        if os.environ.get("AICODER_TEST_MODE") or any('pytest' in arg for arg in sys.argv):
            # In test mode, return empty tools to avoid launching server processes
            if config.DEBUG:
                print(f"DEBUG: Skipping MCP server {server_name} in test mode")
            return {}

        # Get server configuration
        server_config = self.mcp_tools.get(server_name)
        if not server_config or server_config.get("type") != "mcp-stdio":
            return {}

        try:
            # Start the server process
            process = subprocess.Popen(
                server_config["command"].split(),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )

            def send_request(request_data):
                js = json.dumps(request_data) + "\n"
                process.stdin.write(js)
                process.stdin.flush()
                if request_data.get("id") is not None:
                    response_line = process.stdout.readline()
                    return json.loads(response_line)
                return None

            # Initialize the server
            initialize_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {"elicitation": {}},
                    "clientInfo": {
                        "name": f"{config.APP_NAME}-client",
                        "version": "1.0.0",
                    },
                },
            }

            response = send_request(initialize_request)
            if not response or "result" not in response:
                # Clean up the process if initialization fails
                try:
                    process.terminate()
                    process.wait(timeout=1)
                except:
                    try:
                        process.kill()
                    except:
                        pass  # Process might have already terminated
                raise Exception(f"Failed to initialize MCP server: {response}")

            # Send initialized notification
            send_request({"jsonrpc": "2.0", "method": "notifications/initialized"})

            # Get tool list
            tools_response = send_request(
                {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
            )

            if not tools_response or "result" not in tools_response:
                # Clean up the process if tools list fails
                try:
                    process.terminate()
                    process.wait(timeout=1)
                except:
                    try:
                        process.kill()
                    except:
                        pass  # Process might have already terminated
                raise Exception(f"Failed to get tools list: {tools_response}")

            # Store server process and discovered tools
            tools = {
                tool["name"]: tool for tool in tools_response["result"].get("tools", [])
            }
            self.mcp_servers[server_name] = (process, tools)

            # Print discovered tools count
            print(
                f"{config.GREEN}    - Discovered {len(tools)} tools from {server_name}{config.RESET}"
            )

            return tools
        except Exception as e:
            print(f"Error discovering tools from server {server_name}: {e}")
            return {}

    def cleanup_mcp_servers(self):
        """Clean up all MCP server processes when shutting down."""
        for server_name, (process, _) in self.mcp_servers.items():
            try:
                print(f"Terminating MCP server: {server_name}")
                # Try graceful termination first
                process.terminate()
                try:
                    # Wait for up to 2 seconds for process to terminate
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    # Force kill if it doesn't terminate gracefully
                    print(f"Force killing MCP server: {server_name}")
                    process.kill()
                    process.wait()
            except Exception as e:
                print(f"Error terminating MCP server {server_name}: {e}")
        # Clear the servers dictionary
        self.mcp_servers.clear()

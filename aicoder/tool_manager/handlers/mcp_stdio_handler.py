"""
Handler for MCP stdio tools in AI Coder.
"""

import json
from typing import Dict, Any, Tuple

from ...tool_manager.approval_system import CancelAllToolCalls, DENIED_MESSAGE


class McpStdioToolHandler:
    """Handles execution of MCP stdio tools."""

    def __init__(self, tool_registry, stats, approval_system):
        self.tool_registry = tool_registry
        self.stats = stats
        self.approval_system = approval_system

    def handle(self, tool_name: str, arguments: Dict[str, Any], config_module) -> Tuple[str, Dict[str, Any], bool]:
        """Handle execution of an MCP stdio tool."""
        # Get tool configuration from the registry
        tool_config = self.tool_registry.mcp_tools.get(tool_name)
        server_name = None  # Initialize server_name
        
        if not tool_config:
            # If direct lookup fails, check if it's a tool from an MCP server
            # Find which server this tool belongs to
            for name, config in self.tool_registry.mcp_tools.items():
                if config.get("type") == "mcp-stdio":
                    # Check if this server has been discovered and contains this tool
                    if name in self.tool_registry.mcp_servers:
                        _, server_tools = self.tool_registry.mcp_servers[name]
                        if tool_name in server_tools:
                            server_name = name
                            # Use the individual tool's config from the server, not the server config
                            tool_config = dict(server_tools[tool_name])  # Make a copy to avoid modifying original
                            tool_config["server"] = name
                            tool_config["type"] = "mcp-stdio"  # Ensure type is set
                            break
            
            if not tool_config:
                raise Exception(f"MCP tool '{tool_name}' not found in configuration")
        else:
            # Direct lookup succeeded, get server name from config
            server_name = tool_config.get("server")

        # Use the tool name as server name if not specified in config
        server_name = server_name or tool_name
        if server_name not in self.tool_registry.mcp_servers:
            # Discover tools if server not yet initialized
            self.tool_registry._discover_mcp_server_tools(server_name)

        if server_name not in self.tool_registry.mcp_servers:
            raise Exception(f"MCP server {server_name} not available")

        process, _ = self.tool_registry.mcp_servers[server_name]

        def send_request(request_data):
            js = json.dumps(request_data) + "\n"
            process.stdin.write(js)
            process.stdin.flush()
            if request_data.get("id") is not None:
                response_line = process.stdout.readline()
                return json.loads(response_line)
            return None

        try:
            # Handle approval
            auto_approved = tool_config.get("auto_approved", False)
            with_guidance = False  # Initialize with_guidance to handle auto-approved cases
            
            if not auto_approved and not config_module.YOLO_MODE:
                prompt_message = self.approval_system.format_tool_prompt(
                    tool_name, arguments, tool_config
                )
                # Check if prompt_message is a validation error
                if prompt_message.startswith("Error:"):
                    # Return validation error directly
                    return prompt_message, tool_config, False
                approved, with_guidance = (
                    self.approval_system.request_user_approval(
                        prompt_message, tool_name, arguments, tool_config
                    )
                )
                if not approved:
                    # For denied tools, return with guidance flag if requested
                    show_main_prompt = with_guidance
                    return DENIED_MESSAGE, tool_config, show_main_prompt

            # Determine if guidance was requested for successful execution
            show_main_prompt = with_guidance

            # Execute tool call
            tool_call_request = {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": arguments},
            }

            response = send_request(tool_call_request)

            if not response or "result" not in response:
                raise Exception(f"Tool call failed: {response}")

            result = json.dumps(response["result"])

            # Handle guidance prompt after successful execution
            if not auto_approved and not config_module.YOLO_MODE and with_guidance:
                self._handle_guidance_prompt(with_guidance)

            return result, tool_config, show_main_prompt
        except json.JSONDecodeError as e:
            self.stats.tool_errors += 1
            return f"Error executing MCP stdio tool '{tool_name}': {e}", tool_config, False
        except CancelAllToolCalls:
            # Properly handle cancellation requests by re-raising the exception
            raise
        except Exception as e:
            self.stats.tool_errors += 1
            # Check if this is the cancellation exception (string or proper exception)
            if str(e) == "CANCEL_ALL_TOOL_CALLS":
                return "CANCEL_ALL_TOOL_CALLS", tool_config, False
            return f"Error executing MCP stdio tool '{tool_name}': {e}", tool_config, False

    def _handle_guidance_prompt(self, with_guidance):
        """Handle guidance prompt - placeholder that can be implemented by subclasses or handled differently."""
        # This method is expected by the original code but might not be needed
        # in the refactored version. For now, return None to maintain compatibility.
        return None
"""
Handler for JSON-RPC tools in AI Coder.
"""

import urllib.request
import json
from typing import Dict, Any, Tuple

from ...tool_manager.approval_system import CancelAllToolCalls, DENIED_MESSAGE


class JsonRpcToolHandler:
    """Handles execution of JSON-RPC tools."""

    def __init__(self, tool_registry, stats, approval_system):
        self.tool_registry = tool_registry
        self.stats = stats
        self.approval_system = approval_system

    def handle(self, tool_name: str, arguments: Dict[str, Any], config_module) -> Tuple[str, Dict[str, Any], bool]:
        """Handle execution of a JSON-RPC tool."""
        tool_config = self._current_tool_config
        
        try:
            # Handle approval
            auto_approved = tool_config.get("auto_approved", False)
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

            # Determine if guidance was requested
            show_main_prompt = False
            if not auto_approved and not config_module.YOLO_MODE and with_guidance:
                show_main_prompt = True

            # Prepare arguments for execution
            self._prepare_tool_arguments(arguments)

            url = tool_config["url"]
            method = tool_config["method"]
            payload = {
                "jsonrpc": "2.0",
                "method": method,
                "params": arguments,
                "id": 1,
            }
            print(f"   - Executing JSON-RPC call to {url} with method {method}")
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req) as response:
                response_data = response.read()
                # Handle the case where response_data might be a mock object
                if hasattr(response_data, 'decode'):
                    decoded_data = response_data.decode("utf-8")
                else:
                    decoded_data = str(response_data)
                
                rpc_result = json.loads(decoded_data)
                if "error" in rpc_result:
                    self.stats.tool_errors += 1
                    return (
                        json.dumps(rpc_result["error"]),
                        tool_config,
                        False,
                    )
                result = json.dumps(rpc_result.get("result"))

                # Handle guidance prompt after successful execution
                if not auto_approved and not config_module.YOLO_MODE and with_guidance:
                    self._handle_guidance_prompt(
                        with_guidance
                    )

                return result, tool_config, show_main_prompt
        except json.JSONDecodeError as e:
            self.stats.tool_errors += 1
            return f"Error executing JSON-RPC tool '{tool_name}': {e}", tool_config, False
        except CancelAllToolCalls:
            # Properly handle cancellation requests by re-raising the exception
            raise
        except Exception as e:
            self.stats.tool_errors += 1
            # Check if this is the cancellation exception (string or proper exception)
            if str(e) == "CANCEL_ALL_TOOL_CALLS":
                return "CANCEL_ALL_TOOL_CALLS", tool_config, False
            return f"Error executing JSON-RPC tool '{tool_name}': {e}", tool_config, False

    def _handle_guidance_prompt(self, with_guidance):
        """Handle guidance prompt - placeholder that can be implemented by subclasses or handled differently."""
        # This method is expected by the original code but might not be needed
        # in the refactored version. For now, return None to maintain compatibility.
        return None

    def _prepare_tool_arguments(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize and validate arguments for tool execution.

        Returns:
            Normalized arguments dictionary
        """
        # Normalize arguments to ensure they are in dictionary format
        arguments = self._normalize_arguments(arguments)

        # Final validation: ensure arguments is a dictionary for tool execution
        if not isinstance(arguments, dict):
            from ...utils import emsg
            error_msg = (
                "ERROR: Invalid JSON format in arguments. "
                "The JSON string could not be parsed into a dictionary. "
                "Please ensure your JSON arguments are properly formatted with correct syntax, "
                "double quotes for strings, and proper escaping."
            )
            emsg(f" * {error_msg}")
            raise ValueError(error_msg)

        return arguments

    def _normalize_arguments(self, arguments):
        """
        Normalize arguments to ensure they are in dictionary format.

        Note: Arguments should already be parsed by the time this is called,
        but we handle the case where they might still be a string for backward compatibility.
        """
        from ...utils import parse_json_arguments
        import json

        # Handle any remaining string arguments (shouldn't happen if we parse earlier)
        if isinstance(arguments, str):
            try:
                arguments = parse_json_arguments(arguments)
            except (json.JSONDecodeError, ValueError):
                # If parsing fails, return the original value
                pass

        # Ensure arguments is a dictionary before using **
        if not isinstance(arguments, dict):
            # If arguments is still not a dict, try to convert common types
            if isinstance(arguments, list) and len(arguments) > 0:
                # If it's a list, use the first element if it's a dict
                if isinstance(arguments[0], dict):
                    arguments = arguments[0]
                else:
                    # Wrap the list in a dict
                    arguments = {"value": arguments}
            elif isinstance(arguments, (int, float, bool, type(None))):
                # If it's a primitive, wrap it in a dict
                arguments = {"value": arguments}
            elif isinstance(arguments, str):
                # If it's still a string, wrap it in a dict as content
                arguments = {"content": arguments}
            else:
                # Default to empty dict as fallback
                arguments = {}

        return arguments
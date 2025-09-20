"""
Tool parameter validation for AI Coder.
"""

from typing import Dict, Any, Tuple
from ..config import DEBUG, RED, RESET


def validate_tool_parameters(
    tool_name: str, tool_definition: Dict[str, Any], arguments: Dict[str, Any]
) -> Tuple[bool, str]:
    """
    Validate tool parameters against tool definition.

    Args:
        tool_name: Name of the tool being called
        tool_definition: Tool definition with parameter schema
        arguments: Arguments provided by the AI

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        # Get parameters schema
        parameters = tool_definition.get("parameters", {})
        if not parameters:
            # If no parameters defined, accept any arguments
            return True, ""

        properties = parameters.get("properties", {})
        required_params = parameters.get("required", [])
        additional_properties = parameters.get("additionalProperties", True)

        # Check for required parameters
        missing_params = [param for param in required_params if param not in arguments]
        if missing_params:
            return False, (
                f"Missing required parameters: {missing_params}\n"
                f"Required parameters: {required_params}\n"
                f"Provided parameters: {list(arguments.keys())}"
            )

        # Check for invalid parameters if additionalProperties is False
        if not additional_properties:
            valid_params = set(properties.keys())
            invalid_params = set(arguments.keys()) - valid_params
            if invalid_params:
                return False, (
                    f"Invalid parameters: {list(invalid_params)}\n"
                    f"Valid parameters: {list(valid_params)}\n"
                    f"Required parameters: {required_params}"
                )

        # Validate parameter types (basic validation)
        for param_name, param_value in arguments.items():
            if param_name in properties:
                param_schema = properties[param_name]
                param_type = param_schema.get("type")

                if param_type:
                    if not _validate_type(param_value, param_type):
                        expected_type = _get_type_name(param_type)
                        actual_type = type(param_value).__name__
                        return False, (
                            f"Invalid type for parameter '{param_name}': "
                            f"expected {expected_type}, got {actual_type}"
                        )

        return True, ""

    except Exception as e:
        if DEBUG:
            print(f"{RED} *** Error during tool parameter validation: {e}{RESET}")
        return True, ""  # Allow the tool to run if validation fails


def validate_function_signature(
    tool_name: str,
    tool_definition: Dict[str, Any],
    arguments: Dict[str, Any],
    additional_params: list,
) -> Tuple[bool, str]:
    """
    Validate that the provided arguments match the tool definition.

    Args:
        tool_name: Name of the tool being called
        tool_definition: Tool definition with parameter schema
        arguments: Arguments provided by the AI
        additional_params: Additional parameters that will be added by the executor

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        # Get parameters schema
        parameters = tool_definition.get("parameters", {})
        if not parameters:
            # If no parameters defined, accept any arguments
            return True, ""

        properties = parameters.get("properties", {})
        required_params = parameters.get("required", [])

        # Check for required parameters, excluding those provided by the executor
        missing_params = [
            param
            for param in required_params
            if param not in arguments and param not in additional_params
        ]
        if missing_params:
            return False, (
                f"Missing required parameters: {missing_params}\n"
                f"Required parameters: {required_params}\n"
                f"Provided arguments: {list(arguments.keys())}\n"
                f"Note: The following parameters are automatically provided by the system: {additional_params}"
            )

        # Check for unexpected parameters if additionalProperties is False
        additional_properties = parameters.get("additionalProperties", True)
        if not additional_properties:
            valid_params = set(properties.keys())
            # Include parameters that will be provided by the executor
            valid_params.update(additional_params)
            invalid_params = set(arguments.keys()) - valid_params
            if invalid_params:
                return False, (
                    f"Invalid parameters: {list(invalid_params)}\n"
                    f"Valid parameters: {list(valid_params)}\n"
                    f"Required parameters: {required_params}"
                )

        return True, ""

    except Exception as e:
        if DEBUG:
            print(f"{RED} *** Error during function signature validation: {e}{RESET}")
        # Don't fail validation on inspection errors
        return True, ""


def _validate_type(value: Any, expected_type: str) -> bool:
    """Validate that a value matches the expected type."""
    type_mapping = {
        "string": str,
        "integer": int,
        "number": (int, float),
        "boolean": bool,
        "array": list,
        "object": dict,
    }

    expected_python_type = type_mapping.get(expected_type)
    if expected_python_type is None:
        return True  # Unknown type, allow it

    if isinstance(expected_python_type, tuple):
        return isinstance(value, expected_python_type)
    else:
        return isinstance(value, expected_python_type)


def _get_type_name(type_spec: str) -> str:
    """Get human-readable type name."""
    return type_spec


def format_validation_error(
    tool_name: str,
    error_message: str,
    tool_definition: Dict[str, Any],
    arguments: Dict[str, Any],
) -> str:
    """
    Format a validation error into an AI-friendly message.

    Args:
        tool_name: Name of the tool
        error_message: Validation error message
        tool_definition: Tool definition
        arguments: Arguments that caused the error

    Returns:
        Formatted error message for the AI
    """
    try:
        parameters = tool_definition.get("parameters", {})
        required_params = parameters.get("required", [])
        properties = parameters.get("properties", {})

        # Build usage example
        usage_parts = []
        for param in required_params:
            if param in properties:
                usage_parts.append(f"{param}=<value>")
            else:
                usage_parts.append(f"{param}=<value>")

        usage_example = (
            f"{tool_name}({', '.join(usage_parts)})"
            if usage_parts
            else f"{tool_name}()"
        )

        # Build detailed parameter info
        param_descriptions = []
        for param_name, param_info in properties.items():
            param_type = param_info.get("type", "string")
            description = param_info.get("description", "No description available")
            required = param_name in required_params
            param_descriptions.append(
                f"  {param_name} ({param_type}){' - REQUIRED' if required else ''}: {description}"
            )

        param_info = (
            "\n".join(param_descriptions)
            if param_descriptions
            else "No parameters defined"
        )

        return (
            f"ERROR: Invalid parameters for tool '{tool_name}'\n"
            f"Please use the correct syntax:\n\n"
            f"Correct usage: {usage_example}\n\n"
            f"Parameter definitions:\n{param_info}"
        )

    except Exception as e:
        if DEBUG:
            print(f"{RED} *** Error formatting validation error: {e}{RESET}")
        return f"ERROR: Invalid parameters for tool '{tool_name}': {error_message}"


def get_tool_usage_example(tool_name: str, tool_definition: Dict[str, Any]) -> str:
    """Generate a usage example for a tool."""
    try:
        parameters = tool_definition.get("parameters", {})
        required_params = parameters.get("required", [])
        properties = parameters.get("properties", {})

        usage_parts = []
        for param in required_params:
            if param in properties:
                usage_parts.append(f"{param}=<value>")
            else:
                usage_parts.append(f"{param}=<value>")

        return (
            f"{tool_name}({', '.join(usage_parts)})"
            if usage_parts
            else f"{tool_name}()"
        )

    except Exception:
        return f"{tool_name}()"

"""
Tools Manager Plugin for AI Coder

This plugin provides commands to temporarily list, enable, and disable tools during a session.
"""

# Store disabled tools during the session
_disabled_tools = {}


def on_plugin_load():
    """Called when the plugin is loaded"""
    pass


def on_aicoder_init(aicoder_instance):
    """Called when AICoder instance is initialized"""
    try:
        # Store reference to aicoder instance
        global _aicoder_ref
        _aicoder_ref = aicoder_instance

        # Add /tools command to the command registry
        aicoder_instance.command_handlers["/tools"] = _handle_tools_command

        print("✅ Tools manager plugin loaded successfully")
        print("   - /tools command available")
        print(
            "   - Use /tools to list tools, /tools enable/disable <tool> to manage them"
        )
        return True
    except Exception as e:
        print(f"❌ Failed to load tools manager plugin: {e}")
        return False


def _handle_tools_command(args):
    """Handle /tools command"""
    global _aicoder_ref, _disabled_tools

    if not _aicoder_ref:
        print("❌ Tools functionality not available")
        return False, False

    if not hasattr(_aicoder_ref, "tool_manager") or not hasattr(
        _aicoder_ref.tool_manager, "registry"
    ):
        print("❌ Tool registry not available")
        return False, False

    if not args:
        # List all tools
        _list_tools()
        return False, False

    command = args[0].lower()

    if command in ["list", "ls"]:
        _list_tools()
        return False, False
    elif command == "enable":
        if len(args) < 2:
            print("❌ Usage: /tools enable <tool_name>")
            return False, False
        _enable_tool(args[1])
        return False, False
    elif command == "disable":
        if len(args) < 2:
            print("❌ Usage: /tools disable <tool_name>")
            return False, False
        _disable_tool(args[1])
        return False, False
    elif command == "info":
        if len(args) < 2:
            print("❌ Usage: /tools info <tool_name>")
            return False, False
        _tool_info(args[1])
        return False, False
    else:
        print(f"❌ Unknown command: {command}")
        print("Available commands: list, enable, disable, info")
        return False, False


def _list_tools():
    """List all available tools"""
    global _aicoder_ref, _disabled_tools

    if not hasattr(_aicoder_ref, "tool_manager") or not hasattr(
        _aicoder_ref.tool_manager, "registry"
    ):
        print("❌ Tool registry not available")
        return

    # Get currently loaded tools
    current_tools = _aicoder_ref.tool_manager.registry.mcp_tools

    if not current_tools and not _disabled_tools:
        print("No tools available")
        return

    print("\n📋 Available Tools:")
    print("=" * 80)

    # Combine active and disabled tools
    all_tools = {}

    # Add active tools
    for tool_name, tool_config in current_tools.items():
        all_tools[tool_name] = {"config": tool_config, "status": "✅ Enabled"}

    # Add disabled tools
    for tool_name, tool_data in _disabled_tools.items():
        all_tools[tool_name] = {"config": tool_data["config"], "status": "❌ Disabled"}

    # Sort tools by name
    sorted_tools = sorted(all_tools.items())

    for tool_name, tool_data in sorted_tools:
        tool_config = tool_data["config"]
        status = tool_data["status"]
        description = tool_config.get("description", "No description")

        # Truncate long descriptions
        if len(description) > 50:
            description = description[:47] + "..."

        print(f"{tool_name:<25} {status:<12} {description}")


def _disable_tool(tool_name):
    """Temporarily disable a tool by moving it to the disabled dict"""
    global _aicoder_ref, _disabled_tools

    if not hasattr(_aicoder_ref, "tool_manager") or not hasattr(
        _aicoder_ref.tool_manager, "registry"
    ):
        print("❌ Tool registry not available")
        return

    # Check if tool is currently enabled
    current_tools = _aicoder_ref.tool_manager.registry.mcp_tools
    if tool_name not in current_tools:
        # Check if already disabled
        if tool_name in _disabled_tools:
            print(f"❌ Tool '{tool_name}' is already disabled")
        else:
            print(f"❌ Tool '{tool_name}' not found")
        return

    # Move tool to disabled dict
    tool_config = current_tools[tool_name]
    _disabled_tools[tool_name] = {"config": tool_config}

    # Remove from active tools
    del current_tools[tool_name]

    print(f"✅ Tool '{tool_name}' disabled successfully")
    print("💡 Note: This is temporary for this session only")


def _enable_tool(tool_name):
    """Re-enable a temporarily disabled tool"""
    global _aicoder_ref, _disabled_tools

    if not hasattr(_aicoder_ref, "tool_manager") or not hasattr(
        _aicoder_ref.tool_manager, "registry"
    ):
        print("❌ Tool registry not available")
        return

    # Check if tool is currently disabled
    if tool_name not in _disabled_tools:
        # Check if already enabled
        current_tools = _aicoder_ref.tool_manager.registry.mcp_tools
        if tool_name in current_tools:
            print(f"❌ Tool '{tool_name}' is already enabled")
        else:
            print(f"❌ Tool '{tool_name}' not found")
        return

    # Move tool back to active tools
    tool_data = _disabled_tools[tool_name]
    _aicoder_ref.tool_manager.registry.mcp_tools[tool_name] = tool_data["config"]

    # Remove from disabled tools
    del _disabled_tools[tool_name]

    print(f"✅ Tool '{tool_name}' enabled successfully")


def _tool_info(tool_name):
    """Show detailed information about a tool"""
    global _aicoder_ref, _disabled_tools

    if not hasattr(_aicoder_ref, "tool_manager") or not hasattr(
        _aicoder_ref.tool_manager, "registry"
    ):
        print("❌ Tool registry not available")
        return

    # Get tools from registry
    current_tools = _aicoder_ref.tool_manager.registry.mcp_tools

    # Check if tool exists
    tool_config = None
    status = "Unknown"

    if tool_name in current_tools:
        tool_config = current_tools[tool_name]
        status = "✅ Enabled"
    elif tool_name in _disabled_tools:
        tool_config = _disabled_tools[tool_name]["config"]
        status = "❌ Disabled"

    if not tool_config:
        print(f"❌ Tool '{tool_name}' not found")
        return

    print(f"\n🔍 Tool Information: {tool_name}")
    print("=" * 50)
    print(f"Description: {tool_config.get('description', 'No description')}")
    print(f"Type: {tool_config.get('type', 'Unknown')}")
    print(f"Status: {status}")

    # Show parameters if available
    if "parameters" in tool_config:
        print("\nParameters:")
        params = tool_config["parameters"]
        if "properties" in params:
            for param_name, param_info in params["properties"].items():
                required = (
                    " (required)"
                    if "required" in params and param_name in params["required"]
                    else ""
                )
                print(
                    f"  - {param_name}: {param_info.get('description', 'No description')}{required}"
                )

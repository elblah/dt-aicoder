"""
Disable update_plan Plugin for AI Coder

This plugin completely removes the update_plan tool from the tool registry,
preventing the AI from seeing or using it. This saves API requests and costs
for users who prefer to let the AI work without progress tracking.

Usage:
1. Copy this file to ~/.config/aicoder/plugins/
2. Run AI Coder - update_plan will be completely hidden from the AI
3. To re-enable, simply remove this plugin file

Benefits:
- Saves API requests (and money) by preventing update_plan calls
- Completely hides the tool from AI visibility
- No-op implementation that doesn't waste tokens
- Easy to enable/disable without code changes
"""


def on_plugin_load():
    """Called when the plugin is loaded - removes update_plan from tool registry"""
    # Nothing to do at load time - we need the AICoder instance first
    pass


def on_aicoder_init(aicoder_instance):
    """Called when AICoder instance is initialized - removes update_plan tool"""
    try:
        # Access the tool manager and registry
        if hasattr(aicoder_instance, "tool_manager") and hasattr(
            aicoder_instance.tool_manager, "registry"
        ):
            registry = aicoder_instance.tool_manager.registry

            # Completely remove update_plan from the tool registry
            if "update_plan" in registry.mcp_tools:
                del registry.mcp_tools["update_plan"]
                print("✅ update_plan tool completely removed from AI visibility")
                print("   - AI will not see or attempt to use this tool")
                print("   - No API requests will be wasted on progress tracking")
                print("   - Cost savings achieved for request-limited accounts")
            else:
                print(
                    "ℹ️  update_plan tool not found in registry (may already be removed)"
                )
        else:
            print("❌ Could not access tool registry to remove update_plan")

        return True
    except Exception as e:
        print(f"❌ Failed to remove update_plan tool: {e}")
        return False


# Only execute on load when running as a plugin
if __name__ != "__main__":
    on_plugin_load()

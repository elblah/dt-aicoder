"""
Integrated Plan Plugin for AI Coder

This plugin provides a complete plan management system with:
1. A /plan command for users to view and manage plans
2. A custom update_plan tool implementation for the AI to track progress
3. Memory storage for plan persistence during sessions
"""

# Global storage for plans (in-memory during session)
_last_plan_storage = {"plan_text": None, "explanation": None}

# Custom update_plan tool definition
UPDATE_PLAN_TOOL_DEFINITION = {
    "type": "internal",
    "auto_approved": True,
    "hide_results": True,
    "hide_arguments": True,
    "approval_excludes_arguments": True,
    "hidden_parameters": ["plan_text", "explanation"],
    "name": "update_plan",
    "description": "Track and display task progress to the user using text-based input. Use this tool to show what steps you're working on and keep the user informed about your progress. Provide a formatted plan text with clear checkboxes.",
    "parameters": {
        "type": "object",
        "properties": {
            "plan_text": {
                "type": "string",
                "description": "Formatted plan text with clear checkboxes (e.g., '- [x] Completed task\\n- [ ] Pending task')",
            },
            "explanation": {
                "type": "string",
                "description": "Optional explanation or note about the plan",
            },
        },
        "required": ["plan_text"],
    },
}


def execute_update_plan(plan_text: str, explanation: str = None, stats=None) -> str:
    """
    Custom update_plan tool implementation.

    This tool displays a task plan to the user with progress tracking.
    The AI can call this tool to show what steps it's working on.

    Args:
        plan_text: Formatted plan text with clear checkboxes
        explanation: Optional explanation/note (string)
        stats: Stats object (unused but required for internal tools)

    Returns:
        String with tool execution result
    """
    # Validate that plan_text is a string
    if not isinstance(plan_text, str):
        raise ValueError("Invalid plan_text format: plan_text must be a string.")

    # Validate explanation if provided
    if explanation is not None and not isinstance(explanation, str):
        raise ValueError("Invalid explanation format: Explanation must be a string.")

    # Store the plan in global storage
    global _last_plan_storage
    _last_plan_storage["plan_text"] = plan_text
    _last_plan_storage["explanation"] = explanation

    # Format and display the plan
    _display_plan(plan_text, explanation)

    return "Plan updated successfully"


def _display_plan(plan_text: str, explanation: str = None) -> None:
    """
    Display the plan in a user-friendly format.

    Args:
        plan_text: Formatted plan text with clear checkboxes
        explanation: Optional explanation text
    """
    # Extract plan title (first line starting with # or use a generic title)
    lines = plan_text.strip().split("\n")
    title = "Plan Update"
    for line in lines:
        # Only use lines that start with # as titles, not task lines
        if line.strip().startswith("#"):
            title = line.strip().lstrip("#").strip()
            break

    # Count completed and total tasks
    completed = 0
    total = 0

    for line in lines:
        # Count checkboxes
        if "[x]" in line or "[X]" in line:
            completed += 1
            total += 1
        elif "[ ]" in line:
            total += 1

    # Create simple progress bar
    width = 10
    filled = int((completed * width) / max(total, 1)) if total > 0 else 0
    empty = width - filled

    progress_bar = "█" * filled + "░" * empty
    header = f"📋 {title} [{progress_bar}] {completed}/{total}"
    print(header)
    print()

    # Print plan text
    if not plan_text.strip():
        print("(no steps provided)")
    else:
        # Print each line of the plan with the emojis from the previous JSON version
        for line in lines:
            # Add appropriate markers for different line types
            stripped_line = line.strip()
            if stripped_line.startswith("#"):
                # Header line - use the same emoji as before
                print(f"📋 {stripped_line}")
            elif "[x]" in line or "[X]" in line:
                # Completed task - use the same emoji as before
                print(f"  ✅ {line.replace('[x]', '').replace('[X]', '').strip()}")
            elif "[ ]" in line:
                # Pending task - use the same emoji as before
                print(f"  ⏸️ {line.replace('[ ]', '').strip()}")
            elif stripped_line.startswith("-"):
                # List item without checkbox - use a neutral marker
                print(f"  • {line[1:].strip()}")
            elif stripped_line:
                # Regular text
                print(f"  {line}")
            else:
                # Empty line
                print()

    # Print explanation if provided (moved to the end with proper separation)
    if explanation:
        print()
        print(f"note: {explanation}")

    # Add blank line for separation
    print()


def on_plugin_load():
    """Called when the plugin is loaded"""
    pass


def on_aicoder_init(aicoder_instance):
    """Called when AICoder instance is initialized"""
    try:
        # Store reference to aicoder instance for access to message history
        global _aicoder_ref
        _aicoder_ref = aicoder_instance

        # Add /plan command to the command registry
        aicoder_instance.command_handlers["/plan"] = _handle_plan_command

        # Add plan storage to the aicoder instance
        aicoder_instance.last_plan = None
        aicoder_instance.last_plan_explanation = None

        # Add the custom update_plan tool to the tool registry
        if hasattr(aicoder_instance, "tool_manager") and hasattr(
            aicoder_instance.tool_manager, "registry"
        ):
            # Add the tool definition to the registry
            aicoder_instance.tool_manager.registry.mcp_tools["update_plan"] = (
                UPDATE_PLAN_TOOL_DEFINITION
            )

            # Override the tool execution to use our custom implementation
            # We need to patch the executor to use our function
            original_execute_tool = aicoder_instance.tool_manager.executor.execute_tool

            def patched_execute_tool(tool_name, arguments, tool_index=0, total_tools=0):
                if tool_name == "update_plan":
                    # Use our custom implementation
                    try:
                        plan_text = arguments.get("plan_text", "")
                        explanation = arguments.get("explanation", None)
                        result = execute_update_plan(plan_text, explanation)

                        # Store in aicoder instance as well
                        if hasattr(aicoder_instance, "last_plan"):
                            aicoder_instance.last_plan = plan_text
                            aicoder_instance.last_plan_explanation = explanation

                        # Return the tool configuration as the second element, not True
                        return result, UPDATE_PLAN_TOOL_DEFINITION, None
                    except Exception as e:
                        return (
                            f"Error executing update_plan: {e}",
                            UPDATE_PLAN_TOOL_DEFINITION,
                            None,
                        )
                else:
                    # Use original implementation for other tools
                    return original_execute_tool(
                        tool_name, arguments, tool_index, total_tools
                    )

            aicoder_instance.tool_manager.executor.execute_tool = patched_execute_tool

        # Add comprehensive information about plan functionality to the system prompt
        if (
            hasattr(aicoder_instance, "message_history")
            and aicoder_instance.message_history.messages
        ):
            system_prompt = aicoder_instance.message_history.messages[0]
            if isinstance(system_prompt, dict) and "content" in system_prompt:
                plan_info = """
                
Task Planning with update_plan Tool

The AI Coder includes an update_plan tool inspired by OpenAI Codex CLI that allows you to track and display task progress to users. This tool helps demonstrate your understanding of tasks and conveys your approach clearly using text-based input.

When to Use the update_plan Tool:
Use the update_plan tool when:
- Working on complex, multi-step tasks
- You want to communicate your approach to the user
- There are logical phases or dependencies in your work
- You want to provide intermediate checkpoints for feedback
- The task has ambiguity that benefits from outlining high-level goals

How to Use the update_plan Tool:
1. Create a plan with meaningful, logically ordered steps
2. Use clear checkbox formatting:
   - [x] or [X] - Completed steps
   - [ ] - Pending steps
3. Organize with headers using # for main title and ## for sections
4. Include an explanation when changing plans significantly

Best Practices for update_plan:
- Break tasks into meaningful steps that are easy to verify
- Update the plan before moving to the next step
- Use clear, concise step descriptions
- Don't pad simple work with unnecessary steps
- Include an explanation when the rationale for changes isn't obvious

Example Usage:
{
  "name": "update_plan",
  "arguments": {
    "plan_text": "# Plan: Build New Website\\n\\n## Phase 1: Project Setup\\n - [x] Initialize git repository\\n - [x] Create project structure (folders for src, assets, etc.)\\n - [x] Install dependencies (e.g., React, Webpack)\\n\\n## Phase 2: Develop Core Features\\n - [x] Create homepage component\\n - [ ] Implement user authentication\\n - [ ] Design the database schema\\n\\n## Phase 3: Deployment\\n - [ ] Write unit tests\\n - [ ] Configure production build\\n - [ ] Deploy to hosting provider",
    "explanation": "Moving from development to deployment phase"
  }
}

The tool will display a visual progress indicator with:
- ✅ Completed steps
- ⏸️ Pending steps
- 📋 Plan title

This helps users understand what you're working on and how much progress has been made.

Users can also use the /plan command to view the current plan:
- /plan - Shows the current stored plan
- /plan update - Forces a new plan request from the AI
"""
                if (
                    "Task Planning with update_plan Tool"
                    not in system_prompt["content"]
                ):
                    system_prompt["content"] += plan_info

        print("✅ Integrated plan plugin loaded successfully")
        print("   - /plan command available")
        print("   - Custom update_plan tool registered")
        print("   - AI instructions added to system prompt")
        print("   - Use /plan to view plans, /plan update to force updates")
        return True
    except Exception as e:
        print(f"❌ Failed to load integrated plan plugin: {e}")
        return False


def _handle_plan_command(args):
    """Handle /plan command - show last plan or request new one."""
    global _aicoder_ref, _last_plan_storage

    if not _aicoder_ref:
        print("❌ Plan functionality not available")
        return False, False

    if args and args[0].lower() in ["update", "force", "refresh"]:
        # Force a new plan request by asking the AI to call update_plan
        print("\n*** Requesting new plan from AI...")
        _aicoder_ref.message_history.add_user_message(
            "Please provide an updated plan using the update_plan tool to track your current progress."
        )
        return False, True  # Run API call

    # Check for stored plan in global storage
    plan_text = _last_plan_storage.get("plan_text")
    explanation = _last_plan_storage.get("explanation")

    # Show the last plan if available
    if plan_text:
        print("\n*** Current Plan:")
        _display_plan(plan_text, explanation)
        return False, False
    else:
        # No plan exists, ask AI to provide one
        print("\n*** No plan found. Requesting plan from AI...")
        _aicoder_ref.message_history.add_user_message(
            "Please provide a plan using the update_plan tool to track your current progress and goals."
        )
        return False, True  # Run API call

"""
Autopilot plugin for AI Coder.
"""

import os
from typing import Tuple, Optional, List

PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))


def get_plugin_info():
    """Return plugin information."""
    return {
        "name": "Autopilot",
        "version": "1.0.0",
        "description": "Adds autopilot functionality to AI Coder",
        "author": "AI Coder Team",
        "dependencies": [],
    }


def on_aicoder_init(aicoder_instance):
    """Called when AICoder is initialized."""
    # Add autopilot attributes to the AICoder instance
    aicoder_instance.autopilot_enabled = False
    aicoder_instance.autopilot_response = None

    # Add command handlers
    aicoder_instance.command_handlers["/autopilot"] = _handle_autopilot_command
    aicoder_instance.command_handlers["/a"] = _handle_autopilot_command

    # Store reference to our handler functions
    aicoder_instance._autopilot_handle_logic = _handle_autopilot_logic
    aicoder_instance._autopilot_handle_command = _handle_autopilot_command


def _handle_autopilot_logic(aicoder_instance) -> Tuple[bool, Optional[str]]:
    """Handles autopilot logic before user input."""
    from aicoder.config import DEBUG, GREEN, YELLOW, RED, RESET
    from aicoder.utils import safe_strip

    # Print current autopilot value
    status = "on" if aicoder_instance.autopilot_enabled else "off"

    if (
        len(aicoder_instance.message_history.messages) > 0
        and aicoder_instance.message_history.messages[-1].get("role", None)
        == "assistant"
    ):
        if aicoder_instance.autopilot_enabled:
            print(f"\n{GREEN}Current autopilot value: {status}{RESET}")
    else:
        return True, None

    # If autopilot is not enabled, continue with normal input
    if not aicoder_instance.autopilot_enabled:
        return True, None

    # If we have a cached response, use it
    if aicoder_instance.autopilot_response:
        response = aicoder_instance.autopilot_response
        aicoder_instance.autopilot_response = None
        return False, response

    print(f"\n{GREEN}Checking if a decision has to be made...{RESET}")

    # Create autopilot decision prompt
    autopilot_messages = []
    autopilot_messages.append(
        {
            "role": "system",
            "content": (
                "You are in autopilot mode. Decide what to do next based on the last assistant message. "
                "Respond with exactly one of these options:\n"
                "1. If you have a clear next step, respond with your action.\n"
                "2. If the task is complete, respond with: DONE\n"
                "3. If you are unsure, choose whatever seems to be possible based on the options available. Choose something just to keep the activities going.\n"
                "4. Only if you can't choose anything, but use it only as a LAST LAST LAST RESORT respond with: ASK_USER:<your question>\n\n"
                "Be concise and focused on the next immediate step."
            ),
        }
    )
    # Only include the last assistant message to avoid issues with tool call results
    # that may contain special characters or ANSI codes
    if len(aicoder_instance.message_history.messages) > 0:
        last_message = aicoder_instance.message_history.messages[-1]
        if last_message.get("role") == "assistant":
            # Clean the message using our helper function
            from aicoder.message_history import clean_message_for_api

            clean_last_message = clean_message_for_api(last_message)
            autopilot_messages.append(clean_last_message)

    # Add a clear prompt at the end
    autopilot_messages.append(
        {
            "role": "user",
            "content": "What should be the next step in autopilot mode? Respond with exactly one of the options from the system prompt.",
        }
    )

    if DEBUG:
        print(f"{GREEN} *** Autopilot messages count: {len(autopilot_messages)}{RESET}")

    # Get decision from AI (disable streaming and tools for autopilot decisions to ensure reliable response handling)
    if DEBUG:
        print(f"{GREEN} *** Autopilot request messages: {autopilot_messages}{RESET}")
    response = aicoder_instance._make_api_request(
        autopilot_messages, disable_streaming_mode=True, disable_tools=True
    )
    if DEBUG:
        print(f"{GREEN} *** Autopilot response: {response}{RESET}")
        if response and "choices" in response and response["choices"]:
            choice = response["choices"][0]
            message = choice.get("message", {})
            print(
                f"{GREEN} *** Autopilot response content: '{message.get('content', '')}'{RESET}"
            )

    if response is None or "choices" not in response or not response["choices"]:
        print(f"{RED}Autopilot decision failed. Returning to manual mode.{RESET}")
        aicoder_instance.autopilot_enabled = False
        return True, None

    # Extract content properly handling both regular and streaming responses
    choice = response["choices"][0]
    message = choice.get("message", {})

    if DEBUG:
        print(f"{GREEN} *** Autopilot message keys: {message.keys()}{RESET}")

    # Handle streaming responses which may have already been printed
    if message.get("_streaming_response"):
        # For streaming responses, the content was already printed, but we still need to process it
        # The content should still be available in the message
        decision = safe_strip(message.get("content", ""), default="no decision content")
        if DEBUG:
            print(f"{GREEN} *** Autopilot decision (from streaming): {decision}{RESET}")
    else:
        # Regular response handling
        decision = safe_strip(
            message.get("content"),
            default="no decision content",
        )
        if DEBUG:
            print(f"{GREEN} *** Autopilot decision (from regular): {decision}{RESET}")

    # Process the decision
    if DEBUG:
        print(f"{GREEN} *** Autopilot extracted decision: '{decision}'{RESET}")

    if decision.startswith("ASK_USER:"):
        # Extract the question and ask the user
        question = decision[9:].strip()  # Remove "ASK_USER:" prefix
        print(f"\n{YELLOW}Autopilot needs input:{RESET} {question}")
        aicoder_instance.autopilot_enabled = (
            False  # Disable autopilot until user responds
        )
        return True, None
    elif decision == "DONE":
        # Task is complete, disable autopilot
        print(f"\n{GREEN}Autopilot task completed.{RESET}")
        aicoder_instance.autopilot_enabled = False
        return True, None
    elif decision.strip() == "no decision content" or not decision.strip():
        # No valid decision was made (empty decision or default)
        if DEBUG:
            print(
                f"{RED} *** Autopilot decision was empty or default: '{decision}'{RESET}"
            )
        print(
            f"{RED}Autopilot could not make a decision. Returning to manual mode.{RESET}"
        )
        aicoder_instance.autopilot_enabled = False
        return True, None
    else:
        print(f"{YELLOW}\nAutopilot decision: {RESET}{decision}\n")
        # Use the decision as the next action
        return False, decision


def _handle_autopilot_command(aicoder_instance, args: List[str]) -> Tuple[bool, bool]:
    """Enables or disables autopilot mode."""
    from aicoder.config import GREEN, RED, RESET

    if not args:
        # Print current status with decision check message
        status = "on" if aicoder_instance.autopilot_enabled else "off"
        print(f"\n{GREEN}Autopilot: {status}{RESET}")
        print(f"\n{GREEN}Checking if a decision has to be made...{RESET}")
        return False, False

    command = args[0].lower()
    if command in ["on", "enable", "true"]:
        aicoder_instance.autopilot_enabled = True
        print(f"\n{GREEN}Autopilot enabled.{RESET}")
        print(f"\n{GREEN}Checking if a decision has to be made...{RESET}")
    elif command in ["off", "disable", "false"]:
        aicoder_instance.autopilot_enabled = False
        print(f"\n{GREEN}Autopilot disabled.{RESET}")
    else:
        print(f"\n{RED}Invalid autopilot command. Use 'on' or 'off'.{RESET}")

    return False, False


def before_user_input(aicoder_instance):
    """Called before each user input to handle autopilot logic."""
    # Call the autopilot logic if the method exists
    if hasattr(aicoder_instance, "_autopilot_handle_logic"):
        return aicoder_instance._autopilot_handle_logic(aicoder_instance)
    return True, None

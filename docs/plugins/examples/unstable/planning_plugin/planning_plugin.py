"""
Planning Plugin for AI Coder - Adds Goose-style planning capabilities.
This plugin provides a two-phase approach: plan then execute.
"""

from typing import List, Tuple, Optional
from dataclasses import dataclass

# Plugin metadata
__version__ = "1.0.0"
__author__ = "AI Coder Plugin Developer"
__description__ = "Adds Goose-style two-phase planning: plan then execute"

# Try to import from aicoder, but handle graceful degradation
try:
    from aicoder.config import DEBUG, GREEN, YELLOW, RED, RESET, BOLD
    from aicoder.utils import parse_markdown

    IMPORTS_AVAILABLE = True
except ImportError:
    # Fallback colors for standalone testing
    DEBUG = False
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    RESET = "\033[0m"
    BOLD = "\033[1m"

    def parse_markdown(text):
        return text  # Simple fallback

    IMPORTS_AVAILABLE = False


@dataclass
class PlanningStep:
    """Represents a single step in a plan."""

    step_number: int
    description: str
    dependencies: List[int]  # Step numbers this depends on
    estimated_time: Optional[str] = None
    tools_needed: List[str] = None
    notes: str = ""


@dataclass
class Plan:
    """Represents a complete execution plan."""

    title: str
    description: str
    steps: List[PlanningStep]
    total_estimated_time: Optional[str] = None
    prerequisites: List[str] = None
    success_criteria: List[str] = None

    def __post_init__(self):
        if self.prerequisites is None:
            self.prerequisites = []
        if self.success_criteria is None:
            self.success_criteria = []


class PlanningPlugin:
    """Plugin that adds planning capabilities to AI Coder."""

    def __init__(self):
        self.name = "planner"
        self.version = "1.0.0"
        self.description = "Adds two-phase planning: plan then execute"
        self.current_plan: Optional[Plan] = None
        self.planning_mode = False
        self.plan_approved = False
        self.aicoder = None

    def initialize(self, aicoder_instance):
        """Initialize the plugin with AICoder instance."""
        self.aicoder = aicoder_instance
        self._register_commands()

        if DEBUG:
            print(f"{GREEN}Planning plugin initialized successfully!{RESET}")
            print(f"{YELLOW}Use /plan to start planning mode{RESET}")

    def _register_commands(self):
        """Register planning commands."""
        if hasattr(self.aicoder, "command_handlers"):
            # Register our planning commands
            self.aicoder.command_handlers["/plan"] = self._handle_plan_command
            self.aicoder.command_handlers["/endplan"] = self._handle_endplan_command
            self.aicoder.command_handlers["/showplan"] = self._handle_showplan_command
            self.aicoder.command_handlers["/approveplan"] = (
                self._handle_approveplan_command
            )

            if DEBUG:
                print(
                    f"{GREEN}Planning commands registered: /plan, /endplan, /showplan, /approveplan{RESET}"
                )
        else:
            print(
                f"{RED}Warning: Could not register planning commands - no command_handlers found{RESET}"
            )

    def _handle_plan_command(self, args: List[str]) -> Tuple[bool, bool]:
        """Handle /plan command - enter planning mode."""
        print(f"\n{BOLD}{GREEN}Entering Planning Mode{RESET}")
        print(
            f"{YELLOW}I'll help you create a detailed plan before starting execution.{RESET}"
        )
        print(
            f"{YELLOW}This ensures we understand all requirements and have clear steps.{RESET}\n"
        )

        self.planning_mode = True
        self.plan_approved = False
        self.current_plan = None

        # Start the planning conversation
        self._start_planning_conversation()

        return False, False  # Don't quit, don't make API call yet

    def _handle_endplan_command(self, args: List[str]) -> Tuple[bool, bool]:
        """Handle /endplan command - exit planning mode."""
        if not self.planning_mode:
            print(f"\n{RED}Not in planning mode. Use /plan to start planning.{RESET}")
            return False, False

        print(f"\n{YELLOW}Exiting planning mode.{RESET}")
        self.planning_mode = False
        self.current_plan = None
        self.plan_approved = False

        return False, False

    def _handle_showplan_command(self, args: List[str]) -> Tuple[bool, bool]:
        """Handle /showplan command - display current plan."""
        if not self.current_plan:
            print(f"\n{RED}No active plan. Use /plan to create one.{RESET}")
            return False, False

        self._display_plan()
        return False, False

    def _handle_approveplan_command(self, args: List[str]) -> Tuple[bool, bool]:
        """Handle /approveplan command - approve and execute current plan."""
        if not self.current_plan:
            print(f"\n{RED}No plan to approve. Use /plan to create one.{RESET}")
            return False, False

        if self.plan_approved:
            print(f"\n{YELLOW}Plan already approved.{RESET}")
            return False, False

        print(f"\n{BOLD}{GREEN}Approving Plan...{RESET}")
        self._display_plan()

        response = input(f"\n{GREEN}Execute this plan? (y/N): {RESET}").strip().lower()
        if response in ["y", "yes"]:
            self.plan_approved = True
            self.planning_mode = False
            print(f"\n{GREEN}Plan approved! Starting execution...{RESET}")

            # Convert plan to execution context and start execution
            self._execute_plan()
            return False, False  # Let execution happen naturally
        else:
            print(
                f"\n{YELLOW}Plan not approved. You can modify it with /plan or exit with /endplan.{RESET}"
            )
            return False, False

    def _start_planning_conversation(self):
        """Start the planning conversation with the AI."""
        if not self.aicoder or not hasattr(self.aicoder, "message_history"):
            print(f"{RED}Error: AI Coder instance not properly initialized{RESET}")
            return

        # Create a specialized planning prompt
        planning_prompt = self._create_planning_prompt()

        # Temporarily modify the system message to focus on planning
        original_messages = self.aicoder.message_history.messages.copy()

        # Add planning context
        planning_context = {"role": "system", "content": planning_prompt}

        # Insert planning context after the original system message
        system_index = next(
            (i for i, msg in enumerate(original_messages) if msg["role"] == "system"), 0
        )
        original_messages.insert(system_index + 1, planning_context)

        # Get user's initial request
        user_request = input(f"{GREEN}What would you like to plan? {RESET}").strip()

        if user_request:
            # Add user request to messages
            original_messages.append({"role": "user", "content": user_request})

            # Make API call for planning
            try:
                response = self.aicoder._make_api_request(
                    original_messages, disable_streaming_mode=False
                )

                if response and "choices" in response:
                    ai_response = response["choices"][0]["message"]
                    print(
                        f"\n{BOLD}{GREEN}Planner:{RESET} {parse_markdown(ai_response['content'])}"
                    )

                    # Check if response contains clarifying questions or a plan
                    if self._is_asking_questions(ai_response["content"]):
                        print(
                            f"\n{YELLOW}Please answer the clarifying questions above.{RESET}"
                        )
                        # Continue conversation in planning mode
                    else:
                        # Try to parse the response as a plan
                        parsed_plan = self._parse_plan_from_response(
                            ai_response["content"]
                        )
                        if parsed_plan:
                            self.current_plan = parsed_plan
                            print(
                                f"\n{GREEN}Plan created! Use /showplan to view, /approveplan to execute.{RESET}"
                            )
                        else:
                            print(
                                f"\n{YELLOW}I created a plan but couldn't parse it automatically. The plan is above.{RESET}"
                            )

            except Exception as e:
                print(f"\n{RED}Error during planning: {e}{RESET}")
                print(f"{YELLOW}You can continue the conversation manually.{RESET}")

    def _create_planning_prompt(self) -> str:
        """Create the planning system prompt."""
        return """You are now acting as a specialized PLANNER AI. Your task is to:

1. Ask clarifying questions to fully understand the user's requirements
2. Create a detailed, step-by-step execution plan
3. Break down complex tasks into manageable steps
4. Identify dependencies between steps
5. Suggest tools needed for each step

IMPORTANT: You are only planning - NOT executing. Focus on understanding and planning.

For complex requests, always start by asking clarifying questions about:
- Specific requirements and constraints
- Preferred technologies or approaches
- Timeline and budget considerations
- Success criteria
- Potential risks or challenges

Once you have sufficient information, present a detailed plan with numbered steps, dependencies, and clear descriptions.

Format your plan as:
# PLAN: [Plan Title]
## Description
[Brief description of what will be accomplished]

## Steps
1. [Step description]
   - Dependencies: [previous steps]
   - Estimated time: [time estimate]
   - Tools needed: [list of tools]

2. [Step description]
   - Dependencies: [previous steps]
   - Estimated time: [time estimate]
   - Tools needed: [list of tools]

[Continue with all steps...]

## Success Criteria
- [Criterion 1]
- [Criterion 2]
- [Criterion 3]

Remember: Your goal is to create a clear, executable plan that another AI could follow."""

    def _is_asking_questions(self, content: str) -> bool:
        """Check if the response is asking clarifying questions."""
        question_indicators = [
            "?",
            "questions:",
            "clarify",
            "need more information",
            "please provide",
        ]
        content_lower = content.lower()
        return any(indicator in content_lower for indicator in question_indicators)

    def _parse_plan_from_response(self, content: str) -> Optional[Plan]:
        """Parse a plan from the AI response. Simple parsing for demo."""
        try:
            lines = content.split("\n")
            title = ""
            description = ""
            steps = []
            current_step = None

            for line in lines:
                line = line.strip()
                if line.startswith("# PLAN:"):
                    title = line[8:].strip()
                elif line.startswith("## Description"):
                    # Get description from next few lines
                    description = ""
                elif line.startswith("## Steps"):
                    continue
                elif line.startswith("## Success Criteria"):
                    break
                elif line and line[0].isdigit() and "." in line[:5]:
                    # New step
                    if current_step:
                        steps.append(current_step)

                    step_num = int(line.split(".")[0])
                    step_desc = line.split(".", 1)[1].strip()
                    current_step = PlanningStep(
                        step_number=step_num,
                        description=step_desc,
                        dependencies=[],
                        tools_needed=[],
                    )
                elif current_step and line.startswith("- Dependencies:"):
                    deps = line[14:].strip()
                    if deps and deps.lower() != "none":
                        try:
                            current_step.dependencies = [
                                int(d.strip()) for d in deps.split(",") if d.strip()
                            ]
                        except ValueError:
                            current_step.dependencies = []
                elif current_step and line.startswith("- Estimated time:"):
                    current_step.estimated_time = line[16:].strip()
                elif current_step and line.startswith("- Tools needed:"):
                    tools = line[14:].strip()
                    if tools and tools.lower() != "none":
                        current_step.tools_needed = [
                            t.strip() for t in tools.split(",") if t.strip()
                        ]
                elif current_step and line.startswith("- Notes:"):
                    current_step.notes = line[8:].strip()

            if current_step:
                steps.append(current_step)

            if title and steps:
                return Plan(title=title, description=description, steps=steps)

        except Exception as e:
            if DEBUG:
                print(f"{RED}Error parsing plan: {e}{RESET}")

        return None

    def _display_plan(self):
        """Display the current plan in a formatted way."""
        if not self.current_plan:
            return

        print(f"\n{BOLD}{GREEN}=== PLAN: {self.current_plan.title} ==={RESET}")
        print(f"{YELLOW}Description: {self.current_plan.description}{RESET}\n")

        print(f"{BOLD}Steps:{RESET}")
        for step in self.current_plan.steps:
            print(f"  {GREEN}{step.step_number}. {RESET}{step.description}")
            if step.dependencies:
                print(
                    f"     {YELLOW}Dependencies: {', '.join(map(str, step.dependencies))}{RESET}"
                )
            if step.estimated_time:
                print(f"     {YELLOW}Time: {step.estimated_time}{RESET}")
            if step.tools_needed:
                print(f"     {YELLOW}Tools: {', '.join(step.tools_needed)}{RESET}")
            if step.notes:
                print(f"     {YELLOW}Notes: {step.notes}{RESET}")
            print()

        if self.current_plan.success_criteria:
            print(f"{BOLD}Success Criteria:{RESET}")
            for criterion in self.current_plan.success_criteria:
                print(f"  ✓ {criterion}")
            print()

    def _execute_plan(self):
        """Execute the approved plan."""
        if not self.current_plan or not self.plan_approved or not self.aicoder:
            return

        # Clear message history and inject plan as context
        self.aicoder.message_history.messages = [
            {"role": "system", "content": self._get_system_message()},
            {"role": "user", "content": self._format_plan_for_execution()},
        ]

        print(
            f"\n{GREEN}Plan injected as context. AI will now execute the plan.{RESET}"
        )

        # The main loop will naturally continue with the new context
        # No need for special handling - the AI now has the plan and will execute it

    def _get_system_message(self) -> str:
        """Get the base system message."""
        if not self.aicoder or not hasattr(self.aicoder, "message_history"):
            return "You are an AI assistant that helps with coding tasks."

        # Try to get the original system message
        for msg in self.aicoder.message_history.messages:
            if msg["role"] == "system":
                return msg["content"]
        return "You are an AI assistant that helps with coding tasks."

    def _format_plan_for_execution(self) -> str:
        """Format the current plan as an execution context."""
        plan = self.current_plan

        execution_context = f"""# EXECUTION PLAN

## Plan: {plan.title}
{plan.description}

## Steps to Execute:
"""

        for step in plan.steps:
            execution_context += f"""
{step.step_number}. {step.description}
   - Dependencies: {", ".join(map(str, step.dependencies)) if step.dependencies else "None"}
   - Tools needed: {", ".join(step.tools_needed) if step.tools_needed else "Standard tools"}
   - Notes: {step.notes}
"""

        if plan.success_criteria:
            execution_context += "\n## Success Criteria:\n"
            for criterion in plan.success_criteria:
                execution_context += f"- {criterion}\n"

        execution_context += """

## Instructions:
Execute this plan step by step. For each step:
1. Use the appropriate tools
2. Verify completion before moving to the next step
3. Respect dependencies between steps
4. Ask for clarification if anything is unclear

Focus on successful completion of all steps according to the criteria above."""

        return execution_context

    def get_plugin_info(self):
        """Return plugin information."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "commands": ["/plan", "/endplan", "/showplan", "/approveplan"],
            "status": "active" if self.planning_mode else "inactive",
        }


# Plugin entry point - this is what AICoder will look for
def initialize_plugin(aicoder_instance):
    """Initialize the planning plugin."""
    plugin = PlanningPlugin()
    plugin.initialize(aicoder_instance)
    return plugin


def on_aicoder_init(aicoder_instance):
    """Initialize the planning plugin when AICoder starts up (compatible with plugin system)."""
    try:
        # Initialize the planning plugin
        plugin = PlanningPlugin()
        plugin.initialize(aicoder_instance)

        # Store reference to the plugin instance so it's accessible
        if not hasattr(aicoder_instance, "planning_plugin"):
            aicoder_instance.planning_plugin = plugin

        return True
    except Exception as e:
        print(f"❌ Failed to initialize planning plugin: {e}")
        import traceback

        traceback.print_exc()
        return False


def on_plugin_load():
    """Called when the plugin is loaded"""
    print("✅ Planning plugin loaded (unstable version)")


if __name__ == "__main__":
    # Standalone testing
    print("Planning Plugin - Standalone Test")
    print("Version:", __version__)
    print("Description:", __description__)
    print("Plugin loaded successfully!")

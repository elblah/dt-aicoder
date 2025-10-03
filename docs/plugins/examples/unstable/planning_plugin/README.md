# Planning Plugin for AI Coder

This plugin adds Goose-style two-phase planning capabilities to AI Coder. It provides a structured approach to complex tasks by separating planning from execution.

## Features

- **Two-Phase Planning**: Plan first, then execute approach similar to Goose CLI
- **Interactive Planning**: AI asks clarifying questions to understand requirements
- **Structured Plans**: Creates detailed plans with dependencies, time estimates, and tool requirements
- **Context Optimization**: Clears conversation history and injects only the approved plan for execution
- **Plan Management**: Commands to create, view, approve, and exit planning mode

## Commands

- `/plan` - Enter planning mode and start creating a plan
- `/showplan` - Display the current plan
- `/approveplan` - Approve the current plan and start execution
- `/endplan` - Exit planning mode without executing

## How It Works

1. **Planning Phase**: When you use `/plan`, the AI enters planning mode and acts as a specialized planner
2. **Clarification**: The AI asks questions to fully understand your requirements
3. **Plan Creation**: Once requirements are clear, the AI creates a detailed step-by-step plan
4. **Approval**: You review and approve the plan with `/approveplan`
5. **Execution**: The system clears conversation history and injects only the approved plan as context
6. **Focused Execution**: The AI executes the plan with clear, focused context

## Benefits

- **Reduced Token Usage**: By clearing history and injecting only the plan, token usage is optimized
- **Better Requirements Gathering**: Forces clarification of all requirements before starting work
- **Structured Approach**: Complex tasks are broken down into manageable steps
- **Clear Dependencies**: Shows how steps depend on each other
- **Success Criteria**: Defines what successful completion looks like

## Installation

1. Copy the plugin to your AICoder plugins directory:
   ```bash
   cp -r /path/to/planning_plugin /path/to/aicoder/plugins/
   ```

2. The plugin will be automatically loaded when AICoder starts.

## Usage Example

```
> /plan
Entering Planning Mode
I'll help you create a detailed plan before starting execution.
This ensures we understand all requirements and have clear steps.

What would you like to plan? build a web application with user authentication

Planner: I need to gather more information before creating a detailed web application plan. Please provide clarification on the following:

1. What type of web application? (e.g., e-commerce, blog, social media)
2. What technology stack do you prefer?
3. What authentication features do you need?
4. What's your timeline?

> [provide answers]

Planner: Here's the detailed plan:

# PLAN: Web Application with User Authentication

## Description
Build a modern web application with comprehensive user authentication system

## Steps
1. Set up project structure
   - Dependencies: None
   - Estimated time: 30 minutes
   - Tools needed: file system tools

2. Implement backend authentication
   - Dependencies: Step 1
   - Estimated time: 2 hours
   - Tools needed: coding tools

3. Create frontend login interface
   - Dependencies: Step 1, 2
   - Estimated time: 1.5 hours
   - Tools needed: coding tools

> /approveplan
Approving Plan...
=== PLAN: Web Application with User Authentication ===
Description: Build a modern web application with comprehensive user authentication system

Steps:
  1. Set up project structure
     Dependencies: None
     Time: 30 minutes
     Tools: file system tools

  2. Implement backend authentication
     Dependencies: 1
     Time: 2 hours
     Tools: coding tools

  3. Create frontend login interface
     Dependencies: 1, 2
     Time: 1.5 hours
     Tools: coding tools

Execute this plan? (y/N): y

Plan approved! Starting execution...
Plan injected as context. AI will now execute the plan.
```

## Configuration

The plugin can be configured by modifying these constants in `planning_plugin.py`:

- `DEBUG`: Enable debug output (default: False)
- Planning prompt template in `_create_planning_prompt()`

## Architecture

This plugin implements the key efficiency features from Goose CLI:

1. **Specialized Planner AI**: Different prompts and behavior for planning vs execution
2. **Context Optimization**: Clears history and injects only the plan for execution
3. **Structured Output**: Plans have consistent format with dependencies and metadata
4. **User Approval**: Requires explicit approval before execution

## Requirements

- AI Coder v2.0 or later
- Access to configured AI model for planning and execution

## Troubleshooting

If the plugin fails to load:
1. Ensure the plugin directory structure is correct
2. Check that AICoder has permission to read the plugin files
3. Verify that the plugin location is in AICoder's plugin search path

If planning commands are not available:
1. Check that the plugin loaded successfully (look for initialization messages)
2. Verify that the AICoder instance has command_handlers attribute
3. Try restarting AICoder with the plugin installed

## Differences from Goose CLI

While inspired by Goose CLI, this implementation is simplified:

- **No separate planner model**: Uses the same model for planning and execution
- **No recipe system**: Plans are created dynamically rather than from templates
- **Simpler parsing**: Basic text parsing vs structured recipe format
- **Single file**: Everything in one plugin file vs modular architecture

The core efficiency benefits (two-phase approach, context optimization) are preserved while keeping the implementation simple and maintainable.

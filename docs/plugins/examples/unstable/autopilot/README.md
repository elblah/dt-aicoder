# Autopilot Plugin

This plugin adds autopilot functionality to AI Coder, allowing the AI to automatically make decisions and continue working without user intervention.

## Features

- Automatically decides what to do next based on the last assistant message
- Can be enabled/disabled with `/autopilot on` or `/autopilot off`
- Asks user for input when it can't make a decision
- Disables itself when the task is complete

## Usage

1. Enable autopilot mode:
   ```
   /autopilot on
   ```

2. The AI will automatically make decisions and continue working

3. Disable autopilot mode:
   ```
   /autopilot off
   ```

## Commands

- `/autopilot on` - Enable autopilot mode
- `/autopilot off` - Disable autopilot mode
- `/a on` - Short form to enable autopilot
- `/a off` - Short form to disable autopilot

## How It Works

When autopilot is enabled, after each AI response, the plugin will ask the AI to decide what to do next. The AI can choose to:

1. Continue with a clear next step
2. Mark the task as DONE
3. Ask the user for input (ASL_USER:)
4. Make a reasonable guess if unsure

The autopilot will automatically disable itself when the task is complete or if it encounters an error.
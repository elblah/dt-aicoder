# Custom Prompt Overrides

AI Coder supports custom prompt overrides through environment variables, giving you complete control over the system's behavior and responses.

## Environment Variables

You can override any of the following prompts using environment variables:

- `AICODER_PROMPT_MAIN`: Main system prompt (replaces AICODER.md)
- `AICODER_PROMPT_PLAN`: Planning mode prompt 
- `AICODER_PROMPT_BUILD_SWITCH`: Build switch prompt
- `AICODER_PROMPT_COMPACTION`: Compaction/summarization prompt
- `AICODER_PROMPT_PROJECT`: Project-specific context file (replaces AGENTS.md)

## Usage Methods

### 1. Direct Content Override

Set the prompt content directly in the environment variable:

```bash
export AICODER_PROMPT_MAIN="You are a specialized AI assistant for Go development. Focus on best practices and clean code."
```

### 2. File Path Override

Point to a file containing your custom prompt:

```bash
export AICODER_PROMPT_MAIN="./custom-prompts/go-development.md"
export AICODER_PROMPT_PLAN="./custom-prompts/go-planning.md"
```

### 3. Script-based Configuration

Create per-project configurations in scripts:

```bash
#!/bin/bash
# project-setup.sh

# Detect project type and set appropriate prompts
if [[ -f "go.mod" ]]; then
    export AICODER_PROMPT_MAIN="$(cat ./prompts/go-main.md)"
    export AICODER_PROMPT_PLAN="$(cat ./prompts/go-plan.md)"
elif [[ -f "package.json" ]]; then
    export AICODER_PROMPT_MAIN="$(cat ./prompts/node-main.md)"
    export AICODER_PROMPT_PLAN="$(cat ./prompts/node-plan.md)"
fi

# Run AI Coder with custom prompts
aicoder
```

### 4. Project-Specific Context Files

Configure the project-specific context filename (replaces AGENTS.md):

```bash
# Use model-specific context files
export AICODER_PROMPT_PROJECT="CLAUDE.md"  # Will load CLAUDE.md instead of AGENTS.md

# Use lowercase version automatically (tries CLAUDE.md then claude.md)
export AICODER_PROMPT_PROJECT="claude"

# Model-specific project configurations
if [[ "$MODEL" == "claude" ]]; then
    export AICODER_PROMPT_PROJECT="CLAUDE.md"
elif [[ "$MODEL" == "gemini" ]]; then
    export AICODER_PROMPT_PROJECT="GEMINI.md"
elif [[ "$MODEL" == "gpt" ]]; then
    export AICODER_PROMPT_PROJECT="GPT.md"
fi
```

### 5. Dynamic Prompts

Use shell variables and commands to create dynamic prompts:

```bash
# Project-specific prompts
export AICODER_PROMPT_MAIN="You are helping with $(basename $PWD). Focus on this specific project."

# Include current directory context
export AICODER_PROMPT_PLAN="You are planning work in $(pwd). Consider the existing codebase structure."
```

## File Path Detection

AI Coder automatically determines whether an environment variable contains:

- **File path**: If it contains `/` or starts with `.` or `~`
- **Literal content**: Otherwise

Examples:
- `/home/user/prompts/custom.md` → Treated as file path
- `./prompts/custom.md` → Treated as file path  
- `~/prompts/custom.md` → Treated as file path
- `You are a helpful assistant` → Treated as literal content

## Default Prompt Files

When no environment variable is set, AI Coder loads default prompts from `aicoder/prompts/`:

- `main.md` - Main system prompt
- `plan.md` - Planning mode prompt
- `build-switch.md` - Build switch prompt
- `compaction.md` - Compaction/summarization prompt

## Integration Examples

### Container/DevOps Usage

```bash
# Dockerfile
ENV AICODER_PROMPT_MAIN="You are a DevOps assistant specialized in Kubernetes and container orchestration."
ENV AICODER_PROMPT_PLAN="Focus on infrastructure planning, deployment strategies, and operational considerations."

# Run with container-specific prompts
docker run -e AICODER_PROMPT_MAIN -e AICODER_PROMPT_PLAN my-aicoder-image
```

### Development Workflow

```bash
# .envrc (for direnv)
export AICODER_PROMPT_MAIN="./prompts/project-main.md"
export AICODER_PROMPT_PLAN="./prompts/project-plan.md"

# Activates automatically when entering directory
```

### Per-Language Configuration

```bash
# Python projects
export AICODER_PROMPT_MAIN="You are a Python expert following PEP 8, type hints, and modern Python practices."

# JavaScript projects  
export AICODER_PROMPT_MAIN="You are a JavaScript/TypeScript expert focusing on ES6+, async patterns, and modern frameworks."
```

## Debug Mode

Enable debug mode to see which prompts are being loaded:

```bash
DEBUG=1 aicoder
```

This will show output like:
```
*** Loaded main from default prompt file
*** Loaded plan from environment variable content
*** Loaded build-switch from file: /path/to/custom.md
```

## Fallback Behavior

If a custom prompt file:
- **Doesn't exist**: Falls back to treating the environment variable as literal content
- **Is empty**: Falls back to the default prompt file
- **Cannot be read**: Falls back to treating the environment variable as literal content

If no environment variable is set and the default file cannot be found, AI Coder uses hardcoded fallback prompts to ensure the system always works.

## Best Practices

1. **Keep prompts focused**: Each prompt should have a clear, single purpose
2. **Use consistent formatting**: Follow the structure of default prompts
3. **Test incrementally**: Start with simple prompts and build complexity
4. **Version control your prompts**: Store custom prompt files in your repository
5. **Document your customizations**: Include comments explaining why prompts were customized

## Example Custom Prompt Files

### Custom Main Prompt (`./prompts/web-dev.md`)
```markdown
# Web Development Assistant

You are a specialized AI assistant for modern web development, focusing on:
- React/Vue/Angular best practices
- Responsive design principles  
- Performance optimization
- Accessibility standards
- Modern CSS/JavaScript patterns

Current project: {current_directory}
Available tools: {available_tools}
```

### Custom Planning Prompt (`./prompts/team-planning.md`)  
```markdown
# Team Planning Mode

You are helping with team planning. Consider:
- Team skill levels and availability
- Project timeline and dependencies
- Code review requirements
- Testing and documentation needs
- Deployment and maintenance considerations

Focus on creating clear, actionable plans that can be distributed among team members.
```

### Model-Specific Project Context (`CLAUDE.md`)
```markdown
# Claude-Specific Context

## Project Guidelines
- Follow the Anthropic Constitutional AI principles
- Emphasize safety and helpfulness in all responses
- Use step-by-step reasoning for complex problems
- Prioritize clear explanations over brevity

## Code Style Preferences
- Use Python type hints when appropriate
- Follow PEP 8 guidelines strictly
- Include comprehensive docstrings
- Write testable, modular code

## Communication Style
- Be thorough but concise
- Acknowledge uncertainties
- Provide alternative approaches when relevant
```

### Model-Specific Project Context (`GEMINI.md`)
```markdown
# Gemini-Specific Context

## Project Guidelines
- Leverage multimodal understanding when helpful
- Use the latest Google best practices
- Emphasize performance and scalability
- Consider Google Cloud integration opportunities

## Code Style Preferences
- Follow Google's style guides
- Use modern JavaScript/TypeScript patterns
- Implement proper error handling
- Include performance monitoring

## Communication Style
- Be direct and actionable
- Provide concrete examples
- Consider integration with Google services
```

## Model-Specific Workflow Examples

```bash
#!/bin/bash
# model-config.sh - Set prompts based on the AI model being used

MODEL=${1:-$(echo $OPENAI_MODEL | tr '[:upper:]' '[:lower:]')}

case $MODEL in
    *claude*)
        export AICODER_PROMPT_PROJECT="CLAUDE.md"
        export AICODER_PROMPT_MAIN="You are Claude, helpful and thorough assistant focused on safety and clear reasoning."
        ;;
    *gemini*)
        export AICODER_PROMPT_PROJECT="GEMINI.md"
        export AICODER_PROMPT_MAIN="You are Gemini, Google's advanced AI with multimodal capabilities."
        ;;
    *gpt*)
        export AICODER_PROMPT_PROJECT="GPT.md"
        export AICODER_PROMPT_MAIN="You are GPT, OpenAI's capable assistant with broad knowledge and reasoning skills."
        ;;
    *)
        # Default configuration
        export AICODER_PROMPT_PROJECT="AGENTS.md"
        ;;
esac

echo "Configuration set for model: $MODEL"
```

## Tmux Popup Editor

When running inside tmux, AI Coder can automatically open editors in tmux popups for a more elegant editing experience:

### Environment Variables:
```bash
TMUX_POPUP_EDITOR=1              # Enable tmux popup editor (default: 0)
TMUX_POPUP_WIDTH_PERCENT=80      # Popup width as % of terminal (default: 80)
TMUX_POPUP_HEIGHT_PERCENT=80     # Popup height as % of terminal (default: 80)
```

### Usage:
- **/edit** or **/e** - Opens editor in tmux popup when inside tmux
- **/memory** or **/m** - Opens memory editor in tmux popup when inside tmux
- Automatically falls back to normal editor if tmux popup fails

### Example:
```bash
# Customize popup size
export TMUX_POPUP_WIDTH_PERCENT=70
export TMUX_POPUP_HEIGHT_PERCENT=90

# Disable popup editor entirely
export TMUX_POPUP_EDITOR=0
```

## /prompt Command

AI Coder includes a built-in `/prompt` command to inspect and manage your prompt configuration:

```bash
/prompt           Show current prompt (truncated view)
/prompt full     Show current prompt (full content)
/prompt list     List available prompts from ~/.config/aicoder/prompts
/prompt set <n>  Set prompt <n> as active main prompt
/prompt edit     Edit current main prompt in $EDITOR
/prompt help     Show detailed help for prompt system
```

### Dynamic Prompt Switching

The enhanced `/prompt` command supports dynamic prompt switching from a user-managed directory:

1. **Create prompt files** in `~/.config/aicoder/prompts/` (supports `.txt` and `.md` files)
2. **List available prompts** with `/prompt list` - shows numbered list
3. **Switch between prompts** instantly with `/prompt set <number>`
4. **Template variables** like `{current_directory}`, `{current_user}` are automatically replaced

Example:
```bash
# Create a Python expert prompt
mkdir -p ~/.config/aicoder/prompts
cat > ~/.config/aicoder/prompts/python-expert.md << 'EOF'
You are a Python expert working in {current_directory}.
Current user: {current_user}
Time: {current_datetime}

Focus on clean, idiomatic Python code.
EOF

# List and switch prompts
/prompt list
/prompt set 1

# Edit the current prompt
/prompt edit
```

For detailed documentation, see [docs/prompts_command.md](prompts_command.md).

The command displays:
- **Main System Prompt**: Current source, length, and content preview
- **Project Context File**: Which file is loaded and its content
- **Planning Mode Prompts**: Status (active/inactive) and content
- **Environment Variables**: All configured prompt overrides
- **Source Detection**: Whether prompts come from files, environment variables, or defaults

### Example Output:
```
╔══════════════════════════════════════════════════════════════╗
║                        CURRENT PROMPTS                          ║
╚══════════════════════════════════════════════════════════════╝

MAIN SYSTEM PROMPT
   Source: Environment Variable (literal)
   Length: 4800 characters
   ──────────────────────────────────────────────────────────────
   Custom prompt content preview...

PROJECT CONTEXT FILE
   File: CLAUDE.md
   Source: Environment Variable → CLAUDE.md
   Status: [✓] Found
   Length: 4356 characters
```

This system gives you complete control over AI Coder's behavior while maintaining compatibility with all existing workflows. The project-specific context files allow you to tailor the AI's behavior to different models or project requirements.
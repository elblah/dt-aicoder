# Enhanced /prompt Command

The `/prompt` command in AI Coder has been enhanced to support dynamic prompt switching from a user-managed prompt directory.

## Features

### 1. List Available Prompts
```bash
/prompt list
```
Lists all prompt files from `~/.config/aicoder/prompts/` with numbers for easy selection.

### 2. Set Active Prompt
```bash
/prompt set <number>
```
Sets the specified prompt as the active main system prompt. The prompt is loaded with all template variables replaced.

### 3. Edit Current Prompt
```bash
/prompt edit
```
Opens the current main system prompt in `$EDITOR` for editing. After editing, you can:
- Save the prompt to `~/.config/aicoder/prompts/` (recommended)
- Apply it temporarily for the current session only
- Discard changes

If the current prompt is already from a file in `~/.config/aicoder/prompts/`, it will be edited directly.

### 4. Show Current Prompt Info
```bash
/prompt
```
Shows information about the currently loaded prompt(s).

### 4. Full Prompt Display
```bash
/prompt full
```
Shows the full content of current prompts.

### 5. Help
```bash
/prompt help
```
Displays detailed help information.

## Prompt Directory Structure

Create prompt files in `~/.config/aicoder/prompts/`:

```
~/.config/aicoder/prompts/
├── 001-gemini.txt
├── 002-qwen.md
├── python-expert.md
└── web-developer.txt
```

### Supported File Formats
- `.txt` files
- `.md` files

### Naming Conventions
- Files are sorted alphabetically
- Numbered prefixes (e.g., `001-`, `002-`) ensure consistent ordering
- Any valid filename is supported

## Template Variables

Prompt files can include template variables that are automatically replaced:

| Variable | Description |
|----------|-------------|
| `{current_directory}` | Current working directory |
| `{current_datetime}` | Current date and time (YYYY-MM-DD HH:MM:SS) |
| `{current_user}` | Current username |
| `{system_info}` | System information (OS, architecture) |
| `{platform_info}` | Detailed platform information |
| `{available_tools}` | List of detected tools (rg, fd, etc.) |

## Example Prompt Files

### Gemini Assistant (`001-gemini.txt`)
```
You are Gemini, a helpful AI assistant created by Google.

Current working directory: {current_directory}
Current user: {current_user}
Current time: {current_datetime}

You excel at:
- Creative writing and brainstorming
- Code generation and explanation
- Analysis and problem-solving

Always be helpful, accurate, and thoughtful in your responses.
```

### Python Expert (`python-expert.md`)
```markdown
# Python Programming Expert

You are a Python programming expert with deep knowledge of:

- Python best practices and PEP standards
- Popular libraries (numpy, pandas, matplotlib, django, fastapi)
- Performance optimization and profiling
- Testing strategies and test-driven development

## Context
- Directory: {current_directory}
- User: {current_user}
- Available tools: {available_tools}

Provide Pythonic, well-structured solutions with explanations.
```

## Usage Examples

### Setting Up Prompts
```bash
# Create the prompts directory
mkdir -p ~/.config/aicoder/prompts

# Create a Python expert prompt
cat > ~/.config/aicoder/prompts/python-expert.md << 'EOF'
You are a Python expert working in {current_directory}.
Current user: {current_user}
Time: {current_datetime}

Focus on clean, idiomatic Python code following PEP 8.
EOF

# List available prompts
/prompt list

# Set Python expert as active
/prompt set 1

# Edit the current prompt
/prompt edit
```

### Switching Between Prompts
```bash
# List all prompts
/prompt list

# Switch to web development prompt
/prompt set 3

# Verify the change
/prompt
```

## How It Works

1. **Prompt Discovery**: The system scans `~/.config/aicoder/prompts/` for `.txt` and `.md` files
2. **Variable Replacement**: When a prompt is loaded, all template variables are replaced with current values
3. **Environment Override**: The selected prompt is set via `AICODER_PROMPT_MAIN` environment variable
4. **Live Update**: The current conversation's system prompt is updated immediately

## Integration with Existing Features

The enhanced `/prompt` command integrates seamlessly with existing AI Coder features:

- **Environment Variables**: Still supports `AICODER_PROMPT_MAIN` overrides
- **Project Context**: Works alongside project-specific context files
- **Planning Mode**: Separate from planning mode prompts
- **Plugin System**: Compatible with all existing plugins

## Troubleshooting

### No Prompts Found
```
No prompt files found in ~/.config/aicoder/prompts
Create prompt files (.txt or .md) to use this feature
```
**Solution**: Create the directory and add prompt files.

### Prompt Not Loading
```
Error: Could not read prompt file 'filename'
```
**Solution**: Check file permissions and ensure valid UTF-8 encoding.

### Variables Not Replaced
If template variables appear unchanged in the prompt, ensure they use the correct format:
- Use curly braces: `{current_directory}`
- No spaces within the braces
- Check the variable names against the supported list

## Migration from Environment Variables

If you're currently using environment variables for prompts:

```bash
# Old way
export AICODER_PROMPT_MAIN="You are a Python expert"

# New way - create a file instead
echo "You are a Python expert" > ~/.config/aicoder/prompts/python.txt
/prompt set 1
```

Benefits of the new approach:
- Multiple prompts available simultaneously
- Easy switching without restarting
- Template variable support
- Better organization and version control
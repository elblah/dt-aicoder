# AI Coder

**Fast, lightweight AI-assisted development that runs anywhere**

<img src="https://img.shields.io/badge/Python-3.8+-blue.svg" alt="Python">

AI Coder is a blazing-fast, resource-efficient CLI for AI-powered coding that brings the power of GPT models directly to your terminal. Built with performance and simplicity in mind, it runs flawlessly on everything from Raspberry Pi to high-end workstations.

## ✨ Why AI Coder?

**🚀 Blazing Fast**
- Less than a second startup on most computers (~2s on low-end computers)
- Uses <5% CPU on Raspberry Pi 3 and <1% CPU on normal computers most of the time)
- Minimal memory footprint (~25M RAM)
- Zero background processes

**🛡️ Secure by Design** 
- No external dependencies
- Full sandbox support with Firejail
- All operations visible and controlled

**⚡ Developer Experience**
- Tab completion for commands
- Planning mode for safe exploration
- Beautiful themes and syntax highlighting
- Seamless TMUX integration
- Simple plugin system using monkey patch
- Works well with bash scripts

## 🚀 Quick Start

### Install with UV (Recommended)
```bash
uv tool install --python 3.13 git+https://github.com/elblah/dt-aicoder
export OPENAI_API_KEY="your-api-key"
uvx aicoder
```

## 🎯 Core Features

### 💬 Smart AI Chat
- Interactive conversation with GPT models
- Context-aware responses
- Session management (save/load)
- Memory compaction for long conversations

### 🛠️ Powerful Tools
- **File Operations**: Read, write, edit files with diff preview
- **Command Execution**: Run shell commands with timeout protection  
- **Search & Navigation**: Grep search, file discovery, directory traversal
- **Planning Mode**: Read-only exploration mode with `/plan toggle`

### 🎨 Beautiful Interface
- **Dynamic Themes**: Luna, Ocean, Forest, Sunset color schemes
- **Syntax Highlighting**: Markdown, code diffs, and search results
- **Progress Tracking**: Visual task plans with completion status
- **Responsive Prompts**: Context-aware command suggestions

### 🔒 Enterprise Security
- **Sandbox Mode**: Firejail integration for isolated execution
- **Approval System**: User approval for sensitive operations
- **Audit Trail**: Complete visibility of all AI actions
- **Zero Dependencies**: No external package vulnerabilities

## 📖 Usage Examples

### Basic Chat
```bash
aicoder
> Help me refactor this Python function
[PLAN] AI: I'll analyze the function and suggest improvements...
```

### Planning Mode (Safe Exploration)
```bash
> /plan toggle
*** Planning mode enabled (read-only)
[PLAN] > ls -la
Planning mode: Read-only tools only
```

### File Operations
```bash
> Edit the auth.py file to add JWT validation
└─ AI wants to call: edit_file
   File: src/auth.py
   Changes:
   - Add validate_jwt_token function
   - Update authenticate method
   
Approve? [a]llow once [s]ession [d]eny
```

## 🛠️ Configuration

### Environment Variables
```bash
export OPENAI_BASE_URL="http://localhost:4999"
export OPENAI_API_KEY="your-api-key"
export OPENAI_MODEL="gpt-5"           # Default: gpt-5-nano
export DEBUG=1                        # Enable debug mode
export YOLO_MODE=1                    # Bypass approvals
```

### Custom Tools
```json
// mcp_tools.json
{
  "tools": [
    {
      "name": "deploy_app",
      "command": "kubectl",
      "args": ["apply", "-f", "manifest.yaml"],
      "description": "Deploy application to Kubernetes"
    }
  ]
}
```

## 🎨 Themes & Customization

### Available Themes
- **Luna** - Elegant purple theme
- **Ocean** - Calming blue tones  
- **Forest** - Natural green palette
- **Sunset** - Warm orange/red sunset
- **Original** - Classic terminal colors

### Switch Themes
```bash
> /theme ocean
✅ Applied theme: ocean
```

## 🔧 Development

### Building from Source
```bash
git clone https://github.com/elblah/dt-aicoder
cd dt-aicoder
pip install -e .
python aicoder.py
```

### Running Tests
```bash
# Comprehensive test suite
./run-tests.sh
```

## 📚 Documentation

- **[Configuration Guide](docs/configuration.md)** - Detailed setup options
- **[Plugin Development](docs/plugins/README.md)** - Build custom extensions
- **[MCP Tools](docs/mcp/configuration_guide.md)** - External tool integration
- **[Planning Mode](docs/planning_mode.md)** - Safe exploration features

## 🏗️ Architecture

AI Coder is built with a modular, extensible architecture:

```
aicoder/
├── core/           # Application core
├── tool_manager/   # Tool execution & approval
├── plugin_system/  # Extensible plugin framework  
├── streaming/      # Real-time response handling
└── themes/         # Visual customization
```

## 🔌 Plugin System - Extend Your Workflow

AI Coder's modular architecture makes it easy to build and share custom plugins. Whether you want to add new tools, integrate with external services, or customize the user experience, the plugin system has you covered.

### 🚀 Easy Plugin Development

Create powerful plugins with just a few lines of code:

```python
# Example: Custom notification plugin
class NotifyPlugin:
    def on_ai_response(self, message):
        # Send desktop notifications for AI responses
        subprocess.run(['notify-send', 'AI Response', message[:100]])
    
    def on_command_complete(self, command, result):
        # Notify when long-running commands finish
        if command.duration > 60:
            subprocess.run(['notify-send', 'Command Complete', command.name])
```

### 📦 Available Plugins

- **📋 Plan Plugin** - Integrated planning mode with `/plan toggle` and visual task tracking
- **🎨 Theme Plugin** - Dynamic color themes (Luna, Ocean, Forest, Sunset)
- **🔔 Notify Plugin** - Desktop notifications for AI responses and command completion
- **🔤 Char Filter Plugin** - Content filtering and sanitization
- **many more...**

### 🔧 Advanced Features

- **Tool Integration**: Add custom tools that the AI can call
- **Theme Support**: Create custom color schemes
- **Event Hooks**: Respond to AI responses, command completions, errors
- **Configuration**: Per-plugin configuration files

### 📚 Plugin Resources

- **[Plugin Development Guide](docs/plugins/README.md)** - Complete development tutorial
- **[Plugin Examples](docs/plugins/examples/)** - Ready-to-use plugin templates
- **[API Reference](docs/plugins/api.md)** - Plugin system API documentation

### 🌟 Community Plugins

Share your plugins with the community! Submit a pull request to add your plugin to the official repository, or share them independently.

**Why Plugins?**
- **Customization**: Tailor AI Coder to your workflow
- **Integration**: Connect with your favorite tools and services  
- **Automation**: Automate repetitive tasks and workflows
- **Productivity**: Add shortcuts and power-user features

Get started in minutes with our [Plugin Development Guide](docs/plugins/README.md)!

## 🌟 Performance

| Platform | CPU Usage | Memory | Startup Time |
|----------|-----------|---------|--------------|
| Raspberry Pi 3B | <5% | ~25MB | ~1s |
| Modern Laptop | <1% | ~30MB | <1s |
| Docker Container | <2% | ~30MB | ~1s |

## License

Apache 2.0

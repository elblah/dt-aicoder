# AI Coder Plugin System

AI Coder supports a simple but powerful plugin system. Plugins are Python files that are executed at startup and can modify any part of the application.

## How It Works

1. AI Coder looks for plugins in `~/.config/aicoder/plugins/`
2. All `.py` files (except those starting with `_`) are executed
3. Plugins can modify any class, method, or function using standard Python techniques
4. Plugins have full access to the AI Coder codebase

## Creating Plugins

Plugins are just Python files. Here's the basic structure:

```python
# my_plugin.py
import functools
from aicoder.some_module import SomeClass

# Store original method
_original_method = SomeClass.some_method

# Create your modified version
@functools.wraps(_original_method)
def my_modified_method(self, *args, **kwargs):
    # Do something before
    print("Before method call")
    
    # Call original method
    result = _original_method(self, *args, **kwargs)
    
    # Do something after
    print("After method call")
    
    return result

# Replace the original method
SomeClass.some_method = my_modified_method

print("My plugin loaded!")
```

## Available Examples

Check the `docs/examples/` directory for ready-to-use plugins:

- `01_logging_plugin.py` - Log all tool executions
- `02_auto_approve_plugin.py` - Auto-approve safe operations
- `03_custom_command_plugin.py` - Add custom commands
- `04_export_history_plugin.py` - Export conversation history

## Installation

1. Create the plugins directory:
   ```bash
   mkdir -p ~/.config/aicoder/plugins
   ```

2. Copy plugins to the directory:
   ```bash
   cp docs/examples/01_logging_plugin.py ~/.config/aicoder/plugins/
   ```

3. Run AI Coder - plugins will be loaded automatically!
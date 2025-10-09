# Smart Edit Tool Plugin

🚀 **Advanced safe file editing with rich diff preview and intelligent conflict detection**

## Overview

The Smart Edit Tool Plugin is a sophisticated file editing solution that provides multiple editing strategies, beautiful diff visualization, and atomic safety operations. It wraps around AI Coder's existing `edit_file` and `write_file` tools while adding layers of intelligence and safety.

## Features

### 🎯 Multiple Editing Strategies
- **Context-based**: Smart matching using surrounding lines (safest)
- **Line-based**: Direct line number ranges for precise edits
- **Pattern-based**: Regex-based structural changes
- **Semantic**: Language-aware editing
- **Auto-detect**: Automatically chooses the best strategy

### 🌈 Rich Diff Visualization
- Color-coded terminal output showing additions/deletions
- Line-by-line comparison with context
- Interactive preview mode for reviewing changes
- Summary statistics of modifications

### 🛡️ Atomic Safety Features
- Automatic timestamped backups before every modification
- Real-time conflict detection
- Full rollback capability
- Preview-first workflow

## Installation

```bash
# Copy the plugin to your AI Coder plugins directory
cp docs/plugins/examples/unstable/smart_edit/smart_edit.py ~/.config/aicoder/plugins/

# Restart AI Coder
aicoder
```

## Usage Examples

### Context-Based Edit (Recommended)
```python
smart_edit(
    file_path="src/app.py",
    changes=[{
        "context": [
            "def calculate_total(items):",
            "    total = 0",
            "    for item in items:"
        ],
        "replacement": [
            "def calculate_total(items):", 
            "    total = 0.0",  # Support floating point
            "    for item in items:"
        ]
    }]
)
```

### Line-Based Edit
```python
smart_edit(
    file_path="config.json",
    changes=[{
        "mode": "line_based",
        "lines": [10, 15],
        "replacement": '"debug": true,\n"log_level": "verbose"\n'
    }]
)
```

### Multiple Changes
```python
smart_edit(
    file_path="models/user.py",
    changes=[
        {
            "context": ["class User:", "    def __init__(self):"],
            "replacement": ["class User:", "    def __init__(self):", "        self.created_at = datetime.now()"]
        },
        {
            "mode": "line_based", 
            "lines": [25, 25],
            "replacement": "    def get_display_name(self):\n        return f'{self.first_name} {self.last_name}'\n"
        }
    ],
    preview_mode="rich"
)
```

## Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `file_path` | string | required | Absolute path to the file to edit |
| `changes` | array | required | List of changes to apply |
| `mode` | string | "context" | Primary editing mode |
| `preview_mode` | string | "rich" | Diff display (rich, simple, none) |
| `create_backup` | boolean | true | Create automatic backup |
| `auto_confirm` | boolean | false | Skip preview if no conflicts |
| `encoding` | string | "utf-8" | File encoding |

## Testing

```bash
# Run the comprehensive test suite
python test_smart_edit.py
```

## Version

**Version**: 1.0.0 (unstable)  
**Compatibility**: AI Coder v2.0+
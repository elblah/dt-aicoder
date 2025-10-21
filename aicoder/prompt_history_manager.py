"""
Enhanced prompt history manager with file persistence for AI Coder.

Extends the existing ReadlineHistoryManager to add file-based persistence
of user prompts across sessions.
"""

import json
from pathlib import Path
from typing import List, Optional
from .utils import emsg


class PromptHistoryManager:
    """Enhanced history manager with file persistence."""

    def __init__(self, project_dir=None, max_history: int = None):
        """
        Initialize prompt history manager.

        Args:
            project_dir: Project directory. If None, uses current working directory.
            max_history: Maximum number of prompts to save in history file.
                        If None, uses configuration default.
        """
        # Import config here to avoid circular imports
        try:
            from . import config
            if max_history is None:
                max_history = getattr(config, 'PROMPT_HISTORY_MAX_SIZE', 100)
            self.enabled = getattr(config, 'PROMPT_HISTORY_ENABLED', True)
        except ImportError:
            max_history = max_history or 100
            self.enabled = True
            
        self.project_dir = Path(project_dir) if project_dir else Path.cwd()
        self.history_file = self.project_dir / ".dt-aicoder" / "history"
        self.max_history = max_history
        self._ensure_history_dir()

    def _ensure_history_dir(self):
        """Ensure the .dt-aicoder directory exists."""
        try:
            self.history_file.parent.mkdir(exist_ok=True)
        except OSError as e:
            emsg(f"Warning: Could not create history directory: {e}")

    def load_history(self) -> List[str]:
        """
        Load prompt history from file.

        Returns:
            List of historical prompts, empty list if file doesn't exist or is corrupted.
        """
        if not self.enabled or not self.history_file.exists():
            return []

        try:
            # First, try to read the entire file to detect format
            with open(self.history_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            if not content:
                return []
            
            # Check if it's an old format JSON array (starts with [)
            if content.startswith('['):
                try:
                    # Old format - parse as JSON array
                    data = json.loads(content)
                    if isinstance(data, list):
                        prompts = data
                        # Migrate to new format
                        self._save_history(prompts)
                        return prompts[-self.max_history:] if len(prompts) > self.max_history else prompts
                except json.JSONDecodeError:
                    pass  # Fall through to line-by-line parsing
            
            # New JSONL format - parse line by line
            prompts = []
            lines = content.split('\n')
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if not line:
                    continue
                
                try:
                    # Parse each line as JSON
                    data = json.loads(line)
                    if isinstance(data, dict) and 'prompt' in data:
                        prompts.append(data['prompt'])
                    elif isinstance(data, str):
                        # Handle migration from old format or simple string lines
                        prompts.append(data)
                    else:
                        emsg(f"Warning: Invalid history entry at line {line_num}")
                except json.JSONDecodeError:
                    # Handle non-JSON lines (migration from old format)
                    prompts.append(line)
            
            # Return only the most recent prompts (up to max_history)
            return prompts[-self.max_history:] if len(prompts) > self.max_history else prompts
                
        except (IOError, OSError) as e:
            emsg(f"Warning: Could not load prompt history: {e}")
            return []

    def save_prompt(self, prompt: str) -> bool:
        """
        Save a single prompt to history file.

        Args:
            prompt: The prompt string to save.

        Returns:
            True if successful, False otherwise.
        """
        if not self.enabled or not prompt.strip():  # Don't save empty prompts or if disabled
            return True

        try:
            self._ensure_history_dir()
            
            # Check if this is a duplicate of the last prompt
            last_prompt = self._get_last_prompt()
            if last_prompt == prompt:
                return True  # Duplicate, but that's fine
            
            # Append prompt as a single JSON line (efficient append-only operation)
            history_entry = {
                'prompt': prompt,
                'timestamp': str(Path().resolve()),  # Current directory as context
                'ts': __import__('time').time()  # Unix timestamp for ordering
            }
            
            with open(self.history_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(history_entry) + '\n')
            
            # Periodically clean up old entries to prevent file from growing indefinitely
            # Clean up every 50 saves to balance performance and file size
            if hasattr(self, '_save_count'):
                self._save_count += 1
            else:
                self._save_count = 1
                
            if self._save_count % 50 == 0:
                self._cleanup_old_entries()
            
            return True
            
        except Exception as e:
            emsg(f"Error saving prompt to history: {e}")
            return False

    def _get_last_prompt(self) -> Optional[str]:
        """
        Get the last prompt from history without loading the entire file.
        
        Returns:
            The last prompt string, or None if no history exists.
        """
        if not self.history_file.exists():
            return None
        
        try:
            with open(self.history_file, 'rb') as f:
                # Seek to end of file and read backwards to find last line
                f.seek(0, 2)  # Go to end
                file_size = f.tell()
                
                if file_size == 0:
                    return None
                
                # Read last line efficiently
                f.seek(max(0, file_size - 4096))  # Read last 4KB max
                lines = f.read().decode('utf-8').splitlines()
                if lines:
                    last_line = lines[-1]
                    try:
                        data = json.loads(last_line)
                        return data.get('prompt') if isinstance(data, dict) else last_line
                    except json.JSONDecodeError:
                        return last_line
                
            return None
        except Exception:
            return None

    def _save_history(self, prompts: List[str]) -> bool:
        """
        Save prompts to history file in JSONL format.
        
        Args:
            prompts: List of prompts to save.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            self._ensure_history_dir()
            
            with open(self.history_file, 'w', encoding='utf-8') as f:
                for prompt in prompts:
                    history_entry = {
                        'prompt': prompt,
                        'timestamp': str(Path().resolve()),
                        'ts': __import__('time').time()
                    }
                    f.write(json.dumps(history_entry) + '\n')
            
            return True
            
        except (IOError, OSError) as e:
            emsg(f"Error saving history file: {e}")
            return False

    def _cleanup_old_entries(self) -> bool:
        """
        Clean up old history entries to keep file size manageable.
        This rewrites the file with only the most recent max_history entries.
        
        Returns:
            True if successful, False otherwise.
        """
        try:
            prompts = self.load_history()
            if len(prompts) <= self.max_history:
                return True  # No cleanup needed
            
            # Keep only the most recent prompts
            recent_prompts = prompts[-self.max_history:]
            
            # Rewrite file with only recent prompts
            with open(self.history_file, 'w', encoding='utf-8') as f:
                for prompt in recent_prompts:
                    history_entry = {
                        'prompt': prompt,
                        'timestamp': str(Path().resolve()),
                        'ts': __import__('time').time()
                    }
                    f.write(json.dumps(history_entry) + '\n')
            
            return True
            
        except Exception as e:
            emsg(f"Error cleaning up history file: {e}")
            return False

    def clear_history(self) -> bool:
        """
        Clear the prompt history file.

        Returns:
            True if successful, False otherwise.
        """
        try:
            if self.history_file.exists():
                self.history_file.unlink()
                # Reset save count
                if hasattr(self, '_save_count'):
                    delattr(self, '_save_count')
            return True
        except OSError as e:
            emsg(f"Error clearing history file: {e}")
            return False

    def get_history_stats(self) -> dict:
        """
        Get statistics about the prompt history.

        Returns:
            Dictionary with history statistics.
        """
        prompts = self.load_history()
        file_size = 0
        if self.history_file.exists():
            try:
                file_size = self.history_file.stat().st_size
            except OSError:
                pass
        
        return {
            'total_prompts': len(prompts),
            'max_history': self.max_history,
            'history_file': str(self.history_file),
            'file_exists': self.history_file.exists(),
            'file_size_bytes': file_size,
            'format': 'JSONL (one JSON object per line)'
        }


# Global instance
prompt_history_manager = PromptHistoryManager()
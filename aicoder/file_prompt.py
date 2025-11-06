"""
File-based prompting system for automated AI Coder testing.
"""

import time
import threading
from pathlib import Path
from typing import Optional

from .config import get_file_prompt_mode, get_file_prompt_path


class FilePromptManager:
    """Manages file-based prompting for automated testing."""
    
    def __init__(self):
        self.prompt_path = Path(get_file_prompt_path())
        self.monitor_thread = None
        self.is_monitoring = False
        self.last_mtime = 0
        
    def is_file_mode_enabled(self) -> bool:
        """Check if file-based prompting mode is enabled."""
        return get_file_prompt_mode()
    
    def setup_file_mode(self) -> bool:
        """Setup file-based prompting mode. Returns True if in file mode."""
        if not self.is_file_mode_enabled():
            return False
            
        print("📄 File-based prompting enabled")
        print(f"📝 Reading prompts from: {self.prompt_path}")
        print("⌨️  Press Ctrl+C to exit file mode\n")
        
        return True
    
    def wait_for_prompt_file(self) -> Optional[str]:
        """Wait for and read the prompt file. Returns None if file doesn't exist."""
        try:
            if not self.prompt_path.exists():
                return None
            
            # Get file modification time
            mtime = self.prompt_path.stat().st_mtime
            
            # If file hasn't changed, wait a bit more
            if mtime == self.last_mtime:
                time.sleep(0.1)
                return None
            
            self.last_mtime = mtime
            
            # Read the file content
            content = self.prompt_path.read_text(encoding='utf-8').strip()
            
            if not content:
                return None
            
            # Delete the prompt file after reading (one-time use)
            try:
                self.prompt_path.unlink()
            except OSError:
                pass  # File might have been deleted by another process
            
            return content
            
        except Exception as e:
            print(f"❌ Error reading prompt file: {e}")
            return None
    
    def start_monitoring(self):
        """Start monitoring for prompt files in background mode."""
        if self.is_monitoring:
            return
            
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        print(f"🔍 Started monitoring {self.prompt_path} for prompts")
    
    def stop_monitoring(self):
        """Stop monitoring for prompt files."""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)
    
    def _monitor_loop(self):
        """Background monitoring loop for prompts."""
        while self.is_monitoring:
            try:
                prompt = self.wait_for_prompt_file()
                if prompt:
                    print(f"📝 Found new prompt: {prompt[:50]}...")
                    # The actual processing will be handled by the main app
                    # This just monitors and notifies
                    
                time.sleep(0.1)  # Check every 100ms
                
            except Exception as e:
                print(f"❌ Error in monitoring loop: {e}")
                time.sleep(1.0)  # Wait longer on error
    
    def get_prompt_path(self) -> Path:
        """Get the prompt file path."""
        return self.prompt_path


# Global instance
_file_prompt_manager = None


def get_file_prompt_manager() -> FilePromptManager:
    """Get the global file prompt manager instance."""
    global _file_prompt_manager
    if _file_prompt_manager is None:
        _file_prompt_manager = FilePromptManager()
    return _file_prompt_manager


def is_file_mode() -> bool:
    """Check if file-based prompting mode is enabled."""
    return get_file_prompt_mode()


def create_test_prompt_file(content: str, prompt_path: Optional[str] = None) -> bool:
    """Create a test prompt file with the given content."""
    try:
        path = Path(prompt_path) if prompt_path else Path(get_file_prompt_path())
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
        return True
    except Exception as e:
        print(f"❌ Failed to create test prompt file: {e}")
        return False
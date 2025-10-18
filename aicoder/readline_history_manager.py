"""Readline history management for different input contexts."""

from typing import List

try:
    import readline
    READLINE_AVAILABLE = True
except ImportError:
    READLINE_AVAILABLE = False
    readline = None


class ReadlineHistoryManager:
    """Manages separate readline histories for different input contexts."""
    
    def __init__(self):
        self.histories = {
            'user_input': [],
            'tool_approval': [
                'a) Allow once',
                'a+) Allow once with guidance',
                's) Allow for session',
                's+) Allow for session with guidance',
                'd) Deny',
                'd+) Deny with guidance',
                'c) Cancel all',
                'diff) Show external diff',
                'diff-edit) Interactive diff edit',
                'yolo) YOLO mode',
                'yolo+) YOLO mode with guidance',
                'help) Show help'
            ]
        }
        self.current_context = 'user_input'
        self._max_history = 1000  # Maximum history items per context
        
    def switch_context(self, context: str):
        """Switch to a different input context, saving current history."""
        if not READLINE_AVAILABLE:
            return
            
        # Save current history, but NOT for tool_approval (keep it static)
        if self.current_context in self.histories and self.current_context != 'tool_approval':
            self.histories[self.current_context] = []
            try:
                # Get current history
                length = readline.get_current_history_length()
                for i in range(length):
                    self.histories[self.current_context].append(readline.get_history_item(i + 1))
            except:
                pass
        
        # Load new context history
        self.current_context = context
        if context in self.histories:
            self._load_history(self.histories[context])
    
    def _load_history(self, history_items: List[str]):
        """Load history items into readline."""
        if not READLINE_AVAILABLE:
            return
            
        try:
            # Clear current history
            readline.clear_history()
            
            # Load new history
            # Items are stored in display order, but readline shows them in reverse
            # when pressing UP, so we add them in reverse order
            for item in reversed(history_items[-self._max_history:]):
                readline.add_history(item)
        except:
            pass
    
    def add_to_current_history(self, item: str):
        """Add an item to the current context history."""
        if not READLINE_AVAILABLE:
            return
            
        if self.current_context in self.histories:
            self.histories[self.current_context].append(item)
            # Keep only recent items
            if len(self.histories[self.current_context]) > self._max_history:
                self.histories[self.current_context] = self.histories[self.current_context][-self._max_history:]
    
    def save_user_input(self, user_input: str):
        """Save user input to the user input history."""
        if user_input.strip():  # Only save non-empty inputs
            # Switch to user context, add the input, then switch back
            original_context = self.current_context
            self.switch_context('user_input')
            self.add_to_current_history(user_input)
            if original_context != 'user_input':
                self.switch_context(original_context)
    
    def setup_user_input_mode(self):
        """Switch to user input mode."""
        self.switch_context('user_input')
    
    def setup_tool_approval_mode(self):
        """Switch to tool approval mode."""
        self.switch_context('tool_approval')


# Global instance
prompt_history_manager = ReadlineHistoryManager()
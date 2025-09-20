"""
Session Manager Plugin for AI Coder

This plugin provides automatic session management with save/load capabilities.
Sessions are stored in .aicoder/sessions/ by default.
"""

import os
import json
import atexit
from datetime import datetime

# Global variables
_session_dir = None
_current_session_file = None
_session_manager_ref = None
_debug_enabled = False


def on_plugin_load():
    """Called when the plugin is loaded"""
    pass


def on_aicoder_init(aicoder_instance):
    """Called when AICoder instance is initialized"""
    try:
        global _session_manager_ref, _debug_enabled
        _session_manager_ref = aicoder_instance
        _debug_enabled = os.environ.get("DEBUG", "0") == "1"

        # Debug: Check message history state when plugin is initialized
        if _debug_enabled and hasattr(aicoder_instance, "message_history"):
            messages = aicoder_instance.message_history.messages
            print(f"DEBUG: Plugin init - message history has {len(messages)} messages")
            if messages:
                print(
                    f"DEBUG: First message role: {messages[0].get('role', 'unknown')}"
                )

        # Add /sessions command to the command registry
        aicoder_instance.command_handlers["/sessions"] = _handle_sessions_command

        # Initialize session directory
        _init_session_directory()

        # Try to load the current session
        _load_current_session()

        # Register exit handler for auto-save
        atexit.register(_auto_save_on_exit)

        print("✅ Session manager plugin loaded successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to load session manager plugin: {e}")
        import traceback

        traceback.print_exc()
        return False


def _auto_save_on_exit():
    """Auto-save session on exit"""
    try:
        _save_current_session()
        print("✅ Current session auto-saved")
    except Exception as e:
        print(f"❌ Error during session auto-save: {e}")


def _get_session_dir():
    """Get the session directory path"""
    global _session_dir
    if _session_dir:
        return _session_dir

    # Check environment variable override
    session_dir_env = os.environ.get("AICODER_SESSIONS_DIR")
    if session_dir_env:
        _session_dir = session_dir_env
    else:
        # Default to .aicoder/sessions in current directory
        _session_dir = os.path.join(os.getcwd(), ".aicoder", "sessions")

    return _session_dir


def _init_session_directory():
    """Initialize the session directory"""
    session_dir = _get_session_dir()
    os.makedirs(session_dir, exist_ok=True)
    return session_dir


def _get_current_session_file():
    """Get the path to the current session tracking file"""
    session_dir = _get_session_dir()
    return os.path.join(session_dir, "session_current.json")


def _load_current_session():
    """Load the current session on startup"""
    global _current_session_file

    current_session_file = _get_current_session_file()

    # Check if current session file exists
    if os.path.exists(current_session_file):
        try:
            with open(current_session_file, "r") as f:
                current_session_data = json.load(f)
                session_filename = current_session_data.get("session_file")

                if session_filename and os.path.exists(session_filename):
                    # Debug: Check current message history before loading
                    if _debug_enabled and hasattr(
                        _session_manager_ref, "message_history"
                    ):
                        current_messages = _session_manager_ref.message_history.messages
                        print(
                            f"DEBUG: Current message history has {len(current_messages)} messages before loading"
                        )
                        if current_messages:
                            print(
                                f"DEBUG: First message role: {current_messages[0].get('role', 'unknown')}"
                            )

                    _current_session_file = session_filename
                    session_name = _get_session_name_from_file(session_filename)

                    # Actually load the session content
                    _load_session_by_filename(session_filename)

                    print(f"✅ Loaded session: {session_name}")
                else:
                    print("⚠️  Current session file not found, creating new session")
                    _create_new_session()
        except Exception as e:
            print(f"❌ Error loading current session: {e}")
            _create_new_session()
    else:
        # No current session, create new one
        _create_new_session()


def _create_new_session(session_name=None):
    """Create a new session"""
    global _current_session_file

    # Generate session filename
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    if not session_name:
        session_name = "unnamed"

    # Sanitize session name
    sanitized_name = _sanitize_session_name(session_name)
    session_filename = f"session_{timestamp}__{sanitized_name}.json"

    session_dir = _get_session_dir()
    full_session_path = os.path.join(session_dir, session_filename)

    # Import the clean_message_for_api function
    from aicoder.message_history import clean_message_for_api

    # Create empty session file with proper initial messages (compatible with /save /load)
    if hasattr(_session_manager_ref, "message_history"):
        # Get the initial messages from the current message history
        initial_messages = _session_manager_ref.message_history.messages
        # Clean them using the same function as the built-in load_session
        clean_initial_messages = [
            clean_message_for_api(msg) for msg in initial_messages
        ]

        # Save just the messages array for compatibility with /save /load
        session_data = clean_initial_messages
    else:
        # Fallback if message history is not available
        session_data = []

    try:
        with open(full_session_path, "w") as f:
            json.dump(session_data, f, indent=2)

        # Update current session tracking
        _update_current_session_tracking(full_session_path)
        _current_session_file = full_session_path

        print(f"✅ Created new session: session_{timestamp}__{sanitized_name}")

    except Exception as e:
        print(f"❌ Error creating new session: {e}")


def _sanitize_session_name(name):
    """Sanitize session name for filesystem compatibility"""
    # Replace spaces and special characters with underscores
    sanitized = "".join(
        c if c.isalnum() or c in "-_" or c == " " else "_" for c in name
    )
    # Replace spaces with underscores
    sanitized = sanitized.replace(" ", "_")
    # Remove multiple consecutive underscores
    while "__" in sanitized:
        sanitized = sanitized.replace("__", "_")
    # Remove leading/trailing underscores
    sanitized = sanitized.strip("_")
    return sanitized or "unnamed"


def _update_current_session_tracking(session_file_path):
    """Update the current session tracking file"""
    current_session_file = _get_current_session_file()

    tracking_data = {
        "session_file": session_file_path,
        "updated_at": datetime.now().isoformat(),
    }

    try:
        with open(current_session_file, "w") as f:
            json.dump(tracking_data, f, indent=2)
    except Exception as e:
        print(f"❌ Error updating current session tracking: {e}")


def _get_session_name_from_file(filepath):
    """Extract session name from file path"""
    filename = os.path.basename(filepath)
    if filename.endswith(".json"):
        filename = filename[:-5]  # Remove .json extension
    return filename


def _handle_sessions_command(args):
    """Handle /sessions command"""
    global _session_manager_ref, _current_session_file

    if not _session_manager_ref:
        print("❌ Session manager not available")
        return False, False

    if not args:
        # List sessions
        _list_sessions()
        return False, False

    command = args[0].lower()

    if command in ["list", "ls"]:
        _list_sessions()
        return False, False
    elif command == "load":
        if len(args) < 2:
            print("❌ Usage: /sessions load <session_name>")
            return False, False
        _load_session(args[1])
        return False, False
    elif command == "save":
        _save_current_session()
        return False, False
    elif command == "new":
        session_name = " ".join(args[1:]) if len(args) > 1 else None
        _create_new_session(session_name)
        return False, False
    elif command == "delete":
        if len(args) < 2:
            print("❌ Usage: /sessions delete <session_name>")
            return False, False
        _delete_session(args[1])
        return False, False
    elif command == "rename":
        if len(args) < 2:
            print("❌ Usage: /sessions rename <new_name>")
            return False, False
        # Join all arguments as a single name
        new_name = " ".join(args[1:])
        _rename_current_session(new_name)
        return False, False
    elif command == "info":
        _show_session_info()
        return False, False
    elif command == "help":
        _show_help()
        return False, False
    else:
        print(f"❌ Unknown command: {command}")
        print("Use '/sessions help' for available commands")
        return False, False


def _show_help():
    """Show help information for /sessions commands"""
    print("\n📋 Session Manager Help:")
    print("=" * 50)
    print("/sessions                    - List all sessions")
    print("/sessions list              - List all sessions")
    print("/sessions load <name>       - Load a specific session")
    print("/sessions save              - Save the current session")
    print("/sessions new [name]        - Create a new session (optional name)")
    print("/sessions delete <name>     - Delete a session")
    print("/sessions rename <name>     - Rename the current session")
    print("/sessions info              - Show current session information")
    print("/sessions help              - Show this help message")
    print("\n💡 Tips:")
    print("- Session names with spaces are automatically converted to underscores")
    print("- All arguments after 'rename' are treated as a single name")
    print("- Sessions are auto-saved when AI Coder exits")


def _list_sessions():
    """List all available sessions"""
    session_dir = _get_session_dir()

    if not os.path.exists(session_dir):
        print("No sessions directory found")
        return

    # Get all session files
    session_files = [
        f
        for f in os.listdir(session_dir)
        if f.startswith("session_")
        and f.endswith(".json")
        and f != "session_current.json"
    ]

    if not session_files:
        print("No sessions found")
        return

    print("\n📋 Available Sessions:")
    print("=" * 60)

    # Sort by creation time (filename)
    session_files.sort()

    current_session_name = None
    if _current_session_file:
        current_session_name = _get_session_name_from_file(_current_session_file)

    for session_file in session_files:
        session_name = session_file[:-5]  # Remove .json extension
        current_marker = " (current)" if session_name == current_session_name else ""
        print(f"  {session_name}{current_marker}")


def _load_session(session_name):
    """Load a specific session"""
    global _current_session_file

    session_dir = _get_session_dir()
    session_file = f"{session_name}.json"
    full_session_path = os.path.join(session_dir, session_file)

    if not os.path.exists(full_session_path):
        print(f"❌ Session '{session_name}' not found")
        return

    try:
        # Load session data
        with open(full_session_path, "r") as f:
            session_data = json.load(f)

        # Update message history
        if hasattr(_session_manager_ref, "message_history"):
            # Debug: Check current state before loading
            if _debug_enabled:
                old_messages = _session_manager_ref.message_history.messages
                print(
                    f"DEBUG: About to load session, current message count: {len(old_messages)}"
                )

            # Import the clean_message_for_api function
            from aicoder.message_history import clean_message_for_api

            # Handle both formats:
            # 1. Old format: {"messages": [...], "created_at": "...", ...}
            # 2. New format: [...] (direct array like /save produces)
            if isinstance(session_data, dict) and "messages" in session_data:
                # Old format with metadata
                loaded_messages = session_data.get("messages", [])
                if _debug_enabled:
                    print(
                        f"DEBUG: Loading from old format with {len(loaded_messages)} messages"
                    )
            elif isinstance(session_data, list):
                # New format - direct messages array like /save produces
                loaded_messages = session_data
                if _debug_enabled:
                    print(
                        f"DEBUG: Loading from new format with {len(loaded_messages)} messages"
                    )
            else:
                print(f"❌ Invalid session format in '{session_name}'")
                return

            # Clean messages using the same function as the built-in load_session
            clean_messages = [clean_message_for_api(msg) for msg in loaded_messages]

            _session_manager_ref.message_history.messages = clean_messages

            # Debug: Check result after loading
            if _debug_enabled:
                new_messages = _session_manager_ref.message_history.messages
                print(f"DEBUG: After loading, message count: {len(new_messages)}")

            print(f"✅ Loaded session: {session_name}")

            # Update current session tracking
            _update_current_session_tracking(full_session_path)
            _current_session_file = full_session_path
        else:
            print("❌ Message history not available")
    except Exception as e:
        print(f"❌ Error loading session '{session_name}': {e}")
        import traceback

        traceback.print_exc()


def _load_session_by_filename(session_filename):
    """Load a session directly by filename"""
    global _current_session_file

    if not os.path.exists(session_filename):
        print(f"❌ Session file not found: {session_filename}")
        return

    try:
        # Load session data
        with open(session_filename, "r") as f:
            session_data = json.load(f)

        # Update message history
        if hasattr(_session_manager_ref, "message_history"):
            # Debug: Check current state before loading
            if _debug_enabled:
                old_messages = _session_manager_ref.message_history.messages
                print(
                    f"DEBUG: About to load session, current message count: {len(old_messages)}"
                )

            # Import the clean_message_for_api function
            from aicoder.message_history import clean_message_for_api

            # Handle both formats:
            # 1. Old format: {"messages": [...], "created_at": "...", ...}
            # 2. New format: [...] (direct array like /save produces)
            if isinstance(session_data, dict) and "messages" in session_data:
                # Old format with metadata
                loaded_messages = session_data.get("messages", [])
                if _debug_enabled:
                    print(
                        f"DEBUG: Loading from old format with {len(loaded_messages)} messages"
                    )
            elif isinstance(session_data, list):
                # New format - direct messages array like /save produces
                loaded_messages = session_data
                if _debug_enabled:
                    print(
                        f"DEBUG: Loading from new format with {len(loaded_messages)} messages"
                    )
            else:
                print(f"❌ Invalid session format in '{session_filename}'")
                return

            # Clean messages using the same function as the built-in load_session
            clean_messages = [clean_message_for_api(msg) for msg in loaded_messages]

            _session_manager_ref.message_history.messages = clean_messages

            # Debug: Check result after loading
            if _debug_enabled:
                new_messages = _session_manager_ref.message_history.messages
                print(f"DEBUG: After loading, message count: {len(new_messages)}")

            # Update current session tracking
            _update_current_session_tracking(session_filename)
            _current_session_file = session_filename
        else:
            print("❌ Message history not available")
    except Exception as e:
        print(f"❌ Error loading session '{session_filename}': {e}")
        import traceback

        traceback.print_exc()


def _save_current_session():
    """Save the current session"""
    global _current_session_file

    if not _current_session_file:
        print("❌ No current session to save")
        return

    if not hasattr(_session_manager_ref, "message_history"):
        print("❌ Message history not available")
        return

    try:
        # Prepare session data - just the messages for compatibility with /save /load
        # Import the clean_message_for_api function
        from aicoder.message_history import clean_message_for_api

        # Clean the messages using the same function as the built-in save_session
        clean_messages = [
            clean_message_for_api(msg)
            for msg in _session_manager_ref.message_history.messages
        ]

        # Save just the messages array for compatibility with /save /load
        session_data = clean_messages

        # Save session data
        with open(_current_session_file, "w") as f:
            json.dump(session_data, f, indent=2)

        session_name = _get_session_name_from_file(_current_session_file)
        print(f"✅ Saved session: {session_name}")

    except Exception as e:
        print(f"❌ Error saving session: {e}")


def _delete_session(session_name):
    """Delete a session"""
    global _current_session_file

    session_dir = _get_session_dir()
    session_file = f"{session_name}.json"
    full_session_path = os.path.join(session_dir, session_file)

    if not os.path.exists(full_session_path):
        print(f"❌ Session '{session_name}' not found")
        return

    try:
        # Check if this is the current session
        is_current = (
            _current_session_file
            and os.path.basename(_current_session_file) == session_file
        )

        # Delete the file
        os.remove(full_session_path)
        print(f"✅ Deleted session: {session_name}")

        # If we deleted the current session, create a new one
        if is_current:
            _current_session_file = None
            _create_new_session()

    except Exception as e:
        print(f"❌ Error deleting session '{session_name}': {e}")


def _rename_current_session(new_name):
    """Rename the current session"""
    global _current_session_file

    if not _current_session_file:
        print("❌ No current session to rename")
        return

    try:
        # Get current session name
        current_session_name = _get_session_name_from_file(_current_session_file)

        # Sanitize new name
        sanitized_name = _sanitize_session_name(new_name)

        # Extract timestamp from current name
        parts = current_session_name.split("__")
        if len(parts) >= 2:
            timestamp = parts[0]  # Keep the timestamp part
            new_session_name = f"{timestamp}__{sanitized_name}"
        else:
            # Fallback if naming convention is unexpected
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            new_session_name = f"session_{timestamp}__{sanitized_name}"

        # Create new filename
        session_dir = _get_session_dir()
        new_session_file = f"{new_session_name}.json"
        new_full_path = os.path.join(session_dir, new_session_file)

        # Rename the file
        os.rename(_current_session_file, new_full_path)

        # Update tracking
        _update_current_session_tracking(new_full_path)
        _current_session_file = new_full_path

        print(f"✅ Renamed session to: {new_session_name}")

    except Exception as e:
        print(f"❌ Error renaming session: {e}")


def _show_session_info():
    """Show information about the current session"""
    global _current_session_file

    if not _current_session_file or not os.path.exists(_current_session_file):
        print("❌ No current session")
        return

    try:
        with open(_current_session_file, "r") as f:
            session_data = json.load(f)

        session_name = _get_session_name_from_file(_current_session_file)

        print(f"\n🔍 Session Information: {session_name}")
        print("=" * 50)
        print(f"File: {_current_session_file}")

        # Handle both formats
        if isinstance(session_data, dict) and "messages" in session_data:
            # Old format with metadata
            print(f"Created: {session_data.get('created_at', 'Unknown')}")
            print(f"Last Modified: {session_data.get('last_modified', 'Unknown')}")
            message_count = len(session_data.get("messages", []))
        elif isinstance(session_data, list):
            # New format - direct messages array
            message_count = len(session_data)
            # Try to get file modification time as fallback
            try:
                mod_time = os.path.getmtime(_current_session_file)
                print(f"Last Modified: {datetime.fromtimestamp(mod_time).isoformat()}")
            except Exception:
                print("Last Modified: Unknown")
        else:
            print("Created: Unknown")
            print("Last Modified: Unknown")
            message_count = 0

        print(f"Messages: {message_count}")

        # Try to get file size
        try:
            file_size = os.path.getsize(_current_session_file)
            print(f"File Size: {file_size} bytes")
        except Exception:
            pass

    except Exception as e:
        print(f"❌ Error getting session info: {e}")

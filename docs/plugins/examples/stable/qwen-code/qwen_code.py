"""
Qwen Code Plugin for AI Coder.
Provides a /qwen-code refresh command to load Qwen API key from oauth credentials file.
"""

import json
from pathlib import Path


def on_aicoder_init(app):
    """Hook called when AICoder is initialized."""

    # Add the qwen-code refresh command to the command handlers
    def handle_qwen_code_refresh(args):
        """Refresh Qwen API key from ~/.qwen/oauth_creds.json"""
        oauth_file = Path.home() / ".qwen" / "oauth_creds.json"

        if not oauth_file.exists():
            print(f"\n[X] Qwen OAuth credentials file not found at {oauth_file}")
            print("   Make sure you've authenticated with Qwen first.")
            return False, False

        try:
            with open(oauth_file, "r") as f:
                creds = json.load(f)

            access_token = creds.get("access_token")
            if not access_token:
                print(f"\n[X] No access_token found in {oauth_file}")
                return False, False

            # Update the API key in the config module
            import aicoder.config

            aicoder.config.API_KEY = access_token

            print(f"\n[✓] Qwen API key refreshed from {oauth_file}")
            print(f"   Key length: {len(access_token)} characters")

            return False, False

        except json.JSONDecodeError as e:
            print(f"\n[X] Failed to parse JSON from {oauth_file}: {e}")
            return False, False
        except Exception as e:
            print(f"\n[X] Failed to read Qwen OAuth credentials: {e}")
            return False, False

    # Register the command handler
    app.command_handlers["/qwen-code refresh"] = handle_qwen_code_refresh
    app.command_handlers["/qwen-code"] = handle_qwen_code_refresh

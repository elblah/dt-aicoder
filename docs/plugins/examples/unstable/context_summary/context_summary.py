"""
Context Summary Plugin with Auto Compaction for AICoder
Automatically summarizes conversation context and compacts memory based on model-specific token limits
"""

import os

# Plugin metadata
__version__ = "1.0.0"
__author__ = "AI Coder Plugin Developer"
__description__ = "Automatically summarizes conversation context and compacts memory based on model-specific token limits"

# Model-specific token limits (based on first tier or default values)
MODEL_TOKEN_LIMITS = {
    # OpenAI models
    "gpt-5-nano": 128000,
    # Google models
    "gemini-2.5-pro": 100000,
    "gemini-2.5-flash": 100000,
    # Qwen models with tiered pricing
    "qwen3-coder-plus": 128000,
    "qwen3-coder-flash": 128000,
    # Cerebras models
    "qwen-3-coder-480b": 60000,
    # Default fallback
    "default": 128000,
}

# Configuration
AUTO_SUMMARY_THRESHOLD = 50  # Number of messages before auto-summarization
SUMMARY_INTERVAL = 20  # Summarize every N messages after threshold
TOKEN_LIMIT_THRESHOLD = 0.9  # 90% of model token limit


def get_model_token_limit(model_name: str) -> int:
    """Get the token limit for a specific model."""
    # Try exact match first
    if model_name in MODEL_TOKEN_LIMITS:
        return MODEL_TOKEN_LIMITS[model_name]

    # Try partial match (useful for versioned models)
    for model_key in MODEL_TOKEN_LIMITS:
        if model_key in model_name:
            return MODEL_TOKEN_LIMITS[model_key]

    # Fallback to default
    return MODEL_TOKEN_LIMITS["default"]


def get_current_model_name() -> str:
    """Get the current model name from environment variables."""
    return (
        os.environ.get("OPENAI_MODEL")
        or os.environ.get("MODEL")
        or os.environ.get("AI_MODEL")
        or "default"
    )


def on_plugin_load():
    """Called when the plugin is loaded"""
    # Monkey patch MessageHistory to add auto-summarization and auto-compaction
    from aicoder.message_history import MessageHistory
    from aicoder.stats import Stats

    # Store reference to the main AICoder instance
    main_aicoder_instance = None

    # Store the original method
    original_add_assistant_message = MessageHistory.add_assistant_message

    def _enhanced_add_assistant_message(self, message):
        """Wrapper that adds auto-summarization and auto-compaction with detailed reasons"""
        # Call the original method
        result = original_add_assistant_message(self, message)

        # Check if we should auto-summarize based on message count
        message_count = len(self.messages)
        if message_count >= AUTO_SUMMARY_THRESHOLD:
            if message_count == AUTO_SUMMARY_THRESHOLD:
                print(
                    f"ℹ️  Reached initial auto-summary threshold ({AUTO_SUMMARY_THRESHOLD} messages), triggering context summarization"
                )
                self.summarize_context()
                return result
            elif message_count % SUMMARY_INTERVAL == 0:
                print(
                    f"ℹ️  Reached periodic summary interval ({SUMMARY_INTERVAL} messages), triggering context summarization"
                )
                self.summarize_context()
                return result

        # Check if we should auto-compact based on token count
        # Try to get the main application's stats from our stored reference
        stats_instance = None
        if main_aicoder_instance and hasattr(main_aicoder_instance, "stats"):
            stats_instance = main_aicoder_instance.stats
        elif "aicoder" in globals() and hasattr(globals()["aicoder"], "stats"):
            stats_instance = globals()["aicoder"].stats
        elif hasattr(self, "api_handler") and hasattr(self.api_handler, "stats"):
            # Try to get stats from the api_handler (which should be the AICoder instance)
            stats_instance = self.api_handler.stats
        elif hasattr(self, "aicoder") and hasattr(self.aicoder, "stats"):
            stats_instance = self.aicoder.stats
        elif hasattr(self, "stats"):
            stats_instance = self.stats

        if stats_instance and isinstance(stats_instance, Stats):
            # Debug output to see what tokens we're getting
            prompt_tokens = stats_instance.prompt_tokens
            completion_tokens = stats_instance.completion_tokens
            total_tokens = prompt_tokens + completion_tokens
            print(
                f"DEBUG: Token counts - Prompt: {prompt_tokens}, Completion: {completion_tokens}, Total: {total_tokens}"
            )

            # Get current model token limit
            model_name = get_current_model_name()
            token_limit = get_model_token_limit(model_name)

            # Check if we're approaching the limit
            if total_tokens > (token_limit * TOKEN_LIMIT_THRESHOLD):
                usage_percentage = (total_tokens / token_limit) * 100
                print(
                    f"⚠️  Approaching token limit for {model_name} ({total_tokens}/{token_limit} tokens, {usage_percentage:.1f}%), triggering auto-compaction"
                )
                # Trigger compaction
                self.compact_memory()

        return result

    # Apply the monkey patch
    MessageHistory.add_assistant_message = _enhanced_add_assistant_message

    print("✅ MessageHistory patched for auto-summarization and auto-compaction")
    print("✅ Context summary with auto-compaction plugin loaded successfully")
    print(f"   - Auto-summary threshold: {AUTO_SUMMARY_THRESHOLD} messages")
    print(f"   - Summary interval: every {SUMMARY_INTERVAL} messages")
    print(
        f"   - Token limit threshold: {TOKEN_LIMIT_THRESHOLD * 100:.0f}% of model limit"
    )
    print("   - Model-specific token limits enabled")
    print("   - Use '/summarize' to manually trigger context summarization")
    print("   - Use '/compact' to manually trigger context compaction")

    return True


def on_aicoder_init(aicoder_instance):
    """Called when AICoder instance is initialized"""
    try:
        # Store reference to aicoder instance in global namespace so the monkey-patched function can access it
        global main_aicoder_instance
        main_aicoder_instance = aicoder_instance

        # Also store in globals() dictionary for explicit access
        globals()["aicoder"] = aicoder_instance

        # Also store reference on the instance itself
        aicoder_instance.context_summary_aicoder = aicoder_instance

        # Register the /summarize command
        def summarize_command(args):
            """Manually trigger context summarization"""
            if hasattr(aicoder_instance, "message_history"):
                message_count = len(aicoder_instance.message_history.messages)
                print(
                    f"ℹ️  Manual summarization triggered (current message count: {message_count})"
                )
                aicoder_instance.message_history.summarize_context()
                new_message_count = len(aicoder_instance.message_history.messages)
                print(
                    f"✅ Context summarized (message count: {message_count} → {new_message_count})"
                )
            else:
                print("❌ Failed to find message history")
            # Return (should_quit, run_api_call) tuple as expected by command handler
            return False, False

        # Register the /compact command
        def compact_command(args):
            """Manually trigger context compaction"""
            if hasattr(aicoder_instance, "message_history"):
                message_count = len(aicoder_instance.message_history.messages)
                # Get token information if available
                token_info = ""
                # Use the main application's stats instead of message history's stats
                if hasattr(aicoder_instance, "stats"):
                    stats = aicoder_instance.stats
                    total_tokens = stats.prompt_tokens + stats.completion_tokens
                    model_name = get_current_model_name()
                    token_limit = get_model_token_limit(model_name)
                    token_info = f" (tokens: {total_tokens}/{token_limit})"
                print(
                    f"ℹ️  Manual compaction triggered (current message count: {message_count}{token_info})"
                )
                aicoder_instance.message_history.compact_memory()
                new_message_count = len(aicoder_instance.message_history.messages)
                print(
                    f"✅ Context compacted (message count: {message_count} → {new_message_count})"
                )
            else:
                print("❌ Failed to find message history")
            # Return (should_quit, run_api_call) tuple as expected by command handler
            return False, False

        # Register the commands with the app's command handlers
        aicoder_instance.command_handlers["/summarize"] = summarize_command
        aicoder_instance.command_handlers["/compact"] = compact_command
        print("✅ Context summary and compaction commands registered successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to register context summary and compaction commands: {e}")
        return False


# Only execute on load when running as a plugin
# This prevents execution when importing for testing
if __name__ != "__main__":
    on_plugin_load()

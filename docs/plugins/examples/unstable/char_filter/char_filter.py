"""
Character Filter Plugin for AI Coder

Filters ALL message content to prevent problematic characters from entering message history.
This prevents context pollution and model instability.

This plugin is trying to correct Deepseek v3.1 that randomly generates chinese chars
and becomes crazy
"""

import re
import os

# Working regex pattern that blocks non-Latin scripts
BLOCKED_PATTERN = re.compile('[^\u0000-\u007F\u0080-\u00FF\u0100-\u017F\u0180-\u024F]', re.UNICODE)

def should_load():
    return "deepseek" in os.environ.get("OPENAI_MODEL", "")

def filter_all_content(content):
    """Remove all blocked characters from any content"""
    if not content or not isinstance(content, str):
        return content or ""
    return BLOCKED_PATTERN.sub('', content)

def on_plugin_load():
    """Called when the plugin is loaded"""
    if not should_load():
        return
    print("Character filter plugin loaded - ready to filter all message content")
    return True

def on_aicoder_init(aicoder_instance):
    """Install filters on ALL message addition points"""
    if not should_load():
        return
    try:
        # Store original methods
        original_user_add = aicoder_instance.message_history.add_user_message
        original_assistant_add = aicoder_instance.message_history.add_assistant_message
        original_tool_add = aicoder_instance.message_history.add_tool_results
        
        # Filter user messages
        def safe_add_user_message(content, **kwargs):
            filtered_content = filter_all_content(content)
            return original_user_add(filtered_content, **kwargs)
        
        # Filter assistant messages
        def safe_add_assistant_message(content, **kwargs):
            filtered_content = filter_all_content(content)
            return original_assistant_add(filtered_content, **kwargs)
        
        # Filter tool results
        def safe_add_tool_results(results, **kwargs):
            filtered_results = []
            for result in results:
                if isinstance(result, dict) and 'content' in result:
                    result = result.copy()
                    result['content'] = filter_all_content(result['content'])
                filtered_results.append(result)
            return original_tool_add(filtered_results, **kwargs)
        
        # Replace methods
        aicoder_instance.message_history.add_user_message = safe_add_user_message
        aicoder_instance.message_history.add_assistant_message = safe_add_assistant_message
        aicoder_instance.message_history.add_tool_results = safe_add_tool_results
        
        print("Character filter installed - all message content will be filtered")
        print("Blocked: Non-Latin scripts (Chinese, Cyrillic, Arabic, etc)")
        return True
    except Exception as e:
        print(f"Failed to install character filter: {e}")
        return False

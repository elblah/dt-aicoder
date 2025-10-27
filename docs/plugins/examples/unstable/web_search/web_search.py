"""
Web Search Plugin for AI Coder

This plugin adds web search capability using DuckDuckGo.
The AI can call the 'web_search' tool to find information online.
"""

import json
import urllib.parse
import urllib.request

# Web search tool definition
WEB_SEARCH_TOOL_DEFINITION = {
    "type": "internal",
    "auto_approved": True,
    "hide_results": False,
    "hide_arguments": False,
    "name": "web_search",
    "description": "Perform a web search to find information about a topic using DuckDuckGo",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The search query"},
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results to return",
                "default": 5,
            },
        },
        "required": ["query"],
    },
}


def execute_web_search(query: str, max_results: int = 5, stats=None) -> str:
    """
    Execute a web search using DuckDuckGo Instant Answer API.

    Args:
        query: The search query string
        max_results: Maximum number of results to return (default: 5)
        stats: Stats object (unused but required for internal tools)

    Returns:
        String with search results or error message
    """
    # Validate parameters
    if not isinstance(query, str):
        raise ValueError("Invalid query format: query must be a string.")

    if not isinstance(max_results, int) or max_results < 1:
        raise ValueError(
            "Invalid max_results format: max_results must be a positive integer."
        )

    try:
        # Use DuckDuckGo Instant Answer API
        encoded_query = urllib.parse.quote(query)
        url = f"https://api.duckduckgo.com/?q={encoded_query}&format=json&no_html=1&skip_disambig=1"

        req = urllib.request.Request(
            url, headers={"User-Agent": "AI Coder Web Search Plugin"}
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())

        # Extract relevant information
        results = []

        # Add abstract/definition if available
        if data.get("Abstract"):
            results.append(f"Definition: {data['Abstract']}")

        # Add related topics
        if data.get("RelatedTopics"):
            for topic in data["RelatedTopics"][:max_results]:
                if isinstance(topic, dict) and topic.get("Text"):
                    results.append(topic["Text"])

        # Add results section
        if data.get("Results"):
            for result in data["Results"][:max_results]:
                if isinstance(result, dict) and result.get("Text"):
                    results.append(result["Text"])

        if results:
            return "\n".join(results[:max_results])
        else:
            return "No relevant results found for the search query."

    except Exception as e:
        return f"Error performing web search: {str(e)}"


def on_plugin_load():
    """Called when the plugin is loaded"""
    pass


def on_aicoder_init(aicoder_instance):
    """Called when AICoder instance is initialized"""
    try:
        # Add the web_search tool to the tool registry
        if hasattr(aicoder_instance, "tool_manager") and hasattr(
            aicoder_instance.tool_manager, "registry"
        ):
            # Add the tool definition to the registry
            aicoder_instance.tool_manager.registry.mcp_tools["web_search"] = (
                WEB_SEARCH_TOOL_DEFINITION
            )

            # Override the tool execution to use our custom implementation
            original_execute_tool = aicoder_instance.tool_manager.executor.execute_tool

            def patched_execute_tool(tool_name, arguments, tool_index=0, total_tools=0):
                if tool_name == "web_search":
                    # Use our custom implementation
                    try:
                        query = arguments.get("query", "")
                        max_results = arguments.get("max_results", 5)
                        result = execute_web_search(query, max_results)
                        return result, WEB_SEARCH_TOOL_DEFINITION, None
                    except Exception as e:
                        return (
                            f"Error executing web_search: {e}",
                            WEB_SEARCH_TOOL_DEFINITION,
                            None,
                        )
                else:
                    # Use original implementation for other tools
                    return original_execute_tool(
                        tool_name, arguments, tool_index, total_tools
                    )

            aicoder_instance.tool_manager.executor.execute_tool = patched_execute_tool

        # Add comprehensive information about web search functionality to the system prompt
        if (
            hasattr(aicoder_instance, "message_history")
            and aicoder_instance.message_history.messages
        ):
            system_prompt = aicoder_instance.message_history.messages[0]
            if isinstance(system_prompt, dict) and "content" in system_prompt:
                web_search_info = """
                
Web Search Capability

The AI Coder includes a web_search tool that allows you to find information online using DuckDuckGo.
This tool helps you access current information that may not be in your training data.

When to Use the web_search Tool:
Use the web_search tool when:
- You need current information (news, recent events, etc.)
- You need specific factual information (statistics, definitions, etc.)
- You want to verify information
- You're working on a task that requires up-to-date knowledge

How to Use the web_search Tool:
1. Identify what information you need
2. Formulate a clear, specific search query
3. Call the web_search tool with your query
4. Use the returned information to answer the user's question or complete the task

Example Usage:
{
  "name": "web_search",
  "arguments": {
    "query": "current population of Tokyo",
    "max_results": 3
  }
}

The tool will return search results that you can use in your response.
"""
                if "Web Search Capability" not in system_prompt["content"]:
                    system_prompt["content"] += web_search_info

        print("[✓] Web search plugin loaded successfully")
        print("   - Custom web_search tool registered")
        print("   - AI instructions added to system prompt")
        return True

    except Exception as e:
        print(f"[X] Failed to load web search plugin: {e}")
        return False

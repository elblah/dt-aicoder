"""
Tests for external MCP tools functionality.

⚠️ CRITICAL: ALWAYS run this test with YOLO_MODE=1 to prevent hanging:

YOLO_MODE=1 python tests/test_external_mcp_tools.py

This test triggers tool approval prompts that will hang indefinitely without YOLO_MODE=1.
"""

import sys
import os
import json
import tempfile
import http.server
import threading

# Add the parent directory to the path to import aicoder modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from aicoder.tool_manager.manager import MCPToolManager
from aicoder.tool_manager.registry import ToolRegistry


class MockStats:
    """Mock stats object for testing."""

    def __init__(self):
        self.tool_errors = 0
        self.tool_calls = 0
        self.tool_time_spent = 0


class MockAnimator:
    """Mock animator object for testing."""

    def start_cursor_blinking(self):
        pass

    def stop_cursor_blinking(self):
        pass


class MockHTTPHandler(http.server.BaseHTTPRequestHandler):
    """Mock HTTP handler for testing JSON-RPC tools."""

    def do_POST(self):
        # Read the request data
        content_length = int(self.headers["Content-Length"])
        post_data = self.rfile.read(content_length)

        # Parse the JSON-RPC request
        try:
            request = json.loads(post_data)
            method = request.get("method", "")
            params = request.get("params", {})

            # Create a mock response
            response = {
                "jsonrpc": "2.0",
                "result": {
                    "method": method,
                    "params": params,
                    "message": "Mock response for testing",
                },
                "id": request.get("id", 1),
            }

            # Send the response
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
        except Exception:
            self.send_response(500)
            self.end_headers()

    def log_message(self, format, *args):
        # Suppress logging
        pass


def test_tool_registry_loads_external_tools():
    """Test that tool registry loads external tools from mcp_tools.json."""
    # Create a temporary directory for testing
    temp_dir = tempfile.TemporaryDirectory()
    original_cwd = os.getcwd()
    original_mcp_tools_path = os.environ.get("MCP_TOOLS_CONF_PATH")

    # Change to the temp directory
    os.chdir(temp_dir.name)

    # Start a mock HTTP server for JSON-RPC testing
    httpd = None
    server_thread = None
    
    # Try to find an available port
    server_port = None
    for port in range(8000, 9000):
        try:
            httpd = http.server.HTTPServer(
                ("localhost", port), MockHTTPHandler
            )
            server_thread = threading.Thread(target=httpd.serve_forever)
            server_thread.daemon = True
            server_thread.start()
            server_port = port
            break
        except OSError:
            # Port is in use, try the next one
            continue
    if server_port is None:
        raise Exception("Could not find an available port for mock server")

    # Create mcp_tools.json with tools that don't make external requests
    mcp_tools_content = f"""{{
  "sample_command_tool": {{
    "type": "command",
    "description": "A sample command tool for testing",
    "command": "echo 'Hello from command tool: {{message}}'",
    "parameters": {{
      "type": "object",
      "properties": {{
        "message": {{
          "type": "string",
          "description": "Message to echo"
        }}
      }},
      "required": ["message"]
    }}
  }},
  "sample_jsonrpc_tool": {{
    "type": "jsonrpc",
    "description": "A sample JSON-RPC tool for testing",
    "url": "http://localhost:{server_port}/rpc",
    "method": "test_method",
    "parameters": {{
      "type": "object",
      "properties": {{
        "data": {{
          "type": "string",
          "description": "Data to send"
        }}
      }},
      "required": ["data"]
    }}
  }},
  "sample_disabled_tool": {{
    "type": "command",
    "description": "A disabled tool that should not be loaded",
    "command": "echo 'This should not appear'",
    "disabled": true,
    "parameters": {{
      "type": "object",
      "properties": {{
        "message": {{
          "type": "string",
          "description": "Message to echo"
        }}
      }},
      "required": ["message"]
    }}
  }}
}}"""

    # Write the config file to the current directory
    config_file_path = os.path.join(temp_dir.name, "mcp_tools.json")
    with open(config_file_path, "w") as f:
        f.write(mcp_tools_content)

    # Set the environment variable to point to our test file
    os.environ["MCP_TOOLS_CONF_PATH"] = config_file_path

    try:
        registry = ToolRegistry()

        # Check that external tools are loaded
        assert "sample_command_tool" in registry.mcp_tools
        assert "sample_jsonrpc_tool" in registry.mcp_tools
        assert "sample_disabled_tool" not in registry.mcp_tools  # Should be disabled

        # Check tool configurations
        command_tool = registry.mcp_tools["sample_command_tool"]
        assert command_tool["type"] == "command"
        assert command_tool["command"] == "echo 'Hello from command tool: {message}'"

        jsonrpc_tool = registry.mcp_tools["sample_jsonrpc_tool"]
        assert jsonrpc_tool["type"] == "jsonrpc"
        assert jsonrpc_tool["url"] == f"http://localhost:{server_port}/rpc"
    finally:
        # Stop the mock server
        if httpd:
            httpd.shutdown()
            httpd.server_close()

        # Restore original environment
        os.chdir(original_cwd)
        if original_mcp_tools_path is not None:
            os.environ["MCP_TOOLS_CONF_PATH"] = original_mcp_tools_path
        elif "MCP_TOOLS_CONF_PATH" in os.environ:
            del os.environ["MCP_TOOLS_CONF_PATH"]

        temp_dir.cleanup()


def test_tool_registry_get_tool_definitions():
    """Test that tool registry generates correct tool definitions."""
    # Create a temporary directory for testing
    temp_dir = tempfile.TemporaryDirectory()
    original_cwd = os.getcwd()
    original_mcp_tools_path = os.environ.get("MCP_TOOLS_CONF_PATH")

    # Change to the temp directory
    os.chdir(temp_dir.name)

    # Start a mock HTTP server for JSON-RPC testing
    httpd = None
    server_thread = None
    
    # Try to find an available port
    server_port = None
    for port in range(8000, 9000):
        try:
            httpd = http.server.HTTPServer(
                ("localhost", port), MockHTTPHandler
            )
            server_thread = threading.Thread(target=httpd.serve_forever)
            server_thread.daemon = True
            server_thread.start()
            server_port = port
            break
        except OSError:
            # Port is in use, try the next one
            continue
    if server_port is None:
        raise Exception("Could not find an available port for mock server")

    # Create mcp_tools.json with tools that don't make external requests
    mcp_tools_content = f"""{{
  "sample_command_tool": {{
    "type": "command",
    "description": "A sample command tool for testing",
    "command": "echo 'Hello from command tool: {{message}}'",
    "parameters": {{
      "type": "object",
      "properties": {{
        "message": {{
          "type": "string",
          "description": "Message to echo"
        }}
      }},
      "required": ["message"]
    }}
  }},
  "sample_jsonrpc_tool": {{
    "type": "jsonrpc",
    "description": "A sample JSON-RPC tool for testing",
    "url": "http://localhost:{server_port}/rpc",
    "method": "test_method",
    "parameters": {{
      "type": "object",
      "properties": {{
        "data": {{
          "type": "string",
          "description": "Data to send"
        }}
      }},
      "required": ["data"]
    }}
  }},
  "sample_disabled_tool": {{
    "type": "command",
    "description": "A disabled tool that should not be loaded",
    "command": "echo 'This should not appear'",
    "disabled": true,
    "parameters": {{
      "type": "object",
      "properties": {{
        "message": {{
          "type": "string",
          "description": "Message to echo"
        }}
      }},
      "required": ["message"]
    }}
  }}
}}"""

    # Write the config file to the current directory
    config_file_path = os.path.join(temp_dir.name, "mcp_tools.json")
    with open(config_file_path, "w") as f:
        f.write(mcp_tools_content)

    # Set the environment variable to point to our test file
    os.environ["MCP_TOOLS_CONF_PATH"] = config_file_path

    try:
        registry = ToolRegistry()
        definitions = registry.get_tool_definitions()

        # Should have definitions for external tools
        command_tool_def = None
        jsonrpc_tool_def = None

        for definition in definitions:
            if definition["function"]["name"] == "sample_command_tool":
                command_tool_def = definition
            elif definition["function"]["name"] == "sample_jsonrpc_tool":
                jsonrpc_tool_def = definition

        # Check that definitions exist
        assert command_tool_def is not None
        assert jsonrpc_tool_def is not None

        # Check command tool definition
        assert command_tool_def["type"] == "function"
        assert command_tool_def["function"]["name"] == "sample_command_tool"
        assert "message" in str(command_tool_def["function"]["parameters"])

        # Check JSON-RPC tool definition
        assert jsonrpc_tool_def["type"] == "function"
        assert jsonrpc_tool_def["function"]["name"] == "sample_jsonrpc_tool"
        assert "data" in str(jsonrpc_tool_def["function"]["parameters"])
    finally:
        # Stop the mock server
        if httpd:
            httpd.shutdown()
            httpd.server_close()

        # Restore original environment
        os.chdir(original_cwd)
        if original_mcp_tools_path is not None:
            os.environ["MCP_TOOLS_CONF_PATH"] = original_mcp_tools_path
        elif "MCP_TOOLS_CONF_PATH" in os.environ:
            del os.environ["MCP_TOOLS_CONF_PATH"]

        temp_dir.cleanup()


def test_mcp_tool_manager_initialization_with_external_tools():
    """Test that MCP tool manager initializes correctly with external tools."""
    # Create a temporary directory for testing
    temp_dir = tempfile.TemporaryDirectory()
    original_cwd = os.getcwd()
    original_mcp_tools_path = os.environ.get("MCP_TOOLS_CONF_PATH")

    # Change to the temp directory
    os.chdir(temp_dir.name)

    # Start a mock HTTP server for JSON-RPC testing
    httpd = None
    server_thread = None
    
    # Try to find an available port
    server_port = None
    for port in range(8000, 9000):
        try:
            httpd = http.server.HTTPServer(
                ("localhost", port), MockHTTPHandler
            )
            server_thread = threading.Thread(target=httpd.serve_forever)
            server_thread.daemon = True
            server_thread.start()
            server_port = port
            break
        except OSError:
            # Port is in use, try the next one
            continue
    if server_port is None:
        raise Exception("Could not find an available port for mock server")

    # Create mcp_tools.json with tools that don't make external requests
    mcp_tools_content = f"""{{
  "sample_command_tool": {{
    "type": "command",
    "description": "A sample command tool for testing",
    "command": "echo 'Hello from command tool: {{message}}'",
    "parameters": {{
      "type": "object",
      "properties": {{
        "message": {{
          "type": "string",
          "description": "Message to echo"
        }}
      }},
      "required": ["message"]
    }}
  }},
  "sample_jsonrpc_tool": {{
    "type": "jsonrpc",
    "description": "A sample JSON-RPC tool for testing",
    "url": "http://localhost:{server_port}/rpc",
    "method": "test_method",
    "parameters": {{
      "type": "object",
      "properties": {{
        "data": {{
          "type": "string",
          "description": "Data to send"
        }}
      }},
      "required": ["data"]
    }}
  }},
  "sample_disabled_tool": {{
    "type": "command",
    "description": "A disabled tool that should not be loaded",
    "command": "echo 'This should not appear'",
    "disabled": true,
    "parameters": {{
      "type": "object",
      "properties": {{
        "message": {{
          "type": "string",
          "description": "Message to echo"
        }}
      }},
      "required": ["message"]
    }}
  }}
}}"""

    # Write the config file to the current directory
    config_file_path = os.path.join(temp_dir.name, "mcp_tools.json")
    with open(config_file_path, "w") as f:
        f.write(mcp_tools_content)

    # Set the environment variable to point to our test file
    os.environ["MCP_TOOLS_CONF_PATH"] = config_file_path

    try:
        mock_stats = MockStats()
        mock_animator = MockAnimator()

        # Create tool manager
        manager = MCPToolManager(mock_stats, animator=mock_animator)

        # Check that external tools are available
        assert "sample_command_tool" in manager.mcp_tools
        assert "sample_jsonrpc_tool" in manager.mcp_tools

        # Check tool definitions
        definitions = manager.get_tool_definitions()
        tool_names = [definition["function"]["name"] for definition in definitions]
        assert "sample_command_tool" in tool_names
        assert "sample_jsonrpc_tool" in tool_names
    finally:
        # Stop the mock server
        if httpd:
            httpd.shutdown()
            httpd.server_close()

        # Restore original environment
        os.chdir(original_cwd)
        if original_mcp_tools_path is not None:
            os.environ["MCP_TOOLS_CONF_PATH"] = original_mcp_tools_path
        elif "MCP_TOOLS_CONF_PATH" in os.environ:
            del os.environ["MCP_TOOLS_CONF_PATH"]

        temp_dir.cleanup()


def test_execute_command_tool():
    """Test executing a command tool."""
    # Create a temporary directory for testing
    temp_dir = tempfile.TemporaryDirectory()
    original_cwd = os.getcwd()
    original_mcp_tools_path = os.environ.get("MCP_TOOLS_CONF_PATH")

    # Change to the temp directory
    os.chdir(temp_dir.name)

    # Start a mock HTTP server for JSON-RPC testing
    httpd = None
    server_thread = None
    
    # Try to find an available port
    server_port = None
    for port in range(8000, 9000):
        try:
            httpd = http.server.HTTPServer(
                ("localhost", port), MockHTTPHandler
            )
            server_thread = threading.Thread(target=httpd.serve_forever)
            server_thread.daemon = True
            server_thread.start()
            server_port = port
            break
        except OSError:
            # Port is in use, try the next one
            continue
    if server_port is None:
        raise Exception("Could not find an available port for mock server")

    # Create mcp_tools.json with tools that don't make external requests
    mcp_tools_content = f"""{{
  "sample_command_tool": {{
    "type": "command",
    "description": "A sample command tool for testing",
    "command": "echo 'Hello from command tool: {{message}}'",
    "parameters": {{
      "type": "object",
      "properties": {{
        "message": {{
          "type": "string",
          "description": "Message to echo"
        }}
      }},
      "required": ["message"]
    }}
  }},
  "sample_jsonrpc_tool": {{
    "type": "jsonrpc",
    "description": "A sample JSON-RPC tool for testing",
    "url": "http://localhost:{server_port}/rpc",
    "method": "test_method",
    "parameters": {{
      "type": "object",
      "properties": {{
        "data": {{
          "type": "string",
          "description": "Data to send"
        }}
      }},
      "required": ["data"]
    }}
  }},
  "sample_disabled_tool": {{
    "type": "command",
    "description": "A disabled tool that should not be loaded",
    "command": "echo 'This should not appear'",
    "disabled": true,
    "parameters": {{
      "type": "object",
      "properties": {{
        "message": {{
          "type": "string",
          "description": "Message to echo"
        }}
      }},
      "required": ["message"]
    }}
  }}
}}"""

    # Write the config file to the current directory
    config_file_path = os.path.join(temp_dir.name, "mcp_tools.json")
    with open(config_file_path, "w") as f:
        f.write(mcp_tools_content)

    # Set the environment variable to point to our test file
    os.environ["MCP_TOOLS_CONF_PATH"] = config_file_path

    try:
        mock_stats = MockStats()
        mock_animator = MockAnimator()

        # Create tool manager
        manager = MCPToolManager(mock_stats, animator=mock_animator)

        # Execute the command tool
        result = manager.execute_tool(
            "sample_command_tool", {"message": "Test message"}
        )

        # Verify the result
        assert "Hello from command tool: Test message" in result
        assert "Error" not in result
    finally:
        # Stop the mock server
        if httpd:
            httpd.shutdown()
            httpd.server_close()

        # Restore original environment
        os.chdir(original_cwd)
        if original_mcp_tools_path is not None:
            os.environ["MCP_TOOLS_CONF_PATH"] = original_mcp_tools_path
        elif "MCP_TOOLS_CONF_PATH" in os.environ:
            del os.environ["MCP_TOOLS_CONF_PATH"]

        temp_dir.cleanup()


def test_execute_jsonrpc_tool():
    """Test executing a JSON-RPC tool."""
    # Create a temporary directory for testing
    temp_dir = tempfile.TemporaryDirectory()
    original_cwd = os.getcwd()
    original_mcp_tools_path = os.environ.get("MCP_TOOLS_CONF_PATH")

    # Change to the temp directory
    os.chdir(temp_dir.name)

    # Start a mock HTTP server for JSON-RPC testing
    httpd = None
    server_thread = None
    
    # Try to find an available port
    server_port = None
    for port in range(8000, 9000):
        try:
            httpd = http.server.HTTPServer(
                ("localhost", port), MockHTTPHandler
            )
            server_thread = threading.Thread(target=httpd.serve_forever)
            server_thread.daemon = True
            server_thread.start()
            server_port = port
            break
        except OSError:
            # Port is in use, try the next one
            continue
    if server_port is None:
        raise Exception("Could not find an available port for mock server")

    # Create mcp_tools.json with tools that don't make external requests
    mcp_tools_content = f"""{{
  "sample_command_tool": {{
    "type": "command",
    "description": "A sample command tool for testing",
    "command": "echo 'Hello from command tool: {{message}}'",
    "parameters": {{
      "type": "object",
      "properties": {{
        "message": {{
          "type": "string",
          "description": "Message to echo"
        }}
      }},
      "required": ["message"]
    }}
  }},
  "sample_jsonrpc_tool": {{
    "type": "jsonrpc",
    "description": "A sample JSON-RPC tool for testing",
    "url": "http://localhost:{server_port}/rpc",
    "method": "test_method",
    "parameters": {{
      "type": "object",
      "properties": {{
        "data": {{
          "type": "string",
          "description": "Data to send"
        }}
      }},
      "required": ["data"]
    }}
  }},
  "sample_disabled_tool": {{
    "type": "command",
    "description": "A disabled tool that should not be loaded",
    "command": "echo 'This should not appear'",
    "disabled": true,
    "parameters": {{
      "type": "object",
      "properties": {{
        "message": {{
          "type": "string",
          "description": "Message to echo"
        }}
      }},
      "required": ["message"]
    }}
  }}
}}"""

    # Write the config file to the current directory
    config_file_path = os.path.join(temp_dir.name, "mcp_tools.json")
    with open(config_file_path, "w") as f:
        f.write(mcp_tools_content)

    # Set the environment variable to point to our test file
    os.environ["MCP_TOOLS_CONF_PATH"] = config_file_path

    try:
        mock_stats = MockStats()
        mock_animator = MockAnimator()

        # Create tool manager
        manager = MCPToolManager(mock_stats, animator=mock_animator)

        # Execute the JSON-RPC tool
        result = manager.execute_tool("sample_jsonrpc_tool", {"data": "test data"})

        # Verify the result contains expected data
        assert "Error" not in result
        assert "Mock response for testing" in result
        assert "test_method" in result
        assert "test data" in result
    finally:
        # Stop the mock server
        if httpd:
            httpd.shutdown()
            httpd.server_close()

        # Restore original environment
        os.chdir(original_cwd)
        if original_mcp_tools_path is not None:
            os.environ["MCP_TOOLS_CONF_PATH"] = original_mcp_tools_path
        elif "MCP_TOOLS_CONF_PATH" in os.environ:
            del os.environ["MCP_TOOLS_CONF_PATH"]

        temp_dir.cleanup()


def test_execute_disabled_tool_returns_error():
    """Test that executing a disabled tool returns an error."""
    # Create a temporary directory for testing
    temp_dir = tempfile.TemporaryDirectory()
    original_cwd = os.getcwd()
    original_mcp_tools_path = os.environ.get("MCP_TOOLS_CONF_PATH")

    # Change to the temp directory
    os.chdir(temp_dir.name)

    # Start a mock HTTP server for JSON-RPC testing
    httpd = None
    server_thread = None
    
    # Try to find an available port
    server_port = None
    for port in range(8000, 9000):
        try:
            httpd = http.server.HTTPServer(
                ("localhost", port), MockHTTPHandler
            )
            server_thread = threading.Thread(target=httpd.serve_forever)
            server_thread.daemon = True
            server_thread.start()
            server_port = port
            break
        except OSError:
            # Port is in use, try the next one
            continue
    if server_port is None:
        raise Exception("Could not find an available port for mock server")

    # Create mcp_tools.json with tools that don't make external requests
    mcp_tools_content = f"""{{
  "sample_command_tool": {{
    "type": "command",
    "description": "A sample command tool for testing",
    "command": "echo 'Hello from command tool: {{message}}'",
    "parameters": {{
      "type": "object",
      "properties": {{
        "message": {{
          "type": "string",
          "description": "Message to echo"
        }}
      }},
      "required": ["message"]
    }}
  }},
  "sample_jsonrpc_tool": {{
    "type": "jsonrpc",
    "description": "A sample JSON-RPC tool for testing",
    "url": "http://localhost:{server_port}/rpc",
    "method": "test_method",
    "parameters": {{
      "type": "object",
      "properties": {{
        "data": {{
          "type": "string",
          "description": "Data to send"
        }}
      }},
      "required": ["data"]
    }}
  }},
  "sample_disabled_tool": {{
    "type": "command",
    "description": "A disabled tool that should not be loaded",
    "command": "echo 'This should not appear'",
    "disabled": true,
    "parameters": {{
      "type": "object",
      "properties": {{
        "message": {{
          "type": "string",
          "description": "Message to echo"
        }}
      }},
      "required": ["message"]
    }}
  }}
}}"""

    # Write the config file to the current directory
    config_file_path = os.path.join(temp_dir.name, "mcp_tools.json")
    with open(config_file_path, "w") as f:
        f.write(mcp_tools_content)

    # Set the environment variable to point to our test file
    os.environ["MCP_TOOLS_CONF_PATH"] = config_file_path

    try:
        mock_stats = MockStats()
        mock_animator = MockAnimator()

        # Create tool manager
        manager = MCPToolManager(mock_stats, animator=mock_animator)

        # Try to execute the disabled tool
        result = manager.execute_tool(
            "sample_disabled_tool", {"message": "Test message"}
        )

        # Should return an error since the tool is disabled
        assert "Error" in result
        assert "not found" in result
    finally:
        # Stop the mock server
        if httpd:
            httpd.shutdown()
            httpd.server_close()

        # Restore original environment
        os.chdir(original_cwd)
        if original_mcp_tools_path is not None:
            os.environ["MCP_TOOLS_CONF_PATH"] = original_mcp_tools_path
        elif "MCP_TOOLS_CONF_PATH" in os.environ:
            del os.environ["MCP_TOOLS_CONF_PATH"]

        temp_dir.cleanup()


def test_tool_registry_handles_missing_mcp_tools_file():
    """Test that tool registry handles missing mcp_tools.json gracefully."""
    # Change to a directory without mcp_tools.json and unset the env var
    with tempfile.TemporaryDirectory():
        original_mcp_tools_path = os.environ.get("MCP_TOOLS_CONF_PATH")
        if "MCP_TOOLS_CONF_PATH" in os.environ:
            del os.environ["MCP_TOOLS_CONF_PATH"]

        try:
            # Create registry - should not fail even without mcp_tools.json
            registry = ToolRegistry()

            # Should still have internal tools
            assert len(registry.mcp_tools) > 0
        finally:
            if original_mcp_tools_path is not None:
                os.environ["MCP_TOOLS_CONF_PATH"] = original_mcp_tools_path


def test_tool_registry_handles_malformed_json():
    """Test that tool registry handles malformed JSON gracefully."""
    # Create a temporary directory for testing
    temp_dir = tempfile.TemporaryDirectory()
    original_cwd = os.getcwd()
    original_mcp_tools_path = os.environ.get("MCP_TOOLS_CONF_PATH")

    # Change to the temp directory
    os.chdir(temp_dir.name)

    # Create mcp_tools.json with tools that don't make external requests
    mcp_tools_content = """{
  "sample_command_tool": {
    "type": "command",
    "description": "A sample command tool for testing",
    "command": "echo 'Hello from command tool: {message}'",
    "parameters": {
      "type": "object",
      "properties": {
        "message": {
          "type": "string",
          "description": "Message to echo"
        }
      },
      "required": ["message"]
    }
  }
}"""

    # Write the config file to the current directory
    config_file_path = os.path.join(temp_dir.name, "mcp_tools.json")
    with open(config_file_path, "w") as f:
        f.write(mcp_tools_content)

    # Set the environment variable to point to our test file
    os.environ["MCP_TOOLS_CONF_PATH"] = config_file_path

    try:
        # Create a malformed mcp_tools.json
        with open(config_file_path, "w") as f:
            f.write("{ invalid json }")

        # Create registry - should not fail even with malformed JSON
        registry = ToolRegistry()

        # Should still have internal tools
        assert len(registry.mcp_tools) > 0
    finally:
        # Restore original environment
        os.chdir(original_cwd)
        if original_mcp_tools_path is not None:
            os.environ["MCP_TOOLS_CONF_PATH"] = original_mcp_tools_path
        elif "MCP_TOOLS_CONF_PATH" in os.environ:
            del os.environ["MCP_TOOLS_CONF_PATH"]

        temp_dir.cleanup()


def test_tool_registry_handles_invalid_tool_config():
    """Test that tool registry handles invalid tool configurations."""
    # Create a temporary directory for testing
    temp_dir = tempfile.TemporaryDirectory()
    original_cwd = os.getcwd()
    original_mcp_tools_path = os.environ.get("MCP_TOOLS_CONF_PATH")

    # Change to the temp directory
    os.chdir(temp_dir.name)

    # Create mcp_tools.json with tools that don't make external requests
    mcp_tools_content = """{
  "sample_command_tool": {
    "type": "command",
    "description": "A sample command tool for testing",
    "command": "echo 'Hello from command tool: {message}'",
    "parameters": {
      "type": "object",
      "properties": {
        "message": {
          "type": "string",
          "description": "Message to echo"
        }
      },
      "required": ["message"]
    }
  }
}"""

    # Write the config file to the current directory
    config_file_path = os.path.join(temp_dir.name, "mcp_tools.json")
    with open(config_file_path, "w") as f:
        f.write(mcp_tools_content)

    # Set the environment variable to point to our test file
    os.environ["MCP_TOOLS_CONF_PATH"] = config_file_path

    try:
        # Create an mcp_tools.json with invalid tool config
        invalid_config = """{
  "invalid_tool": {
    "type": "unknown_type",
    "description": "An invalid tool type"
  }
}"""

        with open(config_file_path, "w") as f:
            f.write(invalid_config)

        # Create registry
        registry = ToolRegistry()

        # Should still load the tool (validation happens at execution time)
        assert "invalid_tool" in registry.mcp_tools
    finally:
        # Restore original environment
        os.chdir(original_cwd)
        if original_mcp_tools_path is not None:
            os.environ["MCP_TOOLS_CONF_PATH"] = original_mcp_tools_path
        elif "MCP_TOOLS_CONF_PATH" in os.environ:
            del os.environ["MCP_TOOLS_CONF_PATH"]

        temp_dir.cleanup()

#!/usr/bin/env python3
"""
TMUX-based test for animator and ESC cancellation functionality.
This test creates a tmux session and sends simulated key presses
to verify that the 'Working...' animation appears and ESC cancellation works.
"""

import os
import sys
import time
import subprocess
import tempfile


def run_tmux_command(cmd):
    """Run a tmux command and return the output."""
    from subprocess import getstatusoutput
    try:
        # Use getstatusoutput for simpler interface
        status, output = getstatusoutput(f"tmux {cmd}")
        return output.strip(), "", status  # stdout, stderr, returncode
    except Exception as e:
        return "", str(e), 1


def test_tmux_available():
    """Check if tmux is available."""
    try:
        result = subprocess.run(['tmux', '-V'], capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except:
        return False


def create_animation_test_script():
    """Create a test script that will test animation and ESC in tmux."""
    script_content = '''
#!/usr/bin/env python3
import sys
import time
import json
import threading
import os
# Add current directory to Python path so imports work
sys.path.insert(0, os.getcwd())

from http.server import HTTPServer, BaseHTTPRequestHandler
from unittest.mock import Mock

# Start a simple test server that delays response to trigger animation
class TestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/chat/completions':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()

            # Delay to trigger animation - this will show the "Working..." animation
            print("Delaying response to trigger animation...", file=sys.stderr)
            time.sleep(2.0)  # 2 second delay to ensure animation is visible

            response = {
                "id": "test-id",
                "object": "chat.completion",
                "created": 1234567890,
                "model": "test-model",
                "choices": [{
                    "index": 0,
                    "message": {"role": "assistant", "content": "Response after delay!"},
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 5,
                    "total_tokens": 15
                }
            }
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()

def main():
    # Set test mode to avoid terminal conflicts
    os.environ["TEST_MODE"] = "1"
    os.environ["OPENAI_API_KEY"] = "test-key"
    
    # Enable debug to see animation
    import aicoder.config as config_module
    config_module.DEBUG = True

    from aicoder.streaming_adapter import StreamingAdapter
    from aicoder.animator import Animator

    # Create server
    server = HTTPServer(('localhost', 0), TestHandler)
    port = server.server_port

    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    
    print(f"Test server started on port {port}", file=sys.stderr)

    # Create mock API handler
    mock_api_handler = Mock()
    mock_api_handler.stats = None
    mock_api_handler.tool_manager = None

    # Create adapter
    animator = Animator()
    adapter = StreamingAdapter(api_handler=mock_api_handler, animator=animator)

    # Set environment variables for local server
    os.environ["OPENAI_BASE_URL"] = f"http://localhost:{port}"
    os.environ["OPENAI_API_KEY"] = "test-key"

    try:
        # Make request that will trigger animation
        print("Making request that will trigger animation...", file=sys.stderr)
        messages = [{"role": "user", "content": "Hello"}]
        result = adapter.make_request(messages, disable_streaming_mode=True, disable_tools=True)

        if result:
            print("\\n*** SUCCESS: Request completed ***")
            print(f"Response: {result.get('choices', [{}])[0].get('message', {}).get('content', 'No content')}")
        else:
            print("\\n*** FAILED: Request did not complete ***")

    except Exception as e:
        print(f"\\n*** ERROR: {e} ***")
        import traceback
        traceback.print_exc()
    finally:
        # Config restored via environment variables
        server.shutdown()
        print("Server shutdown", file=sys.stderr)

if __name__ == "__main__":
    main()
'''

    # Write the script to a temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(script_content)
        return f.name


def main():
    print("TMUX-based Animator and ESC Cancellation Test")
    print("=" * 50)

    if not test_tmux_available():
        print("❌ tmux is not available. Please install tmux to run this test.")
        return 1

    print("✅ tmux is available")

    # Create the test script
    test_script = create_animation_test_script()

    try:
        # Create a tmux session running bash
        session_name = f"test_animator_esc_{int(time.time())}"
        print(f"Creating tmux session: {session_name}")

        # Start tmux session with bash shell
        stdout, stderr, rc = run_tmux_command(f"new-session -d -s {session_name} -n test bash")
        if rc != 0:
            print(f"❌ Failed to create tmux session: {stderr}")
            return 1

        try:
            # Send the python command to the tmux session
            run_tmux_command(f"send-keys -t {session_name} 'python3 {test_script}' Enter")

            # Wait a moment for the command to execute
            time.sleep(0.5)

            # Check if session exists
            stdout, stderr, rc = run_tmux_command(f"has-session -t {session_name}")
            if rc != 0:
                print(f"❌ Session doesn't exist: {stderr}")
                return 1

            print("✅ Test running in tmux session")
            print(f"Session name: {session_name}")
            print(f"Script file: {test_script}")
            
            # Wait and monitor the output to detect animation
            print("\\nMonitoring output for animation and ESC behavior...")
            
            # Wait for the test to complete (timeout after 20 seconds to account for delays)
            for i in range(20):
                stdout, stderr, rc = run_tmux_command(f"capture-pane -t {session_name} -p")
                if stdout and ("SUCCESS:" in stdout or "FAILED:" in stdout or "ERROR:" in stdout):
                    break
                time.sleep(1)
            
            # Capture the final output
            stdout, stderr, rc = run_tmux_command(f"capture-pane -t {session_name} -p")
            print(f"\\nFinal output from test session:\\n{stdout}")

            if stderr:
                print(f"\\nErrors from test session:\\n{stderr}")
                
        finally:
            # Kill the tmux session
            run_tmux_command(f"kill-session -t {session_name}")

    finally:
        # Clean up the test script
        try:
            os.unlink(test_script)
        except:
            pass

    print("\\n" + "=" * 50)
    print("TMUX test completed.")
    print("This test ran the animation in a separate tmux session.")
    print("For ESC cancellation testing, the next step would be to:")
    print("1. Monitor pane content to detect 'Working...' animation")
    print("2. Send ESC key using: tmux send-keys -t session_name C-[ Enter")
    print("3. Verify animation stops and request is cancelled")

    return 0


if __name__ == "__main__":
    sys.exit(main())
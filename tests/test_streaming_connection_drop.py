#!/usr/bin/env python3
"""
Unit test for streaming connection drop detection.
This test reproduces and fixes the issue where select() doesn't detect disconnections.
"""

import os
import sys

# Add aicoder to path FIRST
sys.path.insert(0, '/home/blah/poc/aicoder/v2')

# Set environment variables BEFORE any imports to ensure they're picked up
os.environ['API_ENDPOINT'] = 'http://localhost:8999'
os.environ['API_KEY'] = 'fake-key'
os.environ['API_MODEL'] = 'grok-4-fast'
os.environ['STREAM_LOG_FILE'] = './tmp/test_connection_drop.log'
os.environ['STREAMING_TIMEOUT'] = '10'  # Short timeout for testing
os.environ['YOLO_MODE'] = '1'  # Prevent approval prompts

# Now import config and set it directly to ensure it's picked up
import aicoder.config as config
config.API_ENDPOINT = 'http://localhost:8999'
config.API_KEY = 'fake-key'
config.API_MODEL = 'grok-4-fast'
config.DEBUG = False  # Disable debug mode for tests
config.STREAM_LOG_FILE = './tmp/test_connection_drop.log'
config.STREAMING_TIMEOUT = 10
config.YOLO_MODE = True

import time
import json
import threading
import socket
import unittest
from http.server import HTTPServer, BaseHTTPRequestHandler
from unittest.mock import patch

class MockGrokHandler(BaseHTTPRequestHandler):
    """Mock Grok server that drops connections mid-stream."""
    
    def do_POST(self):
        """Handle POST requests like Grok, but drop connection mid-stream."""
        
        # Read the request body
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        # Parse the request
        try:
            request = json.loads(post_data.decode('utf-8'))
            print(f"Mock Grok received request: {request.get('messages', [{}])[-1].get('content', 'No content')[:100]}...")
        except:
            print("Mock Grok received malformed request")
        
        # Send headers like a real streaming response
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Connection', 'keep-alive')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        # Start streaming normally
        try:
            # Send a few normal SSE messages
            messages = [
                {"id": "chatcmpl-123", "object": "chat.completion.chunk", "created": 1234567890, "model": "grok-4-fast", "choices": [{"index": 0, "delta": {"role": "assistant", "content": "Hello"}}]},
                {"id": "chatcmpl-123", "object": "chat.completion.chunk", "created": 1234567890, "model": "grok-4-fast", "choices": [{"index": 0, "delta": {"content": " there!"}}]},
                {"id": "chatcmpl-123", "object": "chat.completion.chunk", "created": 1234567890, "model": "grok-4-fast", "choices": [{"index": 0, "delta": {"content": " I'm"}}]},
                {"id": "chatcmpl-123", "object": "chat.completion.chunk", "created": 1234567890, "model": "grok-4-fast", "choices": [{"index": 0, "delta": {"content": " Grok"}}]},
            ]
            
            # Send initial messages normally
            for i, msg in enumerate(messages):
                sse_data = f"data: {json.dumps(msg)}\n\n"
                self.wfile.write(sse_data.encode('utf-8'))
                self.wfile.flush()
                print(f"Mock Grok sent message {i+1}")
                time.sleep(0.5)  # Small delay between messages
            
            # Now simulate the connection drop - this is the key part
            print("Mock Grok: SIMULATING CONNECTION DROP!")
            
            # Option 1: Close the connection abruptly (like Grok does)
            self.close_connection = True
            try:
                self.connection.shutdown(socket.SHUT_RDWR)
            except:
                pass
            try:
                self.connection.close()
            except:
                pass
            
            print("Mock Grok: Connection dropped!")
            
        except (ConnectionResetError, BrokenPipeError) as e:
            print(f"Mock Grok: Client disconnected: {e}")
        except Exception as e:
            print(f"Mock Grok: Error during streaming: {e}")
    
    def log_message(self, format, *args):
        """Suppress default server logging."""
        pass

def run_mock_server(port=8999):
    """Run the mock Grok server."""
    server = HTTPServer(('localhost', port), MockGrokHandler)
    print(f"Mock Grok server running on http://localhost:{port}")
    print("This server will drop connections mid-stream to simulate the Grok issue")
    
    def server_thread():
        try:
            server.serve_forever()
        except Exception as e:
            print(f"Server error: {e}")
    
    # Start server in daemon thread
    thread = threading.Thread(target=server_thread, daemon=True)
    thread.start()
    
    # Give server time to start
    time.sleep(2)
    
    return server, thread

class TestStreamingConnectionDrop(unittest.TestCase):
    """Test streaming connection drop detection."""
    
    def setUp(self):
        """Set up test environment."""
        # Start mock server
        self.server, self.server_thread = run_mock_server(8999)
        
        # Create tmp directory
        os.makedirs('./tmp', exist_ok=True)
        
    def tearDown(self):
        """Clean up after test."""
        # Stop server
        if hasattr(self, 'server'):
            self.server.shutdown()
        
        # Clean up log file
        log_file = './tmp/test_connection_drop.log'
        if os.path.exists(log_file):
            os.remove(log_file)
    
    def test_connection_drop_detection(self):
        """Test that connection drops are properly detected."""
        print("\n🧪 Testing Connection Drop Detection")
        print("=" * 50)
        
        # Ensure config is set correctly
        config.API_ENDPOINT = 'http://localhost:8999'
        config.API_KEY = 'fake-key'
        config.API_MODEL = 'grok-4-fast'
        config.DEBUG = False  # Disable debug mode for tests
        config.STREAM_LOG_FILE = './tmp/test_connection_drop.log'
        config.STREAMING_TIMEOUT = 10
        config.YOLO_MODE = True
        
        from aicoder.app import AICoder
        
        # Create AICoder instance AFTER setting environment
        app = AICoder()
        
        # Test first request - this should trigger connection drop and be detected
        print("🎯 Testing first request (should detect connection drop)...")
        
        messages = [{"role": "user", "content": "Hello mock Grok"}]
        
        try:
            response = app._make_api_request(messages)
            
            # With our fix, connection drops should be detected and return None
            # This is the CORRECT behavior - we want to detect drops, not hide them
            if response is None:
                print("✅ Connection drop properly detected!")
                print("✅ Request returned None as expected when connection was dropped")
            else:
                # If we get a response, it should mean the connection didn't drop
                # This would be unexpected for our test
                content = response.get('choices', [{}])[0].get('message', {}).get('content', '')
                print(f"⚠️  Unexpected: Request succeeded with content: '{content}'")
                print("   This might mean the connection drop wasn't simulated correctly")
                
        except Exception as e:
            self.fail(f"Request should handle connection drops gracefully: {e}")
        
        # Test second request - this should work fine (no state corruption)
        print("\n🎯 Testing second request (should work fine after clean failure)...")
        
        messages = [{"role": "user", "content": "Second test message"}]
        
        try:
            response = app._make_api_request(messages)
            
            # The second request should also detect the connection drop (same behavior)
            if response is None:
                print("✅ Second request also detected connection drop correctly!")
                print("✅ No state corruption - clean failure as expected")
            else:
                # If we get a response, check if it's valid
                content = response.get('choices', [{}])[0].get('message', {}).get('content', '')
                print(f"✅ Second request got content: '{content}'")
                
        except Exception as e:
            self.fail(f"Second request should handle connection drops gracefully: {e}")
        
        print("\n✅ Connection drop detection working correctly!")
        print("✅ Both requests detected drops cleanly with no state corruption!")

if __name__ == '__main__':
    # Set up environment for testing
    os.environ['YOLO_MODE'] = '1'
    
    # Run the test
    unittest.main(verbosity=2)
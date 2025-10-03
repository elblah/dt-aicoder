#!/usr/bin/env python3
"""
Test server for retry functionality testing.
This server provides endpoints that return specific HTTP error codes
to test the retry logic in the AI Coder application.
"""

import http.server
import socketserver
import json
import threading
import time
import sys
import os
from urllib.parse import urlparse, parse_qs


class RetryTestHandler(http.server.BaseHTTPRequestHandler):
    """HTTP handler that returns specific error codes for testing retry logic."""

    def do_POST(self):
        """Handle POST requests with various error responses."""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        query_params = parse_qs(parsed_path.query)
        
        # Get delay parameter if provided
        delay = float(query_params.get('delay', [0])[0])
        
        # Get request body for logging
        content_length = int(self.headers.get('Content-Length', 0))
        request_body = self.rfile.read(content_length)
        
        try:
            request_data = json.loads(request_body.decode('utf-8'))
            print(f"Test Server: Received request to {path}")
            print(f"Test Server: Request data: {json.dumps(request_data, indent=2)}")
        except:
            print(f"Test Server: Received request to {path} (invalid JSON)")
        
        # Simulate delay if requested
        if delay > 0:
            print(f"Test Server: Delaying response for {delay} seconds")
            time.sleep(delay)
        
        # Route based on path
        if path == '/success':
            self._send_success_response()
        elif path == '/502':
            self._send_error_response(502, "Bad Gateway")
        elif path == '/500':
            self._send_error_response(500, "Internal Server Error")
        elif path == '/503':
            self._send_error_response(503, "Service Unavailable")
        elif path == '/504':
            self._send_error_response(504, "Gateway Timeout")
        elif path == '/429':
            self._send_error_response(429, "Too Many Requests")
        elif path == '/524':
            self._send_error_response(524, "A Timeout Occurred")
        elif path == '/401':
            self._send_error_response(401, "Unauthorized")
        elif path == '/400':
            self._send_error_response(400, "Bad Request")
        elif path == '/500_with_429_content':
            self._send_500_with_429_content()
        elif path == '/timeout':
            # Simulate timeout by not responding
            print("Test Server: Simulating timeout - not responding")
            # Just hang here to simulate timeout
            while True:
                time.sleep(1)
        elif path == '/connection_error':
            # Simulate connection error by closing connection abruptly
            print("Test Server: Simulating connection error - closing connection")
            self.close_connection = True
            return
        elif path.startswith('/custom/'):
            # Custom error code: /custom/404, /custom/418, etc.
            try:
                error_code = int(path.split('/')[-1])
                self._send_error_response(error_code, f"Custom Error {error_code}")
            except ValueError:
                self._send_error_response(400, "Invalid custom error code")
        else:
            self._send_error_response(404, "Not Found")
    
    def do_GET(self):
        """Handle GET requests for health checks."""
        if self.path == '/health':
            self._send_success_response()
        else:
            self._send_error_response(404, "Not Found")
    
    def _send_success_response(self):
        """Send a successful response."""
        response_data = {
            "id": "test-chat-" + str(int(time.time())),
            "object": "chat.completion",
            "created": int(time.time()),
            "model": "test-model",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "Test successful response"
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15
            }
        }
        
        response_json = json.dumps(response_data)
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response_json)))
        self.end_headers()
        self.wfile.write(response_json.encode('utf-8'))
    
    def _send_error_response(self, code, message):
        """Send an error response."""
        error_data = {
            "error": {
                "message": message,
                "type": "api_error",
                "code": code
            }
        }
        
        response_json = json.dumps(error_data)
        
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response_json)))
        self.end_headers()
        self.wfile.write(response_json.encode('utf-8'))
    
    def _send_500_with_429_content(self):
        """Send a 500 error with 429 content (for testing rate limiting detection)."""
        error_data = {
            "error": {
                "message": "429 Too Many Requests",
                "type": "rate_limit_error",
                "code": 500
            }
        }
        
        response_json = json.dumps(error_data)
        
        self.send_response(500)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response_json)))
        self.end_headers()
        self.wfile.write(response_json.encode('utf-8'))
    
    def log_message(self, format, *args):
        """Override to use our own logging."""
        print(f"Test Server: {format % args}")


class RetryTestServer:
    """Test server for retry functionality."""
    
    def __init__(self, port=0):
        """Initialize the test server."""
        self.port = port
        self.server = None
        self.server_thread = None
        self.base_url = None
    
    def start(self):
        """Start the test server."""
        # Create server with port 0 to let OS choose available port
        self.server = socketserver.TCPServer(("", self.port), RetryTestHandler)
        self.port = self.server.server_address[1]
        self.base_url = f"http://localhost:{self.port}"
        
        print(f"Test server started on port {self.port}")
        print(f"Base URL: {self.base_url}")
        print("\nAvailable endpoints:")
        print("  POST /success          - Returns 200 OK")
        print("  POST /502             - Returns 502 Bad Gateway")
        print("  POST /500             - Returns 500 Internal Server Error")
        print("  POST /503             - Returns 503 Service Unavailable")
        print("  POST /504             - Returns 504 Gateway Timeout")
        print("  POST /429             - Returns 429 Too Many Requests")
        print("  POST /524             - Returns 524 A Timeout Occurred")
        print("  POST /401             - Returns 401 Unauthorized")
        print("  POST /400             - Returns 400 Bad Request")
        print("  POST /500_with_429_content - Returns 500 with 429 content")
        print("  POST /timeout         - Simulates timeout (never responds)")
        print("  POST /connection_error - Simulates connection error")
        print("  POST /custom/<code>   - Returns custom HTTP error code")
        print("  GET  /health          - Health check endpoint")
        print("\nQuery parameters:")
        print("  ?delay=X             - Delay response by X seconds")
        
        # Start server in a separate thread
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()
        
        # Wait a moment for server to start
        time.sleep(0.1)
        
        return self.base_url
    
    def stop(self):
        """Stop the test server."""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            if self.server_thread:
                self.server_thread.join(timeout=1.0)
            print("Test server stopped")
    
    def get_endpoint_url(self, endpoint):
        """Get the full URL for a specific endpoint."""
        return f"{self.base_url}{endpoint}"


def main():
    """Run the test server as a standalone process."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test server for retry functionality')
    parser.add_argument('--port', type=int, default=0, help='Port to listen on (0 for random)')
    parser.add_argument('--write-port-file', type=str, help='Write port number to file')
    
    args = parser.parse_args()
    
    server = RetryTestServer(port=args.port)
    try:
        base_url = server.start()
        
        # Write port to file if requested
        if args.write_port_file:
            with open(args.write_port_file, 'w') as f:
                f.write(str(server.port))
            print(f"Port {server.port} written to {args.write_port_file}")
        
        print(f"\nServer running. Press Ctrl+C to stop.")
        print(f"Test with: curl {base_url}/health")
        
        # Keep the server running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        server.stop()


if __name__ == '__main__':
    main()
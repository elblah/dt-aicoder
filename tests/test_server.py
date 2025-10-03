#!/usr/bin/env python3
"""
Generic test server for HTTP-based tests.
This server provides various endpoints for testing different HTTP scenarios
without requiring external internet access.
"""

import http.server
import socketserver
import json
import threading
import time
import sys
import os
import socket
from urllib.parse import urlparse, parse_qs


class TestServerHandler(http.server.BaseHTTPRequestHandler):
    """HTTP handler that provides various test scenarios."""

    def do_POST(self):
        """Handle POST requests with various test responses."""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        query_params = parse_qs(parsed_path.query)
        
        # Get request body for logging
        content_length = int(self.headers.get('Content-Length', 0))
        request_body = self.rfile.read(content_length)
        
        # Get special behaviors from query params
        delay = float(query_params.get('delay', [0])[0])
        drop_connection = query_params.get('drop', ['false'])[0].lower() == 'true'
        partial_response = query_params.get('partial', ['false'])[0].lower() == 'true'
        
        try:
            request_data = json.loads(request_body.decode('utf-8'))
            print(f"Test Server: Received request to {path}")
            if 'messages' in request_data:
                content = request_data['messages'][-1].get('content', 'No content')
                print(f"Test Server: Content: {content[:100]}...")
        except:
            print(f"Test Server: Received request to {path} (invalid JSON)")
        
        # Simulate delay if requested
        if delay > 0:
            print(f"Test Server: Delaying response for {delay} seconds")
            time.sleep(delay)
        
        # Handle special connection drop scenario
        if drop_connection:
            print("Test Server: Simulating connection drop")
            self._drop_connection()
            return
        
        # Route based on path
        if path == '/success':
            self._send_success_response()
        elif path == '/streaming':
            self._send_streaming_response(partial=partial_response)
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
            self._drop_connection()
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
            self._send_health_response()
        else:
            self._send_error_response(404, "Not Found")
    
    def _drop_connection(self):
        """Drop the connection abruptly (simulates server crash)."""
        self.close_connection = True
        try:
            if hasattr(self, 'connection'):
                self.connection.shutdown(socket.SHUT_RDWR)
                self.connection.close()
        except:
            pass
    
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
    
    def _send_streaming_response(self, partial=False):
        """Send a streaming response (for SSE testing)."""
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Connection', 'keep-alive')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        try:
            # Send streaming messages
            messages = [
                {"id": "chatcmpl-123", "object": "chat.completion.chunk", "created": int(time.time()), "model": "test-model", "choices": [{"index": 0, "delta": {"role": "assistant", "content": "Hello"}}]},
                {"id": "chatcmpl-123", "object": "chat.completion.chunk", "created": int(time.time()), "model": "test-model", "choices": [{"index": 0, "delta": {"content": " world!"}}]},
            ]
            
            for i, msg in enumerate(messages):
                sse_data = f"data: {json.dumps(msg)}\n\n"
                self.wfile.write(sse_data.encode('utf-8'))
                self.wfile.flush()
                print(f"Test Server: Sent streaming message {i+1}")
                time.sleep(0.1)
                
                # Drop connection mid-stream if partial=True
                if partial and i == 0:
                    print("Test Server: Dropping connection mid-stream")
                    self._drop_connection()
                    return
            
            # Send final message
            final_msg = {"id": "chatcmpl-123", "object": "chat.completion.chunk", "created": int(time.time()), "model": "test-model", "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}
            sse_data = f"data: {json.dumps(final_msg)}\n\n"
            self.wfile.write(sse_data.encode('utf-8'))
            self.wfile.flush()
            
        except (ConnectionResetError, BrokenPipeError) as e:
            print(f"Test Server: Client disconnected: {e}")
        except Exception as e:
            print(f"Test Server: Error during streaming: {e}")
    
    def _send_health_response(self):
        """Send a health check response."""
        health_data = {
            "status": "healthy",
            "timestamp": int(time.time()),
            "endpoints": [
                "POST /success",
                "POST /streaming",
                "POST /502",
                "POST /500",
                "POST /503",
                "POST /504",
                "POST /429",
                "POST /524",
                "POST /401",
                "POST /400",
                "POST /500_with_429_content",
                "POST /timeout",
                "POST /connection_error",
                "POST /custom/<code>",
                "GET /health"
            ]
        }
        
        response_json = json.dumps(health_data)
        
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


class GenericTestServer:
    """Generic test server for HTTP-based testing."""
    
    def __init__(self, port=0):
        """Initialize the test server."""
        self.port = port
        self.server = None
        self.server_thread = None
        self.base_url = None
    
    def start(self):
        """Start the test server."""
        # Create server with port 0 to let OS choose available port
        self.server = socketserver.TCPServer(("", self.port), TestServerHandler)
        self.port = self.server.server_address[1]
        self.base_url = f"http://localhost:{self.port}"
        
        print(f"Generic test server started on port {self.port}")
        print(f"Base URL: {self.base_url}")
        print("\nAvailable endpoints:")
        print("  POST /success             - Returns 200 OK with JSON response")
        print("  POST /streaming            - Returns streaming SSE response")
        print("  POST /streaming?partial=true - Drops connection mid-stream")
        print("  POST /502                  - Returns 502 Bad Gateway")
        print("  POST /500                  - Returns 500 Internal Server Error")
        print("  POST /503                  - Returns 503 Service Unavailable")
        print("  POST /504                  - Returns 504 Gateway Timeout")
        print("  POST /429                  - Returns 429 Too Many Requests")
        print("  POST /524                  - Returns 524 A Timeout Occurred")
        print("  POST /401                  - Returns 401 Unauthorized")
        print("  POST /400                  - Returns 400 Bad Request")
        print("  POST /500_with_429_content - Returns 500 with 429 content")
        print("  POST /timeout              - Simulates timeout (never responds)")
        print("  POST /connection_error     - Simulates connection error")
        print("  POST /custom/<code>        - Returns custom HTTP error code")
        print("  GET  /health               - Health check endpoint")
        print("\nQuery parameters:")
        print("  ?delay=X                   - Delay response by X seconds")
        print("  ?drop=true                 - Drop connection without response")
        print("  ?partial=true              - For streaming: drop mid-stream")
        
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


# Context manager for easy use in tests
class TestServerContext:
    """Context manager for test server."""
    
    def __init__(self, port=0):
        self.server = GenericTestServer(port)
        
    def __enter__(self):
        self.base_url = self.server.start()
        return self.server
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.server.stop()


def main():
    """Run the test server as a standalone process."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generic test server for HTTP testing')
    parser.add_argument('--port', type=int, default=0, help='Port to listen on (0 for random)')
    parser.add_argument('--write-port-file', type=str, help='Write port number to file')
    
    args = parser.parse_args()
    
    server = GenericTestServer(port=args.port)
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
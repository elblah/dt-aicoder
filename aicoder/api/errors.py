"""API and streaming error messages - complex multi-line errors only"""

from aicoder.utils import emsg


class APIErrors:
    """Complex API and streaming error messages"""
    
    # === HTTP TIMEOUT ERRORS ===
    HTTP_TIMEOUT = """HTTP connection timeout reached ({timeout} seconds).
The connection to the AI model timed out. This can happen with slow models.
Tip: Set HTTP_TIMEOUT=X to increase timeout (e.g., HTTP_TIMEOUT=600 for 10 minutes)
Tip: You can also press ESC to cancel if you think it's taking too long."""
    
    # === STREAMING TIMEOUT ERRORS ===
    STREAMING_TIMEOUT = """Streaming timeout reached ({timeout} seconds with no SSE data).
Tip: Set STREAMING_TIMEOUT=X to adjust (e.g., STREAMING_TIMEOUT=600 for 10 minutes)
Tip: For HTTP connection timeouts, set HTTP_TIMEOUT=X (e.g., HTTP_TIMEOUT=600)"""
    
    # === CONNECTION ERRORS ===
    CONNECTION_ERROR = """Connection Error: {reason}
Check your internet connection and API endpoint."""
    
    CONNECTION_DROPPED = """🚫 Connection dropped by server ({reason}).
The AI model server closed the connection unexpectedly.
Please try your request again - connection may work next time."""
    
    # === STREAMING PROCESSING ERRORS ===
    STREAMING_PROCESSING_ERROR = """Error processing streaming response: {error}
This appears to be an API compatibility issue. The streaming was interrupted.
You can try running with ENABLE_STREAMING=0 to disable streaming mode."""
    
    # === RETRY ERRORS ===
    RETRY_ERROR = """{error_type} error detected. Retrying in {retry_sleep_secs} secs..."""
    
    RETRY_ERROR_WITH_CANCEL = """{error_type} detected. Retrying in {retry_sleep_secs} secs... (Press ESC to cancel)"""
    
    # === TIMEOUT REMINDER ERRORS ===
    TIMEOUT_REMINDER = """⚠️  It's been {read_timeout_seconds} seconds with no new data.
   Press ESC to cancel the request, or wait for more data..."""
    
    # === RETRY ERRORS ===
    MAX_RETRIES_EXCEEDED = "Maximum retry attempts ({max_attempts}) exceeded. Giving up."
    
    RETRY_WITH_CANCEL = """{error_type} detected. Retrying in {retry_sleep_secs} secs... (Press ESC to cancel)"""
    
    RETRY_NO_CANCEL = """{error_type} error detected. Retrying in {retry_sleep_secs} secs..."""
    
    # === API RESPONSE ERRORS ===
    API_ERROR_WITH_CONTENT = """API Error: {code} {reason}
{content}"""
    
    # === AUTHENTICATION ERRORS ===
    AUTHENTICATION_FAILED = "Authentication failed. Please check your API key/token."
    
    @classmethod
    def print(cls, template, **kwargs):
        """Print formatted error message"""
        try:
            formatted = template.format(**kwargs)
            emsg(formatted)
        except KeyError as e:
            emsg(f"Error: Missing parameter {e} in API error template")
        except Exception as e:
            emsg(f"Error formatting API message: {e}")
    
    @classmethod
    def format(cls, template, **kwargs):
        """Get formatted error string"""
        try:
            return template.format(**kwargs)
        except KeyError as e:
            return f"Error: Missing parameter {e} in API error template"
        except Exception as e:
            return f"Error formatting API message: {e}"
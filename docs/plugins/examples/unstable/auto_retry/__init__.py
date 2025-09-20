"""
Auto Retry Plugin

Provides automatic retry functionality for API errors, specifically designed to handle
the case where you get "500 Internal Server Error" with "429 Too Many Requests" content,
as well as other common API errors.
"""

from .auto_retry import install_auto_retry_plugin

# Plugin description for the plugin system
PLUGIN_DESCRIPTION = """
Auto Retry Plugin - Automatically retries failed API requests

This plugin enhances AI Coder's error handling by automatically retrying failed API requests,
especially for common issues like:
- 500 Internal Server Error with 429 Too Many Requests content
- Rate limiting errors (429 and similar)
- Server errors (502, 503, 504)
- Connection timeouts and network issues

Features:
- Smart error detection and classification
- Configurable retry delays and counts
- ESC key support to cancel retries
- User-friendly error messages
- Environment variable configuration

Configuration:
- AUTO_RETRY_DELAY=5       # Delay between retries in seconds
- AUTO_RETRY_MAX_RETRIES=3  # Maximum number of retries
"""

# Install the plugin when the module is imported
install_auto_retry_plugin()

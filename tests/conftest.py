"""
Global test configuration.
This file is automatically loaded by unittest/pytest before any tests run.
It blocks external internet access for all tests.
"""

import os
import sys
import urllib.request
import urllib.error
import socket
from urllib.parse import urlparse

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Global flag to track if blocking is active
_internet_blocked = False


def block_external_internet():
    """Block external internet access but allow local connections."""
    global _internet_blocked
    if _internet_blocked:
        return  # Already blocked

    print("🔒 Blocking external internet access for all tests...")

    def mock_urlopen(*args, **kwargs):
        """Mock urllib.urlopen to block external URLs."""
        # Extract URL
        url = args[0] if args else None
        if hasattr(url, "get_full_url"):  # urllib.request.Request object
            url = url.get_full_url()
        elif not isinstance(url, str):
            url = str(url)

        # Check if it's an external URL
        if url and not _is_local_url(url):
            raise RuntimeError(
                f"🚫 EXTERNAL INTERNET ACCESS BLOCKED in tests!\n"
                f"Attempted URL: {url}\n"
                f"Fix: Use local test servers or mock objects\n"
                f"Allowed: localhost, 127.0.0.1, ::1, 0.0.0.0\n"
                f"Blocked: All external addresses"
            )

        # Allow local URLs
        return _original_urlopen(*args, **kwargs)

    def mock_socket_create(*args, **kwargs):
        """Mock socket.create_connection to block external connections."""
        if len(args) > 0 and isinstance(args[0], tuple):
            address = args[0][0] if args[0] else None
            if address and not _is_local_address(address):
                raise RuntimeError(
                    f"🚫 EXTERNAL NETWORK ACCESS BLOCKED in tests!\n"
                    f"Attempted connection to: {address}\n"
                    f"Fix: Use local test servers\n"
                    f"Allowed: localhost, 127.0.0.1, ::1, 0.0.0.0"
                )

        return _original_socket_create(*args, **kwargs)

    def _is_local_url(url):
        """Check if URL points to local address."""
        try:
            parsed = urlparse(url)
            hostname = parsed.hostname
            return _is_local_address(hostname) if hostname else False
        except Exception:
            return False

    def _is_local_address(address):
        """Check if address is local."""
        if not address:
            return False
        local_addresses = ["127.0.0.1", "::1", "localhost", "0.0.0.0"]
        return any(
            address == local or address.startswith(local + ".")
            for local in local_addresses
        )

    # Save originals and install mocks
    global _original_urlopen, _original_socket_create
    _original_urlopen = urllib.request.urlopen
    _original_socket_create = socket.create_connection

    urllib.request.urlopen = mock_urlopen
    socket.create_connection = mock_socket_create

    _internet_blocked = True
    print("✅ External internet access blocked (local connections allowed)")


# Auto-block internet when this module is imported
if os.environ.get("AICODER_BLOCK_INTERNET", "1") != "0":
    block_external_internet()


# Test detection helpers
def is_test_context():
    """Simple check if we're in a test context."""
    return (
        "test" in " ".join(sys.argv).lower()
        or any("test" in arg.lower() for arg in sys.argv)
        or os.environ.get("PYTEST_CURRENT_TEST")
        or os.environ.get("AICODER_TEST_MODE")
        or "unittest" in sys.modules
        or "pytest" in sys.modules
    )


# Block internet automatically in test contexts
if is_test_context() and not _internet_blocked:
    block_external_internet()

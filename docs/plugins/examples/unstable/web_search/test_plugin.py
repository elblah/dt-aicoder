#!/usr/bin/env python3
"""
Test file for the enhanced web search plugin.
This can be run locally to test the plugin functionality without requiring
global installation. Run with: python test_plugin.py

Tests the embedded DuckDuckGo search and the new get_url_content functionality.
"""

import sys
import os
import unittest
from unittest.mock import Mock, patch, MagicMock
import subprocess

# Add the current directory to the path so we can import the plugin
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from web_search import (
    DuckDuckGoSearch,
    execute_web_search,
    execute_get_url_content,
    WEB_SEARCH_TOOL_DEFINITION,
    URL_CONTENT_TOOL_DEFINITION
)


class TestDuckDuckGoSearch(unittest.TestCase):
    """Test the embedded DuckDuckGo search functionality."""

    def test_search_initialization(self):
        """Test that DuckDuckGoSearch initializes correctly."""
        searcher = DuckDuckGoSearch()
        self.assertEqual(searcher.base_url, "https://lite.duckduckgo.com/lite/")

    def test_search_query_validation(self):
        """Test search query validation."""
        searcher = DuckDuckGoSearch()
        
        # Test with valid query
        result = searcher.search("python programming")
        self.assertIsInstance(result, dict)
        self.assertIn('results', result)
        self.assertIn('has_next', result)
        self.assertIn('current_page', result)

    def test_search_empty_query(self):
        """Test search with empty query."""
        searcher = DuckDuckGoSearch()
        result = searcher.search("")
        # Should handle gracefully
        self.assertIsInstance(result, dict)


class TestWebSearchTool(unittest.TestCase):
    """Test the web_search tool functionality."""

    def test_web_search_tool_definition(self):
        """Test that the web search tool definition is correct."""
        self.assertEqual(WEB_SEARCH_TOOL_DEFINITION["auto_approved"], True)
        self.assertIn("query", WEB_SEARCH_TOOL_DEFINITION["parameters"]["properties"])
        self.assertIn("max_results", WEB_SEARCH_TOOL_DEFINITION["parameters"]["properties"])

    def test_execute_web_search_valid_input(self):
        """Test execute_web_search with valid input."""
        # Mock the DuckDuckGoSearch to avoid actual network calls
        with patch('web_search.DuckDuckGoSearch') as mock_search_class:
            mock_searcher = Mock()
            mock_search_class.return_value = mock_searcher
            mock_searcher.search.return_value = {
                'results': [
                    {
                        'title': 'Python Programming',
                        'url': 'https://python.org',
                        'description': 'Python programming language'
                    }
                ],
                'has_next': False,
                'current_page': 1
            }
            
            result = execute_web_search("python", 5)
            
            # Check that the result is formatted correctly
            self.assertIn("1. Python Programming", result)
            self.assertIn("https://python.org", result)
            self.assertIn("Python programming language", result)

    def test_execute_web_search_invalid_query(self):
        """Test execute_web_search with invalid query."""
        result = execute_web_search(123, 5)  # Non-string query
        self.assertIn("Error:", result)

    def test_execute_web_search_invalid_max_results(self):
        """Test execute_web_search with invalid max_results."""
        with self.assertRaises(ValueError):
            execute_web_search("python", "invalid")  # Non-integer max_results
        
        with self.assertRaises(ValueError):
            execute_web_search("python", 0)  # Zero or negative

    def test_execute_web_search_no_results(self):
        """Test execute_web_search when no results are found."""
        with patch('web_search.DuckDuckGoSearch') as mock_search_class:
            mock_searcher = Mock()
            mock_search_class.return_value = mock_searcher
            mock_searcher.search.return_value = {
                'results': [],
                'has_next': False,
                'current_page': 1
            }
            
            result = execute_web_search("nonexistentquery12345", 5)
            self.assertEqual(result, "No results found for the search query.")


class TestGetUrlContentTool(unittest.TestCase):
    """Test the get_url_content tool functionality."""

    def test_url_content_tool_definition(self):
        """Test that the URL content tool definition is correct."""
        self.assertEqual(URL_CONTENT_TOOL_DEFINITION["name"], "get_url_content")
        self.assertEqual(URL_CONTENT_TOOL_DEFINITION["auto_approved"], False)  # Requires approval
        self.assertIn("url", URL_CONTENT_TOOL_DEFINITION["parameters"]["properties"])

    def test_execute_get_url_content_valid_input(self):
        """Test execute_get_url_content with valid input."""
        # Mock subprocess.run to simulate lynx output
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Sample webpage content\nThis is a test page."
        mock_result.stderr = ""
        
        with patch('subprocess.run', return_value=mock_result):
            result = execute_get_url_content("https://example.com")
            self.assertIn("Sample webpage content", result)
            self.assertIn("This is a test page", result)

    def test_execute_get_url_content_invalid_url(self):
        """Test execute_get_url_content with invalid URL."""
        with self.assertRaises(ValueError):
            execute_get_url_content("")  # Empty URL
        
        result = execute_get_url_content("not-a-url")  # Missing protocol
        self.assertIn("URL must start with http:// or https://", result)

    def test_execute_get_url_content_lynx_not_found(self):
        """Test execute_get_url_content when lynx is not installed."""
        with patch('subprocess.run', side_effect=FileNotFoundError("lynx not found")):
            result = execute_get_url_content("https://example.com")
            self.assertIn("'lynx' command not found", result)
            self.assertIn("sudo apt install lynx", result)

    def test_execute_get_url_content_timeout(self):
        """Test execute_get_url_content with timeout."""
        import subprocess
        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired(['lynx'], 30)):
            result = execute_get_url_content("https://example.com")
            self.assertIn("timed out after 30 seconds", result)

    def test_execute_get_url_content_command_error(self):
        """Test execute_get_url_content when lynx returns an error."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "HTTP error: 404 Not Found"
        
        with patch('subprocess.run', return_value=mock_result):
            result = execute_get_url_content("https://example.com/nonexistent")
            self.assertIn("Error fetching URL content", result)
            self.assertIn("404 Not Found", result)

    def test_execute_get_url_content_large_content_truncation(self):
        """Test that large content is truncated properly."""
        # Create very long content
        long_content = "A" * 10000
        
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = long_content
        mock_result.stderr = ""
        
        with patch('subprocess.run', return_value=mock_result):
            result = execute_get_url_content("https://example.com")
            self.assertIn("truncated to 8000 characters", result)
            self.assertLess(len(result), 8500)  # Should be less than 8000 + message

    def test_execute_get_url_content_empty_response(self):
        """Test execute_get_url_content when URL returns no content."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        
        with patch('subprocess.run', return_value=mock_result):
            result = execute_get_url_content("https://example.com")
            self.assertEqual(result, "The URL returned no content.")


class TestPluginIntegration(unittest.TestCase):
    """Test plugin integration aspects."""

    def test_plugin_imports(self):
        """Test that all required functions can be imported."""
        # This test just verifies the imports work
        self.assertTrue(callable(DuckDuckGoSearch))
        self.assertTrue(callable(execute_web_search))
        self.assertTrue(callable(execute_get_url_content))

    def test_tool_registration_structure(self):
        """Test that tool definitions have the required structure."""
        # Check web search tool
        self.assertIn("type", WEB_SEARCH_TOOL_DEFINITION)
        self.assertIn("name", WEB_SEARCH_TOOL_DEFINITION)
        self.assertIn("description", WEB_SEARCH_TOOL_DEFINITION)
        self.assertIn("parameters", WEB_SEARCH_TOOL_DEFINITION)
        
        # Check URL content tool
        self.assertIn("type", URL_CONTENT_TOOL_DEFINITION)
        self.assertIn("name", URL_CONTENT_TOOL_DEFINITION)
        self.assertIn("description", URL_CONTENT_TOOL_DEFINITION)
        self.assertIn("parameters", URL_CONTENT_TOOL_DEFINITION)


def run_manual_tests():
    """Run manual tests that require actual network access."""
    print("\n" + "="*60)
    print("MANUAL TESTS (require network access)")
    print("="*60)
    
    print("\n1. Testing DuckDuckGo search...")
    try:
        results = execute_web_search("python programming", 3)
        print("Search results:")
        print(results)
        print("✓ Web search test passed")
    except Exception as e:
        print(f"✗ Web search test failed: {e}")
    
    print("\n2. Testing URL content fetch (if lynx is available)...")
    # First check if lynx is available
    try:
        subprocess.run(['which', 'lynx'], capture_output=True, check=True)
        print("lynx is available, testing URL content fetch...")
        
        try:
            # Test with a simple, reliable URL
            content = execute_get_url_content("https://httpbin.org/html")
            print("URL content (first 200 chars):")
            print(content[:200] + "..." if len(content) > 200 else content)
            print("✓ URL content test passed")
        except Exception as e:
            print(f"✗ URL content test failed: {e}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("lynx is not available, skipping URL content test")


if __name__ == "__main__":
    print("Running enhanced web search plugin tests...")
    print("="*60)
    
    # Run unit tests
    print("UNIT TESTS (no network access required)")
    print("="*60)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestDuckDuckGoSearch))
    suite.addTests(loader.loadTestsFromTestCase(TestWebSearchTool))
    suite.addTests(loader.loadTestsFromTestCase(TestGetUrlContentTool))
    suite.addTests(loader.loadTestsFromTestCase(TestPluginIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\nFAILURES:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print("\nERRORS:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
    
    # Ask user if they want to run manual tests
    if not result.failures and not result.errors:
        print("\nAll unit tests passed!")
        response = input("\nDo you want to run manual tests that require network access? (y/N): ")
        if response.lower() in ['y', 'yes']:
            run_manual_tests()
    
    print(f"\n{'='*60}")
    print("Test run complete!")
    print(f"{'='*60}")
    
    # Exit with appropriate code
    sys.exit(0 if not result.failures and not result.errors else 1)
"""
Web Search Plugin for AI Coder

This plugin adds web search capability using DuckDuckGo Lite HTML parsing.
The AI can call the 'web_search' tool to find information online.
Uses no external dependencies - only Python standard library.
"""

import html
import json
import urllib.parse
import urllib.request
import re
import subprocess
import os
from typing import List, Dict, Optional
from html.parser import HTMLParser


class SearchResult:
    """Represents a single search result."""
    
    def __init__(self, title: str = "", description: str = "", url: str = ""):
        self.title = title
        self.description = description
        self.url = url


class DuckDuckGoHTMLParser(HTMLParser):
    """HTML parser for DuckDuckGo search results."""
    
    def __init__(self, page_format: str = "page1"):
        super().__init__()
        self.page_format = page_format
        self.results: List[SearchResult] = []
        self.current_result: Optional[SearchResult] = None
        self.collecting_text = False
        self.text_buffer = []
        self.in_next_page_form = False
        self.form_params: Dict[str, str] = {}
        self.found_next_page = False
        self.in_result_snippet = False
        
    def handle_starttag(self, tag: str, attrs: List[tuple]):
        attrs_dict = dict(attrs)
        
        if tag == 'a' and 'href' in attrs_dict:
            href = attrs_dict['href']
            class_attr = attrs_dict.get('class') or ''
            
            # Check for search results
            if 'result-link' in class_attr:
                # Page 1 uses uddg redirects, page 2+ uses direct URLs
                if self.page_format == "page1" and 'uddg=' in href:
                    url = self._process_url(href)
                    self.current_result = SearchResult(url=url)
                    self.collecting_text = True
                    self.text_buffer = []
                elif self.page_format == "page2" and not self._should_skip_url(href):
                    url = self._process_url(href)
                    self.current_result = SearchResult(url=url)
                    self.collecting_text = True
                    self.text_buffer = []
        
        elif tag == 'form' and 'action' in attrs_dict:
            if attrs_dict['action'] == '/lite/':
                self.in_next_page_form = True
        
        elif tag == 'input' and self.in_next_page_form:
            name = attrs_dict.get('name')
            value = attrs_dict.get('value', '')
            if name:
                self.form_params[name] = value
        
        elif tag == 'td' and 'result-snippet' in attrs_dict.get('class', ''):
            # We're entering a description for a result
            self.in_result_snippet = True
            self.collecting_text = True
            self.text_buffer = []
    
    def handle_data(self, data: str):
        if self.collecting_text:
            # Clean up the data and add to buffer
            clean_data = data.strip()
            if clean_data:
                self.text_buffer.append(clean_data)
    
    def handle_endtag(self, tag: str):
        if tag == 'a' and self.current_result and self.collecting_text:
            # Finished collecting the title
            title = ' '.join(self.text_buffer).strip()
            if title and not self._should_skip_title(title):
                self.current_result.title = title
                # Add to results but description will be added later
                self.results.append(self.current_result)
            
            self.current_result = None
            self.collecting_text = False
            self.text_buffer = []
        
        elif tag == 'td' and self.in_result_snippet:
            # Finished collecting description - assign to the most recent result
            description = ' '.join(self.text_buffer).strip()
            description = self._clean_text(description)
            
            # Find the most recent result without a description
            for result in reversed(self.results):
                if result.title and not result.description:
                    result.description = description
                    break
            
            self.in_result_snippet = False
            self.collecting_text = False
            self.text_buffer = []
        
        elif tag == 'form' and self.in_next_page_form:
            self.in_next_page_form = False
            self.found_next_page = True
    
    def handle_comment(self, data: str):
        if 'Next Page Button Sub-template' in data:
            self.found_next_page = True
    
    def _should_skip_url(self, url: str) -> bool:
        """Check if URL should be skipped."""
        skip_patterns = [
            'duckduckgo.com',
            'javascript:',
            '#',
            '/lite/',
            'opensearch'
        ]
        return any(pattern in url for pattern in skip_patterns)
    
    def _should_skip_title(self, title: str) -> bool:
        """Check if title should be skipped."""
        skip_patterns = [
            'All Regions',
            'Any Time',
            'Search',
            'Next Page',
            'Previous Page',
            'DuckDuckGo',
            'References',
            'More',
            'Videos',
            'Images',
            'Maps',
            'News'
        ]
        return any(pattern.lower() in title.lower() for pattern in skip_patterns)
    
    def _process_url(self, url: str) -> str:
        """Process URL (handle redirects and relative URLs)."""
        # Handle relative URLs
        if url.startswith('//'):
            url = 'https:' + url
        elif url.startswith('/'):
            url = 'https://duckduckgo.com' + url
        
        # Extract actual URL from DuckDuckGo redirect
        if 'uddg=' in url:
            parsed = urllib.parse.urlparse(url)
            params = urllib.parse.parse_qs(parsed.query)
            if 'uddg' in params:
                return urllib.parse.unquote(params['uddg'][0])
        
        return url
    
    def _clean_text(self, text: str) -> str:
        """Clean text content."""
        if not text:
            return ""
        
        # Remove HTML entities
        text = html.unescape(text)
        
        # Clean up whitespace
        text = ' '.join(text.split())
        
        # Remove date stamps and other trailing metadata
        parts = text.split()
        cleaned_parts = []
        for part in parts:
            # Stop if we encounter something that looks like a date
            if (part.startswith(('20', '19')) and 
                ('-' in part or '/' in part or len(part) >= 8)):
                break
            cleaned_parts.append(part)
        
        return ' '.join(cleaned_parts)


class DuckDuckGoSearch:
    """Simple DuckDuckGo Lite search scraper."""

    def __init__(self):
        self.base_url = "https://lite.duckduckgo.com/lite/"

    def search(self, query: str, page: int = 1) -> Dict[str, any]:
        """
        Search DuckDuckGo and return results.

        Args:
            query: Search query string
            page: Page number (1-based)

        Returns:
            Dictionary with:
            - results: List of search results
            - has_next: Boolean indicating if there are more pages
            - current_page: Current page number
        """
        params = {'q': query}

        if page == 1:
            return self._search_page1(query, params)
        else:
            return self._search_subsequent_page(query, page)

    def _search_page1(self, query: str, params: Dict[str, str]) -> Dict[str, any]:
        """Handle first page search."""
        url = f"{self.base_url}?{urllib.parse.urlencode(params)}"
        
        try:
            req = urllib.request.Request(
                url,
                headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'}
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                html_content = response.read().decode('utf-8', errors='ignore')

            parser = DuckDuckGoHTMLParser("page1")
            parser.feed(html_content)
            
            results = []
            for result in parser.results:
                if result.title and result.url:  # Only include results with title and URL
                    results.append({
                        'title': result.title,
                        'description': result.description,
                        'url': result.url
                    })

            return {
                'results': results,
                'has_next': parser.found_next_page,
                'current_page': 1,
                'query': query,
                'form_params': parser.form_params
            }

        except Exception as e:
            return {
                'results': [],
                'has_next': False,
                'current_page': 1,
                'query': query,
                'error': str(e)
            }

    def _search_subsequent_page(self, query: str, page: int) -> Dict[str, any]:
        """Handle subsequent pages search."""
        # First get page 1 to extract form parameters
        page1_result = self._search_page1(query, {'q': query})
        if 'error' in page1_result:
            return {
                **page1_result,
                'current_page': page
            }

        form_params = page1_result.get('form_params', {})
        if not form_params:
            return {
                'results': [],
                'has_next': False,
                'current_page': page,
                'query': query,
                'error': 'Could not extract pagination parameters'
            }

        # Update the 's' parameter for the requested page
        offset = (page - 1) * 10  # DuckDuckGo shows 10 results per page
        form_params['s'] = str(offset)
        form_params['q'] = query  # Ensure query is included

        try:
            data = urllib.parse.urlencode(form_params).encode('utf-8')
            req = urllib.request.Request(
                self.base_url,
                data=data,
                headers={
                    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                html_content = response.read().decode('utf-8', errors='ignore')

            parser = DuckDuckGoHTMLParser("page2")
            parser.feed(html_content)
            
            results = []
            for result in parser.results:
                if result.title and result.url:  # Only include results with title and URL
                    results.append({
                        'title': result.title,
                        'description': result.description,
                        'url': result.url
                    })

            return {
                'results': results,
                'has_next': parser.found_next_page,
                'current_page': page,
                'query': query
            }

        except Exception as e:
            return {
                'results': [],
                'has_next': False,
                'current_page': page,
                'query': query,
                'error': str(e)
            }


# Tool definitions
WEB_SEARCH_TOOL_DEFINITION = {
    "type": "internal",
    "auto_approved": True,  # Auto-approve web searches
    "description": "Search the web for information using DuckDuckGo.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query string.",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results to return (optional, returns all available if not specified).",
                "minimum": 1,
                "maximum": 50,
            },
        },
        "required": ["query"],
    },
}

URL_CONTENT_TOOL_DEFINITION = {
    "type": "internal",
    "auto_approved": False,  # Require approval for URL content fetching
    "description": "Fetch and read the full text content of a URL using lynx browser.",
    "parameters": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The URL to fetch content from (http/https only).",
            },
        },
        "required": ["url"],
    },
}

def execute_web_search(query: str, max_results: Optional[int] = None, **kwargs) -> str:
    """Execute web search and return formatted results."""
    if not query.strip():
        return "Error: Search query cannot be empty."

    search = DuckDuckGoSearch()

    try:
        result = search.search(query, page=1)
        results = result.get('results', [])

        if not results:
            return f"No results found for query: {query}"

        # Apply max_results limit if specified
        if max_results is not None and max_results > 0:
            results = results[:max_results]

        # Format results
        formatted_results = []
        for i, item in enumerate(results, 1):
            formatted_results.append(
                f"{i}. {item['title']}\n"
                f"{item['description']}\n"
                f"URL: {item['url']}"
            )

        return "\n\n".join(formatted_results)

    except Exception as e:
        return f"Error performing web search: {str(e)}"

def execute_get_url_content(url: str, **kwargs) -> str:
    """Execute URL content fetching using lynx."""
    if not url.strip():
        return "Error: URL cannot be empty."

    # Check if HTTP is allowed via environment variable
    allow_http = os.environ.get('ALLOW_HTTP', '').lower() in ('1', 'true', 'yes')

    # Process URL based on ALLOW_HTTP setting
    if not (url.startswith('http://') or url.startswith('https://')):
        # Auto-add protocol based on setting
        if allow_http:
            url = f'http://{url}'
        else:
            url = f'https://{url}'
    elif not allow_http and url.startswith('http://'):
        # Upgrade http:// to https:// only if HTTP is not allowed
        url = f'https://{url[7:]}'

    # Check if lynx is available
    try:
        subprocess.run(['which', 'lynx'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "Error: lynx browser is not installed. Please install it with: sudo apt install lynx"

    try:
        # Use lynx to dump the page content
        result = subprocess.run(
            ['lynx', '-dump', '-nolist', url],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            error_msg = result.stderr.strip() if result.stderr else "lynx failed to retrieve content"
            return f"Error fetching URL content: {error_msg}"

        content = result.stdout.strip()

        if not content:
            return f"URL '{url}' returned no readable content."

        # Truncate if too long (keep it reasonable)
        max_length = 8000
        if len(content) > max_length:
            content = content[:max_length] + "\n\n[Content truncated due to length]"

        return f"Content from {url}:\n\n{content}"

    except subprocess.TimeoutExpired:
        return f"Error: Request to '{url}' timed out after 30 seconds."
    except Exception as e:
        return f"Error fetching URL content: {str(e)}"

def on_aicoder_init(aicoder_instance):
    """Initialize plugin and register tools."""
    # Register our tools as internal tools
    from aicoder.tool_manager.internal_tools import INTERNAL_TOOL_FUNCTIONS

    INTERNAL_TOOL_FUNCTIONS["web_search"] = execute_web_search
    INTERNAL_TOOL_FUNCTIONS["get_url_content"] = execute_get_url_content

    # Register tool definitions in the tool registry
    aicoder_instance.tool_manager.registry.mcp_tools["web_search"] = WEB_SEARCH_TOOL_DEFINITION
    aicoder_instance.tool_manager.registry.mcp_tools["get_url_content"] = URL_CONTENT_TOOL_DEFINITION

    # Add information about web search functionality to the system prompt
    if (
        hasattr(aicoder_instance, "message_history")
        and aicoder_instance.message_history.messages
    ):
        system_prompt = aicoder_instance.message_history.messages[0]

        if hasattr(system_prompt, "content"):
            if "web_search" not in system_prompt.content:
                system_prompt.content += """
You have access to a web search tool that can search the internet for current information using DuckDuckGo. Use it when you need up-to-date information or details about recent events.

You also have access to a get_url_content tool that can fetch and read the full content of specific URLs. This requires user approval each time it's used.

Example usage:
- web_search(query="latest news about technology")
- get_url_content(url="https://example.com/article")

Note: web_search is auto-approved for efficiency, while get_url_content requires explicit user approval for security.
"""

    print("Web Search Plugin: Enabled web search and URL content tools")
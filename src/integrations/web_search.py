"""
Web search and content fetching integration.
Allows the assistant to search the internet and fetch webpage content.
"""

from typing import List, Dict, Any, Optional
import httpx
from bs4 import BeautifulSoup
import re
from datetime import datetime
import json


class WebSearchIntegration:
    """Integration for web search and content fetching"""

    def __init__(self, timeout: int = 10):
        """
        Initialize web search integration.

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        self.client = httpx.Client(timeout=timeout, headers=self.headers, follow_redirects=True)

    def search_google(self, query: str, num_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search Google and return top results.

        Args:
            query: Search query
            num_results: Number of results to return (max 10)

        Returns:
            List of search results with title, url, snippet
        """
        try:
            # Use Google search URL
            search_url = f"https://www.google.com/search?q={query}&num={min(num_results, 10)}"

            response = self.client.get(search_url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            results = []

            # Parse search results
            for g in soup.find_all('div', class_='g')[:num_results]:
                # Extract title
                title_elem = g.find('h3')
                title = title_elem.text if title_elem else 'No title'

                # Extract URL
                link_elem = g.find('a')
                url = link_elem['href'] if link_elem and 'href' in link_elem.attrs else None

                # Extract snippet
                snippet_elem = g.find('div', class_=['VwiC3b', 'yXK7lf'])
                snippet = snippet_elem.text if snippet_elem else ''

                if url:
                    results.append({
                        'title': title,
                        'url': url,
                        'snippet': snippet
                    })

            return results

        except Exception as e:
            print(f"Error searching Google: {e}")
            return []

    def fetch_webpage(self, url: str, max_length: int = 5000) -> Dict[str, Any]:
        """
        Fetch and extract text content from a webpage.

        Args:
            url: URL to fetch
            max_length: Maximum content length to return

        Returns:
            Dict with url, title, content, summary
        """
        try:
            response = self.client.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()

            # Extract title
            title = soup.title.string if soup.title else 'No title'

            # Extract main content
            # Try to find main content area
            main_content = soup.find('main') or soup.find('article') or soup.find('body')

            if main_content:
                text = main_content.get_text(separator='\n', strip=True)
            else:
                text = soup.get_text(separator='\n', strip=True)

            # Clean up text
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            content = '\n'.join(lines)

            # Truncate if too long
            if len(content) > max_length:
                content = content[:max_length] + f"\n\n[Content truncated - total length: {len(content)} characters]"

            # Generate summary (first 500 chars)
            summary = content[:500] + "..." if len(content) > 500 else content

            return {
                'url': url,
                'title': title,
                'content': content,
                'summary': summary,
                'length': len(content),
                'fetched_at': datetime.now().isoformat()
            }

        except httpx.HTTPError as e:
            return {
                'url': url,
                'error': f'HTTP Error: {str(e)}',
                'title': None,
                'content': None,
                'summary': None
            }
        except Exception as e:
            return {
                'url': url,
                'error': f'Error fetching page: {str(e)}',
                'title': None,
                'content': None,
                'summary': None
            }

    def search_and_fetch(self, query: str, num_results: int = 3) -> List[Dict[str, Any]]:
        """
        Search Google and fetch content from top results.

        Args:
            query: Search query
            num_results: Number of results to fetch (max 5 to avoid slowness)

        Returns:
            List of results with search info + fetched content
        """
        # Search Google
        search_results = self.search_google(query, num_results)

        if not search_results:
            return []

        # Fetch content from each result
        enriched_results = []
        for result in search_results[:num_results]:
            url = result['url']
            print(f"Fetching content from: {url}")

            webpage = self.fetch_webpage(url, max_length=3000)

            enriched_results.append({
                'search_result': result,
                'webpage': webpage,
                'title': webpage.get('title') or result['title'],
                'url': url,
                'snippet': result['snippet'],
                'content_preview': webpage.get('summary', result['snippet'])
            })

        return enriched_results

    def get_weather(self, location: str) -> Dict[str, Any]:
        """
        Get current weather for a location (uses web search).

        Args:
            location: City name or location

        Returns:
            Weather information
        """
        query = f"weather {location} today"
        results = self.search_google(query, num_results=1)

        if not results:
            return {'error': 'Could not fetch weather information'}

        # Google often shows weather widget in search results
        # Return the snippet which usually contains weather info
        return {
            'location': location,
            'query': query,
            'info': results[0]['snippet'],
            'source_url': results[0]['url']
        }

    def get_news(self, topic: str = "latest news", num_results: int = 5) -> List[Dict[str, Any]]:
        """
        Get latest news about a topic.

        Args:
            topic: News topic to search for
            num_results: Number of news articles to return

        Returns:
            List of news articles
        """
        query = f"{topic} news"
        results = self.search_google(query, num_results)

        return [
            {
                'title': r['title'],
                'url': r['url'],
                'snippet': r['snippet']
            }
            for r in results
        ]

    def __del__(self):
        """Cleanup: close HTTP client"""
        try:
            self.client.close()
        except:
            pass

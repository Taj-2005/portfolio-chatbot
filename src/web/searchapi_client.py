"""
SearchAPI integration for web search augmentation.

Provides fallback web search when resume context is insufficient.
"""

from typing import Optional

try:
    import requests
except ImportError:
    requests = None

from ..config import settings
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class SearchAPIClient:
    """
    Client for SearchAPI.io service.
    
    Provides web search functionality for context augmentation
    when resume content is insufficient.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize SearchAPIClient.
        
        Args:
            api_key: SearchAPI key. If None, uses settings.SEARCHAPI_API_KEY.
        """
        self.api_key = api_key or settings.SEARCHAPI_API_KEY
        
        if not self.api_key:
            logger.warning("SearchAPI key not configured - web search will be unavailable")
        
        if requests is None:
            logger.warning("requests library not installed - web search will be unavailable")
    
    def search(self, query: str) -> Optional[str]:
        """
        Perform web search and return relevant snippets.
        
        Args:
            query: Search query string.
        
        Returns:
            Optional[str]: Combined search results as text, or None if no results.
        """
        if not self.api_key:
            logger.warning("SearchAPI key not configured")
            return None
        
        if not requests:
            logger.error("requests library not available")
            return None
        
        try:
            url = "https://www.searchapi.io/api/v1/search"
            
            params = {
                'engine': 'google',
                'q': query,
                'api_key': self.api_key,
                'num': settings.SEARCHAPI_MAX_RESULTS
            }
            
            logger.info(f"SearchAPI query: {query}")
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('organic_results', [])
                
                if results:
                    context_parts = []
                    for result in results[:settings.SEARCHAPI_RESULTS_TO_USE]:
                        title = result.get('title', '')
                        snippet = result.get('snippet', '')
                        if title and snippet:
                            context_parts.append(f"{title}: {snippet[:200]}")
                    
                    combined = "\n".join(context_parts) if context_parts else None
                    logger.info(f"SearchAPI returned {len(context_parts)} results")
                    return combined
                else:
                    logger.info("SearchAPI returned no results")
                    return None
            
            elif response.status_code == 429:
                logger.warning("SearchAPI quota exceeded (free tier limit)")
                print("  ⚠️  SearchAPI quota exceeded (free tier limit)")
                return None
            
            elif response.status_code == 401:
                logger.error("SearchAPI authentication failed - invalid API key")
                return None
            
            else:
                logger.warning(f"SearchAPI returned status code {response.status_code}")
                return None
            
        except requests.exceptions.Timeout:
            logger.warning("SearchAPI request timed out")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"SearchAPI request error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in SearchAPI: {e}")
            return None

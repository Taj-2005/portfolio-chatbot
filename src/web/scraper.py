"""
Web scraping functionality for GitHub and general web pages.

Scrapes README content from GitHub repositories and extracts
clean text from web pages.
"""

import re
from typing import List, Tuple, Set
from urllib.parse import urlparse

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    requests = None
    BeautifulSoup = None

from ..config import settings
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class WebScraper:
    """
    Web scraping utility for GitHub repositories and general web pages.
    
    Extracts README content from GitHub repos and clean text from web pages.
    """
    
    def __init__(self):
        """Initialize WebScraper."""
        if requests is None or BeautifulSoup is None:
            logger.warning(
                "requests and/or beautifulsoup4 not installed - "
                "web scraping will be unavailable"
            )
    
    def scrape_webpage(
        self,
        url: str,
        timeout: int = None
    ) -> Tuple[str, str, bool]:
        """
        Scrape content from a web page.
        
        Removes scripts, styles, navigation, and other non-content elements.
        
        Args:
            url: URL to scrape.
            timeout: Request timeout in seconds. If None, uses settings value.
        
        Returns:
            Tuple of (title, text_content, success_flag).
        """
        if requests is None or BeautifulSoup is None:
            logger.error("Web scraping libraries not available")
            return "Error", "[Web scraping unavailable]", False
        
        timeout = timeout or settings.WEB_SCRAPE_TIMEOUT
        
        try:
            headers = {'User-Agent': settings.USER_AGENT}
            response = requests.get(url, timeout=timeout, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            title = soup.title.string if soup.title else "No title"
            
            # Remove non-content elements
            for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                element.decompose()
            
            # Extract text
            text = soup.get_text(separator='\n', strip=True)
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            text = '\n'.join(lines)
            
            # Truncate if too long
            if len(text) > settings.MAX_SCRAPED_TEXT_LENGTH:
                text = text[:settings.MAX_SCRAPED_TEXT_LENGTH] + "..."
                logger.debug(f"Truncated scraped content to {settings.MAX_SCRAPED_TEXT_LENGTH} chars")
            
            logger.info(f"Successfully scraped {url}: {len(text)} chars")
            return title, text, True
            
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout scraping {url}")
            return "Error", "", False
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request error scraping {url}: {e}")
            return "Error", "", False
        except Exception as e:
            logger.error(f"Unexpected error scraping {url}: {e}")
            return "Error", "", False
    
    def process_github_links(self, github_urls: List[str]) -> List[Tuple[str, str]]:
        """
        Process GitHub repository URLs and extract README content.
        
        Args:
            github_urls: List of GitHub repository URLs.
        
        Returns:
            List of tuples (source_label, content).
        """
        results = []
        max_links = min(len(github_urls), settings.MAX_GITHUB_LINKS)
        
        logger.info(f"Processing {max_links} GitHub links")
        
        for url in github_urls[:max_links]:
            try:
                parsed = urlparse(url)
                path_parts = [p for p in parsed.path.split('/') if p]
                
                if len(path_parts) >= 2:
                    repo_name = f"{path_parts[0]}/{path_parts[1]}"
                    
                    title, content, success = self.scrape_webpage(
                        url,
                        timeout=settings.GITHUB_SCRAPE_TIMEOUT
                    )
                    
                    if success and content:
                        # Try to extract README section
                        readme_match = re.search(
                            r'README.*?(?=\n\n|\Z)',
                            content,
                            re.DOTALL | re.IGNORECASE
                        )
                        if readme_match:
                            content = readme_match.group(0)[:1000]
                        
                        results.append((f"GitHub: {repo_name}", content))
                        logger.info(f"Extracted content from {repo_name}")
                    else:
                        logger.warning(f"Failed to scrape GitHub repo: {url}")
            except Exception as e:
                logger.error(f"Error processing GitHub link {url}: {e}")
        
        logger.info(f"Successfully processed {len(results)} GitHub repositories")
        return results
    
    def should_use_web_augmentation(
        self,
        question: str,
        context: str,
        sections: dict,
        links: Set[str]
    ) -> Tuple[bool, str, str]:
        """
        Determine if web augmentation should be used.
        
        Decides whether to use web search based on context size,
        question type, and available links.
        
        Args:
            question: User's question.
            context: Current context string.
            sections: Resume sections dictionary.
            links: Set of URLs from resume.
        
        Returns:
            Tuple of (should_use, search_query, reason).
        """
        context_length = len(context)
        question_lower = question.lower()
        
        # Insufficient context - try web augmentation
        if context_length < 800:
            projects = sections.get('PROJECTS', '')
            if projects:
                lines = [l.strip() for l in projects.split('\n') if l.strip()]
                for line in lines[:5]:
                    if 10 < len(line) < 60 and not line.startswith('-'):
                        return True, f"{line[:40]} github", "resume insufficient"
            
            # Try GitHub links
            for link in links:
                if 'github.com' in link:
                    match = re.search(r'github\.com/([\w\-]+/[\w\-]+)', link)
                    if match:
                        return True, f"{match.group(1)}", "resume insufficient"
            
            return True, "portfolio projects", "resume insufficient"
        
        # Project-specific questions
        if any(kw in question_lower for kw in ['github', 'repo', 'project']):
            projects = sections.get('PROJECTS', '')
            if projects:
                lines = projects.split('\n')[:3]
                for line in lines:
                    if 10 < len(line) < 50:
                        return True, f"{line.strip()} project details", "project-specific question"
        
        # Don't augment for definitional questions
        if any(kw in question_lower for kw in ['what is', 'explain', 'how does', 'define']):
            return False, "", ""
        
        return False, "", ""

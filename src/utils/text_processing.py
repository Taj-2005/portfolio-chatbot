"""
Text processing utilities for the Portfolio Chatbot.

Provides functions for cleaning LaTeX text, extracting links,
and other text manipulation tasks.
"""

import re
import hashlib
from typing import Set, Dict, List
from urllib.parse import urlparse
from .logger import setup_logger

logger = setup_logger(__name__)


def clean_latex_text(text: str) -> str:
    """
    Clean LaTeX formatting from text.
    
    Removes LaTeX commands, special characters, and formatting while
    preserving the actual content and structure.
    
    Args:
        text: Input text potentially containing LaTeX commands.
    
    Returns:
        str: Cleaned text without LaTeX formatting.
    """
    if not text:
        return ""
    
    try:
        # Handle \href{url}{text} specially - convert to "text (url)"
        href_pattern = r'\\href\{([^}]+)\}\{([^}]+)\}'
        hrefs = re.findall(href_pattern, text)
        for url, link_text in hrefs:
            text = text.replace(f'\\href{{{url}}}{{{link_text}}}', f'{link_text} ({url})')
        
        # Remove common LaTeX formatting commands
        latex_commands = [
            r'\\section\*?\{([^}]+)\}',
            r'\\subsection\*?\{([^}]+)\}',
            r'\\textbf\{([^}]+)\}',
            r'\\textit\{([^}]+)\}',
            r'\\emph\{([^}]+)\}',
            r'\\underline\{([^}]+)\}',
            r'\\texttt\{([^}]+)\}',
            r'\\item\s+',
        ]
        
        for pattern in latex_commands:
            try:
                text = re.sub(pattern, r'\1', text)
            except re.error:
                continue
        
        # Remove remaining LaTeX commands
        text = re.sub(r'\\[a-zA-Z]+\*?', '', text)
        text = re.sub(r'[{}]', '', text)
        text = re.sub(r'\\', '', text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\s*\n\s*', '\n', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Remove page numbers and other artifacts
        text = re.sub(r'Page \d+ of \d+', '', text)
        text = re.sub(r'^\d+\s*$', '', text, flags=re.MULTILINE)
        
        return text.strip()
    except Exception as e:
        logger.warning(f"Error cleaning LaTeX text: {e}")
        return text


def extract_all_links(text: str) -> Set[str]:
    """
    Extract all HTTP/HTTPS URLs from text.
    
    Args:
        text: Input text to extract URLs from.
    
    Returns:
        Set[str]: Set of unique URLs found in the text.
    """
    if not text:
        return set()
    
    try:
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]\(\)]+'
        urls = re.findall(url_pattern, text)
        
        # Clean URLs (remove trailing punctuation)
        cleaned = set()
        for url in urls:
            url = url.rstrip('.,;:!?)')
            if url:
                cleaned.add(url)
        
        logger.debug(f"Extracted {len(cleaned)} URLs from text")
        return cleaned
    except Exception as e:
        logger.error(f"Error extracting links: {e}")
        return set()


def categorize_links(urls: Set[str]) -> Dict[str, List[str]]:
    """
    Categorize URLs by domain type (GitHub, LinkedIn, portfolio, other).
    
    Args:
        urls: Set of URLs to categorize.
    
    Returns:
        Dict[str, List[str]]: Dictionary with categorized URLs.
            Keys: 'github', 'linkedin', 'portfolio', 'other'
    """
    categories = {
        'github': [],
        'linkedin': [],
        'portfolio': [],
        'other': []
    }
    
    if not urls:
        return categories
    
    try:
        for url in urls:
            domain = urlparse(url).netloc.lower()
            
            if 'github.com' in domain:
                categories['github'].append(url)
            elif 'linkedin.com' in domain:
                categories['linkedin'].append(url)
            else:
                categories['other'].append(url)
        
        logger.debug(
            f"Categorized {len(urls)} URLs: "
            f"{len(categories['github'])} GitHub, "
            f"{len(categories['linkedin'])} LinkedIn, "
            f"{len(categories['other'])} other"
        )
        return categories
    except Exception as e:
        logger.error(f"Error categorizing links: {e}")
        return categories


def hash_text(text: str) -> str:
    """
    Generate MD5 hash of normalized text.
    
    Used for creating unique identifiers for questions or content.
    
    Args:
        text: Input text to hash.
    
    Returns:
        str: MD5 hash as hexadecimal string.
    """
    if not text:
        return ""
    
    try:
        normalized = text.lower().strip()
        return hashlib.md5(normalized.encode()).hexdigest()
    except Exception as e:
        logger.error(f"Error hashing text: {e}")
        return ""


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate text to maximum length, adding suffix if truncated.
    
    Args:
        text: Input text to truncate.
        max_length: Maximum length of output text (including suffix).
        suffix: Suffix to append if text is truncated.
    
    Returns:
        str: Truncated text with suffix if applicable.
    """
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def normalize_whitespace(text: str) -> str:
    """
    Normalize whitespace in text.
    
    Replaces multiple spaces with single space, normalizes line breaks.
    
    Args:
        text: Input text with potentially irregular whitespace.
    
    Returns:
        str: Text with normalized whitespace.
    """
    if not text:
        return ""
    
    # Replace multiple spaces with single space
    text = re.sub(r' +', ' ', text)
    
    # Normalize line breaks
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    
    return text.strip()

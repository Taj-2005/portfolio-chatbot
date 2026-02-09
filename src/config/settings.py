"""
Configuration settings for the Portfolio Chatbot.

This module centralizes all configuration values including API keys,
file paths, model parameters, and system constants.
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Central configuration class for the application."""
    
    ROOT_DIR: Path = Path(__file__).resolve().parent.parent.parent
    
    DOCS_DIR: str = "docs"
    MEMORY_FILE: Path = ROOT_DIR / "memory.json"
    
    GROQ_API_KEY: Optional[str] = os.getenv('GROQ_API_KEY')
    SEARCHAPI_API_KEY: Optional[str] = os.getenv('SEARCHAPI_API_KEY') or os.getenv('SEARCHAPI_KEY')
    
    LLM_MODEL: str = "llama-3.1-8b-instant"
    LLM_TEMPERATURE: float = 0.2
    LLM_MAX_TOKENS: int = 220
    
    MAX_CONTEXT_SIZE: int = 6000
    MAX_RESPONSE_WORDS: int = 120
    
    MAX_MEMORY_ENTRIES: int = 100
    SIMILARITY_THRESHOLD: float = 0.7
    EASY_QUESTION_THRESHOLD: float = 0.6
    
    WEB_SCRAPE_TIMEOUT: int = 10
    GITHUB_SCRAPE_TIMEOUT: int = 15
    MAX_GITHUB_LINKS: int = 3
    MAX_SCRAPED_TEXT_LENGTH: int = 2000
    
    SEARCHAPI_FREE_TIER_LIMIT: int = 100
    SEARCHAPI_MAX_RESULTS: int = 3
    SEARCHAPI_RESULTS_TO_USE: int = 2
    
    LINKUP_NAMES: tuple = ("linkup", "link-up", "link up")
    PROJECT_JSON_NAMES: tuple = ("project.json", "projects.json")
    
    KEYWORD_TECH_PATTERNS: tuple = (
        "firebase", "react native", "real-time", "realtime", "chat", "auth",
        "next.js", "nextjs", "mongodb", "socket", "typescript", "tailwind",
        "aws", "node", "express", "gemini", "ai", "nodemailer", "shadcn",
    )
    
    SUPPORTED_RESUME_FORMATS: dict = {
        '.pdf': 'PDF',
        '.docx': 'Word Document',
        '.doc': 'Word Document',
        '.txt': 'Text',
        '.md': 'Markdown',
        '.tex': 'LaTeX',
    }
    
    USER_AGENT: str = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    CORS_ALLOW_ORIGIN: str = "*"
    CORS_ALLOW_METHODS: str = "GET, POST, OPTIONS"
    CORS_ALLOW_HEADERS: str = "Content-Type"
    
    @classmethod
    def validate(cls) -> bool:
        """
        Validate required configuration values.
        
        Returns:
            bool: True if all required settings are present, False otherwise.
        """
        if not cls.GROQ_API_KEY:
            return False
        return True
    
    @classmethod
    def get_docs_path(cls) -> Path:
        """
        Get the absolute path to the docs directory.
        
        Returns:
            Path: Absolute path to docs directory.
        """
        return cls.ROOT_DIR / cls.DOCS_DIR


settings = Settings()

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
    
    # Knowledge base directory (source of truth for RAG context).
    # Per your updated requirement, we do NOT use `docs/` for retrieval anymore.
    DOCS_DIR: str = os.getenv("KNOWLEDGE_BASE_DIR", "knowledge-base")
    MEMORY_FILE: Path = ROOT_DIR / "memory.json"
    
    GROQ_API_KEY: Optional[str] = os.getenv('GROQ_API_KEY')
    SEARCHAPI_API_KEY: Optional[str] = os.getenv('SEARCHAPI_API_KEY') or os.getenv('SEARCHAPI_KEY')
    
    LLM_MODEL: str = "llama-3.1-8b-instant"
    LLM_TEMPERATURE: float = 0.2
    LLM_MAX_TOKENS: int = 220
    
    MAX_CONTEXT_SIZE: int = 6000
    MAX_RESPONSE_WORDS: int = 120
    
    # ----------------------------
    # Internal RAG enhancements
    # ----------------------------
    # IMPORTANT: Defaults preserve the current documented behavior (keyword/intent based).
    # Set env vars to opt-in to more advanced retrieval internally without changing APIs.
    RAG_RETRIEVAL_MODE: str = os.getenv("RAG_RETRIEVAL_MODE", "legacy").lower()
    # legacy: existing ContextSelector logic
    # bm25: lexical BM25 retrieval over chunked sources (resume/projects/web/search)
    RAG_BM25_TOP_K: int = int(os.getenv("RAG_BM25_TOP_K", "8"))
    RAG_FINAL_CONTEXT_CHUNKS: int = int(os.getenv("RAG_FINAL_CONTEXT_CHUNKS", "5"))
    RAG_ENABLE_CONTEXT_COMPRESSION: bool = os.getenv("RAG_ENABLE_CONTEXT_COMPRESSION", "true").lower() in ("1", "true", "yes")

    # Lightweight reranking (kept off by default to preserve latency/cost)
    # overlap: deterministic token-overlap rerank (no extra API calls)
    # llm: uses Groq to rerank (extra call) - only enable intentionally
    RAG_RERANK_MODE: str = os.getenv("RAG_RERANK_MODE", "off").lower()

    # ----------------------------
    # Caching (instance-level, TTL)
    # ----------------------------
    CACHE_TTL_SECONDS_MEMORY_HIT: int = int(os.getenv("CACHE_TTL_SECONDS_MEMORY_HIT", "300"))
    CACHE_TTL_SECONDS_RETRIEVAL: int = int(os.getenv("CACHE_TTL_SECONDS_RETRIEVAL", "300"))
    CACHE_TTL_SECONDS_LLM: int = int(os.getenv("CACHE_TTL_SECONDS_LLM", "120"))
    CACHE_MAX_ITEMS: int = int(os.getenv("CACHE_MAX_ITEMS", "512"))

    # Normalize queries before caching/retrieval to improve hit rate.
    CACHE_NORMALIZE_QUERIES: bool = os.getenv("CACHE_NORMALIZE_QUERIES", "true").lower() in ("1", "true", "yes")

    # Serverless/runtime detection (used to avoid file persistence where unsupported)
    IS_VERCEL: bool = os.getenv("VERCEL", "").lower() in ("1", "true", "yes") or bool(os.getenv("VERCEL_ENV"))
    IS_SERVERLESS: bool = IS_VERCEL or bool(os.getenv("AWS_LAMBDA_FUNCTION_NAME")) or bool(os.getenv("FUNCTIONS_WORKER_RUNTIME"))

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
    
    # Owner identity (used for grounding, never guessed by the LLM).
    OWNER_NAME: str = "Shaik Tajuddin"
    PORTFOLIO_URL: str = os.getenv("PORTFOLIO_URL", "https://www.taju.dev")

    # The project the assistant leads with for "your project" / "main project" questions.
    # Matched against project title and slug in projects.json (case-insensitive substring).
    # Override with a comma-separated env var, e.g. FEATURED_PROJECT_NAMES="shopsmart,shop smart".
    FEATURED_PROJECT_NAMES: tuple = tuple(
        n.strip().lower()
        for n in os.getenv("FEATURED_PROJECT_NAMES", "deplo.ai,deplo-ai,deplo ai,deplo").split(",")
        if n.strip()
    )
    PROJECT_JSON_NAMES: tuple = ("project.json", "projects.json")

    KEYWORD_TECH_PATTERNS: tuple = (
        # languages / core
        "typescript", "javascript", "python", "c++", "java", "sql", "bash",
        # web / frontend
        "next.js", "nextjs", "react native", "react", "tailwind", "zustand",
        "framer motion", "expo",
        # backend / data
        "fastapi", "express", "node", "prisma", "postgres", "postgresql",
        "mongodb", "firebase", "dynamodb", "redis", "socket",
        # cloud / devops
        "aws", "gcp", "google cloud", "cloudflare", "terraform", "docker",
        "kubernetes", "github actions", "ci/cd", "amplify", "cognito", "lambda",
        "s3", "vercel",
        # ai / ml
        "ai", "ml", "llm", "genai", "rag", "langchain", "langgraph", "groq",
        "vertex ai", "yolo", "computer vision", "tensorflow", "hugging face",
        # product / other
        "deployment", "deploy", "auth", "rbac", "mfa", "real-time", "realtime",
        "offline", "figma", "jira",
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

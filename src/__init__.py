"""
Portfolio Chatbot with RAG (Retrieval-Augmented Generation).

A modular, production-ready AI chatbot for answering questions about
a resume/portfolio using advanced retrieval and LLM generation.
"""

__version__ = "2.0.0"

from .core import PortfolioChatbot
from .config import settings

__all__ = ['PortfolioChatbot', 'settings']

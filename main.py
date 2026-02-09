#!/usr/bin/env python3
"""
Portfolio Chatbot CLI - Main Entry Point

Command-line interface for the AI-powered portfolio chatbot.
Supports question answering with RAG, memory, and web augmentation.

Usage:
    python main.py "Your question here"

Examples:
    python main.py "What are your technical skills?"
    python main.py "Tell me about your projects"
    python main.py "Explain your most recent project"
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src.core import PortfolioChatbot
from src.config import settings
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def print_header():
    """Print application header."""
    print("\n" + "=" * 70)
    print("🤖 RESUME AI ASSISTANT (Groq + Learning RAG + Web Augmentation)")
    print("=" * 70 + "\n")


def print_usage():
    """Print usage instructions."""
    print("\n🤖 Resume-Aware AI Chatbot (with Learning RAG + Groq)")
    print("=" * 60)
    print("\nUsage: python main.py 'Your question here'")
    print("\nExamples:")
    print("  python main.py 'What are your technical skills?'")
    print("  python main.py 'Tell me about your projects'")
    print("  python main.py 'Explain your most recent project'")
    print("\nOptional: Set SEARCHAPI_API_KEY in .env for web augmentation\n")


def print_response(response: str):
    """Print formatted response."""
    print("=" * 70)
    print("💼 RESPONSE")
    print("=" * 70)
    print(f"\n{response}\n")
    print("=" * 70)
    print(f"📝 Stored in memory for future learning")
    print()


def main():
    """Main CLI application."""
    # Validate configuration
    if not settings.validate():
        logger.error("GROQ_API_KEY not found in environment")
        print("\n❌ Error: GROQ_API_KEY not found in environment")
        print("Create a .env file with your Groq API key")
        print("Get key from: https://console.groq.com/keys\n")
        sys.exit(1)
    
    # Check for question argument
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)
    
    # Get question from arguments
    question = ' '.join(sys.argv[1:])
    
    try:
        # Print header
        print_header()
        
        # Initialize chatbot
        chatbot = PortfolioChatbot(
            groq_api_key=settings.GROQ_API_KEY,
            searchapi_key=settings.SEARCHAPI_API_KEY
        )
        
        # Answer question
        response = chatbot.answer_question(question)
        
        # Print response
        print_response(response)
        
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        print(f"\n❌ Error: {e}\n")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"\n❌ Unexpected error: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()

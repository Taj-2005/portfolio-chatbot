"""
Main chatbot orchestration logic.

Coordinates resume loading, context selection, memory management,
and response generation for the portfolio chatbot.
"""

import re
from typing import Dict, Set, Tuple, Optional, List

from ..config import settings
from ..utils.logger import setup_logger
from ..parsers import ResumeLoader, ProjectLoader
from ..memory import MemoryManager
from ..web import WebScraper, SearchAPIClient
from ..rag import ContextSelector, QuestionClassifier
from ..llm import GroqClient
from ..utils.text_processing import categorize_links

logger = setup_logger(__name__)


class PortfolioChatbot:
    """
    Main portfolio chatbot orchestrator.
    
    Coordinates all components to answer questions about a resume/portfolio
    using RAG, memory, and LLM generation.
    """
    
    def __init__(
        self,
        docs_dir: str = None,
        groq_api_key: str = None,
        searchapi_key: str = None
    ):
        """
        Initialize PortfolioChatbot.
        
        Args:
            docs_dir: Directory containing resume files. If None, uses settings.
            groq_api_key: Groq API key. If None, uses settings.
            searchapi_key: SearchAPI key (optional). If None, uses settings.
        """
        logger.info("Initializing PortfolioChatbot")
        
        # Initialize components
        self.resume_loader = ResumeLoader(docs_dir)
        self.project_loader = ProjectLoader(docs_dir)
        self.memory_manager = MemoryManager()
        self.web_scraper = WebScraper()
        self.context_selector = ContextSelector()
        self.classifier = QuestionClassifier()
        
        # Initialize SearchAPI client (optional)
        self.searchapi_client = SearchAPIClient(searchapi_key)
        
        # Initialize Groq client
        try:
            self.groq_client = GroqClient(groq_api_key)
        except ValueError as e:
            logger.error(f"Failed to initialize Groq client: {e}")
            raise
        
        # Load resume and project data
        self.sections: Dict[str, str] = {}
        self.links: Set[str] = set()
        self.full_resume: str = ""
        self.web_content: List[Tuple[str, str]] = []
        self.project_data: Optional[Dict] = None
        
        self._load_data()
        
        logger.info("PortfolioChatbot initialization complete")
    
    def _load_data(self) -> None:
        """Load resume, project data, and GitHub content."""
        logger.info("Loading resume and project data")
        
        # Load resume
        self.sections, self.links, self.full_resume = self.resume_loader.load_resume()
        
        if not self.sections or all(not v for v in self.sections.values()):
            logger.error("No resume content loaded")
            raise ValueError("No resume found in docs/ directory")
        
        # Load project data
        self.project_data = self.project_loader.load_project_json()
        if self.project_data and self.project_data.get("linkup"):
            print("[CTX] project.json/projects.json loaded (LinkUp as primary project)")
        elif self.project_data:
            print("[CTX] project.json/projects.json loaded")
        
        # Process GitHub links
        if self.links:
            categorized = categorize_links(self.links)
            if categorized['github']:
                print(f"  → Processing {len(categorized['github'])} GitHub link(s)...")
                self.web_content = self.web_scraper.process_github_links(categorized['github'])
                if self.web_content:
                    print(f"    ✓ Loaded {len(self.web_content)} GitHub source(s)")
        
        print(f"\n✓ Resume loaded and structured")
    
    def _check_memory_for_cached_answer(
        self,
        question: str,
        similar: Optional[Dict]
    ) -> Optional[str]:
        """
        Check if question can be answered from cached memory.
        
        Args:
            question: User's question.
            similar: Similar past question from memory.
        
        Returns:
            Optional[str]: Cached answer if valid, None otherwise.
        """
        if not similar:
            return None
        
        is_easy = self.memory_manager.is_easy_question(question)
        
        if not (is_easy and similar.get('is_easy', False)):
            return None
        
        # Calculate similarity score
        question_words = set(re.findall(r'\w+', question.lower()))
        similar_words = set(re.findall(r'\w+', similar['question'].lower()))
        intersection = question_words & similar_words
        union = question_words | similar_words
        similarity = len(intersection) / len(union) if union else 0.0
        
        cached_answer = similar.get('answer', '')
        
        # Validate cache for project questions
        if self.classifier.is_project_intent_question(question):
            has_linkup = 'linkup' in cached_answer.lower() or 'link-up' in cached_answer.lower()
            if not has_linkup and 'meallogger' in cached_answer.lower():
                logger.info("Cached answer invalid (wrong project) — regenerating")
                print("[MEMORY] Cached answer invalid (wrong project) — regenerating")
                return None
            
            is_valid_cache = (
                similarity > 0.75 and
                cached_answer and
                'not found' not in cached_answer.lower() and
                len(cached_answer.split()) > 5
            )
        else:
            is_valid_cache = (
                similarity > 0.75 and
                cached_answer and
                'not found' not in cached_answer.lower() and
                len(cached_answer.split()) > 5
            )
        
        if is_valid_cache:
            logger.info("Using cached answer from memory")
            print("\n💾 Using cached answer from memory (high similarity match)\n")
            return cached_answer
        
        if similarity > 0.75 and not is_valid_cache:
            print("\n[MEMORY] Cached answer invalid — regenerating")
        
        return None
    
    def answer_question(self, question: str) -> str:
        """
        Answer a question about the resume/portfolio.
        
        Main orchestration method that coordinates all components.
        
        Args:
            question: User's question.
        
        Returns:
            str: Generated answer.
        """
        logger.info(f"Answering question: {question[:100]}...")
        
        # Check memory for similar questions
        similar = self.memory_manager.find_similar_question(question)
        is_easy = self.memory_manager.is_easy_question(question)
        
        if similar:
            similarity_score = "high" if is_easy else "medium"
            print(f"💡 Found similar past question ({similarity_score} similarity)")
            print(f"   Previous: {similar['question'][:60]}...")
            
            if is_easy and similar.get('is_easy', False):
                print(f"   ✓ Reusing previous answer (easy question, memory match)")
        
        # Try to use cached answer
        cached_answer = self._check_memory_for_cached_answer(question, similar)
        if cached_answer:
            # Still store this interaction (updates timestamp)
            relevant_sections = self.classifier.classify_sections(question)
            self.memory_manager.store_interaction(question, cached_answer, relevant_sections)
            return cached_answer
        
        # Select initial context
        initial_context = self.context_selector.select_relevant_context(
            self.sections,
            self.web_content,
            question,
            full_resume=self.full_resume,
            project_data=self.project_data
        )
        
        # Check if web augmentation needed
        should_search, search_query, search_reason = self.web_scraper.should_use_web_augmentation(
            question, initial_context, self.sections, self.links
        )
        
        # Perform web search if needed
        searchapi_content = None
        if should_search and self.searchapi_client.api_key:
            print(f"[SEARCH] SearchAPI fallback triggered (reason: {search_reason})")
            print(f"  → Searching for '{search_query}'...")
            searchapi_content = self.searchapi_client.search(search_query)
            if searchapi_content:
                print(f"    ✓ Found web context ({len(searchapi_content)} chars)")
                print(f"[CTX] github / portfolio")
            else:
                print(f"    ℹ️  No additional web context found")
        elif should_search and not self.searchapi_client.api_key:
            print(f"[SEARCH] Would trigger SearchAPI (reason: {search_reason}) but API key not set")
        
        # Select final context with SearchAPI results
        relevant_context = self.context_selector.select_relevant_context(
            self.sections,
            self.web_content,
            question,
            searchapi_content,
            full_resume=self.full_resume,
            project_data=self.project_data
        )
        
        # Display context info
        relevant_sections = self.classifier.classify_sections(question)
        print(f"\n❓ Question: {question}")
        print(f"🎯 Relevant sections: {', '.join(relevant_sections)}")
        print(f"📊 Context size: {len(relevant_context)} chars")
        
        # Generate response
        if similar:
            print("\n🤔 Generating response (refining from memory)...\n")
        else:
            print("\n🤔 Generating response...\n")
        
        response = self.groq_client.generate_response(
            question,
            relevant_context,
            use_memory=similar
        )
        
        # Store in memory
        self.memory_manager.store_interaction(question, response, relevant_sections)
        
        logger.info(f"Answer generated: {len(response)} chars")
        return response
    
    def get_memory_stats(self) -> Dict:
        """
        Get memory statistics.
        
        Returns:
            Dict: Memory statistics including size and easy question count.
        """
        memory_size = self.memory_manager.get_memory_size()
        easy_count = sum(1 for entry in self.memory_manager.memory if entry.get('is_easy', False))
        
        return {
            'total_entries': memory_size,
            'easy_questions': easy_count,
            'complex_questions': memory_size - easy_count
        }

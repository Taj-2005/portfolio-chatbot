"""
Main chatbot orchestration logic.

Coordinates resume loading, context selection, memory management,
and response generation for the portfolio chatbot.
"""

import re
from typing import Dict, Set, Tuple, Optional, List

from ..config import settings
from ..utils.logger import setup_logger
from ..parsers import ResumeLoader, ProjectLoader, KnowledgeBaseLoader
from ..memory import MemoryManager
from ..web import WebScraper, SearchAPIClient
from ..rag import ContextSelector, QuestionClassifier
from ..llm import GroqClient
from ..utils.text_processing import categorize_links, normalize_query, hash_text
from ..utils.cache import TTLCache, stable_cache_key

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
        self.knowledge_loader = KnowledgeBaseLoader(docs_dir)
        self.memory_manager = MemoryManager()
        self.web_scraper = WebScraper()
        self.context_selector = ContextSelector()
        self.classifier = QuestionClassifier()
        
        # Instance-local TTL caches (high impact for serverless warm instances)
        self._retrieval_cache: TTLCache[str] = TTLCache(max_items=settings.CACHE_MAX_ITEMS)
        self._llm_cache: TTLCache[str] = TTLCache(max_items=settings.CACHE_MAX_ITEMS)

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
        self.kb_text: str = ""
        self.kb_sources: Dict[str, str] = {}
        
        self._load_data()
        
        logger.info("PortfolioChatbot initialization complete")

    def _emit(self, msg: str) -> None:
        """
        Print user-facing debug info in CLI, but keep serverless quiet.
        """
        if not settings.IS_SERVERLESS:
            print(msg)
    
    def _load_data(self) -> None:
        """Load resume, project data, and GitHub content."""
        logger.info("Loading resume and project data")
        
        # Load resume
        self.sections, self.links, self.full_resume = self.resume_loader.load_resume()
        
        if not self.sections or all(not v for v in self.sections.values()):
            logger.error("No resume content loaded")
            raise ValueError("No resume found in knowledge base directory")

        # Load additional knowledge-base docs (e.g. portfolio feature descriptions)
        kb_text, kb_links, kb_sources = self.knowledge_loader.load_knowledge()
        self.kb_text = kb_text
        self.kb_sources = kb_sources
        if kb_links:
            self.links.update(kb_links)

        # Make KB available to the legacy context builder by appending to OTHER.
        # This preserves old behavior while allowing new markdown knowledge to be retrieved.
        if self.kb_text:
            other = (self.sections.get("OTHER") or "").strip()
            combined = (other + "\n\n" + self.kb_text).strip() if other else self.kb_text
            # Keep OTHER bounded to avoid crowding out resume sections.
            self.sections["OTHER"] = combined[:8000]
        
        # Load project data
        self.project_data = self.project_loader.load_project_json()
        if self.project_data and self.project_data.get("linkup"):
            self._emit("[CTX] project.json/projects.json loaded (LinkUp as primary project)")
        elif self.project_data:
            self._emit("[CTX] project.json/projects.json loaded")
        
        # Process GitHub links
        if self.links:
            categorized = categorize_links(self.links)
            if categorized['github']:
                self._emit(f"  → Processing {len(categorized['github'])} GitHub link(s)...")
                self.web_content = self.web_scraper.process_github_links(categorized['github'])
                if self.web_content:
                    self._emit(f"    ✓ Loaded {len(self.web_content)} GitHub source(s)")
        
        self._emit("\n✓ Resume loaded and structured")
    
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

        normalized_q = normalize_query(question) if settings.CACHE_NORMALIZE_QUERIES else question.strip()
        # A lightweight "docs version" key to avoid stale retrieval after content updates.
        # This is not perfect, but it prevents obvious staleness when resume/projects change.
        corpus_fingerprint = hash_text(
            (self.full_resume or "")[:2000] + "|" + (self.project_data.get("text_for_rag", "") if self.project_data else "")
        )
        
        # Check memory for similar questions
        similar = self.memory_manager.find_similar_question(question)
        is_easy = self.memory_manager.is_easy_question(question)
        
        if similar:
            similarity_score = "high" if is_easy else "medium"
            self._emit(f"💡 Found similar past question ({similarity_score} similarity)")
            self._emit(f"   Previous: {similar['question'][:60]}...")
            
            if is_easy and similar.get('is_easy', False):
                self._emit("   ✓ Reusing previous answer (easy question, memory match)")
        
        # Try to use cached answer
        cached_answer = self._check_memory_for_cached_answer(question, similar)
        if cached_answer:
            # Still store this interaction (updates timestamp)
            relevant_sections = self.classifier.classify_sections(question)
            self.memory_manager.store_interaction(question, cached_answer, relevant_sections)
            return cached_answer

        # LLM response cache (context-dependent). We check after retrieval is built below.
        
        # Select initial context
        retrieval_cache_key = stable_cache_key("ctx", settings.RAG_RETRIEVAL_MODE, corpus_fingerprint, normalized_q)
        initial_context = self._retrieval_cache.get(retrieval_cache_key)
        if initial_context is None:
            initial_context = self.context_selector.select_relevant_context(
                self.sections,
                self.web_content,
                question,
                full_resume=self.full_resume,
                project_data=self.project_data
            )
            self._retrieval_cache.set(retrieval_cache_key, initial_context, ttl_seconds=settings.CACHE_TTL_SECONDS_RETRIEVAL)
        
        # Check if web augmentation needed
        should_search, search_query, search_reason = self.web_scraper.should_use_web_augmentation(
            question, initial_context, self.sections, self.links
        )
        
        # Perform web search if needed
        searchapi_content = None
        if should_search and self.searchapi_client.api_key:
            self._emit(f"[SEARCH] SearchAPI fallback triggered (reason: {search_reason})")
            self._emit(f"  → Searching for '{search_query}'...")
            searchapi_content = self.searchapi_client.search(search_query)
            if searchapi_content:
                self._emit(f"    ✓ Found web context ({len(searchapi_content)} chars)")
                self._emit("[CTX] github / portfolio")
            else:
                self._emit("    ℹ️  No additional web context found")
        elif should_search and not self.searchapi_client.api_key:
            self._emit(f"[SEARCH] Would trigger SearchAPI (reason: {search_reason}) but API key not set")
        
        # Select final context with SearchAPI results
        final_ctx_cache_key = stable_cache_key(
            "ctx_final",
            settings.RAG_RETRIEVAL_MODE,
            corpus_fingerprint,
            normalized_q,
            hash_text(searchapi_content or ""),
        )
        relevant_context = self._retrieval_cache.get(final_ctx_cache_key)
        if relevant_context is None:
            relevant_context = self.context_selector.select_relevant_context(
                self.sections,
                self.web_content,
                question,
                searchapi_content,
                full_resume=self.full_resume,
                project_data=self.project_data
            )
            self._retrieval_cache.set(final_ctx_cache_key, relevant_context, ttl_seconds=settings.CACHE_TTL_SECONDS_RETRIEVAL)
        
        # Display context info
        relevant_sections = self.classifier.classify_sections(question)
        self._emit(f"\n❓ Question: {question}")
        self._emit(f"🎯 Relevant sections: {', '.join(relevant_sections)}")
        self._emit(f"📊 Context size: {len(relevant_context)} chars")
        
        # Generate response
        if similar:
            self._emit("\n🤔 Generating response (refining from memory)...\n")
        else:
            self._emit("\n🤔 Generating response...\n")

        llm_cache_key = stable_cache_key(
            "llm",
            normalized_q,
            hash_text(relevant_context),
            settings.LLM_MODEL,
            settings.LLM_TEMPERATURE,
            settings.LLM_MAX_TOKENS,
        )
        cached_llm = self._llm_cache.get(llm_cache_key)
        if cached_llm is not None:
            logger.info("Using cached LLM response (context+question match)")
            response = cached_llm
        else:
            response = self.groq_client.generate_response(
                question,
                relevant_context,
                use_memory=similar
            )
            self._llm_cache.set(llm_cache_key, response, ttl_seconds=settings.CACHE_TTL_SECONDS_LLM)
        
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

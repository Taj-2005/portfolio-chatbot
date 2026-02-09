"""
Context selection for RAG (Retrieval-Augmented Generation).

Selects relevant context from resume, project data, and web sources
based on question intent and content matching.
"""

import re
from typing import Dict, List, Tuple, Optional

from ..config import settings
from ..utils.logger import setup_logger
from .question_classifier import QuestionClassifier

logger = setup_logger(__name__)


class ContextSelector:
    """
    Selects and combines relevant context for answering questions.
    
    Implements intelligent context selection based on question intent,
    prioritizing LinkUp project when appropriate and managing context size limits.
    """
    
    def __init__(self, max_context_size: int = None):
        """
        Initialize ContextSelector.
        
        Args:
            max_context_size: Maximum context length. If None, uses settings value.
        """
        self.max_context_size = max_context_size or settings.MAX_CONTEXT_SIZE
        self.classifier = QuestionClassifier()
        logger.info(f"Initialized ContextSelector with max_context_size={self.max_context_size}")
    
    def _extract_linkup_from_projects(self, projects_section: str) -> str:
        """
        Extract only LinkUp project block from projects section.
        
        Args:
            projects_section: Full PROJECTS section text.
        
        Returns:
            str: LinkUp project text only.
        """
        if not projects_section:
            return ""
        
        # Try to find LinkUp project block
        linkup_match = re.search(
            r'(LinkUp|Link-Up)[^\n]*.*?(?=\n\n(?:[A-Z][a-z]+|MealLogger|Melo|EXPERIENCE|EDUCATION|SKILLS)|\Z)',
            projects_section,
            re.DOTALL | re.IGNORECASE
        )
        
        if linkup_match:
            block = linkup_match.group(0).strip()
            if len(block) > 2000:
                block = block[:2000] + "..."
            logger.debug(f"Extracted LinkUp block: {len(block)} chars")
            return block
        
        return ""
    
    def prioritize_linkup_project(
        self,
        sections: Dict[str, str],
        project_data: Optional[Dict],
        web_content: List[Tuple[str, str]],
        full_resume: str
    ) -> str:
        """
        Build context containing ONLY LinkUp project (no other projects).
        
        Args:
            sections: Resume sections dictionary.
            project_data: Project JSON data.
            web_content: List of (source, content) tuples from web scraping.
            full_resume: Full resume text.
        
        Returns:
            str: Context focused exclusively on LinkUp.
        """
        parts = []
        current_length = 0
        
        # 1) project.json LinkUp entry (if available)
        if project_data and project_data.get("linkup_text"):
            chunk = "--- PROJECT (project.json - LinkUp) ---\n" + project_data["linkup_text"] + "\n"
            if current_length + len(chunk) <= self.max_context_size:
                parts.append(chunk)
                current_length += len(chunk)
                logger.debug("Added LinkUp from project.json")
        
        # 2) Resume PROJECTS section: extract only LinkUp block
        projects_section = sections.get("PROJECTS") or sections.get("OTHER") or ""
        linkup_block = self._extract_linkup_from_projects(projects_section)
        if linkup_block:
            chunk = "--- RESUME (LinkUp) ---\n" + linkup_block + "\n"
            if current_length + len(chunk) <= self.max_context_size:
                parts.append(chunk)
                current_length += len(chunk)
                logger.debug("Added LinkUp from resume")
        
        # 3) Web content that mentions LinkUp
        for source, content in web_content:
            if content and ("linkup" in content.lower() or "link-up" in content.lower()):
                chunk = f"--- {source} ---\n" + content[:800] + "\n"
                if current_length + len(chunk) <= self.max_context_size:
                    parts.append(chunk)
                    current_length += len(chunk)
                    logger.debug(f"Added LinkUp-related web content from {source}")
                break
        
        # Fallback if no LinkUp-specific content found
        if not parts and projects_section:
            trunc = projects_section[:self.max_context_size - 200]
            parts.append("--- RESUME PROJECTS ---\n" + trunc + "\n")
            logger.warning("No LinkUp-specific content, using general projects")
        
        result = "\n".join(parts) if parts else ""
        logger.info(f"Built LinkUp-only context: {len(result)} chars")
        return result
    
    def keyword_context_search(
        self,
        keyword: str,
        sections: Dict[str, str],
        full_resume: str,
        project_data: Optional[Dict],
        web_content: List[Tuple[str, str]]
    ) -> str:
        """
        Search for keyword across all sources and build context.
        
        Args:
            keyword: Tech keyword to search for.
            sections: Resume sections dictionary.
            full_resume: Full resume text.
            project_data: Project JSON data.
            web_content: Web scraping results.
        
        Returns:
            str: Context containing keyword matches.
        """
        kw_lower = keyword.lower().strip()
        parts = []
        current_length = 0
        
        def add_chunk(header: str, text: str, cap: int = 1500) -> None:
            nonlocal current_length
            if not text or current_length >= self.max_context_size:
                return
            if kw_lower not in text.lower():
                return
            chunk = f"--- {header} ---\n" + (text[:cap] if len(text) > cap else text) + "\n"
            if current_length + len(chunk) <= self.max_context_size:
                parts.append(chunk)
                current_length += len(chunk)
                logger.debug(f"Added keyword match from {header}")
        
        # Prefer LinkUp if it matches the keyword
        if project_data and project_data.get("linkup_text"):
            lt = project_data["linkup_text"]
            if kw_lower in lt.lower():
                add_chunk("PROJECT (LinkUp)", lt, 1200)
        
        # project.json all projects
        if project_data and project_data.get("text_for_rag"):
            add_chunk("PROJECTS (project.json)", project_data["text_for_rag"], 2500)
        
        # Resume sections
        for name, content in sections.items():
            if content and kw_lower in content.lower():
                add_chunk(f"RESUME_{name}", content, 1200)
        
        if full_resume and kw_lower in full_resume.lower():
            add_chunk("RESUME", full_resume, 1500)
        
        # Web content
        for source, content in web_content:
            if content and kw_lower in content.lower():
                add_chunk(source, content, 600)
        
        result = "\n".join(parts) if parts else ""
        logger.info(f"Built keyword context for '{keyword}': {len(result)} chars")
        return result
    
    def _rank_context_sources(
        self,
        sections: Dict[str, str],
        web_content: List[Tuple[str, str]],
        searchapi_content: Optional[str]
    ) -> List[Tuple[str, str, int]]:
        """
        Rank context sources by priority.
        
        Args:
            sections: Resume sections.
            web_content: Web scraping results.
            searchapi_content: SearchAPI results.
        
        Returns:
            List of (source_name, content, priority) tuples.
        """
        ranked = []
        
        # Priority 1: Resume sections
        for section_name, content in sections.items():
            if content:
                ranked.append((f"RESUME_{section_name}", content, 1))
        
        # Priority 2: Web content
        for source, content in web_content:
            ranked.append((f"WEB_{source}", content, 2))
        
        # Priority 3: SearchAPI
        if searchapi_content:
            ranked.append(("SEARCHAPI", searchapi_content, 3))
        
        return ranked
    
    def select_relevant_context(
        self,
        sections: Dict[str, str],
        web_content: List[Tuple[str, str]],
        question: str,
        searchapi_content: Optional[str] = None,
        full_resume: str = "",
        project_data: Optional[Dict] = None
    ) -> str:
        """
        Select relevant context based on question intent.
        
        Main RAG logic that orchestrates context selection from multiple sources.
        
        Args:
            sections: Resume sections dictionary.
            web_content: Web scraping results.
            question: User's question.
            searchapi_content: SearchAPI results (optional).
            full_resume: Full resume text.
            project_data: Project JSON data (optional).
        
        Returns:
            str: Selected and combined context for LLM.
        """
        intent = self.classifier.detect_project_intent(question)
        logger.info(f"Detected intent: {intent}")
        
        # 1) LinkUp-only context
        if intent in ("linkup_only", "explicit_linkup"):
            ctx = self.prioritize_linkup_project(sections, project_data, web_content, full_resume)
            if ctx:
                return ctx
            # No LinkUp context found
            return (
                "--- INSTRUCTION ---\n"
                "The user asked about LinkUp or their main/most recent project. "
                "No LinkUp-specific context was found in resume or project.json. "
                "Respond in second person that you do not have LinkUp details in your materials, "
                "and do not mention other projects."
            )
        
        # 2) Keyword-based context
        keyword = self.classifier.extract_keyword_from_question(question)
        if keyword and project_data is not None:
            ctx = self.keyword_context_search(
                keyword, sections, full_resume, project_data, web_content
            )
            if ctx:
                return ctx
        
        # 3) General context selection
        return self._build_general_context(
            sections, web_content, question, searchapi_content,
            full_resume, project_data, intent
        )
    
    def _build_general_context(
        self,
        sections: Dict[str, str],
        web_content: List[Tuple[str, str]],
        question: str,
        searchapi_content: Optional[str],
        full_resume: str,
        project_data: Optional[Dict],
        intent: str
    ) -> str:
        """
        Build general context from multiple sources.
        
        Used when not LinkUp-only or keyword-specific.
        """
        relevant_section_names = self.classifier.classify_sections(question)
        is_project_question = self.classifier.is_project_intent_question(question)
        
        context_parts = []
        current_length = 0
        
        # Prefer project.json LinkUp at top for project questions
        if is_project_question and project_data and project_data.get("linkup_text"):
            chunk = "--- PROJECT (project.json - LinkUp) ---\n" + project_data["linkup_text"] + "\n"
            if len(chunk) <= self.max_context_size:
                context_parts.append(chunk)
                current_length += len(chunk)
                logger.debug("Added LinkUp project data for project question")
        
        # For small resumes, include all sections
        total_resume_size = sum(len(v) for v in sections.values() if v)
        if total_resume_size < 1000:
            relevant_section_names = [k for k, v in sections.items() if v.strip()]
        
        # For project questions, prefer LinkUp block only (no mixing)
        if is_project_question and intent != "keyword":
            projects_section = sections.get('PROJECTS') or sections.get('OTHER') or ''
            linkup_content = self._extract_linkup_from_projects(projects_section)
            
            if linkup_content:
                header = "--- RESUME (LinkUp) ---"
                content_chunk = f"{header}\n{linkup_content}\n"
                if current_length + len(content_chunk) <= self.max_context_size:
                    context_parts.append(content_chunk)
                    current_length += len(content_chunk)
                    # Don't add PROJECTS section again
                    relevant_section_names = [s for s in relevant_section_names if s != 'PROJECTS']
                    logger.debug("Added LinkUp resume block for project question")
        
        # Add relevant sections
        added_sections = []
        for section_name in relevant_section_names:
            section_content = sections.get(section_name, '').strip()
            if section_content and current_length < self.max_context_size:
                header = f"--- {section_name} ---"
                content_chunk = f"{header}\n{section_content}\n"
                
                if current_length + len(content_chunk) <= self.max_context_size:
                    context_parts.append(content_chunk)
                    current_length += len(content_chunk)
                    added_sections.append(section_name)
                else:
                    # Truncate to fit
                    remaining = self.max_context_size - current_length - len(header) - 10
                    if remaining > 100:
                        truncated = section_content[:remaining] + "..."
                        context_parts.append(f"{header}\n{truncated}\n")
                        current_length = self.max_context_size
                        added_sections.append(section_name)
                        break
        
        # Fallback: add some sections if nothing added yet
        if not added_sections and current_length < 500:
            for fallback_section in ['SUMMARY', 'SKILLS', 'EXPERIENCE', 'PROJECTS', 'EDUCATION', 'OTHER']:
                section_content = sections.get(fallback_section, '').strip()
                if section_content and current_length < self.max_context_size:
                    header = f"--- {fallback_section} ---"
                    truncated_content = section_content[:1500] if len(section_content) > 1500 else section_content
                    content_chunk = f"{header}\n{truncated_content}\n"
                    
                    if current_length + len(content_chunk) <= self.max_context_size:
                        context_parts.append(content_chunk)
                        current_length += len(content_chunk)
                        added_sections.append(fallback_section)
                    else:
                        remaining = self.max_context_size - current_length - len(header) - 10
                        if remaining > 200:
                            truncated = section_content[:remaining] + "..."
                            context_parts.append(f"{header}\n{truncated}\n")
                            added_sections.append(fallback_section)
                            break
        
        # Last resort: use full resume
        if not context_parts and full_resume and current_length < self.max_context_size:
            truncated_resume = full_resume[:min(self.max_context_size - 100, 3000)]
            context_parts.append(f"--- RESUME CONTENT ---\n{truncated_resume}\n")
            added_sections.append('FULL_RESUME')
            logger.warning("Using full resume as fallback")
        
        # Add web content if space available
        if current_length < self.max_context_size:
            for source, content, priority in self._rank_context_sources(sections, web_content, searchapi_content):
                if priority == 2 and current_length < self.max_context_size:
                    remaining = self.max_context_size - current_length
                    truncated = content[:min(remaining - 50, 500)]
                    if truncated:
                        context_parts.append(f"--- {source} ---\n{truncated}\n")
                        current_length += len(truncated) + 50
        
        # Add SearchAPI if space available
        if current_length < self.max_context_size and searchapi_content:
            remaining = self.max_context_size - current_length
            truncated = searchapi_content[:min(remaining - 50, 300)]
            if truncated:
                context_parts.append(f"--- Web Search ---\n{truncated}\n")
        
        result = '\n'.join(context_parts)
        logger.info(f"Built general context: {len(result)} chars, sections={added_sections}")
        return result

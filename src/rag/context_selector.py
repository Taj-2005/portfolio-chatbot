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
from .bm25_retriever import BM25Retriever, build_chunks_from_sources

logger = setup_logger(__name__)


class ContextSelector:
    """
    Selects and combines relevant context for answering questions.
    
    Implements intelligent context selection based on question intent,
    prioritizing the configured featured project when appropriate and managing
    context size limits.
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
    
    @staticmethod
    def _featured_label(project_data: Optional[Dict]) -> str:
        """
        Human-readable name of the featured project, for context headers and logs.

        Falls back to the first configured alias when project.json has no match.
        """
        if project_data and isinstance(project_data.get("featured"), dict):
            title = (project_data["featured"].get("title") or "").strip()
            if title:
                return title
        return settings.FEATURED_PROJECT_NAMES[0] if settings.FEATURED_PROJECT_NAMES else "featured project"

    def _mentions_featured(self, text: str) -> bool:
        """Check whether text mentions the featured project under any configured alias."""
        if not text:
            return False
        low = text.lower()
        return any(name in low for name in settings.FEATURED_PROJECT_NAMES)

    def _extract_featured_from_projects(self, projects_section: str) -> str:
        """
        Extract only the featured project's block from a projects section.

        Args:
            projects_section: Full PROJECTS section text.

        Returns:
            str: Featured project text only.
        """
        if not projects_section or not settings.FEATURED_PROJECT_NAMES:
            return ""

        # Build the name alternation from configuration so the featured project can
        # change without touching this code.
        alias_pattern = "|".join(re.escape(n) for n in settings.FEATURED_PROJECT_NAMES)
        match = re.search(
            rf'({alias_pattern})[^\n]*.*?(?=\n\n(?:[A-Z][a-z]+|EXPERIENCE|EDUCATION|SKILLS|INTERNSHIPS)|\Z)',
            projects_section,
            re.DOTALL | re.IGNORECASE
        )

        if match:
            block = match.group(0).strip()
            if len(block) > 2000:
                block = block[:2000] + "..."
            logger.debug(f"Extracted featured project block: {len(block)} chars")
            return block

        return ""

    def prioritize_featured_project(
        self,
        sections: Dict[str, str],
        project_data: Optional[Dict],
        web_content: List[Tuple[str, str]],
        full_resume: str
    ) -> str:
        """
        Build context containing ONLY the featured project (no other projects).

        Args:
            sections: Resume sections dictionary.
            project_data: Project JSON data.
            web_content: List of (source, content) tuples from web scraping.
            full_resume: Full resume text.

        Returns:
            str: Context focused exclusively on the featured project.
        """
        parts = []
        current_length = 0
        label = self._featured_label(project_data)

        # 1) projects.json featured entry (if available)
        if project_data and project_data.get("featured_text"):
            chunk = f"--- PROJECT (projects.json - {label}) ---\n" + project_data["featured_text"] + "\n"
            if current_length + len(chunk) <= self.max_context_size:
                parts.append(chunk)
                current_length += len(chunk)
                logger.debug("Added featured project from projects.json")

        # 2) Resume PROJECTS section: extract only the featured block
        projects_section = sections.get("PROJECTS") or sections.get("OTHER") or ""
        featured_block = self._extract_featured_from_projects(projects_section)
        if featured_block:
            chunk = f"--- RESUME ({label}) ---\n" + featured_block + "\n"
            if current_length + len(chunk) <= self.max_context_size:
                parts.append(chunk)
                current_length += len(chunk)
                logger.debug("Added featured project from resume")

        # 3) Web content that mentions the featured project
        for source, content in web_content:
            if self._mentions_featured(content):
                chunk = f"--- {source} ---\n" + content[:800] + "\n"
                if current_length + len(chunk) <= self.max_context_size:
                    parts.append(chunk)
                    current_length += len(chunk)
                    logger.debug(f"Added featured-project web content from {source}")
                break

        # Fallback if no featured-specific content found
        if not parts and projects_section:
            trunc = projects_section[:self.max_context_size - 200]
            parts.append("--- RESUME PROJECTS ---\n" + trunc + "\n")
            logger.warning("No featured-project content, using general projects")

        result = "\n".join(parts) if parts else ""
        logger.info(f"Built featured-project context: {len(result)} chars")
        return result
    
    @staticmethod
    def _projects_named_in(question: str, project_data: Optional[Dict]) -> List[Dict]:
        """
        Find projects the question names explicitly (by title or slug).

        Without this, a question like "tell me about ShopSmart" falls through to generic
        section selection and the project itself never reaches the model.
        """
        if not project_data:
            return []

        q = question.lower()
        hits = []
        for entry in project_data.get("entries", []):
            aliases = {
                (entry.get("title") or "").strip().lower(),
                (entry.get("slug") or "").strip().lower().replace("-", " "),
            }
            for alias in aliases:
                # Short aliases produce false positives; word boundaries stop "melo"
                # matching inside unrelated words.
                if len(alias) >= 4 and re.search(rf"\b{re.escape(alias)}\b", q):
                    hits.append(entry)
                    break

        if hits:
            logger.info(f"Question names projects: {[h.get('title') for h in hits]}")
        return hits

    def _build_named_projects_context(self, named: List[Dict]) -> str:
        """Build context from the specific projects a question named."""
        parts = []
        current_length = 0

        for entry in named:
            title = entry.get("title") or "PROJECT"
            chunk = f"--- PROJECT ({title}) ---\n{entry.get('text', '')}\n"
            if current_length + len(chunk) > self.max_context_size:
                break
            parts.append(chunk)
            current_length += len(chunk)

        result = "\n".join(parts)
        logger.info(f"Built named-project context: {len(result)} chars")
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
        
        # Prefer the featured project if it matches the keyword
        if project_data and project_data.get("featured_text"):
            ft = project_data["featured_text"]
            if kw_lower in ft.lower():
                add_chunk(f"PROJECT ({self._featured_label(project_data)})", ft, 1200)

        # projects.json all projects
        if project_data and project_data.get("text_for_rag"):
            add_chunk("PROJECTS (projects.json)", project_data["text_for_rag"], 2500)
        
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
        
        # 1) Featured-project-only context
        if intent in ("featured_only", "explicit_featured"):
            ctx = self.prioritize_featured_project(sections, project_data, web_content, full_resume)
            if ctx:
                return ctx
            # No featured-project context found
            label = self._featured_label(project_data)
            return (
                "--- INSTRUCTION ---\n"
                f"The user asked about {label} or their main/most recent project. "
                f"No {label}-specific context was found in the resume or projects.json. "
                f"Say in the first person that you do not have {label} details in your materials, "
                "and do not mention other projects."
            )

        # 1.2) A question that names specific projects is answered from those projects,
        # plus the resume block for grounding. This covers every project, not just the
        # featured one.
        named = self._projects_named_in(question, project_data)
        if named:
            ctx = self._build_named_projects_context(named)
            if ctx:
                projects_section = (sections.get("PROJECTS") or "").strip()
                if projects_section and len(ctx) + len(projects_section) < self.max_context_size:
                    ctx += f"\n--- RESUME PROJECTS ---\n{projects_section}\n"
                return ctx

        # 1.5) Optional BM25 retrieval (opt-in)
        # This stays purely lexical (no embeddings/vector DB) to align with project docs by default.
        if settings.RAG_RETRIEVAL_MODE == "bm25":
            return self._build_bm25_context(
                sections=sections,
                web_content=web_content,
                question=question,
                searchapi_content=searchapi_content,
                project_data=project_data,
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

    def _compress_for_question(self, text: str, question: str, max_chars: int) -> str:
        """
        Context compression for small corpora.

        Keeps sentences that contain query terms to reduce noise and hallucinations
        while preserving factual grounding. This is intentionally simple and fast.
        """
        if not text:
            return ""
        if len(text) <= max_chars:
            return text

        q_terms = set(re.findall(r"[a-z0-9]+", question.lower()))
        # Split on sentence-ish boundaries
        sentences = re.split(r"(?<=[\.\!\?])\s+|\n{2,}", text)
        kept = []
        for s in sentences:
            st = s.strip()
            if not st:
                continue
            st_terms = set(re.findall(r"[a-z0-9]+", st.lower()))
            if q_terms & st_terms:
                kept.append(st)
            if sum(len(x) for x in kept) >= max_chars:
                break

        # Fallback: just truncate if nothing matched
        if not kept:
            return text[:max_chars] + "..."

        joined = "\n".join(kept)
        return joined[:max_chars] + ("..." if len(joined) > max_chars else "")

    def _build_bm25_context(
        self,
        sections: Dict[str, str],
        web_content: List[Tuple[str, str]],
        question: str,
        searchapi_content: Optional[str],
        project_data: Optional[Dict],
    ) -> str:
        """
        Build context via BM25 top-k chunks over all sources.

        This improves recall over simple keyword matching while keeping behavior
        explainable and aligned with the project's "no embeddings by default" docs.
        """
        chunks = build_chunks_from_sources(
            sections=sections,
            project_data=project_data,
            web_content=web_content,
            searchapi_content=searchapi_content,
        )
        if not chunks:
            return ""

        retriever = BM25Retriever(chunks)
        top = retriever.top_k(question, k=settings.RAG_BM25_TOP_K)
        if not top:
            # If BM25 found nothing, fall back to the legacy general context.
            return self._build_general_context(
                sections=sections,
                web_content=web_content,
                question=question,
                searchapi_content=searchapi_content,
                full_resume="",
                project_data=project_data,
                intent="general",
            )

        # Deterministic rerank option (no extra calls)
        ranked_chunks = [c for (c, _s) in top]
        if settings.RAG_RERANK_MODE == "overlap":
            q_terms = set(re.findall(r"[a-z0-9]+", question.lower()))

            def overlap_score(txt: str) -> int:
                return len(q_terms & set(re.findall(r"[a-z0-9]+", (txt or "").lower())))

            ranked_chunks = sorted(ranked_chunks, key=lambda c: overlap_score(c.text), reverse=True)

        context_parts = []
        current_length = 0
        max_chunks = max(1, settings.RAG_FINAL_CONTEXT_CHUNKS)

        for chunk in ranked_chunks[:max_chunks]:
            remaining = self.max_context_size - current_length
            if remaining <= 200:
                break

            text = chunk.text
            # Compression is opt-in and capped per-chunk to keep diversity.
            if settings.RAG_ENABLE_CONTEXT_COMPRESSION:
                text = self._compress_for_question(text, question, max_chars=min(1200, remaining - 80))
            else:
                text = text[: min(len(text), remaining - 80)]

            formatted = f"--- {chunk.source} ---\n{text}\n"
            if current_length + len(formatted) > self.max_context_size:
                formatted = formatted[: max(0, remaining)]  # last-ditch cap
            context_parts.append(formatted)
            current_length += len(formatted)

        result = "\n".join(context_parts).strip()
        logger.info(f"Built BM25 context: {len(result)} chars, chunks={len(context_parts)}")
        return result
    
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
        
        Used when not featured-project-only or keyword-specific.
        """
        relevant_section_names = self.classifier.classify_sections(question)
        is_project_question = self.classifier.is_project_intent_question(question)
        label = self._featured_label(project_data)

        context_parts = []
        current_length = 0

        # Prefer the featured project from projects.json at the top for project questions
        if is_project_question and project_data and project_data.get("featured_text"):
            chunk = f"--- PROJECT (projects.json - {label}) ---\n" + project_data["featured_text"] + "\n"
            if len(chunk) <= self.max_context_size:
                context_parts.append(chunk)
                current_length += len(chunk)
                logger.debug("Added featured project data for project question")

        # For small resumes, include all sections
        total_resume_size = sum(len(v) for v in sections.values() if v)
        if total_resume_size < 1000:
            relevant_section_names = [k for k, v in sections.items() if v.strip()]

        # For project questions, prefer the featured block only (no mixing)
        if is_project_question and intent != "keyword":
            projects_section = sections.get('PROJECTS') or sections.get('OTHER') or ''
            featured_content = self._extract_featured_from_projects(projects_section)

            if featured_content:
                header = f"--- RESUME ({label}) ---"
                content_chunk = f"{header}\n{featured_content}\n"
                if current_length + len(content_chunk) <= self.max_context_size:
                    context_parts.append(content_chunk)
                    current_length += len(content_chunk)
                    # Don't add PROJECTS section again
                    relevant_section_names = [s for s in relevant_section_names if s != 'PROJECTS']
                    logger.debug("Added featured resume block for project question")
        
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

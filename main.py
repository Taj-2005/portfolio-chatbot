#!/usr/bin/env python3
"""
Professional Resume-Aware AI Chatbot with Learning RAG and Web Augmentation

Features:
- LaTeX-aware resume parsing
- Intelligent context filtering
- Controlled web augmentation (SearchAPI.io)
- Learning RAG behavior (memory-based)
- Free-tier deployment ready

Built for recruiters, interviewers, clients, and hackathon judges.
"""

import os
import sys
import re
import json
import hashlib
from pathlib import Path
from typing import List, Tuple, Dict, Set, Optional
from urllib.parse import urlparse
from datetime import datetime
from dotenv import load_dotenv

# Groq API
try:
    from groq import Groq
except ImportError:
    Groq = None

# Document parsing
try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

try:
    from docx import Document
except ImportError:
    Document = None

# Web scraping
try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    requests = None
    BeautifulSoup = None


# ==================== CONFIGURATION ====================

MEMORY_FILE = Path("memory.json")
MAX_CONTEXT_SIZE = 6000  # Increased for full resume content
MAX_RESPONSE_WORDS = 120
SEARCHAPI_FREE_TIER_LIMIT = 100  # requests/month


# ==================== LATEX TEXT CLEANING ====================

def clean_latex_text(text: str) -> str:
    """Clean LaTeX artifacts from resume text while preserving semantic structure."""
    if not text:
        return ""
    
    # Extract URLs from \href{url}{text} before removing LaTeX
    href_pattern = r'\\href\{([^}]+)\}\{([^}]+)\}'
    hrefs = re.findall(href_pattern, text)
    for url, link_text in hrefs:
        text = text.replace(f'\\href{{{url}}}{{{link_text}}}', f'{link_text} ({url})')
    
    # Remove common LaTeX commands
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
    
    # Remove remaining LaTeX backslashes and braces
    text = re.sub(r'\\[a-zA-Z]+\*?', '', text)
    text = re.sub(r'[{}]', '', text)
    text = re.sub(r'\\', '', text)
    
    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\s*\n\s*', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Remove PDF artifacts
    text = re.sub(r'Page \d+ of \d+', '', text)
    text = re.sub(r'^\d+\s*$', '', text, flags=re.MULTILINE)
    
    return text.strip()


# ==================== SECTION-BASED EXTRACTION ====================

def extract_resume_sections(text: str) -> Dict[str, str]:
    """Extract structured sections from resume text."""
    sections = {
        'EXPERIENCE': '',
        'PROJECTS': '',
        'SKILLS': '',
        'EDUCATION': '',
        'SUMMARY': '',
        'OTHER': ''
    }
    
    patterns = {
        'EXPERIENCE': r'(?i)(professional\s+)?experience|work\s+history|employment',
        'PROJECTS': r'(?i)projects?|portfolio',
        'SKILLS': r'(?i)(technical\s+)?skills?|technologies|expertise',
        'EDUCATION': r'(?i)education|academic|qualifications',
        'SUMMARY': r'(?i)summary|about|profile|objective',
    }
    
    lines = text.split('\n')
    current_section = 'OTHER'
    section_content = []
    
    for line in lines:
        line_stripped = line.strip()
        is_header = False
        
        for section_name, pattern in patterns.items():
            if re.match(pattern, line_stripped) and len(line_stripped) < 50:
                if section_content:
                    sections[current_section] += '\n'.join(section_content) + '\n\n'
                current_section = section_name
                section_content = []
                is_header = True
                break
        
        if not is_header and line_stripped:
            section_content.append(line)
    
    if section_content:
        sections[current_section] += '\n'.join(section_content)
    
    for key in sections:
        sections[key] = sections[key].strip()
    
    return sections


# ==================== QUESTION CLASSIFICATION ====================

def is_project_intent_question(question: str) -> bool:
    """
    Detect if question is asking about projects (especially "most recent" or "main" project).
    
    Returns True for questions like:
    - "Walk me through your most recent project"
    - "Tell me about your projects"
    - "What have you built?"
    - "Describe a project you're proud of"
    """
    question_lower = question.lower()
    
    project_intent_patterns = [
        r'walk\s+me\s+through.*project',
        r'tell\s+me\s+about.*project',
        r'describe.*project',
        r'what.*project',
        r'most\s+recent\s+project',
        r'latest\s+project',
        r'main\s+project',
        r'best\s+project',
        r'biggest\s+project',
        r'what.*built',
        r'what.*developed',
        r'what.*created',
        r'show\s+me.*project',
        r'portfolio\s+project',
    ]
    
    for pattern in project_intent_patterns:
        if re.search(pattern, question_lower):
            return True
    
    return False


def classify_question(question: str) -> List[str]:
    """Classify question to determine relevant resume sections."""
    question_lower = question.lower()
    relevant_sections = []
    
    if any(kw in question_lower for kw in ['project', 'built', 'developed', 'created', 'github', 'portfolio']):
        relevant_sections.append('PROJECTS')
    
    if any(kw in question_lower for kw in ['skill', 'technology', 'language', 'framework', 'tool', 'stack', 'know', 'expertise']):
        relevant_sections.append('SKILLS')
    
    if any(kw in question_lower for kw in ['experience', 'work', 'job', 'role', 'position', 'company', 'hired']):
        relevant_sections.append('EXPERIENCE')
    
    if any(kw in question_lower for kw in ['education', 'degree', 'university', 'study', 'graduate', 'academic']):
        relevant_sections.append('EDUCATION')
    
    if any(kw in question_lower for kw in ['about', 'yourself', 'who', 'background', 'summary', 'overview']):
        relevant_sections.extend(['SUMMARY', 'EXPERIENCE', 'SKILLS'])
    
    if not relevant_sections:
        relevant_sections = ['SUMMARY', 'EXPERIENCE', 'SKILLS', 'PROJECTS']
    
    seen = set()
    return [x for x in relevant_sections if not (x in seen or seen.add(x))]


# ==================== LEARNING RAG MEMORY ====================

def load_memory() -> List[Dict]:
    """Load interaction memory from JSON file."""
    if MEMORY_FILE.exists():
        try:
            with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_memory(memory: List[Dict]):
    """Save interaction memory to JSON file."""
    try:
        with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(memory, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️  Warning: Could not save memory: {e}")


def hash_question(question: str) -> str:
    """Create a hash of the question for similarity matching."""
    normalized = question.lower().strip()
    return hashlib.md5(normalized.encode()).hexdigest()


def is_easy_question(question: str) -> bool:
    """
    Detect easy/repetitive questions that benefit from memory-based learning.
    
    Examples: "Tell me about yourself", "What skills do you have?", 
    "Summarize your resume", "What tech stack do you use?"
    """
    question_lower = question.lower().strip()
    
    # Easy question patterns
    easy_patterns = [
        r'^(tell me about|what are|describe|summarize|give me|show me)',
        r'(yourself|your skills|your experience|your background|your resume)',
        r'(what tech|what stack|what languages|what technologies)',
        r'^(who are you|introduce yourself|walk me through)',
    ]
    
    for pattern in easy_patterns:
        if re.search(pattern, question_lower):
            return True
    
    return False


def find_similar_question(question: str, memory: List[Dict], threshold: float = 0.7) -> Optional[Dict]:
    """
    Find similar past questions using simple keyword overlap.
    
    Prioritizes easy questions and lowers threshold for them.
    Returns matching memory entry if similarity > threshold.
    """
    question_words = set(re.findall(r'\w+', question.lower()))
    is_easy = is_easy_question(question)
    
    # Lower threshold for easy questions (more likely to match)
    effective_threshold = 0.6 if is_easy else threshold
    
    best_match = None
    best_score = 0.0
    
    for entry in memory:
        past_question = entry.get('question', '')
        past_words = set(re.findall(r'\w+', past_question.lower()))
        
        if not past_words:
            continue
        
        # Simple Jaccard similarity
        intersection = question_words & past_words
        union = question_words | past_words
        similarity = len(intersection) / len(union) if union else 0.0
        
        # Prioritize easy questions in memory
        if is_easy and is_easy_question(past_question):
            similarity += 0.1  # Boost similarity for easy questions
        
        if similarity > best_score and similarity >= effective_threshold:
            best_score = similarity
            best_match = entry
    
    return best_match


def store_interaction(question: str, answer: str, sections_used: List[str], memory: List[Dict]):
    """
    Store interaction in memory for learning.
    
    Prioritizes easy questions - keeps them at the end for faster retrieval.
    """
    entry = {
        'question': question,
        'answer': answer,
        'sections_used': sections_used,
        'timestamp': datetime.now().isoformat(),
        'question_hash': hash_question(question),
        'is_easy': is_easy_question(question)  # Tag for prioritization
    }
    
    is_easy = is_easy_question(question)
    
    # Add to memory
    if is_easy:
        # Easy questions go at the end (checked first in retrieval)
        memory.append(entry)
    else:
        # Regular questions go before easy ones
        # Insert before last easy question if exists
        last_easy_idx = None
        for i in range(len(memory) - 1, -1, -1):
            if memory[i].get('is_easy', False):
                last_easy_idx = i
                break
        
        if last_easy_idx is not None:
            memory.insert(last_easy_idx, entry)
        else:
            memory.append(entry)
    
    # Keep only last 100 interactions to prevent file bloat
    if len(memory) > 100:
        memory = memory[-100:]
    
    save_memory(memory)


# ==================== WEB AUGMENTATION (SEARCHAPI.IO) ====================

def fetch_searchapi_context(query: str, api_key: str) -> Optional[str]:
    """
    Fetch web context using SearchAPI.io (free tier).
    
    Only searches for:
    - GitHub repo names
    - Portfolio project titles
    - User's blog posts
    
    Returns None if search fails or quota exceeded.
    """
    if not api_key or not requests:
        return None
    
    try:
        # SearchAPI.io Google Search API endpoint
        url = "https://www.searchapi.io/api/v1/search"
        
        params = {
            'engine': 'google',
            'q': query,
            'api_key': api_key,
            'num': 3  # Limit to 3 results
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('organic_results', [])
            
            if results:
                # Extract only titles and snippets (no full content)
                context_parts = []
                for result in results[:2]:  # Top 2 results only
                    title = result.get('title', '')
                    snippet = result.get('snippet', '')
                    if title and snippet:
                        context_parts.append(f"{title}: {snippet[:200]}")
                
                return "\n".join(context_parts) if context_parts else None
        
        elif response.status_code == 429:
            print("  ⚠️  SearchAPI quota exceeded (free tier limit)")
            return None
        
    except Exception as e:
        # Fail silently - web augmentation is optional
        pass
    
    return None


# Alias for backward compatibility
fetch_web_context_searchapi = fetch_searchapi_context


def should_use_web_augmentation(question: str, context: str, sections: Dict[str, str], links: Set[str]) -> Tuple[bool, str, str]:
    """
    Determine if web augmentation is needed.
    
    Returns: (should_search, search_query, reason)
    Triggers SearchAPI when:
    - Context is insufficient (< 800 chars)
    - Question asks for specific project/repo details
    - Interview questions need enrichment
    """
    context_length = len(context)
    question_lower = question.lower()
    
    # Always try SearchAPI if context is too small
    if context_length < 800:
        # Try to extract project names or GitHub repos
        projects = sections.get('PROJECTS', '')
        if projects:
            # Extract first project name
            lines = [l.strip() for l in projects.split('\n') if l.strip()]
            for line in lines[:5]:
                if 10 < len(line) < 60 and not line.startswith('-'):
                    return True, f"{line[:40]} github", "resume insufficient"
        
        # Try GitHub links from resume
        for link in links:
            if 'github.com' in link:
                # Extract username/repo
                match = re.search(r'github\.com/([\w\-]+/[\w\-]+)', link)
                if match:
                    return True, f"{match.group(1)}", "resume insufficient"
        
        return True, "portfolio projects", "resume insufficient"
    
    # Check if question asks for specific project/repo
    if 'github' in question_lower or 'repo' in question_lower or 'project' in question_lower:
        projects = sections.get('PROJECTS', '')
        if projects:
            lines = projects.split('\n')[:3]
            for line in lines:
                if len(line) > 10 and len(line) < 50:
                    return True, f"{line.strip()} project details", "project-specific question"
    
    # Don't search for generic tech explanations
    if any(kw in question_lower for kw in ['what is', 'explain', 'how does', 'define']):
        return False, "", ""
    
    return False, "", ""


# ==================== CONTEXT RANKING & SELECTION ====================

def rank_context_sources(
    sections: Dict[str, str],
    web_content: List[Tuple[str, str]],
    searchapi_content: Optional[str]
) -> List[Tuple[str, str, int]]:
    """
    Rank context sources by priority.
    
    Priority order:
    1. Resume sections (highest)
    2. Portfolio/GitHub (medium)
    3. SearchAPI (lowest, last resort)
    
    Returns: List of (source_name, content, priority)
    """
    ranked = []
    
    # Priority 1: Resume sections
    for section_name, content in sections.items():
        if content:
            ranked.append((f"RESUME_{section_name}", content, 1))
    
    # Priority 2: Portfolio/GitHub
    for source, content in web_content:
        ranked.append((f"WEB_{source}", content, 2))
    
    # Priority 3: SearchAPI (lowest)
    if searchapi_content:
        ranked.append(("SEARCHAPI", searchapi_content, 3))
    
    return ranked


def select_relevant_context(
    sections: Dict[str, str],
    web_content: List[Tuple[str, str]],
    question: str,
    searchapi_content: Optional[str] = None,
    full_resume: str = "",
    max_length: int = MAX_CONTEXT_SIZE
) -> str:
    """
    Select and rank relevant context - prioritizes resume content.
    
    For project-intent questions, prioritizes LinkUp project content.
    """
    relevant_section_names = classify_question(question)
    is_project_question = is_project_intent_question(question)
    
    # Rank all sources
    ranked_sources = rank_context_sources(sections, web_content, searchapi_content)
    
    context_parts = []
    current_length = 0
    
    # Calculate total resume content size
    total_resume_size = sum(len(v) for v in sections.values() if v)
    
    # If resume is small or sections are empty, include more sections
    if total_resume_size < 1000:
        # Include all non-empty sections
        relevant_section_names = [k for k, v in sections.items() if v.strip()]
    
    # PRIORITY: For project-intent questions, extract and prioritize LinkUp content
    linkup_content = None
    if is_project_question:
        # Search in PROJECTS section first, then OTHER section (fallback)
        projects_section = sections.get('PROJECTS', '') or sections.get('OTHER', '')
        if projects_section:
            # Try to extract LinkUp-specific content (look for LinkUp title/heading)
            linkup_match = re.search(
                r'(LinkUp|Link-Up)[^\n]*.*?(?=\n\n(?:[A-Z][a-z]+|MealLogger|Melo|EXPERIENCE|EDUCATION|SKILLS)|\Z)',
                projects_section,
                re.DOTALL | re.IGNORECASE
            )
            if linkup_match:
                linkup_content = linkup_match.group(0).strip()
                # Limit to reasonable length (first 1500 chars)
                if len(linkup_content) > 1500:
                    linkup_content = linkup_content[:1500] + "..."
                print("[PROJECT] Prioritizing LinkUp as primary project")
                # Add LinkUp content first
                header = "--- PROJECTS (LinkUp - PRIMARY) ---"
                content_chunk = f"{header}\n{linkup_content}\n"
                if len(content_chunk) <= max_length:
                    context_parts.append(content_chunk)
                    current_length += len(content_chunk)
                    # Don't add PROJECTS section again to avoid duplication
                    relevant_section_names = [s for s in relevant_section_names if s != 'PROJECTS']
            else:
                # LinkUp not found, log warning
                print("[PROJECT] Warning: LinkUp not found in resume, using available projects")
    
    # Add resume sections first (highest priority) - ensure we get content
    added_sections = []
    for section_name in relevant_section_names:
        section_content = sections.get(section_name, '').strip()
        if section_content and current_length < max_length:
            header = f"--- {section_name} ---"
            content_chunk = f"{header}\n{section_content}\n"
            
            if current_length + len(content_chunk) <= max_length:
                context_parts.append(content_chunk)
                current_length += len(content_chunk)
                added_sections.append(section_name)
            else:
                # Truncate to fit but ensure we include something
                remaining = max_length - current_length - len(header) - 10
                if remaining > 100:
                    truncated = section_content[:remaining] + "..."
                    context_parts.append(f"{header}\n{truncated}\n")
                    current_length = max_length
                    added_sections.append(section_name)
                    break
    
    # If no sections were added and context is too small, include all non-empty sections as fallback
    if not added_sections and current_length < 500:
        # Try all sections in priority order
        for fallback_section in ['SUMMARY', 'SKILLS', 'EXPERIENCE', 'PROJECTS', 'EDUCATION', 'OTHER']:
            section_content = sections.get(fallback_section, '').strip()
            if section_content and current_length < max_length:
                header = f"--- {fallback_section} ---"
                # Include up to 1500 chars per section
                truncated_content = section_content[:1500] if len(section_content) > 1500 else section_content
                content_chunk = f"{header}\n{truncated_content}\n"
                
                if current_length + len(content_chunk) <= max_length:
                    context_parts.append(content_chunk)
                    current_length += len(content_chunk)
                    added_sections.append(fallback_section)
                else:
                    # Truncate to fit
                    remaining = max_length - current_length - len(header) - 10
                    if remaining > 200:
                        truncated = section_content[:remaining] + "..."
                        context_parts.append(f"{header}\n{truncated}\n")
                        added_sections.append(fallback_section)
                        break
    
    # Final fallback: if still no content and we have full resume, use it
    if not context_parts and full_resume and current_length < max_length:
        truncated_resume = full_resume[:min(max_length - 100, 3000)]
        context_parts.append(f"--- RESUME CONTENT ---\n{truncated_resume}\n")
        added_sections.append('FULL_RESUME')
    
    # Add web content only if space remains (lower priority)
    if current_length < max_length:
        for source, content, priority in ranked_sources:
            if priority == 2 and current_length < max_length:  # Portfolio/GitHub
                remaining = max_length - current_length
                truncated = content[:min(remaining - 50, 500)]  # Max 500 chars per source
                if truncated:
                    context_parts.append(f"--- {source} ---\n{truncated}\n")
                    current_length += len(truncated) + 50
    
    # Add SearchAPI content only as last resort (lowest priority)
    if current_length < max_length and searchapi_content:
        remaining = max_length - current_length
        truncated = searchapi_content[:min(remaining - 50, 300)]  # Max 300 chars
        if truncated:
            context_parts.append(f"--- Web Search ---\n{truncated}\n")
    
    return '\n'.join(context_parts)


# ==================== DOCUMENT PARSERS ====================

def extract_text_from_pdf(file_path: Path) -> str:
    """Extract text from PDF resume with LaTeX cleaning."""
    if PdfReader is None:
        return "[PDF parsing unavailable]"
    
    try:
        reader = PdfReader(file_path)
        text_parts = []
        
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text.strip():
                cleaned = clean_latex_text(page_text)
                text_parts.append(cleaned)
        
        return "\n\n".join(text_parts)
    except Exception as e:
        return f"[Error parsing PDF: {str(e)[:100]}]"


def extract_text_from_docx(file_path: Path) -> str:
    """Extract text from Word document resume."""
    if Document is None:
        return "[Word parsing unavailable]"
    
    try:
        doc = Document(file_path)
        paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
        text = "\n".join(paragraphs)
        return clean_latex_text(text)
    except Exception as e:
        return f"[Error parsing Word doc: {str(e)[:100]}]"


def read_text_file(file_path: Path) -> str:
    """Read text-based resume with LaTeX cleaning."""
    for encoding in ['utf-8', 'latin-1', 'cp1252']:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                text = f.read()
                return clean_latex_text(text)
        except (UnicodeDecodeError, LookupError):
            continue
    return "[Error: Unable to decode file]"


# ==================== LINK EXTRACTION ====================

def extract_all_links(text: str) -> Set[str]:
    """Extract all URLs from text content."""
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]\(\)]+'
    urls = re.findall(url_pattern, text)
    
    cleaned = set()
    for url in urls:
        url = url.rstrip('.,;:!?)')
        if url:
            cleaned.add(url)
    
    return cleaned


def categorize_links(urls: Set[str]) -> Dict[str, List[str]]:
    """Categorize URLs by type."""
    categories = {
        'github': [],
        'linkedin': [],
        'portfolio': [],
        'other': []
    }
    
    for url in urls:
        domain = urlparse(url).netloc.lower()
        
        if 'github.com' in domain:
            categories['github'].append(url)
        elif 'linkedin.com' in domain:
            categories['linkedin'].append(url)
        else:
            categories['other'].append(url)
    
    return categories


# ==================== WEB SCRAPING ====================

def scrape_webpage(url: str, timeout: int = 10) -> Tuple[str, str, bool]:
    """Scrape content from webpage with aggressive cleaning."""
    if requests is None or BeautifulSoup is None:
        return "Error", "[Web scraping unavailable]", False
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        response = requests.get(url, timeout=timeout, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'lxml')
        title = soup.title.string if soup.title else "No title"
        
        for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            element.decompose()
        
        text = soup.get_text(separator='\n', strip=True)
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        text = '\n'.join(lines)
        
        if len(text) > 2000:
            text = text[:2000] + "..."
        
        return title, text, True
        
    except Exception:
        return "Error", "", False


def process_github_links(github_urls: List[str]) -> List[Tuple[str, str]]:
    """Process GitHub links with focus on READMEs."""
    results = []
    
    for url in github_urls[:3]:
        parsed = urlparse(url)
        path_parts = [p for p in parsed.path.split('/') if p]
        
        if len(path_parts) >= 2:
            title, content, success = scrape_webpage(url, timeout=15)
            if success and content:
                readme_match = re.search(r'README.*?(?=\n\n|\Z)', content, re.DOTALL | re.IGNORECASE)
                if readme_match:
                    content = readme_match.group(0)[:1000]
                results.append((f"GitHub: {path_parts[0]}/{path_parts[1]}", content))
    
    return results


# ==================== RESUME LOADING ====================

def load_resume(docs_dir: str = "docs") -> Tuple[Dict[str, str], Set[str], str]:
    """
    Load resume and extract structured sections + links.
    
    Returns: (sections, links, full_resume_text)
    """
    docs_path = Path(docs_dir)
    
    if not docs_path.exists():
        return {}, set(), ""
    
    handlers = {
        '.pdf': extract_text_from_pdf,
        '.docx': extract_text_from_docx,
        '.doc': extract_text_from_docx,
        '.txt': read_text_file,
        '.md': read_text_file,
        '.tex': read_text_file,
    }
    
    resume_parts = []
    all_links = set()
    
    print("📄 Loading resume...\n")
    
    for file_path in docs_path.rglob('*'):
        if file_path.is_file():
            ext = file_path.suffix.lower()
            handler = handlers.get(ext)
            
            if handler:
                try:
                    content = handler(file_path)
                    if content and not content.startswith('[Error'):
                        resume_parts.append(content)
                        links = extract_all_links(content)
                        all_links.update(links)
                        print(f"✓ {file_path.name} ({len(content)} chars, {len(links)} links)")
                except Exception as e:
                    print(f"✗ Error: {file_path.name}: {e}")
    
    full_resume = "\n\n".join(resume_parts)
    sections = extract_resume_sections(full_resume)
    
    # Ensure sections have content - if sections are mostly empty, put content in OTHER
    total_section_content = sum(len(v) for v in sections.values() if v)
    if total_section_content < 500 and full_resume:
        # If sections are empty, put full resume in OTHER as fallback
        sections['OTHER'] = full_resume[:5000]  # Limit to 5000 chars
    
    return sections, all_links, full_resume


# ==================== AI RESPONSE GENERATION ====================

def call_groq_llm(
    question: str,
    context: str,
    api_key: str,
    use_memory: Optional[Dict] = None
) -> str:
    """
    Generate concise, high-precision response using Groq API (llama-3.1-8b-instant).
    
    Uses strict prompt template and enforces word limits.
    """
    if Groq is None:
        return "[Error: Groq SDK not installed. Run: pip install groq]"
    
    try:
        client = Groq(api_key=api_key)
        
        # Use memory if available
        memory_hint = ""
        if use_memory:
            memory_hint = f"\nNote: Similar question was asked before. Use this as reference but ensure accuracy: {use_memory.get('answer', '')[:100]}"
        
        # Strict prompt template (inference-friendly)
        system_prompt = """You are a professional resume assistant helping with interview questions.

Answer using the provided resume context (resume.pdf and resume.tex).
If the answer is not explicitly stated, INFER it from resume experience, skills, or projects.
Use GitHub/portfolio context when resume alone is insufficient.
Do NOT say "Not found" for interview-style questions - synthesize from available content.
Only say "Not found in resume." if NO relevant information exists after checking resume, GitHub, and portfolio.

IMPORTANT: For project-related questions, prioritize LinkUp as the primary/most recent project.
Only mention other projects if explicitly asked or if discussing multiple projects.

Be concise, factual, and recruiter-ready.
Limit responses to 120 words in 4-7 bullet points.
For projects: include 1-line summary, tech stack, purpose, and your role - NO config file lists."""
        
        user_message = f"""CONTEXT:
{context}
{memory_hint}

QUESTION: {question}

RESPONSE (concise and direct):"""
        
        # Groq chat completions API
        print("[LLM] Using Groq llama-3.1-8b-instant")
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.2,  # Low temperature for factual responses
            max_tokens=200,  # Strict limit (120 words ≈ 160-180 tokens)
            stream=False
        )
        
        answer = response.choices[0].message.content.strip()
        
        # Enforce length limit (safety check)
        words = answer.split()
        if len(words) > MAX_RESPONSE_WORDS + 20:
            answer = ' '.join(words[:MAX_RESPONSE_WORDS]) + "..."
        
        return answer
        
    except Exception as e:
        error_msg = str(e)
        # Handle rate limits and API errors gracefully
        if "rate_limit" in error_msg.lower() or "429" in error_msg:
            return "[Error: Groq API rate limit exceeded. Please try again later.]"
        elif "401" in error_msg or "unauthorized" in error_msg.lower():
            return "[Error: Invalid Groq API key. Check your GROQ_API_KEY.]"
        else:
            return f"[Error generating response: {error_msg[:200]}]"


# Alias for backward compatibility
generate_response = call_groq_llm


# ==================== MAIN APPLICATION ====================

def main():
    """Main application entry point."""
    
    load_dotenv()
    groq_key = os.getenv('GROQ_API_KEY')
    searchapi_key = os.getenv('SEARCHAPI_API_KEY') or os.getenv('SEARCHAPI_KEY')  # Optional (support both)
    
    if not groq_key:
        print("\n❌ Error: GROQ_API_KEY not found in environment")
        print("Create a .env file with your Groq API key")
        print("Get key from: https://console.groq.com/keys\n")
        sys.exit(1)
    
    if len(sys.argv) < 2:
        print("\n🤖 Resume-Aware AI Chatbot (with Learning RAG + Groq)")
        print("="* 60)
        print("\nUsage: python main.py 'Your question here'")
        print("\nExamples:")
        print("  python main.py 'What are your technical skills?'")
        print("  python main.py 'Tell me about your projects'")
        print("\nOptional: Set SEARCHAPI_API_KEY in .env for web augmentation\n")
        sys.exit(1)
    
    question = ' '.join(sys.argv[1:])
    
    print("\n" + "="*70)
    print("🤖 RESUME AI ASSISTANT (Groq + Learning RAG + Web Augmentation)")
    print("="*70 + "\n")
    
    # Load memory
    memory = load_memory()
    
    # Check for similar past questions (prioritize easy questions)
    similar = find_similar_question(question, memory)
    is_easy = is_easy_question(question)
    
    if similar:
        similarity_score = "high" if is_easy else "medium"
        print(f"💡 Found similar past question ({similarity_score} similarity)")
        print(f"   Previous: {similar['question'][:60]}...")
        
        # For easy questions with high similarity, reuse answer directly
        if is_easy and similar.get('is_easy', False):
            print(f"   ✓ Reusing previous answer (easy question, memory match)")
    
    # Load resume
    sections, links, full_resume = load_resume("docs")
    
    if not sections or all(not v for v in sections.values()):
        print("\n❌ Error: No resume found in docs/ directory\n")
        sys.exit(1)
    
    # Check which resume files were loaded
    resume_files = []
    docs_path = Path("docs")
    if (docs_path / "resume.pdf").exists():
        resume_files.append("resume.pdf")
    if (docs_path / "resume.tex").exists():
        resume_files.append("resume.tex")
    
    if resume_files:
        print(f"[CTX] Primary sources: {' + '.join(resume_files)}")
    else:
        print("[CTX] Warning: resume.pdf or resume.tex not found, using available files")
    
    print(f"\n✓ Resume loaded and structured")
    
    # Process links
    web_content = []
    if links:
        categorized = categorize_links(links)
        if categorized['github']:
            print(f"  → Processing {len(categorized['github'])} GitHub link(s)...")
            web_content = process_github_links(categorized['github'])
            if web_content:
                print(f"    ✓ Loaded {len(web_content)} GitHub source(s)")
    
    # Determine if web augmentation needed
    initial_context = select_relevant_context(sections, web_content, question, full_resume=full_resume)
    should_search, search_query, search_reason = should_use_web_augmentation(question, initial_context, sections, links)
    
    searchapi_content = None
    if should_search and searchapi_key:
        print(f"[SEARCH] SearchAPI fallback triggered (reason: {search_reason})")
        print(f"  → Searching for '{search_query}'...")
        searchapi_content = fetch_web_context_searchapi(search_query, searchapi_key)
        if searchapi_content:
            print(f"    ✓ Found web context ({len(searchapi_content)} chars)")
            print(f"[CTX] github / portfolio")
        else:
            print(f"    ℹ️  No additional web context found")
    elif should_search and not searchapi_key:
        print(f"[SEARCH] Would trigger SearchAPI (reason: {search_reason}) but API key not set")
    
    # Select final context with ranking
    relevant_context = select_relevant_context(
        sections, web_content, question, searchapi_content, full_resume=full_resume
    )
    
    relevant_sections = classify_question(question)
    
    print(f"\n❓ Question: {question}")
    print(f"🎯 Relevant sections: {', '.join(relevant_sections)}")
    print(f"📊 Context size: {len(relevant_context)} chars")
    
    # For easy questions with high similarity, check if cached answer is valid
    response = None
    if is_easy and similar and similar.get('is_easy', False):
        # Calculate similarity score
        question_words = set(re.findall(r'\w+', question.lower()))
        similar_words = set(re.findall(r'\w+', similar['question'].lower()))
        intersection = question_words & similar_words
        union = question_words | similar_words
        similarity = len(intersection) / len(union) if union else 0.0
        
        # Check if cached answer is valid
        cached_answer = similar.get('answer', '')
        
        # For project-intent questions, validate that cached answer mentions LinkUp
        if is_project_intent_question(question):
            has_linkup = 'linkup' in cached_answer.lower() or 'link-up' in cached_answer.lower()
            if not has_linkup and 'meallogger' in cached_answer.lower():
                print("[MEMORY] Cached answer invalid (wrong project) — regenerating")
                is_valid_cache = False
            else:
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
        
        # Reuse if similarity > 0.75 and answer is valid
        if is_valid_cache:
            response = cached_answer
            print("\n💾 Using cached answer from memory (high similarity match)\n")
        else:
            if similarity > 0.75 and not is_valid_cache:
                print("\n[MEMORY] Cached answer invalid — regenerating")
            print("\n🤔 Generating response (refining from memory)...\n")
    else:
        print("\n🤔 Generating response...\n")
    
    # Generate response using Groq API if not using cached answer
    if not response:
        response = call_groq_llm(
            question, relevant_context, groq_key,
            use_memory=similar
        )
    
    # Store interaction in memory
    store_interaction(question, response, relevant_sections, memory)
    
    print("="*70)
    print("💼 RESPONSE")
    print("="*70)
    print(f"\n{response}\n")
    print("="*70)
    print(f"📝 Stored in memory for future learning")
    print()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3

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

try:
    from groq import Groq
except ImportError:
    Groq = None

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

try:
    from docx import Document
except ImportError:
    Document = None

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    requests = None
    BeautifulSoup = None


MEMORY_FILE = Path("memory.json")
MAX_CONTEXT_SIZE = 6000
MAX_RESPONSE_WORDS = 120
SEARCHAPI_FREE_TIER_LIMIT = 100

# Project priority: LinkUp is the primary/most recent project
LINKUP_NAMES = ("linkup", "link-up", "link up")
PROJECT_JSON_NAMES = ("project.json", "projects.json")
KEYWORD_TECH_PATTERNS = (
    "firebase", "react native", "real-time", "realtime", "chat", "auth",
    "next.js", "nextjs", "mongodb", "socket", "typescript", "tailwind",
    "aws", "node", "express", "gemini", "ai", "nodemailer", "shadcn",
)


def clean_latex_text(text: str) -> str:
    if not text:
        return ""
    
    href_pattern = r'\\href\{([^}]+)\}\{([^}]+)\}'
    hrefs = re.findall(href_pattern, text)
    for url, link_text in hrefs:
        text = text.replace(f'\\href{{{url}}}{{{link_text}}}', f'{link_text} ({url})')
    
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
    
    text = re.sub(r'\\[a-zA-Z]+\*?', '', text)
    text = re.sub(r'[{}]', '', text)
    text = re.sub(r'\\', '', text)
    
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\s*\n\s*', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    text = re.sub(r'Page \d+ of \d+', '', text)
    text = re.sub(r'^\d+\s*$', '', text, flags=re.MULTILINE)
    
    return text.strip()


def extract_resume_sections(text: str) -> Dict[str, str]:
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


def is_project_intent_question(question: str) -> bool:
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
        r'explain\s+(your|this)\s+project',
    ]
    
    for pattern in project_intent_patterns:
        if re.search(pattern, question_lower):
            return True
    
    return False


def requires_linkup_only(question: str) -> bool:
    """True if the question must be answered with LinkUp only (no other projects)."""
    q = question.lower().strip()
    patterns = [
        r'explain\s+(your|this)\s+project',
        r'tell\s+me\s+about\s+your\s+project',
        r'most\s+recent\s+project',
        r'main\s+project',
        r'best\s+project',
        r'walk\s+me\s+through\s+(your\s+)?project',
    ]
    for p in patterns:
        if re.search(p, q):
            return True
    return False


def explicit_linkup_mention(question: str) -> bool:
    """True if the user explicitly asked about LinkUp."""
    q = question.lower()
    return any(name in q for name in LINKUP_NAMES)


def detect_project_intent(question: str) -> str:
    """
    Returns: 'linkup_only' | 'explicit_linkup' | 'keyword' | 'general'
    """
    q = question.lower()
    if explicit_linkup_mention(question):
        return 'explicit_linkup'
    if requires_linkup_only(question):
        return 'linkup_only'
    for kw in KEYWORD_TECH_PATTERNS:
        if kw in q:
            return 'keyword'
    if is_project_intent_question(question):
        return 'general'
    return 'general'


def load_project_json(docs_dir: str = "docs") -> Optional[Dict]:
    """
    Load docs/project.json or docs/projects.json.
    Returns dict with keys: 'projects' (list), 'linkup' (dict or None), 'text_for_rag' (str).
    """
    docs_path = Path(docs_dir)
    raw = None
    for name in PROJECT_JSON_NAMES:
        f = docs_path / name
        if f.exists():
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    raw = json.load(fp)
                break
            except Exception:
                raw = None
    if not raw:
        return None
    
    # Normalize: support both { "courses": [...], "prev": [...] } and { "projects": [...] }
    all_entries = []
    if "courses" in raw:
        all_entries.extend(raw["courses"])
    if "prev" in raw:
        all_entries.extend(raw["prev"])
    if "projects" in raw:
        all_entries.extend(raw["projects"])
    
    if not all_entries:
        return None
    
    linkup_entry = None
    for entry in all_entries:
        title = (entry.get("title") or "").strip().lower()
        slug = (entry.get("slug") or "").strip().lower()
        if "linkup" in title or "linkup" in slug or "link-up" in title or "link-up" in slug:
            linkup_entry = entry
            break
    
    def project_to_text(p: Dict) -> str:
        parts = [p.get("title") or "", p.get("description") or ""]
        tech = p.get("tech") or []
        if isinstance(tech, list):
            names = [t.get("name") if isinstance(t, dict) else str(t) for t in tech]
            parts.append("Tech: " + ", ".join(names))
        else:
            parts.append("Tech: " + str(tech))
        return " | ".join(p for p in parts if p)
    
    text_parts = []
    for p in all_entries:
        text_parts.append(project_to_text(p))
    text_for_rag = "\n\n---\n\n".join(text_parts)
    
    return {
        "projects": all_entries,
        "linkup": linkup_entry,
        "text_for_rag": text_for_rag,
        "linkup_text": project_to_text(linkup_entry) if linkup_entry else "",
    }


def prioritize_linkup_project(
    sections: Dict[str, str],
    project_data: Optional[Dict],
    web_content: List[Tuple[str, str]],
    full_resume: str,
    max_length: int = MAX_CONTEXT_SIZE,
) -> str:
    """
    Build context containing ONLY LinkUp (resume + project.json + web).
    Do not include other projects.
    """
    parts = []
    current_length = 0
    
    # 1) project.json LinkUp entry (first-class)
    if project_data and project_data.get("linkup_text"):
        chunk = "--- PROJECT (project.json - LinkUp) ---\n" + project_data["linkup_text"] + "\n"
        if current_length + len(chunk) <= max_length:
            parts.append(chunk)
            current_length += len(chunk)
    
    # 2) Resume PROJECTS section: extract only LinkUp block
    projects_section = (sections.get("PROJECTS") or sections.get("OTHER") or "").strip()
    if projects_section:
        linkup_match = re.search(
            r'(LinkUp|Link-Up)[^\n]*.*?(?=\n\n(?:[A-Z][a-z]+|MealLogger|Melo|EXPERIENCE|EDUCATION|SKILLS)|\Z)',
            projects_section,
            re.DOTALL | re.IGNORECASE
        )
        if linkup_match:
            block = linkup_match.group(0).strip()
            if len(block) > 2000:
                block = block[:2000] + "..."
            chunk = "--- RESUME (LinkUp) ---\n" + block + "\n"
            if current_length + len(chunk) <= max_length:
                parts.append(chunk)
                current_length += len(chunk)
    
    # 3) Web content that mentions LinkUp (if any)
    for source, content in web_content:
        if content and ("linkup" in content.lower() or "link-up" in content.lower()):
            chunk = f"--- {source} ---\n" + content[:800] + "\n"
            if current_length + len(chunk) <= max_length:
                parts.append(chunk)
                current_length += len(chunk)
            break
    
    if not parts:
        # Fallback: full resume PROJECTS section truncated
        if projects_section and current_length < max_length:
            trunc = projects_section[: max_length - 200]
            parts.append("--- RESUME PROJECTS ---\n" + trunc + "\n")
    
    return "\n".join(parts) if parts else ""


def keyword_context_search(
    keyword: str,
    sections: Dict[str, str],
    full_resume: str,
    project_data: Optional[Dict],
    web_content: List[Tuple[str, str]],
    max_length: int = MAX_CONTEXT_SIZE,
) -> str:
    """
    Search for keyword in resume, project.json, web. Prefer LinkUp if keyword matches it.
    Return concatenated matching content.
    """
    kw_lower = keyword.lower().strip()
    parts = []
    current_length = 0
    
    def add_chunk(header: str, text: str, cap: int = 1500) -> None:
        nonlocal current_length
        if not text or current_length >= max_length:
            return
        if kw_lower not in text.lower():
            return
        chunk = f"--- {header} ---\n" + (text[:cap] if len(text) > cap else text) + "\n"
        if current_length + len(chunk) <= max_length:
            parts.append(chunk)
            current_length += len(chunk)
    
    # Prefer LinkUp if it matches the keyword
    if project_data and project_data.get("linkup_text"):
        lt = project_data["linkup_text"]
        if kw_lower in lt.lower():
            add_chunk("PROJECT (LinkUp)", lt, 1200)
    
    # project.json all projects (for keyword match)
    if project_data and project_data.get("text_for_rag"):
        add_chunk("PROJECTS (project.json)", project_data["text_for_rag"], 2500)
    
    # Resume
    for name, content in sections.items():
        if content and kw_lower in content.lower():
            add_chunk(f"RESUME_{name}", content, 1200)
    if full_resume and kw_lower in full_resume.lower():
        add_chunk("RESUME", full_resume, 1500)
    
    # Web
    for source, content in web_content:
        if content and kw_lower in content.lower():
            add_chunk(source, content, 600)
    
    return "\n".join(parts) if parts else ""


def enforce_first_person_voice(response: str) -> str:
    """
    Post-process LLM output to fix common third-person phrasing.
    Replace "you" / "the candidate" / "the developer" with first person where appropriate.
    """
    if not response or len(response) < 10:
        return response
    # Common third-person patterns -> first person
    replacements = [
        (r"\bYou\s+worked\b", "I worked"),
        (r"\byou\s+worked\b", "I worked"),
        (r"\bThe\s+candidate\s+", "I "),
        (r"\bthe\s+candidate\s+", "I "),
        (r"\bThe\s+developer\s+", "I "),
        (r"\bthe\s+developer\s+", "I "),
        (r"\bThis\s+candidate\s+", "I "),
        (r"\bThis\s+developer\s+", "I "),
        (r"\bThey\s+built\b", "I built"),
        (r"\bthey\s+built\b", "I built"),
        (r"\bHe\s+built\b", "I built"),
        (r"\bShe\s+built\b", "I built"),
        (r"\bHe\s+worked\b", "I worked"),
        (r"\bShe\s+worked\b", "I worked"),
    ]
    out = response
    for pat, repl in replacements:
        out = re.sub(pat, repl, out, flags=re.IGNORECASE)
    return out


def classify_question(question: str) -> List[str]:
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


def load_memory() -> List[Dict]:
    if MEMORY_FILE.exists():
        try:
            with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_memory(memory: List[Dict]):
    try:
        with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(memory, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️  Warning: Could not save memory: {e}")


def hash_question(question: str) -> str:
    normalized = question.lower().strip()
    return hashlib.md5(normalized.encode()).hexdigest()


def is_easy_question(question: str) -> bool:
    question_lower = question.lower().strip()
    
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
    question_words = set(re.findall(r'\w+', question.lower()))
    is_easy = is_easy_question(question)
    
    effective_threshold = 0.6 if is_easy else threshold
    
    best_match = None
    best_score = 0.0
    
    for entry in memory:
        past_question = entry.get('question', '')
        past_words = set(re.findall(r'\w+', past_question.lower()))
        
        if not past_words:
            continue
        
        intersection = question_words & past_words
        union = question_words | past_words
        similarity = len(intersection) / len(union) if union else 0.0
        
        if is_easy and is_easy_question(past_question):
            similarity += 0.1
        
        if similarity > best_score and similarity >= effective_threshold:
            best_score = similarity
            best_match = entry
    
    return best_match


def store_interaction(question: str, answer: str, sections_used: List[str], memory: List[Dict]):
    entry = {
        'question': question,
        'answer': answer,
        'sections_used': sections_used,
        'timestamp': datetime.now().isoformat(),
        'question_hash': hash_question(question),
        'is_easy': is_easy_question(question)
    }
    
    is_easy = is_easy_question(question)
    
    if is_easy:
        memory.append(entry)
    else:
        last_easy_idx = None
        for i in range(len(memory) - 1, -1, -1):
            if memory[i].get('is_easy', False):
                last_easy_idx = i
                break
        
        if last_easy_idx is not None:
            memory.insert(last_easy_idx, entry)
        else:
            memory.append(entry)
    
    if len(memory) > 100:
        memory = memory[-100:]
    
    save_memory(memory)


def fetch_searchapi_context(query: str, api_key: str) -> Optional[str]:
    if not api_key or not requests:
        return None
    
    try:
        url = "https://www.searchapi.io/api/v1/search"
        
        params = {
            'engine': 'google',
            'q': query,
            'api_key': api_key,
            'num': 3
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('organic_results', [])
            
            if results:
                context_parts = []
                for result in results[:2]:
                    title = result.get('title', '')
                    snippet = result.get('snippet', '')
                    if title and snippet:
                        context_parts.append(f"{title}: {snippet[:200]}")
                
                return "\n".join(context_parts) if context_parts else None
        
        elif response.status_code == 429:
            print("  ⚠️  SearchAPI quota exceeded (free tier limit)")
            return None
        
    except Exception as e:
        pass
    
    return None


fetch_web_context_searchapi = fetch_searchapi_context


def should_use_web_augmentation(question: str, context: str, sections: Dict[str, str], links: Set[str]) -> Tuple[bool, str, str]:
    context_length = len(context)
    question_lower = question.lower()
    
    if context_length < 800:
        projects = sections.get('PROJECTS', '')
        if projects:
            lines = [l.strip() for l in projects.split('\n') if l.strip()]
            for line in lines[:5]:
                if 10 < len(line) < 60 and not line.startswith('-'):
                    return True, f"{line[:40]} github", "resume insufficient"
        
        for link in links:
            if 'github.com' in link:
                match = re.search(r'github\.com/([\w\-]+/[\w\-]+)', link)
                if match:
                    return True, f"{match.group(1)}", "resume insufficient"
        
        return True, "portfolio projects", "resume insufficient"
    
    if 'github' in question_lower or 'repo' in question_lower or 'project' in question_lower:
        projects = sections.get('PROJECTS', '')
        if projects:
            lines = projects.split('\n')[:3]
            for line in lines:
                if len(line) > 10 and len(line) < 50:
                    return True, f"{line.strip()} project details", "project-specific question"
    
    if any(kw in question_lower for kw in ['what is', 'explain', 'how does', 'define']):
        return False, "", ""
    
    return False, "", ""


def rank_context_sources(
    sections: Dict[str, str],
    web_content: List[Tuple[str, str]],
    searchapi_content: Optional[str]
) -> List[Tuple[str, str, int]]:
    ranked = []
    
    for section_name, content in sections.items():
        if content:
            ranked.append((f"RESUME_{section_name}", content, 1))
    
    for source, content in web_content:
        ranked.append((f"WEB_{source}", content, 2))
    
    if searchapi_content:
        ranked.append(("SEARCHAPI", searchapi_content, 3))
    
    return ranked


def _extract_keyword_from_question(question: str) -> Optional[str]:
    """Return the first tech keyword found in the question."""
    q = question.lower()
    for kw in KEYWORD_TECH_PATTERNS:
        if kw in q:
            return kw
    return None


def select_relevant_context(
    sections: Dict[str, str],
    web_content: List[Tuple[str, str]],
    question: str,
    searchapi_content: Optional[str] = None,
    full_resume: str = "",
    project_data: Optional[Dict] = None,
    max_length: int = MAX_CONTEXT_SIZE
) -> str:
    intent = detect_project_intent(question)
    
    # 1) LinkUp-only: explain your project, most recent, main, best, or explicit "LinkUp"
    if intent in ("linkup_only", "explicit_linkup"):
        ctx = prioritize_linkup_project(
            sections, project_data, web_content, full_resume, max_length
        )
        if ctx:
            return ctx
        # No LinkUp context: return minimal instruction so we do not mix other projects
        return (
            "--- INSTRUCTION ---\n"
            "The user asked about LinkUp or their main/most recent project. "
            "No LinkUp-specific context was found in resume or project.json. "
            "Respond in first person that you do not have LinkUp details in your materials, "
            "and do not mention other projects."
        )
    
    # 2) Keyword-based: e.g. "which project uses Firebase?"
    kw = _extract_keyword_from_question(question)
    if kw and project_data is not None:
        ctx = keyword_context_search(
            kw, sections, full_resume, project_data, web_content, max_length
        )
        if ctx:
            return ctx
    
    # 3) General: use existing RAG flow, but inject project.json LinkUp first when project-related
    relevant_section_names = classify_question(question)
    is_project_question = is_project_intent_question(question)
    ranked_sources = rank_context_sources(sections, web_content, searchapi_content)
    
    context_parts = []
    current_length = 0
    
    # Prefer project.json LinkUp at top when answering project questions
    if is_project_question and project_data and project_data.get("linkup_text"):
        chunk = "--- PROJECT (project.json - LinkUp) ---\n" + project_data["linkup_text"] + "\n"
        if len(chunk) <= max_length:
            context_parts.append(chunk)
            current_length += len(chunk)
    
    total_resume_size = sum(len(v) for v in sections.values() if v)
    if total_resume_size < 1000:
        relevant_section_names = [k for k, v in sections.items() if v.strip()]
    
    # Resume: for project questions, prefer LinkUp block only (no mixing)
    if is_project_question and intent != "keyword":
        projects_section = sections.get('PROJECTS', '') or sections.get('OTHER', '')
        if projects_section:
            linkup_match = re.search(
                r'(LinkUp|Link-Up)[^\n]*.*?(?=\n\n(?:[A-Z][a-z]+|MealLogger|Melo|EXPERIENCE|EDUCATION|SKILLS)|\Z)',
                projects_section,
                re.DOTALL | re.IGNORECASE
            )
            if linkup_match:
                linkup_content = linkup_match.group(0).strip()
                if len(linkup_content) > 1500:
                    linkup_content = linkup_content[:1500] + "..."
                header = "--- RESUME (LinkUp) ---"
                content_chunk = f"{header}\n{linkup_content}\n"
                if current_length + len(content_chunk) <= max_length:
                    context_parts.append(content_chunk)
                    current_length += len(content_chunk)
                    relevant_section_names = [s for s in relevant_section_names if s != 'PROJECTS']
    
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
                remaining = max_length - current_length - len(header) - 10
                if remaining > 100:
                    truncated = section_content[:remaining] + "..."
                    context_parts.append(f"{header}\n{truncated}\n")
                    current_length = max_length
                    added_sections.append(section_name)
                    break
    
    if not added_sections and current_length < 500:
        for fallback_section in ['SUMMARY', 'SKILLS', 'EXPERIENCE', 'PROJECTS', 'EDUCATION', 'OTHER']:
            section_content = sections.get(fallback_section, '').strip()
            if section_content and current_length < max_length:
                header = f"--- {fallback_section} ---"
                truncated_content = section_content[:1500] if len(section_content) > 1500 else section_content
                content_chunk = f"{header}\n{truncated_content}\n"
                if current_length + len(content_chunk) <= max_length:
                    context_parts.append(content_chunk)
                    current_length += len(content_chunk)
                    added_sections.append(fallback_section)
                else:
                    remaining = max_length - current_length - len(header) - 10
                    if remaining > 200:
                        truncated = section_content[:remaining] + "..."
                        context_parts.append(f"{header}\n{truncated}\n")
                        added_sections.append(fallback_section)
                        break
    
    if not context_parts and full_resume and current_length < max_length:
        truncated_resume = full_resume[:min(max_length - 100, 3000)]
        context_parts.append(f"--- RESUME CONTENT ---\n{truncated_resume}\n")
        added_sections.append('FULL_RESUME')
    
    if current_length < max_length:
        for source, content, priority in ranked_sources:
            if priority == 2 and current_length < max_length:
                remaining = max_length - current_length
                truncated = content[:min(remaining - 50, 500)]
                if truncated:
                    context_parts.append(f"--- {source} ---\n{truncated}\n")
                    current_length += len(truncated) + 50
    
    if current_length < max_length and searchapi_content:
        remaining = max_length - current_length
        truncated = searchapi_content[:min(remaining - 50, 300)]
        if truncated:
            context_parts.append(f"--- Web Search ---\n{truncated}\n")
    
    return '\n'.join(context_parts)


def extract_text_from_pdf(file_path: Path) -> str:
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
    for encoding in ['utf-8', 'latin-1', 'cp1252']:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                text = f.read()
                return clean_latex_text(text)
        except (UnicodeDecodeError, LookupError):
            continue
    return "[Error: Unable to decode file]"


def extract_all_links(text: str) -> Set[str]:
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]\(\)]+'
    urls = re.findall(url_pattern, text)
    
    cleaned = set()
    for url in urls:
        url = url.rstrip('.,;:!?)')
        if url:
            cleaned.add(url)
    
    return cleaned


def categorize_links(urls: Set[str]) -> Dict[str, List[str]]:
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


def scrape_webpage(url: str, timeout: int = 10) -> Tuple[str, str, bool]:
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


def load_resume(docs_dir: str = "docs") -> Tuple[Dict[str, str], Set[str], str]:
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
    
    total_section_content = sum(len(v) for v in sections.values() if v)
    if total_section_content < 500 and full_resume:
        sections['OTHER'] = full_resume[:5000]
    
    return sections, all_links, full_resume


def call_groq_llm(
    question: str,
    context: str,
    api_key: str,
    use_memory: Optional[Dict] = None
) -> str:
    if Groq is None:
        return "[Error: Groq SDK not installed. Run: pip install groq]"
    
    try:
        client = Groq(api_key=api_key)
        
        memory_hint = ""
        if use_memory:
            memory_hint = f"\nNote: Similar question was asked before. Use this as reference but ensure accuracy: {use_memory.get('answer', '')[:100]}"
        
        system_prompt = """You ARE the person whose resume this is. You speak in first person only.

CRITICAL RULES:
- Always use "I": "I built", "I worked on", "I focused on", "I used".
- NEVER use "you", "the candidate", "the developer", "they built", "he/she worked".
- If asked about projects, answer only about the project(s) in the context (e.g. LinkUp when that is provided). Do not mix or invent projects.
- Use the provided context (resume, project.json, GitHub). Only say "Not found" if there is truly no relevant information.
- For "explain your project" or "most recent project" or "LinkUp": answer ONLY about LinkUp using the context given.

Response style:
- First person, confident, professional
- 4–7 short bullet points OR a short paragraph
- Maximum 120 words
- No raw file dumps, no config lists
- UX-friendly explanations"""
        
        user_message = f"""CONTEXT:
{context}
{memory_hint}

QUESTION: {question}

RESPONSE (concise and direct):"""
        
        print("[LLM] Using Groq llama-3.1-8b-instant")
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.2,
            max_tokens=220,
            stream=False
        )
        
        answer = response.choices[0].message.content.strip()
        answer = enforce_first_person_voice(answer)
        
        words = answer.split()
        if len(words) > MAX_RESPONSE_WORDS + 20:
            answer = ' '.join(words[:MAX_RESPONSE_WORDS]) + "..."
        
        return answer
        
    except Exception as e:
        error_msg = str(e)
        if "rate_limit" in error_msg.lower() or "429" in error_msg:
            return "[Error: Groq API rate limit exceeded. Please try again later.]"
        elif "401" in error_msg or "unauthorized" in error_msg.lower():
            return "[Error: Invalid Groq API key. Check your GROQ_API_KEY.]"
        else:
            return f"[Error generating response: {error_msg[:200]}]"


generate_response = call_groq_llm


def main():
    load_dotenv()
    groq_key = os.getenv('GROQ_API_KEY')
    searchapi_key = os.getenv('SEARCHAPI_API_KEY') or os.getenv('SEARCHAPI_KEY')
    
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
    
    memory = load_memory()
    
    similar = find_similar_question(question, memory)
    is_easy = is_easy_question(question)
    
    if similar:
        similarity_score = "high" if is_easy else "medium"
        print(f"💡 Found similar past question ({similarity_score} similarity)")
        print(f"   Previous: {similar['question'][:60]}...")
        
        if is_easy and similar.get('is_easy', False):
            print(f"   ✓ Reusing previous answer (easy question, memory match)")
    
    sections, links, full_resume = load_resume("docs")
    
    if not sections or all(not v for v in sections.values()):
        print("\n❌ Error: No resume found in docs/ directory\n")
        sys.exit(1)
    
    project_data = load_project_json("docs")
    if project_data and project_data.get("linkup"):
        print("[CTX] project.json/projects.json loaded (LinkUp as primary project)")
    elif project_data:
        print("[CTX] project.json/projects.json loaded")
    
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
    
    web_content = []
    if links:
        categorized = categorize_links(links)
        if categorized['github']:
            print(f"  → Processing {len(categorized['github'])} GitHub link(s)...")
            web_content = process_github_links(categorized['github'])
            if web_content:
                print(f"    ✓ Loaded {len(web_content)} GitHub source(s)")
    
    initial_context = select_relevant_context(
        sections, web_content, question, full_resume=full_resume, project_data=project_data
    )
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
    
    relevant_context = select_relevant_context(
        sections, web_content, question, searchapi_content,
        full_resume=full_resume, project_data=project_data
    )
    
    relevant_sections = classify_question(question)
    
    print(f"\n❓ Question: {question}")
    print(f"🎯 Relevant sections: {', '.join(relevant_sections)}")
    print(f"📊 Context size: {len(relevant_context)} chars")
    
    response = None
    if is_easy and similar and similar.get('is_easy', False):
        question_words = set(re.findall(r'\w+', question.lower()))
        similar_words = set(re.findall(r'\w+', similar['question'].lower()))
        intersection = question_words & similar_words
        union = question_words | similar_words
        similarity = len(intersection) / len(union) if union else 0.0
        
        cached_answer = similar.get('answer', '')
        
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
        
        if is_valid_cache:
            response = cached_answer
            print("\n💾 Using cached answer from memory (high similarity match)\n")
        else:
            if similarity > 0.75 and not is_valid_cache:
                print("\n[MEMORY] Cached answer invalid — regenerating")
            print("\n🤔 Generating response (refining from memory)...\n")
    else:
        print("\n🤔 Generating response...\n")
    
    if not response:
        response = call_groq_llm(
            question, relevant_context, groq_key,
            use_memory=similar
        )
    
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

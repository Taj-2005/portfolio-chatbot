#!/usr/bin/env python3
"""
Professional Resume-Aware AI Chatbot using Gemini 2.5 Flash

Optimized for:
- High-precision, concise responses (6-10 bullets or ≤150 words)
- LaTeX-aware resume parsing
- Intelligent context filtering
- Question-aware relevance scoring

Built for recruiters, interviewers, clients, and hackathon judges.
"""

import os
import sys
import re
from pathlib import Path
from typing import List, Tuple, Dict, Set, Optional
from urllib.parse import urlparse
import google.generativeai as genai
from dotenv import load_dotenv

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


# ==================== LATEX TEXT CLEANING ====================

def clean_latex_text(text: str) -> str:
    """
    Clean LaTeX artifacts from resume text while preserving semantic structure.
    
    Removes:
    - LaTeX commands: \\section, \\textbf, \\href, \\item, etc.
    - Special characters: {, }, \\, ~, etc.
    - Layout artifacts
    
    Preserves:
    - Bullet points and structure
    - URLs from \\href commands
    - Section headers
    
    Args:
        text: Raw text from LaTeX-generated PDF
        
    Returns:
        Cleaned, normalized text
    """
    if not text:
        return ""
    
    # Extract URLs from \href{url}{text} before removing LaTeX
    href_pattern = r'\\href\{([^}]+)\}\{([^}]+)\}'
    hrefs = re.findall(href_pattern, text)
    for url, link_text in hrefs:
        text = text.replace(f'\\href{{{url}}}{{{link_text}}}', f'{link_text} ({url})')
    
    # Remove common LaTeX commands
    latex_commands = [
        r'\\section\*?\{([^}]+)\}',  # \section{Title} → Title
        r'\\subsection\*?\{([^}]+)\}',
        r'\\textbf\{([^}]+)\}',  # \textbf{bold} → bold
        r'\\textit\{([^}]+)\}',  # \textit{italic} → italic
        r'\\emph\{([^}]+)\}',
        r'\\underline\{([^}]+)\}',
        r'\\texttt\{([^}]+)\}',
        r'\\item\s+',  # Remove \item but keep content
    ]
    
    for pattern in latex_commands:
        text = re.sub(pattern, r'\1', text)
    
    # Remove remaining LaTeX backslashes and braces
    text = re.sub(r'\\[a-zA-Z]+\*?', '', text)  # \command
    text = re.sub(r'[{}]', '', text)  # Remove stray braces
    text = re.sub(r'\\', '', text)  # Remove backslashes
    
    # Clean up whitespace and formatting
    text = re.sub(r'\s+', ' ', text)  # Multiple spaces → single space
    text = re.sub(r'\s*\n\s*', '\n', text)  # Clean newlines
    text = re.sub(r'\n{3,}', '\n\n', text)  # Max 2 newlines
    
    # Remove common PDF artifacts
    text = re.sub(r'Page \d+ of \d+', '', text)
    text = re.sub(r'^\d+\s*$', '', text, flags=re.MULTILINE)  # Standalone numbers
    
    return text.strip()


# ==================== SECTION-BASED EXTRACTION ====================

def extract_resume_sections(text: str) -> Dict[str, str]:
    """
    Extract structured sections from resume text.
    
    Identifies and extracts:
    - EXPERIENCE / Work History
    - PROJECTS
    - SKILLS / Technical Skills
    - EDUCATION
    - SUMMARY / About
    
    Args:
        text: Cleaned resume text
        
    Returns:
        Dictionary mapping section names to content
    """
    sections = {
        'EXPERIENCE': '',
        'PROJECTS': '',
        'SKILLS': '',
        'EDUCATION': '',
        'SUMMARY': '',
        'OTHER': ''
    }
    
    # Section header patterns (case-insensitive)
    patterns = {
        'EXPERIENCE': r'(?i)(professional\s+)?experience|work\s+history|employment',
        'PROJECTS': r'(?i)projects?|portfolio',
        'SKILLS': r'(?i)(technical\s+)?skills?|technologies|expertise',
        'EDUCATION': r'(?i)education|academic|qualifications',
        'SUMMARY': r'(?i)summary|about|profile|objective',
    }
    
    # Split text by common section markers
    lines = text.split('\n')
    current_section = 'OTHER'
    section_content = []
    
    for line in lines:
        line_stripped = line.strip()
        
        # Check if this line is a section header
        is_header = False
        for section_name, pattern in patterns.items():
            if re.match(pattern, line_stripped) and len(line_stripped) < 50:
                # Save previous section
                if section_content:
                    sections[current_section] += '\n'.join(section_content) + '\n\n'
                
                # Start new section
                current_section = section_name
                section_content = []
                is_header = True
                break
        
        if not is_header and line_stripped:
            section_content.append(line)
    
    # Save last section
    if section_content:
        sections[current_section] += '\n'.join(section_content)
    
    # Clean up sections
    for key in sections:
        sections[key] = sections[key].strip()
    
    return sections


# ==================== QUESTION CLASSIFICATION ====================

def classify_question(question: str) -> List[str]:
    """
    Classify question to determine relevant resume sections.
    
    Args:
        question: User's question
        
    Returns:
        List of relevant section names
    """
    question_lower = question.lower()
    relevant_sections = []
    
    # Project-related keywords
    if any(kw in question_lower for kw in ['project', 'built', 'developed', 'created', 'github', 'portfolio']):
        relevant_sections.append('PROJECTS')
    
    # Skills-related keywords
    if any(kw in question_lower for kw in ['skill', 'technology', 'language', 'framework', 'tool', 'stack', 'know', 'expertise']):
        relevant_sections.append('SKILLS')
    
    # Experience-related keywords
    if any(kw in question_lower for kw in ['experience', 'work', 'job', 'role', 'position', 'company', 'hired']):
        relevant_sections.append('EXPERIENCE')
    
    # Education-related keywords
    if any(kw in question_lower for kw in ['education', 'degree', 'university', 'study', 'graduate', 'academic']):
        relevant_sections.append('EDUCATION')
    
    # Summary/general keywords
    if any(kw in question_lower for kw in ['about', 'yourself', 'who', 'background', 'summary', 'overview']):
        relevant_sections.extend(['SUMMARY', 'EXPERIENCE', 'SKILLS'])
    
    # If no specific match, include all for broad questions
    if not relevant_sections:
        relevant_sections = ['SUMMARY', 'EXPERIENCE', 'SKILLS', 'PROJECTS']
    
    # Remove duplicates while preserving order
    seen = set()
    return [x for x in relevant_sections if not (x in seen or seen.add(x))]


# ==================== CONTEXT SELECTION ====================

def select_relevant_context(
    sections: Dict[str, str],
    web_content: List[Tuple[str, str]],
    question: str,
    max_length: int = 4000
) -> str:
    """
    Select only relevant context based on question classification.
    
    Args:
        sections: Resume sections dictionary
        web_content: Web-scraped content
        question: User's question
        max_length: Maximum context length in characters
        
    Returns:
        Filtered, relevant context string
    """
    relevant_section_names = classify_question(question)
    
    context_parts = []
    current_length = 0
    
    # Add relevant resume sections
    for section_name in relevant_section_names:
        section_content = sections.get(section_name, '').strip()
        if section_content and current_length < max_length:
            header = f"--- {section_name} ---"
            content_chunk = f"{header}\n{section_content}\n"
            
            if current_length + len(content_chunk) <= max_length:
                context_parts.append(content_chunk)
                current_length += len(content_chunk)
    
    # Add web content only if relevant to question (for projects/GitHub)
    if 'PROJECTS' in relevant_section_names and web_content and current_length < max_length:
        context_parts.append("\n--- GITHUB/PORTFOLIO ---")
        for source, content in web_content[:3]:  # Limit to top 3 sources
            if current_length < max_length:
                # Truncate web content more aggressively
                truncated = content[:1000] if len(content) > 1000 else content
                context_parts.append(f"{source}: {truncated}")
                current_length += len(truncated)
    
    return '\n'.join(context_parts)


# ==================== DOCUMENT PARSERS ====================

def extract_text_from_pdf(file_path: Path) -> str:
    """Extract text from PDF resume with LaTeX cleaning."""
    if PdfReader is None:
        return "[PDF parsing unavailable - install pypdf]"
    
    try:
        reader = PdfReader(file_path)
        text_parts = []
        
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text.strip():
                # Clean LaTeX artifacts immediately
                cleaned = clean_latex_text(page_text)
                text_parts.append(cleaned)
        
        return "\n\n".join(text_parts)
    except Exception as e:
        return f"[Error parsing PDF: {str(e)[:100]}]"


def extract_text_from_docx(file_path: Path) -> str:
    """Extract text from Word document resume."""
    if Document is None:
        return "[Word parsing unavailable - install python-docx]"
    
    try:
        doc = Document(file_path)
        paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
        text = "\n".join(paragraphs)
        return clean_latex_text(text)  # Clean any LaTeX if present
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
    """Categorize URLs by type for intelligent processing."""
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
        
        # Remove unnecessary elements
        for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            element.decompose()
        
        text = soup.get_text(separator='\n', strip=True)
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        text = '\n'.join(lines)
        
        # Aggressive truncation for web content
        if len(text) > 2000:
            text = text[:2000] + "..."
        
        return title, text, True
        
    except Exception:
        return "Error", "", False


def process_github_links(github_urls: List[str]) -> List[Tuple[str, str]]:
    """Process GitHub links with focus on READMEs."""
    results = []
    
    for url in github_urls[:3]:  # Limit to 3 GitHub sources
        parsed = urlparse(url)
        path_parts = [p for p in parsed.path.split('/') if p]
        
        if len(path_parts) >= 2:
            # Repository URL
            title, content, success = scrape_webpage(url, timeout=15)
            if success and content:
                # Extract only README-like content
                readme_match = re.search(r'README.*?(?=\n\n|\Z)', content, re.DOTALL | re.IGNORECASE)
                if readme_match:
                    content = readme_match.group(0)[:1000]
                results.append((f"GitHub: {path_parts[0]}/{path_parts[1]}", content))
    
    return results


# ==================== RESUME LOADING ====================

def load_resume(docs_dir: str = "docs") -> Tuple[Dict[str, str], Set[str]]:
    """
    Load resume and extract structured sections + links.
    
    Returns:
        Tuple of (sections_dict, set_of_links)
    """
    docs_path = Path(docs_dir)
    
    if not docs_path.exists():
        return {}, set()
    
    handlers = {
        '.pdf': extract_text_from_pdf,
        '.docx': extract_text_from_docx,
        '.doc': extract_text_from_docx,
        '.txt': read_text_file,
        '.md': read_text_file,
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
    
    # Combine and extract sections
    full_resume = "\n\n".join(resume_parts)
    sections = extract_resume_sections(full_resume)
    
    return sections, all_links


# ==================== AI RESPONSE GENERATION ====================

def generate_concise_response(
    question: str,
    context: str,
    api_key: str
) -> str:
    """
    Generate concise, high-precision response using Gemini 2.5 Flash.
    
    Optimized for:
    - Brevity (6-10 bullets or ≤150 words)
    - Relevance (only what's asked)
    - Factual accuracy (no speculation)
    
    Args:
        question: User's question
        context: Filtered relevant context
        api_key: Gemini API key
        
    Returns:
        Concise professional response
    """
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    # Optimized prompt for brevity and precision
    prompt = f"""You are an AI resume assistant helping recruiters quickly assess a candidate.

CONTEXT (Resume Sections):
{context}

CRITICAL INSTRUCTIONS:
1. Answer STRICTLY based on the provided context
2. If the answer is not in the context, respond: "Not mentioned in the resume."
3. Be CONCISE: Use 6-10 bullet points OR maximum 150 words
4. Be FACTUAL: No speculation, no external knowledge, no embellishment
5. Be RELEVANT: Answer ONLY what is asked - no extra information
6. Use bullet points for lists, short paragraphs for explanations
7. Avoid adjectives like "highly", "extremely", "passionate"
8. Use resume language, not marketing language
9. Do NOT repeat information
10. Do NOT include unrelated projects or skills

QUESTION: {question}

RESPONSE (concise and direct):"""
    
    try:
        response = model.generate_content(prompt)
        answer = response.text.strip()
        
        # Enforce length limit (safety check)
        words = answer.split()
        if len(words) > 180:
            # Truncate to approximately 150 words
            answer = ' '.join(words[:150]) + "..."
        
        return answer
        
    except Exception as e:
        return f"[Error generating response: {str(e)}]"


# ==================== MAIN APPLICATION ====================

def main():
    """Main application entry point."""
    
    load_dotenv()
    api_key = os.getenv('GEMINI_API_KEY')
    
    if not api_key:
        print("\n❌ Error: GEMINI_API_KEY not found in environment")
        print("Create a .env file with your Gemini API key")
        print("Get key from: https://makersuite.google.com/app/apikey\n")
        sys.exit(1)
    
    if len(sys.argv) < 2:
        print("\n🤖 Resume-Aware Professional AI Chatbot")
        print("="* 60)
        print("\nUsage: python main.py 'Your question here'")
        print("\nExamples:")
        print("  python main.py 'What are your technical skills?'")
        print("  python main.py 'Tell me about your projects'")
        print("  python main.py 'What is your experience?'\n")
        sys.exit(1)
    
    question = ' '.join(sys.argv[1:])
    
    print("\n" + "="*70)
    print("🤖 RESUME AI ASSISTANT (Optimized for Conciseness)")
    print("="*70 + "\n")
    
    # Load resume with section extraction
    sections, links = load_resume("docs")
    
    if not sections or all(not v for v in sections.values()):
        print("\n❌ Error: No resume found in docs/ directory\n")
        sys.exit(1)
    
    print(f"\n✓ Resume loaded and structured")
    
    # Process links (limited)
    web_content = []
    if links:
        categorized = categorize_links(links)
        if categorized['github']:
            print(f"  → Processing {len(categorized['github'])} GitHub link(s)...")
            web_content = process_github_links(categorized['github'])
            if web_content:
                print(f"    ✓ Loaded {len(web_content)} GitHub source(s)")
    
    # Select relevant context based on question
    relevant_context = select_relevant_context(sections, web_content, question)
    
    print(f"\n❓ Question: {question}")
    print(f"🎯 Relevant sections: {', '.join(classify_question(question))}")
    print("\n🤔 Generating concise response...\n")
    
    # Generate response
    response = generate_concise_response(question, relevant_context, api_key)
    
    print("="*70)
    print("💼 RESPONSE")
    print("="*70)
    print(f"\n{response}\n")
    print("="*70)
    print()


if __name__ == "__main__":
    main()

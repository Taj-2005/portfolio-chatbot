"""
Resume loading and parsing functionality.

Supports multiple resume formats: PDF, DOCX, TXT, MD, LaTeX.
Extracts structured sections and links from resume documents.
"""

import re
from pathlib import Path
from typing import Dict, Set, Tuple, Optional

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

try:
    from docx import Document
except ImportError:
    Document = None

from ..config import settings
from ..utils.logger import setup_logger
from ..utils.text_processing import clean_latex_text, extract_all_links

logger = setup_logger(__name__)


def extract_resume_sections(text: str) -> Dict[str, str]:
    """
    Extract structured sections from resume text.
    
    Identifies and separates standard resume sections like Experience,
    Projects, Skills, Education, and Summary.
    
    Args:
        text: Full resume text.
    
    Returns:
        Dict[str, str]: Dictionary with section names as keys and content as values.
            Keys: 'EXPERIENCE', 'PROJECTS', 'SKILLS', 'EDUCATION', 'SUMMARY', 'OTHER'
    """
    sections = {
        'EXPERIENCE': '',
        'PROJECTS': '',
        'SKILLS': '',
        'EDUCATION': '',
        'SUMMARY': '',
        'OTHER': ''
    }
    
    # Regex patterns to identify section headers
    patterns = {
        'EXPERIENCE': r'(?i)(professional\s+)?experience|work\s+history|employment|internships?',
        'PROJECTS': r'(?i)projects?|portfolio',
        'SKILLS': r'(?i)(technical\s+)?skills?|technologies|expertise',
        'EDUCATION': r'(?i)education|academic|qualifications',
        'SUMMARY': r'(?i)summary|about|profile|objective',
    }

    def heading_text(line: str) -> Optional[str]:
        """
        Return the heading label if this line is a section heading, else None.

        Recognises Markdown headings (`## EXPERIENCE`) and the short all-caps
        headings used by PDF/LaTeX resumes. Requiring a heading shape first stops
        ordinary bullets that happen to contain "projects" from splitting sections.
        """
        stripped = line.strip()
        if not stripped:
            return None

        if stripped.startswith('#'):
            return stripped.lstrip('#').strip().strip('*_: ')

        letters = [c for c in stripped if c.isalpha()]
        if letters and len(stripped) < 50 and all(c.isupper() for c in letters):
            return stripped.strip('*_: ')

        return None

    try:
        lines = text.split('\n')
        current_section = 'OTHER'
        section_content = []

        for line in lines:
            line_stripped = line.strip()
            is_header = False
            heading = heading_text(line)

            # Check if line is a section header
            if heading:
                for section_name, pattern in patterns.items():
                    if re.search(pattern, heading):
                        # Save previous section content
                        if section_content:
                            sections[current_section] += '\n'.join(section_content) + '\n\n'
                        current_section = section_name
                        section_content = []
                        is_header = True
                        break

            # Add line to current section
            if not is_header and line_stripped:
                section_content.append(line)
        
        # Save final section
        if section_content:
            sections[current_section] += '\n'.join(section_content)
        
        # Clean up sections
        for key in sections:
            sections[key] = sections[key].strip()
        
        logger.info(
            f"Extracted resume sections: "
            f"Experience={len(sections['EXPERIENCE'])} chars, "
            f"Projects={len(sections['PROJECTS'])} chars, "
            f"Skills={len(sections['SKILLS'])} chars"
        )
        
        return sections
    except Exception as e:
        logger.error(f"Error extracting resume sections: {e}")
        return sections


class ResumeLoader:
    """
    Loads and parses resume files from various formats.
    
    Supports PDF, DOCX, TXT, MD, and LaTeX formats.
    Extracts structured sections and links from resume content.
    """
    
    def __init__(self, docs_dir: str = None):
        """
        Initialize ResumeLoader.
        
        Args:
            docs_dir: Directory containing resume files. If None, uses settings.DOCS_DIR.
        """
        self.docs_dir = Path(docs_dir) if docs_dir else settings.get_docs_path()
        logger.info(f"Initialized ResumeLoader with docs_dir: {self.docs_dir}")

    def _should_index_file(self, file_path: Path) -> bool:
        """
        Decide whether a file under docs/ should be treated as "resume source".

        Rationale:
        - `docs/` contains both resume artifacts and project documentation.
        - Indexing everything (e.g. `docs/ai-ml/*.md`) pollutes the resume corpus,
          harms section extraction, and weakens grounding.
        - We keep behavior conservative and resume-focused.
        """
        ext = file_path.suffix.lower()
        if ext not in settings.SUPPORTED_RESUME_FORMATS:
            return False

        rel = file_path.relative_to(self.docs_dir)
        rel_parts = {p.lower() for p in rel.parts}

        # Explicitly skip AI/ML documentation and other non-resume assets
        if "ai-ml" in rel_parts:
            return False

        # Skip known non-resume files in docs/
        if file_path.name.lower() in {"projects.json", "project.json", "readme.md"}:
            return False

        # For markdown/text files, only treat as resume if it looks like one.
        # This prevents indexing arbitrary docs as "resume".
        if ext in {".md", ".txt"}:
            name = file_path.name.lower()
            if "resume" not in name and "cv" not in name:
                return False

        return True
    
    def _extract_text_from_pdf(self, file_path: Path) -> str:
        """
        Extract text content from PDF file.
        
        Args:
            file_path: Path to PDF file.
        
        Returns:
            str: Extracted text content.
        """
        if PdfReader is None:
            logger.error("pypdf library not installed - cannot parse PDF files")
            return "[PDF parsing unavailable - install pypdf]"
        
        try:
            reader = PdfReader(file_path)
            text_parts = []
            
            for page_num, page in enumerate(reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text.strip():
                        cleaned = clean_latex_text(page_text)
                        text_parts.append(cleaned)
                except Exception as e:
                    logger.warning(f"Error extracting text from page {page_num}: {e}")
            
            logger.debug(f"Extracted {len(text_parts)} pages from PDF")
            return "\n\n".join(text_parts)
        except Exception as e:
            logger.error(f"Error parsing PDF {file_path}: {e}")
            return f"[Error parsing PDF: {str(e)[:100]}]"
    
    def _extract_text_from_docx(self, file_path: Path) -> str:
        """
        Extract text content from DOCX file.
        
        Args:
            file_path: Path to DOCX file.
        
        Returns:
            str: Extracted text content.
        """
        if Document is None:
            logger.error("python-docx library not installed - cannot parse DOCX files")
            return "[Word parsing unavailable - install python-docx]"
        
        try:
            doc = Document(file_path)
            paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
            text = "\n".join(paragraphs)
            logger.debug(f"Extracted {len(paragraphs)} paragraphs from DOCX")
            return clean_latex_text(text)
        except Exception as e:
            logger.error(f"Error parsing DOCX {file_path}: {e}")
            return f"[Error parsing Word doc: {str(e)[:100]}]"
    
    def _read_text_file(self, file_path: Path) -> str:
        """
        Read text file with multiple encoding fallbacks.
        
        Args:
            file_path: Path to text file.
        
        Returns:
            str: File contents.
        """
        for encoding in ['utf-8', 'latin-1', 'cp1252']:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    text = f.read()
                    logger.debug(f"Read text file with {encoding} encoding")
                    return clean_latex_text(text)
            except (UnicodeDecodeError, LookupError):
                continue
        
        logger.error(f"Unable to decode file {file_path}")
        return "[Error: Unable to decode file]"
    
    def load_resume(self) -> Tuple[Dict[str, str], Set[str], str]:
        """
        Load all resume files from docs directory.
        
        Parses all supported file formats, extracts content, sections, and links.
        
        Returns:
            Tuple containing:
                - Dict[str, str]: Extracted resume sections
                - Set[str]: All URLs found in resume
                - str: Full resume text
        """
        if not self.docs_dir.exists():
            logger.error(f"Docs directory not found: {self.docs_dir}")
            return {}, set(), ""
        
        handlers = {
            '.pdf': self._extract_text_from_pdf,
            '.docx': self._extract_text_from_docx,
            '.doc': self._extract_text_from_docx,
            '.txt': self._read_text_file,
            '.md': self._read_text_file,
            '.tex': self._read_text_file,
        }
        
        resume_parts = []
        all_links = set()

        logger.info("Loading resume files...")

        candidates = [
            p for p in sorted(self.docs_dir.rglob('*'))
            if p.is_file() and self._should_index_file(p)
        ]

        # The knowledge base ships the resume as both Markdown and PDF. Indexing both
        # duplicates every bullet, which skews retrieval — prefer the Markdown copy,
        # since its headings drive section extraction far more reliably than PDF text.
        binary_exts = {'.pdf', '.docx', '.doc', '.tex'}
        if any(p.suffix.lower() in {'.md', '.txt'} for p in candidates):
            kept = []
            for p in candidates:
                if p.suffix.lower() in binary_exts:
                    logger.info(f"Skipping {p.name}: superseded by the Markdown resume")
                else:
                    kept.append(p)
            candidates = kept

        for file_path in candidates:
            handler = handlers.get(file_path.suffix.lower())
            if not handler:
                continue

            try:
                content = handler(file_path)
                if content and not content.startswith('[Error'):
                    resume_parts.append(content)
                    links = extract_all_links(content)
                    all_links.update(links)
                    logger.info(f"Loaded {file_path.name}: {len(content)} chars, {len(links)} links")
            except Exception as e:
                logger.error(f"Error loading {file_path.name}: {e}")
        
        # Combine all resume content
        full_resume = "\n\n".join(resume_parts)
        sections = extract_resume_sections(full_resume)
        
        # If sections are too small, use full resume as OTHER
        total_section_content = sum(len(v) for v in sections.values() if v)
        if total_section_content < 500 and full_resume:
            sections['OTHER'] = full_resume[:5000]
            logger.warning("Resume sections too small, using full text in OTHER")
        
        logger.info(
            f"Resume loading complete: {len(full_resume)} total chars, "
            f"{len(all_links)} links, {len(resume_parts)} files"
        )
        
        return sections, all_links, full_resume

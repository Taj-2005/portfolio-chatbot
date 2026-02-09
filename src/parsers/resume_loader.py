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
        'EXPERIENCE': r'(?i)(professional\s+)?experience|work\s+history|employment',
        'PROJECTS': r'(?i)projects?|portfolio',
        'SKILLS': r'(?i)(technical\s+)?skills?|technologies|expertise',
        'EDUCATION': r'(?i)education|academic|qualifications',
        'SUMMARY': r'(?i)summary|about|profile|objective',
    }
    
    try:
        lines = text.split('\n')
        current_section = 'OTHER'
        section_content = []
        
        for line in lines:
            line_stripped = line.strip()
            is_header = False
            
            # Check if line is a section header
            for section_name, pattern in patterns.items():
                if re.match(pattern, line_stripped) and len(line_stripped) < 50:
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
        print("📄 Loading resume...\n")
        
        for file_path in self.docs_dir.rglob('*'):
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
                            logger.info(f"Loaded {file_path.name}: {len(content)} chars, {len(links)} links")
                    except Exception as e:
                        print(f"✗ Error: {file_path.name}: {e}")
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

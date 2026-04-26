"""
Knowledge base loader for `knowledge-base/`.

This is the source of truth for portfolio Q&A retrieval.
We intentionally do NOT load anything from `docs/` anymore.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Set, Tuple, List

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

from ..config import settings
from ..utils.logger import setup_logger
from ..utils.text_processing import clean_latex_text, extract_all_links

logger = setup_logger(__name__)


class KnowledgeBaseLoader:
    """
    Loads extra portfolio knowledge (beyond resume sections).

    Examples:
    - `knowledge-base/README.md`
    - `knowledge-base/portfolio-features.md` (to be added)
    - `knowledge-base/techstacks.ts`
    - `knowledge-base/projects.json` (also parsed by ProjectLoader)
    """

    def __init__(self, kb_dir: str | None = None):
        self.kb_dir = Path(kb_dir) if kb_dir else settings.get_docs_path()
        logger.info(f"Initialized KnowledgeBaseLoader with kb_dir: {self.kb_dir}")

    def _read_pdf(self, file_path: Path) -> str:
        if PdfReader is None:
            return ""
        try:
            reader = PdfReader(file_path)
            parts: List[str] = []
            for page in reader.pages:
                try:
                    t = page.extract_text() or ""
                    t = t.strip()
                    if t:
                        parts.append(clean_latex_text(t))
                except Exception:
                    continue
            return "\n\n".join(parts).strip()
        except Exception as e:
            logger.warning(f"Failed reading PDF {file_path.name}: {e}")
            return ""

    def _read_text(self, file_path: Path) -> str:
        for enc in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
            try:
                raw = file_path.read_text(encoding=enc)
                return clean_latex_text(raw)
            except Exception:
                continue
        return ""

    def load_knowledge(self) -> Tuple[str, Set[str], Dict[str, str]]:
        """
        Returns:
            full_text: concatenated KB text (excluding resume artifacts + projects.json duplication)
            links: all links found across KB sources
            named_sources: mapping of SOURCE_NAME -> text
        """
        if not self.kb_dir.exists():
            logger.error(f"Knowledge base directory not found: {self.kb_dir}")
            return "", set(), {}

        named_sources: Dict[str, str] = {}
        links: Set[str] = set()

        for file_path in sorted(self.kb_dir.rglob("*")):
            if not file_path.is_file():
                continue

            ext = file_path.suffix.lower()
            name_lower = file_path.name.lower()

            # Skip resume artifacts (handled by ResumeLoader) to avoid duplication.
            if ext in {".pdf", ".tex", ".docx", ".doc"} and ("resume" in name_lower or name_lower == "resume.tex"):
                continue

            # Skip projects.json raw (handled by ProjectLoader into structured text_for_rag).
            if name_lower in {"projects.json", "project.json"}:
                continue

            text = ""
            if ext == ".pdf":
                text = self._read_pdf(file_path)
            elif ext in {".md", ".txt", ".tex", ".ts", ".js", ".json"}:
                text = self._read_text(file_path)
                # If it's JSON and parseable, also add a compact pretty view.
                if ext == ".json":
                    try:
                        obj = json.loads(file_path.read_text(encoding="utf-8"))
                        text = json.dumps(obj, indent=2, ensure_ascii=False)[:8000]
                    except Exception:
                        pass
            else:
                continue

            text = (text or "").strip()
            if not text:
                continue

            source_name = f"KB_{file_path.stem}".upper()
            # Avoid collisions
            if source_name in named_sources:
                source_name = f"{source_name}_{abs(hash(str(file_path))) % 10000}"
            named_sources[source_name] = text
            links.update(extract_all_links(text))

        # Concatenate (bounded) for legacy fallback
        pieces = []
        for k, v in named_sources.items():
            pieces.append(f"--- {k} ---\n{v}")
        full_text = "\n\n".join(pieces)
        # Keep it bounded so it doesn't dominate OTHER.
        full_text = full_text[:12000]

        logger.info(f"Loaded knowledge-base sources: {len(named_sources)} files, {len(links)} links")
        return full_text, links, named_sources


"""
Project data loading functionality.

Loads project information from JSON files (project.json or projects.json)
and identifies the primary project (LinkUp).
"""

import json
from pathlib import Path
from typing import Dict, List, Optional

from ..config import settings
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class ProjectLoader:
    """
    Loads project data from JSON files.
    
    Supports both structured project JSON files with 'courses' and 'prev' arrays,
    as well as simple 'projects' arrays.
    """
    
    def __init__(self, docs_dir: str = None):
        """
        Initialize ProjectLoader.
        
        Args:
            docs_dir: Directory containing project JSON files. If None, uses settings.DOCS_DIR.
        """
        self.docs_dir = Path(docs_dir) if docs_dir else settings.get_docs_path()
        logger.info(f"Initialized ProjectLoader with docs_dir: {self.docs_dir}")
    
    def _project_to_text(self, project: Dict) -> str:
        """
        Convert project dictionary to text representation for RAG.
        
        Args:
            project: Project dictionary with title, description, tech, etc.
        
        Returns:
            str: Text representation of project.
        """
        parts = [
            project.get("title") or "",
            project.get("description") or ""
        ]
        
        # Handle tech stack
        tech = project.get("tech") or []
        if isinstance(tech, list):
            names = [t.get("name") if isinstance(t, dict) else str(t) for t in tech]
            if names:
                parts.append("Tech: " + ", ".join(names))
        else:
            parts.append("Tech: " + str(tech))
        
        return " | ".join(p for p in parts if p)
    
    def _find_linkup_project(self, projects: List[Dict]) -> Optional[Dict]:
        """
        Find LinkUp project from list of projects.
        
        Args:
            projects: List of project dictionaries.
        
        Returns:
            Optional[Dict]: LinkUp project if found, None otherwise.
        """
        for entry in projects:
            title = (entry.get("title") or "").strip().lower()
            slug = (entry.get("slug") or "").strip().lower()
            
            # Check if this is the LinkUp project
            for linkup_name in settings.LINKUP_NAMES:
                if linkup_name in title or linkup_name in slug:
                    logger.info(f"Found LinkUp project: {entry.get('title')}")
                    return entry
        
        logger.warning("LinkUp project not found in project data")
        return None
    
    def load_project_json(self) -> Optional[Dict]:
        """
        Load project data from JSON file.
        
        Searches for project.json or projects.json in docs directory.
        Normalizes different JSON structures and identifies LinkUp project.
        
        Returns:
            Optional[Dict]: Dictionary containing:
                - 'projects': List of all projects
                - 'linkup': LinkUp project dict (or None)
                - 'text_for_rag': Combined text of all projects
                - 'linkup_text': Text representation of LinkUp project
        """
        raw = None
        loaded_file = None
        
        # Try to find and load project JSON file
        for name in settings.PROJECT_JSON_NAMES:
            file_path = self.docs_dir / name
            if file_path.exists():
                try:
                    with open(file_path, "r", encoding="utf-8") as fp:
                        raw = json.load(fp)
                    loaded_file = name
                    logger.info(f"Loaded project data from {name}")
                    break
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON in {name}: {e}")
                    raw = None
                except Exception as e:
                    logger.error(f"Error loading {name}: {e}")
                    raw = None
        
        if not raw:
            logger.warning("No project JSON file found or failed to load")
            return None
        
        # Normalize: support both { "courses": [...], "prev": [...] } and { "projects": [...] }
        all_entries = []
        if "courses" in raw:
            all_entries.extend(raw["courses"])
            logger.debug(f"Found {len(raw['courses'])} projects in 'courses'")
        if "prev" in raw:
            all_entries.extend(raw["prev"])
            logger.debug(f"Found {len(raw['prev'])} projects in 'prev'")
        if "projects" in raw:
            all_entries.extend(raw["projects"])
            logger.debug(f"Found {len(raw['projects'])} projects in 'projects'")
        
        if not all_entries:
            logger.warning(f"No projects found in {loaded_file}")
            return None
        
        # Find LinkUp project
        linkup_entry = self._find_linkup_project(all_entries)
        
        # Convert all projects to text for RAG
        text_parts = [self._project_to_text(p) for p in all_entries]
        text_for_rag = "\n\n---\n\n".join(text_parts)
        
        result = {
            "projects": all_entries,
            "linkup": linkup_entry,
            "text_for_rag": text_for_rag,
            "linkup_text": self._project_to_text(linkup_entry) if linkup_entry else "",
        }
        
        logger.info(
            f"Project data loaded: {len(all_entries)} total projects, "
            f"LinkUp={'found' if linkup_entry else 'not found'}"
        )
        
        return result

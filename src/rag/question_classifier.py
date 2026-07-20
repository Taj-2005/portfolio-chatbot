"""
Question classification and intent detection.

Analyzes user questions to determine intent (project-specific,
skill-related, experience-related, etc.) and relevant resume sections.
"""

import re
from typing import List

from ..config import settings
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class QuestionClassifier:
    """
    Classifies questions to determine relevant context.
    
    Analyzes question intent to identify which resume sections
    and content types are most relevant for answering.
    """
    
    @staticmethod
    def classify_sections(question: str) -> List[str]:
        """
        Classify which resume sections are relevant to the question.
        
        Args:
            question: User's question.
        
        Returns:
            List[str]: List of relevant section names in priority order.
        """
        question_lower = question.lower()
        relevant_sections = []
        
        # Project-related keywords
        if any(kw in question_lower for kw in [
            'project', 'built', 'developed', 'created', 'github', 'portfolio'
        ]):
            relevant_sections.append('PROJECTS')
        
        # Skills-related keywords
        if any(kw in question_lower for kw in [
            'skill', 'technology', 'language', 'framework', 'tool', 'stack',
            'know', 'expertise'
        ]):
            relevant_sections.append('SKILLS')
        
        # Experience-related keywords (includes founder/startup framing)
        if any(kw in question_lower for kw in [
            'experience', 'work', 'job', 'role', 'position', 'company', 'hired',
            'intern', 'internship', 'founder', 'founded', 'startup', 'currently',
            'current', 'now', 'deplo', 'maverick'
        ]):
            relevant_sections.append('EXPERIENCE')
        
        # Education-related keywords
        if any(kw in question_lower for kw in [
            'education', 'degree', 'university', 'study', 'graduate', 'academic'
        ]):
            relevant_sections.append('EDUCATION')
        
        # General/about questions
        if any(kw in question_lower for kw in [
            'about', 'yourself', 'who', 'background', 'summary', 'overview'
        ]):
            relevant_sections.extend(['SUMMARY', 'EXPERIENCE', 'SKILLS'])

        # Identity, "what are you doing now", and contact/link questions are answered from
        # profile facts (founder role, current title, canonical URLs). Those live in the
        # knowledge base, which the chatbot merges into the OTHER section — the resume
        # alone cannot answer them. OTHER is appended last so resume sections keep priority.
        if any(kw in question_lower for kw in [
            'contact', 'email', 'reach', 'link', 'website', 'url', 'linkedin',
            'github', 'resume', 'cv', 'portfolio', 'hire', 'phone',
            'about', 'yourself', 'who', 'background', 'overview',
            'currently', 'current', 'now', 'today', 'these days', 'still',
            'founder', 'founded', 'startup', 'deplo'
        ]):
            relevant_sections.append('OTHER')
        
        # Default to broad sections if no specific match
        if not relevant_sections:
            relevant_sections = ['SUMMARY', 'EXPERIENCE', 'SKILLS', 'PROJECTS']
        
        # Remove duplicates while preserving order
        seen = set()
        unique_sections = [x for x in relevant_sections if not (x in seen or seen.add(x))]
        
        logger.debug(f"Classified question to sections: {unique_sections}")
        return unique_sections
    
    @staticmethod
    def is_project_intent_question(question: str) -> bool:
        """
        Determine if question is asking about projects.
        
        Args:
            question: User's question.
        
        Returns:
            bool: True if question is project-related.
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
            r'explain\s+(your|this)\s+project',
        ]
        
        for pattern in project_intent_patterns:
            if re.search(pattern, question_lower):
                logger.debug(f"Detected project intent: {pattern}")
                return True
        
        return False
    
    @staticmethod
    def requires_featured_project_only(question: str) -> bool:
        """
        Determine if question should be answered with the featured project only.
        
        These are questions that ask for "the" project or "main" project,
        implying a single project response.
        
        Args:
            question: User's question.
        
        Returns:
            bool: True if only the featured project should be mentioned.
        """
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
                logger.debug(f"Requires featured-project-only response: {p}")
                return True
        
        return False
    
    @staticmethod
    def has_explicit_featured_mention(question: str) -> bool:
        """
        Check if question explicitly mentions the featured project by name.
        
        Args:
            question: User's question.
        
        Returns:
            bool: True if the featured project is explicitly mentioned.
        """
        q = question.lower()
        mentioned = any(name in q for name in settings.FEATURED_PROJECT_NAMES)
        
        if mentioned:
            logger.debug("Explicit featured-project mention detected")
        
        return mentioned
    
    @staticmethod
    def detect_project_intent(question: str) -> str:
        """
        Detect the type of project intent in the question.
        
        Args:
            question: User's question.
        
        Returns:
            str: Intent type - 'featured_only', 'explicit_featured', 'keyword', or 'general'.
        """
        # Check for explicit featured-project mention
        if QuestionClassifier.has_explicit_featured_mention(question):
            return 'explicit_featured'
        
        # Check if only the featured project should be mentioned
        if QuestionClassifier.requires_featured_project_only(question):
            return 'featured_only'
        
        # Check for tech keyword mentions
        q = question.lower()
        for kw in settings.KEYWORD_TECH_PATTERNS:
            if kw in q:
                logger.debug(f"Detected tech keyword: {kw}")
                return 'keyword'
        
        # Check if it's a project question at all
        if QuestionClassifier.is_project_intent_question(question):
            return 'general'
        
        return 'general'
    
    @staticmethod
    def extract_keyword_from_question(question: str) -> str:
        """
        Extract the first tech keyword found in question.
        
        Args:
            question: User's question.
        
        Returns:
            str: First matching tech keyword, or empty string.
        """
        q = question.lower()
        for kw in settings.KEYWORD_TECH_PATTERNS:
            if kw in q:
                logger.debug(f"Extracted keyword: {kw}")
                return kw
        return ""

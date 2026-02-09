"""
Groq LLM client integration.

Handles communication with Groq API for text generation,
including response post-processing and error handling.
"""

import re
from typing import Optional, Dict

try:
    from groq import Groq
except ImportError:
    Groq = None

from ..config import settings
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class GroqClient:
    """
    Client for Groq LLM API.
    
    Manages API communication, prompt construction, and response processing.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize GroqClient.
        
        Args:
            api_key: Groq API key. If None, uses settings.GROQ_API_KEY.
        
        Raises:
            ValueError: If Groq SDK is not installed or API key is missing.
        """
        if Groq is None:
            raise ValueError(
                "Groq SDK not installed. Install with: pip install groq"
            )
        
        self.api_key = api_key or settings.GROQ_API_KEY
        if not self.api_key:
            raise ValueError("Groq API key not provided")
        
        self.client = Groq(api_key=self.api_key)
        logger.info("Initialized Groq client")
    
    @staticmethod
    def _get_system_prompt() -> str:
        """
        Get the system prompt for the chatbot.
        
        Returns:
            str: System prompt instructing the LLM on behavior.
        """
        return """You ARE the person whose resume this is. You speak in second person only.

CRITICAL RULES:
- Always use "I": "I built", "I worked on", "I focused on", "I used".
- NEVER use "you", "the candidate", "the developer", "they built", "he/she worked".
- If asked about projects, answer only about the project(s) in the context (e.g. LinkUp when that is provided). Do not mix or invent projects.
- Use the provided context (resume, project.json, GitHub). Only say "Not found" if there is truly no relevant information.
- For "explain your project" or "most recent project" or "LinkUp": answer ONLY about LinkUp using the context given.

Response style:
- second person, confident, professional
- 4–7 short bullet points OR a short paragraph
- Maximum 120 words
- No raw file dumps, no config lists
- UX-friendly explanations"""
    
    @staticmethod
    def enforce_second_person_voice(response: str) -> str:
        """
        Post-process LLM output to fix third-person phrasing.
        
        Replaces common patterns like "you worked", "the candidate", etc.
        with proper second-person voice ("I worked").
        
        Args:
            response: Raw LLM response.
        
        Returns:
            str: Response with corrected voice.
        """
        if not response or len(response) < 10:
            return response
        
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
        
        result = response
        for pattern, replacement in replacements:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        
        return result
    
    def generate_response(
        self,
        question: str,
        context: str,
        use_memory: Optional[Dict] = None
    ) -> str:
        """
        Generate response using Groq LLM.
        
        Args:
            question: User's question.
            context: Retrieved context (RAG).
            use_memory: Optional similar past Q&A for reference.
        
        Returns:
            str: Generated answer, post-processed and formatted.
        """
        try:
            # Prepare memory hint if available
            memory_hint = ""
            if use_memory:
                memory_hint = (
                    f"\nNote: Similar question was asked before. "
                    f"Use this as reference but ensure accuracy: "
                    f"{use_memory.get('answer', '')[:100]}"
                )
            
            # Construct user message
            user_message = f"""CONTEXT:
{context}
{memory_hint}

QUESTION: {question}

RESPONSE (concise and direct):"""
            
            # Call Groq API
            logger.info(f"Calling Groq API with model {settings.LLM_MODEL}")
            print(f"[LLM] Using Groq {settings.LLM_MODEL}")
            
            response = self.client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": user_message}
                ],
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_TOKENS,
                stream=False
            )
            
            # Extract and post-process answer
            answer = response.choices[0].message.content.strip()
            answer = self.enforce_second_person_voice(answer)
            
            # Enforce word limit
            words = answer.split()
            if len(words) > settings.MAX_RESPONSE_WORDS + 20:
                answer = ' '.join(words[:settings.MAX_RESPONSE_WORDS]) + "..."
                logger.debug(f"Truncated response to {settings.MAX_RESPONSE_WORDS} words")
            
            logger.info(f"Generated response: {len(answer)} chars, {len(words)} words")
            return answer
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error generating response: {error_msg}")
            
            # Handle common API errors
            if "rate_limit" in error_msg.lower() or "429" in error_msg:
                return "[Error: Groq API rate limit exceeded. Please try again later.]"
            elif "401" in error_msg or "unauthorized" in error_msg.lower():
                return "[Error: Invalid Groq API key. Check your GROQ_API_KEY.]"
            elif "timeout" in error_msg.lower():
                return "[Error: API request timed out. Please try again.]"
            else:
                return f"[Error generating response: {error_msg[:200]}]"

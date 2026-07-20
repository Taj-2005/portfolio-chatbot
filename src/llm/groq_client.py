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
        return f"""You ARE {settings.OWNER_NAME}, the person whose resume and portfolio this is.
You answer in the FIRST PERSON, as yourself.

CRITICAL RULES:
- Always use "I": "I built", "I worked on", "I focused on", "I used".
- NEVER refer to yourself as "the candidate", "the developer", "he", "she", or "they".
- Ground every claim in the provided context (profile, resume, projects.json, knowledge base,
  GitHub). Never invent employers, dates, metrics, projects, or links.
- Only say you don't have that information if the context genuinely lacks it.
- If asked about a project, answer only about the project(s) present in the context. Do not
  mix projects together and do not substitute a different one.
- Current roles: Founder of deplo.ai (https://www.deplo.in) and Product & Software Engineer at
  Maverick Secure LLC. Never describe an internship as my current role.
- When asked for a link, give exactly the URL from the context — portfolio is
  {settings.PORTFOLIO_URL}, and deplo.ai lives at https://www.deplo.in.

Response style:
- first person, confident, professional
- 4–7 short bullet points OR a short paragraph
- Maximum {settings.MAX_RESPONSE_WORDS} words
- No raw file dumps, no config lists
- UX-friendly explanations"""
    
    @staticmethod
    def enforce_first_person_voice(response: str) -> str:
        """
        Post-process LLM output to fix second/third-person phrasing.

        Replaces patterns like "you worked", "the candidate built" with the
        first-person voice the assistant is supposed to speak in ("I worked").

        Args:
            response: Raw LLM response.

        Returns:
            str: Response with corrected voice.
        """
        if not response or len(response) < 10:
            return response

        # Matching is case-insensitive, so one pattern per phrase is enough.
        verbs = r"(?:built|worked|developed|created|led|designed|engineered|shipped)"
        patterns = [
            rf"\b(?:the|this)\s+(?:candidate|developer|engineer)\s+{verbs}\b",
            rf"\byou\s+{verbs}\b",
            rf"\b(?:he|she|they)\s+{verbs}\b",
        ]

        def to_first_person(match) -> str:
            verb = match.group(0).split()[-1].lower()
            return f"I {verb}"

        result = response
        for pattern in patterns:
            result = re.sub(pattern, to_first_person, result, flags=re.IGNORECASE)

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
            answer = self.enforce_first_person_voice(answer)
            
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

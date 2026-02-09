"""
Memory management for the chatbot.

Implements a learning memory system that caches Q&A pairs
and retrieves similar past questions using Jaccard similarity.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Set

from ..config import settings
from ..utils.logger import setup_logger
from ..utils.text_processing import hash_text

logger = setup_logger(__name__)


class MemoryManager:
    """
    Manages chatbot memory for learning from past interactions.
    
    Stores Q&A pairs, finds similar questions, and provides cached answers
    when appropriate.
    """
    
    def __init__(self, memory_file: Path = None):
        """
        Initialize MemoryManager.
        
        Args:
            memory_file: Path to memory JSON file. If None, uses settings.MEMORY_FILE.
        """
        self.memory_file = memory_file or settings.MEMORY_FILE
        self.memory: List[Dict] = []
        self._load_memory()
        logger.info(f"Initialized MemoryManager with {len(self.memory)} entries")
    
    def _load_memory(self) -> None:
        """Load memory from JSON file."""
        if self.memory_file.exists():
            try:
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    self.memory = json.load(f)
                logger.info(f"Loaded {len(self.memory)} memory entries from {self.memory_file}")
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in memory file: {e}")
                self.memory = []
            except Exception as e:
                logger.error(f"Error loading memory: {e}")
                self.memory = []
        else:
            logger.info("Memory file does not exist, starting with empty memory")
            self.memory = []
    
    def _save_memory(self) -> None:
        """Save memory to JSON file."""
        try:
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(self.memory, f, indent=2, ensure_ascii=False)
            logger.debug(f"Saved {len(self.memory)} memory entries")
        except Exception as e:
            logger.error(f"Failed to save memory: {e}")
            print(f"⚠️  Warning: Could not save memory: {e}")
    
    @staticmethod
    def is_easy_question(question: str) -> bool:
        """
        Determine if a question is "easy" (general/broad).
        
        Easy questions are cached more aggressively and have lower
        similarity thresholds for matching.
        
        Args:
            question: User's question.
        
        Returns:
            bool: True if question is easy/general, False otherwise.
        """
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
    
    def _calculate_similarity(self, words1: Set[str], words2: Set[str]) -> float:
        """
        Calculate Jaccard similarity between two sets of words.
        
        Args:
            words1: First set of words.
            words2: Second set of words.
        
        Returns:
            float: Jaccard similarity score (0.0 to 1.0).
        """
        if not words1 or not words2:
            return 0.0
        
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union) if union else 0.0
    
    def find_similar_question(
        self,
        question: str,
        threshold: Optional[float] = None
    ) -> Optional[Dict]:
        """
        Find most similar past question in memory.
        
        Uses Jaccard similarity with word tokenization. Easy questions
        get a lower threshold for more aggressive matching.
        
        Args:
            question: Current question to match.
            threshold: Similarity threshold (0.0-1.0). If None, uses settings value.
        
        Returns:
            Optional[Dict]: Best matching memory entry, or None if no match above threshold.
        """
        if not self.memory:
            return None
        
        question_words = set(re.findall(r'\w+', question.lower()))
        is_easy = self.is_easy_question(question)
        
        # Lower threshold for easy questions
        effective_threshold = threshold or (
            settings.EASY_QUESTION_THRESHOLD if is_easy else settings.SIMILARITY_THRESHOLD
        )
        
        best_match = None
        best_score = 0.0
        
        for entry in self.memory:
            past_question = entry.get('question', '')
            past_words = set(re.findall(r'\w+', past_question.lower()))
            
            if not past_words:
                continue
            
            similarity = self._calculate_similarity(question_words, past_words)
            
            # Boost similarity for easy questions matching easy questions
            if is_easy and entry.get('is_easy', False):
                similarity += 0.1
            
            if similarity > best_score and similarity >= effective_threshold:
                best_score = similarity
                best_match = entry
        
        if best_match:
            logger.info(
                f"Found similar question (similarity: {best_score:.2f}): "
                f"{best_match['question'][:60]}..."
            )
        
        return best_match
    
    def store_interaction(
        self,
        question: str,
        answer: str,
        sections_used: List[str]
    ) -> None:
        """
        Store a Q&A interaction in memory.
        
        Easy questions are prioritized (added to end), while complex questions
        are inserted before the last easy question.
        
        Args:
            question: User's question.
            answer: Generated answer.
            sections_used: List of resume sections used for context.
        """
        entry = {
            'question': question,
            'answer': answer,
            'sections_used': sections_used,
            'timestamp': datetime.now().isoformat(),
            'question_hash': hash_text(question),
            'is_easy': self.is_easy_question(question)
        }
        
        is_easy = self.is_easy_question(question)
        
        # Insert strategy: easy questions at end, complex before last easy
        if is_easy:
            self.memory.append(entry)
        else:
            # Find last easy question
            last_easy_idx = None
            for i in range(len(self.memory) - 1, -1, -1):
                if self.memory[i].get('is_easy', False):
                    last_easy_idx = i
                    break
            
            if last_easy_idx is not None:
                self.memory.insert(last_easy_idx, entry)
            else:
                self.memory.append(entry)
        
        # Trim memory to max size (FIFO)
        if len(self.memory) > settings.MAX_MEMORY_ENTRIES:
            self.memory = self.memory[-settings.MAX_MEMORY_ENTRIES:]
            logger.info(f"Trimmed memory to {settings.MAX_MEMORY_ENTRIES} entries")
        
        self._save_memory()
        logger.info(f"Stored interaction in memory (total: {len(self.memory)})")
    
    def get_memory_size(self) -> int:
        """
        Get current number of memory entries.
        
        Returns:
            int: Number of stored Q&A pairs.
        """
        return len(self.memory)
    
    def clear_memory(self) -> None:
        """Clear all memory entries."""
        self.memory = []
        self._save_memory()
        logger.warning("Cleared all memory entries")

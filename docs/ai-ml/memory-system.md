# Learning Memory System

## Overview

The **Learning Memory System** is a smart caching mechanism that remembers past Q&A interactions and reuses answers for similar questions. Think of it as the chatbot's **"long-term memory"**.

---

## Why Memory?

### Problem: Redundant API Calls

**Without Memory:**
```
User 1: "What are your skills?" → API call → Answer
User 2: "What are your skills?" → API call → Same answer (waste)
User 3: "Tell me your skills?" → API call → Same answer (waste)
```

**Cost:** 3 API calls, slower responses

**With Memory:**
```
User 1: "What are your skills?" → API call → Answer → Store in memory
User 2: "What are your skills?" → Check memory → Instant answer (cached!)
User 3: "Tell me your skills?" → Check memory → Similar question → Instant answer
```

**Cost:** 1 API call, 2 instant responses from cache

### Benefits

| Benefit | Description |
|---------|-------------|
| **Faster responses** | Cached answers return instantly (<10ms vs ~1000ms LLM call) |
| **Cost savings** | Fewer API calls = lower costs |
| **Consistency** | Same question → same answer (no variation between calls) |
| **Learning** | System improves over time as memory grows |
| **Offline capability** | Can answer cached questions without internet |

---

## How It Works

### 1. Jaccard Similarity

**What is Jaccard Similarity?**

A measure of **overlap between two sets**. For text, we compare word sets.

**Formula:**
```
Jaccard(A, B) = |A ∩ B| / |A ∪ B|
```

Where:
- `A ∩ B` = words in both sets (intersection)
- `A ∪ B` = all unique words (union)

**Example:**

```python
Q1 = "What are your technical skills?"
Q2 = "What are your skills?"

# Step 1: Extract words
words1 = {"what", "are", "your", "technical", "skills"}
words2 = {"what", "are", "your", "skills"}

# Step 2: Calculate intersection and union
intersection = {"what", "are", "your", "skills"}  # 4 words
union = {"what", "are", "your", "technical", "skills"}  # 5 words

# Step 3: Calculate similarity
similarity = len(intersection) / len(union)
# = 4 / 5 = 0.8 (80% similarity)
```

**Threshold:** If similarity ≥ 0.7 (70%), consider questions similar.

**Result:** Q2 matches Q1 → Return cached answer from Q1.

### 2. Easy vs Complex Questions

Not all questions are equal! The system classifies questions into two types:

#### Easy Questions (Broad/General)

**Examples:**
- "Tell me about yourself"
- "What are your skills?"
- "Introduce yourself"
- "What technologies do you know?"

**Characteristics:**
- Broad, open-ended
- Answers don't change frequently
- Safe to cache aggressively

**Threshold:** 0.6 (60% similarity) - more lenient matching

#### Complex Questions (Specific/Detailed)

**Examples:**
- "What's the architecture of LinkUp?"
- "How did you implement real-time chat?"
- "Which project uses MongoDB and TypeScript?"

**Characteristics:**
- Specific, detailed
- Answers may vary based on context
- Require stricter matching

**Threshold:** 0.7 (70% similarity) - stricter matching

### 3. Memory Structure

Each memory entry contains:

```json
{
  "question": "What are your technical skills?",
  "answer": "I have expertise in Python, JavaScript, React...",
  "sections_used": ["SKILLS"],
  "timestamp": "2024-02-10T14:32:15.123456",
  "question_hash": "a3f5d2e8b1c9...",
  "is_easy": true
}
```

**Fields explained:**
- `question`: Original question text
- `answer`: Generated answer
- `sections_used`: Which resume sections were used (for debugging)
- `timestamp`: When this Q&A was created
- `question_hash`: MD5 hash of normalized question (for quick lookup)
- `is_easy`: Whether question is classified as "easy"

### 4. Memory Storage Strategy

Memory entries are stored with a smart **insertion strategy**:

```
[Memory Array - Oldest to Newest]
┌─────────────────────────────────────────────────┐
│ Complex Q1 | Complex Q2 | Easy Q1 | Easy Q2     │
└─────────────────────────────────────────────────┘
                            ↑
                     Last easy question
```

**Insertion rules:**
1. **Easy questions** → Added at the end (FIFO)
2. **Complex questions** → Inserted before the last easy question
3. **Reason**: Easy questions are more likely to be reused

**Why this matters:**
- Easy questions accumulate at the end
- When memory fills up (>100 entries), oldest entries are removed (FIFO)
- Easy questions have longer retention (stay in memory longer)

---

## Memory Lifecycle

### Step 1: Question Arrives
```python
question = "What are your skills?"
```

### Step 2: Check Memory
```python
similar = memory_manager.find_similar_question(question)
# Returns: {"question": "What are your technical skills?", "answer": "...", "is_easy": True}
```

### Step 3: Validate Cached Answer

**For easy questions:**
```python
if is_easy and similar.get('is_easy'):
    # Calculate exact similarity
    similarity = jaccard_similarity(question, similar['question'])
    # 0.8 (80%)
    
    cached_answer = similar['answer']
    
    # Validate cache
    is_valid = (
        similarity > 0.75 and
        cached_answer and
        'not found' not in cached_answer.lower() and
        len(cached_answer.split()) > 5
    )
    
    if is_valid:
        return cached_answer  # ✅ Use cached answer
```

**For project questions (extra validation):**
```python
if is_project_question(question):
    has_linkup = 'linkup' in cached_answer.lower()
    if not has_linkup and 'meallogger' in cached_answer.lower():
        # ❌ Cached answer mentions wrong project!
        print("[MEMORY] Cached answer invalid (wrong project) — regenerating")
        return None  # Force regeneration
```

### Step 4: Generate New Answer (if cache miss)
```python
if not cached_answer:
    answer = groq_client.generate_response(question, context)
```

### Step 5: Store in Memory
```python
memory_manager.store_interaction(question, answer, sections_used)
```

**Storage logic:**
```python
def store_interaction(question, answer, sections_used):
    entry = {
        'question': question,
        'answer': answer,
        'sections_used': sections_used,
        'timestamp': datetime.now().isoformat(),
        'question_hash': hash_question(question),
        'is_easy': is_easy_question(question)
    }
    
    if is_easy_question(question):
        # Easy question: append to end
        memory.append(entry)
    else:
        # Complex question: insert before last easy question
        last_easy_idx = find_last_easy_index(memory)
        if last_easy_idx:
            memory.insert(last_easy_idx, entry)
        else:
            memory.append(entry)
    
    # Trim to max size (100 entries)
    if len(memory) > 100:
        memory = memory[-100:]  # Keep newest 100
    
    save_memory()  # Persist to memory.json
```

---

## Memory File Format

**Location:** `memory.json` in project root

**Example:**
```json
[
  {
    "question": "What are your technical skills?",
    "answer": "I have expertise in Python, JavaScript, React, Next.js, MongoDB, Firebase, AWS, and Tailwind CSS. I'm proficient in full-stack development with a focus on modern web technologies and cloud platforms.",
    "sections_used": ["SKILLS"],
    "timestamp": "2024-02-10T10:15:30.123456",
    "question_hash": "d4f8a9b2c7e1...",
    "is_easy": true
  },
  {
    "question": "Tell me about your most recent project",
    "answer": "I built LinkUp, a modern social platform using Next.js, MongoDB, TypeScript, Socket.IO, and AWS. The app enables real-time chat, customizable profiles, and instant link sharing.",
    "sections_used": ["PROJECTS"],
    "timestamp": "2024-02-10T10:16:45.789012",
    "question_hash": "b2c9d7e3a5f1...",
    "is_easy": true
  }
]
```

---

## Performance Characteristics

### Time Complexity

| Operation | Complexity | Time (100 entries) |
|-----------|------------|-------------------|
| **Find similar question** | O(n) | ~8ms |
| **Store interaction** | O(n) | ~5ms |
| **Load memory from disk** | O(n) | ~10ms |
| **Save memory to disk** | O(n) | ~15ms |

Where `n` = number of memory entries (max 100).

**Why O(n)?** We scan all memory entries to find the best match. This is acceptable for small memory sizes (<1000 entries).

**Optimization idea:** Use inverted index (word → questions) for O(log n) lookup.

### Space Complexity

**Per entry:** ~300 bytes (JSON)
**Max memory:** 100 entries × 300 bytes = **30KB**

**Disk usage:** Negligible (<1MB even with 1000 entries)

### Hit Rate

Based on typical portfolio Q&A patterns:

| Question Type | Cache Hit Rate |
|---------------|----------------|
| **Easy questions** | 80% (high reuse) |
| **Complex questions** | 30% (low reuse) |
| **Overall** | ~55% (averaged) |

**Example:** Out of 100 questions, ~55 are answered from cache (instant), 45 require LLM call.

---

## Advanced Features

### 1. Question Normalization

Before comparing questions, we normalize them:

```python
def normalize_question(question):
    # Convert to lowercase
    question = question.lower()
    
    # Remove punctuation
    question = re.sub(r'[^\w\s]', '', question)
    
    # Remove extra whitespace
    question = ' '.join(question.split())
    
    return question

# Example
"What are your skills?" → "what are your skills"
"What are your skills???" → "what are your skills"
"WHAT ARE YOUR SKILLS" → "what are your skills"
```

**Why:** Ensures "What are your skills?" matches "what are your skills?"

### 2. Memory Hints for LLM

Even when cache doesn't match perfectly, we still use it as a **hint** for the LLM:

```python
if similar:
    memory_hint = f"""
    Note: Similar question was asked before.
    Use this as reference but ensure accuracy: {similar['answer'][:100]}
    """
    
    response = llm.generate(question, context, memory_hint=memory_hint)
```

**Why:** Improves consistency across similar (but not identical) questions.

### 3. Memory Statistics

Track memory usage and effectiveness:

```python
stats = chatbot.get_memory_stats()
# {
#   'total_entries': 45,
#   'easy_questions': 30,
#   'complex_questions': 15
# }
```

---

## Memory Management Best Practices

### 1. When to Clear Memory

**Scenarios:**
- Resume updated significantly (new job, new skills)
- Major project added/removed
- Answers no longer accurate

**How:**
```python
memory_manager.clear_memory()
```

### 2. Memory Size Tuning

**Current:** 100 entries (default)

**Increase** (e.g., 500 entries) if:
- High traffic (1000+ questions/day)
- Many unique questions (diverse Q&A)
- Storage not a concern

**Decrease** (e.g., 50 entries) if:
- Low traffic (<100 questions/day)
- Storage constrained (embedded devices)
- Want only recent answers

**Configure:**
```python
# src/config/settings.py
MAX_MEMORY_ENTRIES = 100  # Change this
```

### 3. Memory Backup

**Backup memory periodically:**
```bash
cp memory.json memory_backup_$(date +%Y%m%d).json
```

**Why:** Recover if memory gets corrupted or accidentally cleared.

---

## Comparison to Other Approaches

### vs. No Caching

| Metric | No Cache | With Memory |
|--------|----------|-------------|
| **Latency** | ~1000ms | ~10ms (cached) |
| **API calls** | 100% | ~45% |
| **Cost** | $X | ~0.45X |
| **Consistency** | Variable | Guaranteed |

### vs. Redis Cache

| Metric | Memory (JSON file) | Redis Cache |
|--------|-------------------|-------------|
| **Complexity** | Simple (no dependencies) | Complex (Redis server) |
| **Speed** | ~10ms | ~2ms |
| **Scalability** | <1000 entries | Millions of entries |
| **Persistence** | File-based | Memory + persistence |
| **Cost** | Free | Redis hosting cost |

**Recommendation:** 
- **JSON file** (current) for <1000 entries
- **Redis** for high-scale production (1M+ questions/day)

---

## Debugging Memory Issues

### Issue 1: "Cache not hitting (expected similarity)"

**Diagnosis:**
```bash
LOG_LEVEL=DEBUG python main.py "what are your skills?"
```

**Look for:**
```
[memory.memory_manager] Found similar question (similarity: 0.82): What are your technical skills?
```

**If similarity < 0.7:** Questions too different, adjust wording or lower threshold.

### Issue 2: "Cached answer is outdated"

**Fix:**
```python
# Clear specific entry
import json

with open('memory.json', 'r') as f:
    memory = json.load(f)

# Remove outdated entries
memory = [e for e in memory if 'old project name' not in e['answer'].lower()]

with open('memory.json', 'w') as f:
    json.dump(memory, f, indent=2)
```

Or clear all memory:
```bash
rm memory.json
```

### Issue 3: "Memory file corrupted"

**Symptoms:** `JSONDecodeError` when loading memory

**Fix:**
```bash
# Backup corrupted file
mv memory.json memory_corrupted.json

# Start fresh
# (memory.json will be recreated on next question)
python main.py "test question"
```

---

## Future Enhancements

### 1. Semantic Similarity (Embeddings)

**Current:** Word-based Jaccard similarity

**Upgrade:** Embedding-based semantic similarity
```python
# Current
similarity = jaccard_similarity(words1, words2)

# Upgraded
embedding1 = sentence_transformer.encode(question1)
embedding2 = sentence_transformer.encode(question2)
similarity = cosine_similarity(embedding1, embedding2)
```

**Why:** Better paraphrasing detection
- "What are your skills?" ≈ "Tell me your expertise"
- "Main project?" ≈ "Most recent work?"

### 2. Expiration Timestamps

**Current:** No expiration (entries persist until memory fills)

**Upgrade:** Auto-expire old entries
```python
# Add to entry
"expires_at": "2024-03-10T00:00:00"  # 30 days from creation

# On load, filter expired
memory = [e for e in memory if not is_expired(e)]
```

**Why:** Ensures answers stay current with resume updates.

### 3. Personalized Memory (Multi-User)

**Current:** Single global memory

**Upgrade:** User-specific memory
```python
memory_file = Path(f"memory_{user_id}.json")
```

**Why:** Supports multiple portfolios on same server.

---

## Next Steps

- **[LLM Integration](llm-integration.md)** - How Groq API works
- **[Architecture](architecture.md)** - Full system design
- **[RAG Explained](rag-explained.md)** - Context retrieval

---

## References

- [Jaccard Similarity](https://en.wikipedia.org/wiki/Jaccard_index)
- [Caching Strategies](https://aws.amazon.com/caching/best-practices/)
- [Redis vs File-based Cache](https://redis.io/docs/manual/persistence/)

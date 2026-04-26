# System Architecture - Portfolio Chatbot

## High-Level Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                         USER / CLIENT                           │
│            (CLI, Web UI, API Consumer, Mobile App)              │
└────────────────┬───────────────────────────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────────────────────────┐
│                      API LAYER                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  main.py (CLI) or api/index.py (Vercel Serverless)      │  │
│  │  → Handles GET/POST requests                             │  │
│  │  → Validates input                                        │  │
│  │  → Returns JSON response                                  │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────┬───────────────────────────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────────────────────────┐
│                   CORE ORCHESTRATION                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  PortfolioChatbot (src/core/chatbot.py)                  │  │
│  │  → Coordinates all modules                               │  │
│  │  → Main answer_question() method                         │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────┬───────────────────────────────────────────────┘
                 │
    ┌────────────┼────────────┐
    │            │            │
    ▼            ▼            ▼
┌────────┐  ┌────────┐  ┌────────┐
│ Memory │  │  RAG   │  │  LLM   │
│ System │  │ System │  │ Client │
└────────┘  └────────┘  └────────┘
    │            │            │
    │            ▼            │
    │    ┌───────────────┐   │
    │    │  Parsers:     │   │
    │    │  • Resume     │   │
    │    │  • Projects   │   │
    │    └───────────────┘   │
    │            │            │
    │            ▼            │
    │    ┌───────────────┐   │
    │    │  Web:         │   │
    │    │  • Scraper    │   │
    │    │  • SearchAPI  │   │
    │    └───────────────┘   │
    │                         │
    ▼                         ▼
┌────────────────┐    ┌──────────────┐
│  memory.json   │    │  Groq API    │
│  (Local disk)  │    │  (External)  │
└────────────────┘    └──────────────┘
```

---

## Module-Level Architecture

### 1. Config Module (`src/config/`)

**Purpose:** Centralized configuration management

```python
settings.py
├── Settings (class)
│   ├── ROOT_DIR
│   ├── GROQ_API_KEY
│   ├── MAX_CONTEXT_SIZE
│   ├── LLM_TEMPERATURE
│   └── validate()
```

**Responsibilities:**
- Load environment variables (.env)
- Provide constants (MAX_CONTEXT_SIZE, LLM_MODEL, etc.)
- Validate configuration (API keys present)
- Expose paths (DOCS_DIR, MEMORY_FILE)

**Why centralized config?**
- ✅ Single source of truth
- ✅ Easy to change parameters
- ✅ Environment-specific overrides (.env)
- ✅ Type safety (IDE autocomplete)

---

### 2. Parsers Module (`src/parsers/`)

**Purpose:** Load and parse resume and project data

```
parsers/
├── resume_loader.py
│   └── ResumeLoader
│       ├── _extract_text_from_pdf()
│       ├── _extract_text_from_docx()
│       ├── _read_text_file()
│       └── load_resume() → (sections, links, full_text)
├── project_loader.py
│   └── ProjectLoader
│       ├── _project_to_text()
│       ├── _find_linkup_project()
│       └── load_project_json() → project_data
└── __init__.py
```

**Data Flow:**
```
docs/resume.pdf ──→ ResumeLoader ──→ {
    "EXPERIENCE": "...",
    "PROJECTS": "...",
    "SKILLS": "...",
    ...
}

docs/projects.json ──→ ProjectLoader ──→ {
    "projects": [...],
    "linkup": {...},
    "linkup_text": "..."
}
```

**Key Features:**
- Multi-format support (PDF, DOCX, TXT, MD, TEX)
- LaTeX cleaning (removes \section{}, \textbf{}, etc.)
- Section extraction (EXPERIENCE, PROJECTS, SKILLS, etc.)
- Link extraction (URLs from resume)

---

### 3. Memory Module (`src/memory/`)

**Purpose:** Learning memory system with Q&A caching

```
memory/
├── memory_manager.py
│   └── MemoryManager
│       ├── _load_memory()
│       ├── _save_memory()
│       ├── is_easy_question()
│       ├── find_similar_question() → similar_entry
│       └── store_interaction()
└── __init__.py
```

**Data Structure (memory.json):**
```json
[
  {
    "question": "What are your skills?",
    "answer": "I have expertise in...",
    "sections_used": ["SKILLS"],
    "timestamp": "2024-02-10T10:15:30",
    "question_hash": "d4f8a9b2...",
    "is_easy": true
  },
  ...
]
```

**Algorithm: Jaccard Similarity**
```python
def jaccard_similarity(words1, words2):
    intersection = words1 & words2
    union = words1 | words2
    return len(intersection) / len(union)
```

**Threshold:**
- Easy questions: 0.6 (60%)
- Complex questions: 0.7 (70%)

---

### 4. Web Module (`src/web/`)

**Purpose:** Web scraping and search augmentation

```
web/
├── scraper.py
│   └── WebScraper
│       ├── scrape_webpage() → (title, content, success)
│       ├── process_github_links() → [(source, content), ...]
│       └── should_use_web_augmentation() → (bool, query, reason)
├── searchapi_client.py
│   └── SearchAPIClient
│       └── search(query) → search_results
└── __init__.py
```

**Web Augmentation Flow:**
```
1. Check if augmentation needed
   ↓
   If context < 800 chars OR "github" in question
   ↓
2. Try GitHub scraping
   → Extract README from linked repos
   ↓
3. Try SearchAPI (if API key available)
   → Query Google for additional context
   ↓
4. Add web content to context (priority 2-3)
```

**User-Agent Spoofing:**
```python
headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)...'}
response = requests.get(url, headers=headers)
```

**Why?** Prevents blocking by GitHub/web servers that reject bot traffic.

---

### 5. RAG Module (`src/rag/`)

**Purpose:** Retrieval-Augmented Generation (context selection)

```
rag/
├── question_classifier.py
│   └── QuestionClassifier
│       ├── classify_sections() → ["SKILLS", "EXPERIENCE", ...]
│       ├── is_project_intent_question() → bool
│       ├── requires_linkup_only() → bool
│       ├── has_explicit_linkup_mention() → bool
│       ├── detect_project_intent() → "linkup_only" | "keyword" | ...
│       └── extract_keyword_from_question() → "firebase" | ...
├── context_selector.py
│   └── ContextSelector
│       ├── prioritize_linkup_project() → linkup_context
│       ├── keyword_context_search() → keyword_context
│       ├── _rank_context_sources() → ranked_sources
│       ├── select_relevant_context() → final_context
│       └── _build_general_context() → general_context
└── __init__.py
```

**Intent Detection Flow:**
```
Question: "Tell me about your project"
    ↓
QuestionClassifier.detect_project_intent()
    ↓
    ┌─────────────────────────────────┐
    │ Check patterns:                 │
    │ 1. Explicit LinkUp? → explicit  │
    │ 2. "Main project"? → linkup_only│
    │ 3. Tech keyword? → keyword      │
    │ 4. Default → general            │
    └─────────────────────────────────┘
    ↓
Intent: "linkup_only"
    ↓
ContextSelector.prioritize_linkup_project()
    ↓
Context: "--- PROJECT (LinkUp) --- ..."
```

**Context Ranking:**
| Priority | Source | Example |
|----------|--------|---------|
| **1** | Resume sections | EXPERIENCE, PROJECTS, SKILLS |
| **2** | Web content | GitHub README |
| **3** | SearchAPI | Google search results |

---

### 6. LLM Module (`src/llm/`)

**Purpose:** Groq API integration for text generation

```
llm/
├── groq_client.py
│   └── GroqClient
│       ├── _get_system_prompt() → system_prompt
│       ├── enforce_second_person_voice() → corrected_text
│       └── generate_response() → answer
└── __init__.py
```

**LLM Call Flow:**
```
1. Construct prompt
   System: "You ARE the person..."
   User: "CONTEXT: ...\nQUESTION: ..."
   ↓
2. Call Groq API
   client.chat.completions.create(
       model="llama-3.1-8b-instant",
       messages=[...],
       temperature=0.2,
       max_tokens=220
   )
   ↓
3. Extract response
   response.choices[0].message.content
   ↓
4. Post-process
   → Fix voice ("you worked" → "I worked")
   → Truncate to 120 words
   ↓
5. Return answer
```

**Error Handling:**
- 429 (Rate Limit) → Return helpful error message
- 401 (Auth) → Suggest checking API key
- Timeout → Suggest retry

---

### 7. Core Module (`src/core/`)

**Purpose:** Main orchestration logic

```
core/
├── chatbot.py
│   └── PortfolioChatbot
│       ├── __init__() → Initialize all components
│       ├── _load_data() → Load resume + projects
│       ├── _check_memory_for_cached_answer() → cached_answer
│       ├── answer_question() → final_answer
│       └── get_memory_stats() → stats
└── __init__.py
```

**Main Flow (`answer_question()`):**
```python
def answer_question(question: str) -> str:
    # 1. Check memory
    similar = memory_manager.find_similar_question(question)
    if similar and is_valid_cache(similar):
        return similar['answer']  # Fast path
    
    # 2. Select initial context (RAG)
    initial_context = context_selector.select_relevant_context(
        sections, web_content, question, project_data=project_data
    )
    
    # 3. Check if web augmentation needed
    should_search, query, reason = web_scraper.should_use_web_augmentation(
        question, initial_context, sections, links
    )
    
    # 4. Perform web search if needed
    searchapi_content = None
    if should_search:
        searchapi_content = searchapi_client.search(query)
    
    # 5. Select final context with SearchAPI results
    final_context = context_selector.select_relevant_context(
        sections, web_content, question, searchapi_content, project_data=project_data
    )
    
    # 6. Generate response (LLM)
    response = groq_client.generate_response(question, final_context, use_memory=similar)
    
    # 7. Store in memory
    memory_manager.store_interaction(question, response, sections_used)
    
    return response
```

---

### 8. Utils Module (`src/utils/`)

**Purpose:** Shared utility functions

```
utils/
├── logger.py
│   └── setup_logger() → configured_logger
├── text_processing.py
│   ├── clean_latex_text() → cleaned_text
│   ├── extract_all_links() → {url1, url2, ...}
│   ├── categorize_links() → {"github": [...], "linkedin": [...]}
│   ├── hash_text() → "md5_hash"
│   ├── truncate_text() → truncated
│   └── normalize_whitespace() → normalized
└── __init__.py
```

---

## API Layer Architecture

### CLI (`main.py`)

```python
main()
├── 1. Validate config (GROQ_API_KEY exists)
├── 2. Parse command-line args
├── 3. Initialize PortfolioChatbot
├── 4. Call chatbot.answer_question(question)
└── 5. Print formatted response
```

**Usage:**
```bash
python main.py "What are your skills?"
```

### Vercel Serverless (`api/index.py`)

```python
handler (BaseHTTPRequestHandler)
├── do_GET() / do_POST()
│   ├── 1. Extract question from query params or JSON body
│   ├── 2. Get chatbot instance (cached per serverless instance)
│   ├── 3. Call chatbot.answer_question(question)
│   ├── 4. Return JSON: {"question": "...", "answer": "..."}
│   └── 5. Handle errors with JSON error responses
└── do_OPTIONS() → CORS headers
```

**Instance-level caching:**
```python
_chatbot_instance = None

def _get_chatbot():
    global _chatbot_instance
    if _chatbot_instance is None:
        # First request: initialize (slow ~500ms)
        _chatbot_instance = PortfolioChatbot(...)
    # Subsequent requests: use cached instance (fast ~50ms)
    return _chatbot_instance
```

**Why caching matters:**
- Resume parsing is expensive (~300ms)
- Vercel keeps instances warm for ~5 minutes
- Subsequent requests in that window are 10x faster

---

## Data Flow Diagram

### Complete Request Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     User asks question                           │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
        ┌────────────────────┐
        │  API Layer         │
        │  (main.py or       │
        │   api/index.py)    │
        └────────┬───────────┘
                 │
                 ▼
        ┌────────────────────┐
        │ PortfolioChatbot   │
        └────────┬───────────┘
                 │
    ┌────────────┼────────────┐
    │            │            │
    ▼            ▼            ▼
┌───────┐   ┌───────┐   ┌───────┐
│Memory │   │ RAG   │   │ LLM   │
│Check  │   │Select │   │Gen    │
└───┬───┘   └───┬───┘   └───┬───┘
    │           │           │
    │ Cache     │ Context   │ Answer
    │ Miss      │           │
    │           │           │
    └───────────┴───────────┘
                 │
                 ▼
        ┌────────────────────┐
        │ Post-process       │
        │ → Fix voice        │
        │ → Truncate         │
        └────────┬───────────┘
                 │
                 ▼
        ┌────────────────────┐
        │ Store in memory    │
        └────────┬───────────┘
                 │
                 ▼
        ┌────────────────────┐
        │ Return answer      │
        └────────────────────┘
```

---

## Deployment Architecture

### Local Development

```
┌─────────────────────┐
│   Developer Machine │
│  ┌───────────────┐  │
│  │   main.py     │  │
│  └───────┬───────┘  │
│          │          │
│  ┌───────▼───────┐  │
│  │   src/        │  │
│  │   (modules)   │  │
│  └───────┬───────┘  │
│          │          │
│  ┌───────▼───────┐  │
│  │   docs/       │  │
│  │   memory.json │  │
│  └───────────────┘  │
└─────────┬───────────┘
          │
          ▼
    ┌─────────────┐
    │  Groq API   │
    └─────────────┘
```

### Vercel Serverless

```
┌──────────────────────────────────────┐
│          Vercel Edge Network         │
└───────────────┬──────────────────────┘
                │
                ▼
┌──────────────────────────────────────┐
│      Vercel Serverless Function      │
│  ┌────────────────────────────────┐  │
│  │    /api/index.py (handler)     │  │
│  └──────────┬─────────────────────┘  │
│             │                         │
│  ┌──────────▼─────────────────────┐  │
│  │    src/ (imported modules)     │  │
│  └──────────┬─────────────────────┘  │
│             │                         │
│  ┌──────────▼─────────────────────┐  │
│  │    docs/ (bundled with app)    │  │
│  └────────────────────────────────┘  │
│                                       │
│  Instance-level cache:                │
│  → Resume sections                    │
│  → Project data                       │
│  → Web content                        │
└───────────────┬──────────────────────┘
                │
                ▼
          ┌─────────────┐
          │  Groq API   │
          └─────────────┘
```

**Key differences:**
- **Local:** Direct file access, persistent memory.json
- **Vercel:** Read-only filesystem (except /tmp), memory.json not persisted between instances

**Vercel limitations workaround:**
- Resume parsed once per instance (cached in memory)
- Memory system disabled in serverless (no persistence)
- Could add Redis/Supabase for persistent memory

---

## Security Architecture

### API Key Management

```
.env (local)
├── GROQ_API_KEY=gsk_...
└── SEARCHAPI_API_KEY=...
    ↓ (Never committed to git)
    ↓
Vercel Environment Variables (production)
├── GROQ_API_KEY → Encrypted in Vercel dashboard
└── SEARCHAPI_API_KEY → Encrypted in Vercel dashboard
    ↓
src/config/settings.py
├── os.getenv('GROQ_API_KEY')
└── os.getenv('SEARCHAPI_API_KEY')
```

**Security best practices:**
- ✅ Never commit `.env` to git (`.gitignore` includes `.env`)
- ✅ Use environment variables for all secrets
- ✅ Rotate API keys periodically
- ✅ Use different keys for dev/prod

### CORS Configuration

```python
# api/index.py
def do_OPTIONS(self):
    self.send_header("Access-Control-Allow-Origin", "*")
    self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    self.send_header("Access-Control-Allow-Headers", "Content-Type")
```

**Why `*` (allow all origins)?**
- Portfolio chatbot is public-facing
- No sensitive user data in responses
- Enables embedding in any website

**For production:** Consider restricting to your domain(s):
```python
self.send_header("Access-Control-Allow-Origin", "https://yourportfolio.com")
```

---

## Performance Characteristics

### Latency Breakdown

| Stage | Time | Percentage |
|-------|------|------------|
| **Memory check** | 10ms | 1% |
| **Resume parsing** (cached) | 0ms | 0% |
| **Context selection** | 50ms | 5% |
| **Web augmentation** (if needed) | 200ms | 20% |
| **LLM generation** | 800ms | 75% |
| **Post-processing** | 10ms | 1% |
| **Memory storage** | 5ms | <1% |
| **Total (cached)** | ~875ms | 100% |
| **Total (cold start)** | ~1375ms | 100% |

**Optimization opportunities:**
1. **Memory hit rate** → 55% cache hit → 55% of requests ~10ms
2. **Async LLM calls** → Parallel processing → ~500ms (batch)
3. **Streaming responses** → First token at ~200ms → Perceived latency reduction

### Throughput

**Current (Free Tier):**
- Groq: 30 requests/minute
- **Throughput: ~0.5 QPS** (questions per second)

**With Paid Tier + Redis Cache:**
- Groq: Unlimited requests
- Cache hit rate: 55%
- **Throughput: ~10-20 QPS** (with load balancing)

---

## Scalability

### Vertical Scaling (Single Instance)

**Current bottleneck:** Groq API rate limit (30 req/min free tier)

**Solution:** Upgrade to paid tier → Unlimited requests

**New bottleneck:** Python GIL (Global Interpreter Lock)

**Solution:** Use async/await or multiprocessing

### Horizontal Scaling (Multiple Instances)

```
┌──────────────┐
│ Load Balancer│
└──────┬───────┘
       │
   ┌───┴────┐
   │        │
   ▼        ▼
┌────────┐ ┌────────┐
│Instance│ │Instance│
│   1    │ │   2    │
└────────┘ └────────┘
   │        │
   └────┬───┘
        │
        ▼
   ┌─────────┐
   │  Redis  │
   │  (Cache)│
   └─────────┘
```

**Benefits:**
- 2x instances → 2x throughput
- Shared Redis cache → Consistent answers
- High availability (one instance fails → others continue)

---

## Next Steps

- **[Overview](overview.md)** - High-level AI/ML concepts
- **[RAG Explained](rag-explained.md)** - Context retrieval
- **[Memory System](memory-system.md)** - Q&A caching
- **[LLM Integration](llm-integration.md)** - Groq API

---

## References

- [System Design Primer](https://github.com/donnemartin/system-design-primer)
- [Vercel Serverless Functions](https://vercel.com/docs/functions/serverless-functions)
- [Python Best Practices](https://realpython.com/python-best-practices/)

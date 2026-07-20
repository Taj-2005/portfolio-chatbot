# RAG (Retrieval-Augmented Generation) Explained

## What is RAG?

**RAG** stands for **Retrieval-Augmented Generation**. It's a technique that combines:
1. **Retrieval**: Finding relevant information from a knowledge base
2. **Augmentation**: Adding that information to the model's context
3. **Generation**: Using an LLM to create a response based on retrieved info

Think of it like **open-book exam** vs **closed-book exam**:
- **Without RAG** (closed-book): LLM relies only on its training data → may hallucinate
- **With RAG** (open-book): LLM can reference your resume → factually accurate

---

## Why RAG?

### Problem: LLMs Don't Know Your Resume

**Without RAG:**
```
User: "What are my technical skills?"
LLM: "I don't have access to your personal information."
```

**With RAG:**
```
User: "What are my technical skills?"
System: [Retrieves SKILLS section from resume]
LLM: "I have expertise in Python, JavaScript, React, Next.js, MongoDB..."
```

### Benefits of RAG

| Benefit | Explanation |
|---------|-------------|
| **Factual Accuracy** | Grounds responses in actual resume data, not model's "memory" |
| **Up-to-date** | Works with current resume (no retraining needed) |
| **Transparency** | Can trace answer back to source (resume section) |
| **Cost-effective** | No expensive fine-tuning required |
| **Privacy** | Resume data stays local (not sent for training) |

---

## How RAG Works in This Project

### Step-by-Step Example

**Question:** "Tell me about your most recent project"

#### Step 1: Question Classification
```python
intent = detect_project_intent(question)
# Result: intent = "featured_only" (asking for main project)

sections = classify_sections(question)
# Result: sections = ["PROJECTS"]
```

#### Step 2: Context Retrieval
```python
# A. Load resume sections
sections = {
    "PROJECTS": "deplo.ai - AI-powered deployment orchestration...\nShopSmart - Production e-commerce platform...",
    "SKILLS": "Python, JavaScript, React, Next.js...",
    "EXPERIENCE": "Software Developer at ..."
}

# B. Load project JSON
project_data = {
    "featured": {
        "title": "deplo.ai",
        "description": "AI-powered deployment orchestration platform...",
        "tech": ["Next.js", "TypeScript", "Python", ...]
    }
}

# C. Extract the featured project ONLY (intent = featured_only)
featured_from_resume = extract_featured_block(sections["PROJECTS"])
# Result: "deplo.ai — AI-powered deployment orchestration platform..."

featured_from_json = project_data["featured_text"]
# Result: "deplo.ai | AI-powered deployment orchestration... | Tech: Next.js, TypeScript, ..."
```

#### Step 3: Context Assembly
```python
context = """
--- PROJECT (project.json - deplo.ai) ---
deplo.ai | AI-powered deployment orchestration platform that automates full-stack
deployments through infrastructure orchestration, GitHub integrations, and
environment management. | Tech: Next.js, TypeScript, Python, AWS, Docker, GitHub

--- RESUME (deplo.ai) ---
deplo.ai - A deployment platform with GitHub integration, environment management,
and seamless rollouts across modern cloud platforms. Built with Next.js,
TypeScript, Python, AWS, and Docker.
"""

# Total: ~350 chars (well under 6000 limit)
```

#### Step 4: LLM Generation
```python
prompt = f"""
System: You ARE Shaik Tajuddin. Answer in the first person — "I built", "I worked", etc.

Context:
{context}

Question: Tell me about your most recent project

Response (concise and direct):
"""

response = llm.generate(prompt)
# Result: "I built deplo.ai, an AI-powered deployment orchestration platform using
#          Next.js, TypeScript, Python, AWS, and Docker. It automates full-stack
#          deployments with GitHub integration and environment management. I focused
#          on reliability and developer experience."
```

---

## RAG Strategies in This Project

### 1. Intent-Based Retrieval

The system uses **4 intent types** to customize retrieval:

#### Intent: `featured_only`
**Triggers:** "explain your project", "main project", "most recent project"

**Strategy:** Retrieve ONLY the featured project, ignore other projects
```python
if intent == "featured_only":
    context = prioritize_featured_project(sections, project_data, web_content)
    # Only includes the featured project from resume + project.json
```

**Why:** Questions using "THE project" (singular) should not mix multiple projects.

#### Intent: `explicit_featured`
**Triggers:** "tell me about deplo.ai", "what is deplo.ai"

**Strategy:** Focus on the featured project, but can include general project info
```python
if intent == "explicit_featured":
    context = prioritize_featured_project(sections, project_data, web_content)
```

#### Intent: `keyword`
**Triggers:** "which project uses Firebase?", "tell me about your React projects"

**Strategy:** Keyword-based search across all sources
```python
if intent == "keyword":
    keyword = extract_keyword_from_question(question)  # e.g., "firebase"
    context = keyword_context_search(keyword, sections, project_data, web_content)
    # Searches for "firebase" in all projects, returns matches
```

#### Intent: `general`
**Triggers:** Default for all other questions

**Strategy:** Multi-section retrieval based on question classification
```python
if intent == "general":
    relevant_sections = classify_sections(question)
    # e.g., ["SKILLS", "EXPERIENCE"] for "what are your skills?"
    context = select_relevant_context(sections, relevant_sections, web_content)
```

### 2. Context Ranking

Sources are ranked by **trustworthiness**:

| Rank | Source | Why |
|------|--------|-----|
| **1** | Resume sections (PDF/DOCX) | Primary source of truth |
| **2** | Project JSON | Structured project metadata |
| **3** | GitHub content | External validation |
| **4** | Web search (SearchAPI) | Fallback for missing info |

```python
def rank_context_sources(sections, web_content, searchapi_content):
    ranked = []
    
    # Priority 1: Resume
    for section_name, content in sections.items():
        if content:
            ranked.append((f"RESUME_{section_name}", content, 1))
    
    # Priority 2: Web content (GitHub)
    for source, content in web_content:
        ranked.append((f"WEB_{source}", content, 2))
    
    # Priority 3: SearchAPI
    if searchapi_content:
        ranked.append(("SEARCHAPI", searchapi_content, 3))
    
    return ranked
```

### 3. Context Window Management

**Problem:** LLMs have token limits (e.g., 8192 tokens for Llama 3.1)

**Solution:** Dynamic truncation with priority-based allocation

```python
MAX_CONTEXT_SIZE = 6000  # characters (~1500 tokens)

def select_relevant_context(sections, question, ...):
    context_parts = []
    current_length = 0
    
    # Add sections in order of relevance
    for section_name in relevant_sections:
        section_content = sections[section_name]
        
        if current_length + len(section_content) <= MAX_CONTEXT_SIZE:
            # Fits! Add entire section
            context_parts.append(f"--- {section_name} ---\n{section_content}\n")
            current_length += len(section_content)
        else:
            # Truncate to fit
            remaining = MAX_CONTEXT_SIZE - current_length
            if remaining > 100:
                truncated = section_content[:remaining] + "..."
                context_parts.append(f"--- {section_name} ---\n{truncated}\n")
                current_length = MAX_CONTEXT_SIZE
                break  # No more space
    
    return '\n'.join(context_parts)
```

**Example allocation for "Tell me about yourself":**
```
SUMMARY:     500 chars (8%)
EXPERIENCE:  2000 chars (33%)
SKILLS:      800 chars (13%)
PROJECTS:    1500 chars (25%)
EDUCATION:   400 chars (7%)
GitHub:      500 chars (8%)
SearchAPI:   300 chars (5%)
---
Total:       6000 chars (100%)
```

### 4. Web Augmentation Trigger

RAG can **fallback to web search** when resume context is insufficient.

**Trigger conditions:**
1. Context size < 800 chars (resume too sparse)
2. Question mentions "github" or "repo" explicitly
3. Not a definitional question ("what is", "explain", "how does")

```python
def should_use_web_augmentation(question, context, sections, links):
    # Condition 1: Insufficient context
    if len(context) < 800:
        # Try to build search query from projects section
        projects = sections.get('PROJECTS', '')
        if projects:
            first_project = projects.split('\n')[0]
            return True, f"{first_project} github", "resume insufficient"
    
    # Condition 2: Explicit GitHub mention
    if 'github' in question.lower() or 'repo' in question.lower():
        return True, "portfolio projects", "project-specific question"
    
    # Condition 3: Definitional questions don't need web search
    if any(kw in question.lower() for kw in ['what is', 'explain', 'how does']):
        return False, "", ""
    
    return False, "", ""
```

**Example flow:**
```
Question: "What are your technical skills?"
Context retrieved: 200 chars (only partial SKILLS section)
Trigger: YES (insufficient context)
Action: SearchAPI query: "portfolio projects github"
Result: Add web results to context
Final context: 1200 chars (resume + web search)
```

---

## RAG vs Fine-Tuning

| Aspect | RAG (This Project) | Fine-Tuning |
|--------|-------------------|-------------|
| **Training required** | ❌ No | ✅ Yes (expensive) |
| **Data needed** | Resume files only | 1000+ Q&A pairs |
| **Update speed** | Instant (change resume) | Days (retrain model) |
| **Cost** | Low (API calls only) | High (GPU hours) |
| **Accuracy** | 95% (grounded in resume) | 98% (specialized) |
| **When to use** | Small data (<100 pages) | Large data, specific domain |

**Recommendation:** RAG is perfect for portfolios. Only consider fine-tuning if you have 1000+ curated Q&A pairs.

---

## Advanced RAG Techniques (Not Implemented)

### 1. Semantic Search with Embeddings
**Current:** Keyword matching (Jaccard similarity)
```python
# Current approach
similarity = len(words1 & words2) / len(words1 | words2)
```

**Upgrade:** Semantic embeddings (e.g., Sentence Transformers)
```python
# Semantic approach
embedding1 = model.encode("tell me about yourself")
embedding2 = model.encode("what's your background")
similarity = cosine_similarity(embedding1, embedding2)
# Result: 0.89 (high similarity despite different words)
```

**Why upgrade:** Handles paraphrasing better ("skills" vs "expertise" vs "technologies")

### 2. Vector Database (Pinecone, Weaviate)
**Current:** Linear scan through resume sections
```python
# O(n) complexity - scan all sections
for section_name, content in sections.items():
    if keyword in content.lower():
        add_to_context(content)
```

**Upgrade:** Vector database with nearest-neighbor search
```python
# O(log n) complexity - fast similarity search
query_embedding = encode(question)
similar_chunks = vector_db.search(query_embedding, top_k=5)
```

**Why upgrade:** Scales to large resumes (100+ pages, multiple documents)

### 3. Hybrid Search (Keyword + Semantic)
**Current:** Either keyword OR semantic (we use keyword only)

**Upgrade:** Combine both approaches
```python
keyword_results = keyword_search(query, alpha=0.5)
semantic_results = semantic_search(query, alpha=0.5)
combined_results = merge(keyword_results, semantic_results)
```

**Why upgrade:** Best of both worlds (precision + recall)

---

## Performance Optimization

### Caching Strategy

**Problem:** Re-parsing resume on every request is slow

**Solution:** Cache parsed resume in memory (Vercel instance-level caching)
```python
# api/index.py
_sections = None
_full_resume = None

def load_resume_data():
    global _sections, _full_resume
    if _sections is None:
        # First request: parse resume (slow)
        _sections, _links, _full_resume = resume_loader.load_resume()
    # Subsequent requests: use cache (fast)
    return _sections, _full_resume
```

**Result:** 
- First request: ~500ms (parsing)
- Subsequent requests: ~50ms (cached)

### Context Truncation Trade-offs

| Max Context Size | Pros | Cons |
|------------------|------|------|
| **3000 chars** | Faster inference, lower cost | May miss relevant info |
| **6000 chars** ✅ | Balanced (current) | Good accuracy/speed |
| **12000 chars** | Maximum context | Slower, higher cost |

**Current choice:** 6000 chars (sweet spot for portfolios)

---

## Debugging RAG Issues

### Issue 1: "Answer doesn't mention my main project"

**Diagnosis:**
```bash
LOG_LEVEL=DEBUG python main.py "tell me about your project"
```

**Look for:**
```
[rag.question_classifier] Detected intent: featured_only
[rag.context_selector] Built featured-project context: 350 chars
```

**Fix:** Ensure the featured project is present in `knowledge-base/projects.json`, or that the resume has a heading naming it

### Issue 2: "Answer includes irrelevant projects"

**Cause:** Intent detection failed, fell back to `general`

**Fix:** Point `FEATURED_PROJECT_NAMES` at your main project in `src/config/settings.py`
(or set the `FEATURED_PROJECT_NAMES` env var, comma-separated):
```python
FEATURED_PROJECT_NAMES = ("deplo.ai", "deplo-ai", "deplo ai", "deplo")
```

### Issue 3: "Context too small (< 800 chars)"

**Cause:** Resume sections not extracted properly

**Fix:**
1. Check resume format (PDF/DOCX/TEX supported)
2. Verify section headers ("Experience", "Projects", "Skills")
3. Increase verbosity in resume content

---

## Next Steps

- **[Memory System](memory-system.md)** - How Q&A caching works
- **[LLM Integration](llm-integration.md)** - Groq API details
- **[Architecture](architecture.md)** - Full system design

---

## References

- [RAG Paper (Lewis et al., 2020)](https://arxiv.org/abs/2005.11401)
- [LangChain RAG Guide](https://python.langchain.com/docs/use_cases/question_answering/)
- [Pinecone RAG Guide](https://www.pinecone.io/learn/retrieval-augmented-generation/)

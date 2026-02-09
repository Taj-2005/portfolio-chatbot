# LLM Integration - Groq API

## Overview

This project uses **Groq's API** to access **Llama 3.1 (8B parameters)** for text generation. This document explains how LLMs work, why we chose Groq, and how we integrate it.

---

## What is an LLM?

**LLM** = **Large Language Model**

A **neural network trained on billions of words** from the internet to:
- Understand natural language
- Generate human-like text
- Answer questions
- Follow instructions

**Think of it like:**
- **Training:** Reading every book in a library (learning patterns)
- **Inference:** Using that knowledge to answer questions (applying patterns)

**In this project:** We use the **pre-trained** Llama 3.1 model (already trained by Meta), accessed via Groq's API.

---

## Why Groq?

### Groq vs Alternatives

| Provider | Model | Speed | Cost | Quality |
|----------|-------|-------|------|---------|
| **Groq** ✅ | Llama 3.1 8B | <1s | Free: 30/min | 9/10 |
| OpenAI | GPT-4 Turbo | ~2s | $0.01/1K tokens | 10/10 |
| OpenAI | GPT-3.5 Turbo | ~1s | $0.0005/1K tokens | 8/10 |
| Anthropic | Claude 3 | ~1.5s | $0.008/1K tokens | 9.5/10 |
| Local (Ollama) | Llama 3.1 8B | ~5s | Free | 9/10 |

**Why Groq wins for portfolios:**
1. **Fast inference** (<1s) - powered by custom LPU hardware
2. **Free tier** (30 requests/min) - perfect for personal portfolios
3. **Good quality** - Llama 3.1 8B rivals GPT-3.5 for Q&A
4. **Open model** - Llama is open-source (transparency)

### Groq's Secret: LPU Architecture

**GPU** (Graphics Processing Unit) - Traditional AI hardware
- Designed for parallel matrix operations
- Good for training and inference
- ~2s response time for LLMs

**LPU** (Language Processing Unit) - Groq's custom hardware
- Designed specifically for sequential language operations
- **10x faster** than GPUs for inference
- ~200ms response time for same model

**Result:** Groq + Llama 3.1 = Near-GPT-4 quality at 10x speed

---

## Llama 3.1 Model Details

### Architecture

**Model:** Llama 3.1 8B Instruct
- **Parameters:** 8 billion (8B)
- **Architecture:** Decoder-only transformer
- **Context window:** 128K tokens (~96K words)
- **Training data:** 15 trillion tokens (books, web, code)
- **Training:** Meta AI (2024)

**What "8B parameters" means:**
- The model has 8 billion learned weights
- Each weight is a number that captures a pattern (e.g., "Python" often precedes "programming")
- More parameters = more capacity to learn complex patterns
- 8B is "small" (GPT-4 has ~1.7 trillion), but efficient for Q&A

### Capabilities

**Strengths:**
- ✅ Question answering (perfect for portfolios)
- ✅ Summarization
- ✅ Instruction following
- ✅ Technical concepts
- ✅ Multiple languages

**Weaknesses:**
- ❌ Math/calculations (use calculator tool)
- ❌ Real-time info (pre-2024 training cutoff)
- ❌ Long-form creative writing (shorter outputs)

**For portfolios:** Llama 3.1 8B is **overkill** (in a good way). Even smaller models (3B) would work well.

---

## Integration Details

### 1. API Setup

**Installation:**
```bash
pip install groq==1.0.0
```

**Initialization:**
```python
from groq import Groq

client = Groq(api_key="gsk_...")
```

**API Key:**
- Get free key at: https://console.groq.com/keys
- Free tier: 30 requests/minute
- Paid tier: No limits, ~$0.10/million tokens

### 2. Prompt Engineering

**The prompt is everything!** LLMs are highly sensitive to how you phrase the prompt.

#### System Prompt (Who is the LLM?)

```python
system_prompt = """You ARE the person whose resume this is. You speak in second person only.

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
```

**Why this matters:**
- **"You ARE the person"** → Forces first-person voice ("I built" not "they built")
- **"CRITICAL RULES"** → Strong enforcement prevents common mistakes
- **"Maximum 120 words"** → Keeps responses concise
- **"UX-friendly"** → Avoids technical jargon dumps

#### User Message (Context + Question)

```python
user_message = f"""CONTEXT:
{relevant_context}
{memory_hint}

QUESTION: {question}

RESPONSE (concise and direct):"""
```

**Structure:**
1. **Context first** → RAG-selected resume sections, project data, web content
2. **Question second** → What the user asked
3. **"RESPONSE"** → Signals to start generating

**Example full prompt:**
```
System: You ARE the person whose resume this is. Always use "I"...

User:
CONTEXT:
--- RESUME_SKILLS ---
Python, JavaScript, React, Next.js, MongoDB, Firebase, AWS, Tailwind CSS

--- PROJECT (LinkUp) ---
LinkUp | A social platform using Next.js, MongoDB, TypeScript, Socket.IO, AWS

QUESTION: What are your technical skills?

RESPONSE (concise and direct):
```

**LLM output:**
```
I have expertise in Python, JavaScript, React, Next.js, MongoDB, Firebase,
AWS, and Tailwind CSS. I'm proficient in full-stack development with a focus
on modern web technologies and cloud platforms.
```

### 3. API Parameters

**Key parameters for `chat.completions.create()`:**

```python
response = client.chat.completions.create(
    model="llama-3.1-8b-instant",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ],
    temperature=0.2,
    max_tokens=220,
    stream=False
)
```

**Parameter explanations:**

| Parameter | Value | Why |
|-----------|-------|-----|
| `model` | `llama-3.1-8b-instant` | Fast inference model |
| `temperature` | 0.2 | Low = focused, factual responses (range: 0-1) |
| `max_tokens` | 220 | ~165 words output limit |
| `stream` | False | Get full response at once (no streaming) |

#### Temperature Deep Dive

**Temperature** controls randomness in generation:

| Temperature | Behavior | Example |
|-------------|----------|---------|
| **0.0** | Deterministic (always same output) | "I built LinkUp" (exact same every time) |
| **0.2** ✅ | Mostly consistent, slight variation | "I built LinkUp" or "I developed LinkUp" |
| **0.5** | Balanced creativity | "I created LinkUp, an innovative social platform" |
| **1.0** | Creative, varied | "I pioneered a revolutionary networking solution called LinkUp" |
| **2.0** | Chaotic, unpredictable | "LinkUp emerged from my vision of quantum social graphs" |

**For portfolios:** 0.2 is perfect (factual but not robotic).

#### Max Tokens Calculation

**Token** ≈ 0.75 words (English)

```
max_tokens = 220
→ ~165 words maximum
→ ~120 words target (with buffer)
```

**Why 220?**
- Target: 120 words (~160 tokens)
- Buffer: +60 tokens for longer words, punctuation
- Safety: Truncate if exceeds

### 4. Response Post-Processing

**Raw LLM output may have issues:**
1. Third-person voice ("You worked", "The developer")
2. Too long (>120 words)
3. Formatting issues

**Solution: Post-processing pipeline**

#### Step 1: Enforce Second-Person Voice

```python
def enforce_second_person_voice(response):
    replacements = [
        (r"\bYou\s+worked\b", "I worked"),
        (r"\bThe\s+candidate\s+", "I "),
        (r"\bThe\s+developer\s+", "I "),
        (r"\bThey\s+built\b", "I built"),
        # ... more patterns
    ]
    
    for pattern, replacement in replacements:
        response = re.sub(pattern, replacement, response, flags=re.IGNORECASE)
    
    return response
```

**Example:**
```
Before: "You worked on LinkUp using Next.js and MongoDB."
After:  "I worked on LinkUp using Next.js and MongoDB."
```

#### Step 2: Truncate to Word Limit

```python
words = response.split()
if len(words) > MAX_RESPONSE_WORDS + 20:  # 120 + buffer
    response = ' '.join(words[:MAX_RESPONSE_WORDS]) + "..."
```

**Example:**
```
Before: (150 words of detailed explanation...)
After:  (First 120 words)...
```

---

## Error Handling

### Common API Errors

#### 1. Rate Limit (429)

**Error:**
```
groq.RateLimitError: Rate limit exceeded (30 requests/minute)
```

**Handling:**
```python
try:
    response = client.chat.completions.create(...)
except Exception as e:
    if "rate_limit" in str(e).lower() or "429" in str(e):
        return "[Error: Groq API rate limit exceeded. Please try again later.]"
```

**Solutions:**
- Wait 60 seconds
- Implement request throttling
- Upgrade to paid tier (no limits)

#### 2. Invalid API Key (401)

**Error:**
```
groq.AuthenticationError: Invalid API key
```

**Handling:**
```python
if "401" in str(e) or "unauthorized" in str(e).lower():
    return "[Error: Invalid Groq API key. Check your GROQ_API_KEY.]"
```

**Solution:** Verify `.env` file has correct `GROQ_API_KEY=gsk_...`

#### 3. Timeout

**Error:**
```
requests.exceptions.Timeout: Request timed out
```

**Handling:**
```python
if "timeout" in str(e).lower():
    return "[Error: API request timed out. Please try again.]"
```

**Solutions:**
- Retry with exponential backoff
- Check internet connection
- Use shorter context (reduce input size)

---

## Performance Optimization

### 1. Context Size Management

**Problem:** Larger context = slower inference

**Solution:** Limit context to 6000 chars (~1500 tokens)

```python
MAX_CONTEXT_SIZE = 6000

if len(context) > MAX_CONTEXT_SIZE:
    context = context[:MAX_CONTEXT_SIZE] + "..."
```

**Impact:**
- 1000 chars context: ~300ms inference
- 6000 chars context: ~800ms inference
- 12000 chars context: ~1500ms inference

### 2. Caching via Memory System

**Without cache:**
- Every question → LLM call → ~1000ms

**With cache:**
- Similar question → Memory lookup → ~10ms (100x faster!)

See [Memory System](memory-system.md) for details.

### 3. Async/Batch Requests (Future)

**Current:** Sequential requests
```python
answer1 = llm.generate(q1, ctx1)  # Wait 1000ms
answer2 = llm.generate(q2, ctx2)  # Wait 1000ms
# Total: 2000ms
```

**Future:** Async/batch
```python
answers = await asyncio.gather(
    llm.generate_async(q1, ctx1),
    llm.generate_async(q2, ctx2)
)
# Total: 1000ms (parallel)
```

---

## Prompt Engineering Best Practices

### 1. Be Specific

**Bad:**
```
System: Answer questions about the resume.
User: What are your skills?
```

**Good:**
```
System: You ARE the person whose resume this is. Always use "I built", "I worked".
User: What are your skills?
```

**Why:** Specific instructions → more accurate responses.

### 2. Provide Examples (Few-Shot)

**Bad:**
```
System: Answer concisely.
```

**Good:**
```
System: Answer concisely. Example:
Q: What are your skills?
A: I have expertise in Python, JavaScript, and React.

Q: Tell me about your project.
A: I built LinkUp, a social platform using Next.js and MongoDB.
```

**Why:** Examples teach the model the desired format.

### 3. Use Constraints

**Bad:**
```
System: Answer questions.
```

**Good:**
```
System: Answer questions. Rules:
- Maximum 120 words
- Use bullet points or short paragraph
- No technical jargon unless necessary
```

**Why:** Constraints prevent rambling or overly technical responses.

---

## Testing & Debugging

### Test Prompts

**Test if LLM follows instructions:**

```python
# Test 1: Voice enforcement
question = "What's your main project?"
context = "LinkUp - A social platform..."
response = llm.generate(question, context)
assert "I built" in response or "I developed" in response

# Test 2: Length limit
response = llm.generate(question, long_context)
word_count = len(response.split())
assert word_count <= 140  # 120 + buffer

# Test 3: Context grounding
response = llm.generate("What's your main project?", "MealLogger - A food app...")
assert "MealLogger" in response
assert "LinkUp" not in response  # Should not hallucinate
```

### Debug Logging

**Enable debug mode:**
```bash
LOG_LEVEL=DEBUG python main.py "test"
```

**Look for:**
```
[llm.groq_client] Calling Groq API with model llama-3.1-8b-instant
[llm.groq_client] Generated response: 85 chars, 12 words
```

---

## Cost Analysis

### Free Tier

**Limits:**
- 30 requests/minute
- 60 requests/hour (seems contradictory, but both apply)
- No monthly cap (unlimited requests if within rate limits)

**Cost:** $0

**Good for:**
- Personal portfolios (<1000 visitors/day)
- Development/testing

### Paid Tier

**Pricing:** ~$0.10 per million tokens

**Example calculation:**
```
1 question:
- Context: 1500 tokens (resume sections)
- Response: 160 tokens
- Total: 1660 tokens

Cost per question: $0.000166 (~$0.0002)
Cost per 1000 questions: $0.20
Cost per million questions: $200
```

**Good for:**
- High-traffic production portfolios (10K+ visitors/day)
- Business use cases

---

## Alternatives to Groq

### When to Consider Alternatives

| Scenario | Recommended Alternative |
|----------|------------------------|
| **Need absolute best quality** | OpenAI GPT-4 Turbo |
| **Need long-form writing** | Anthropic Claude 3 |
| **Need privacy/self-hosting** | Ollama (local Llama 3.1) |
| **Need multilingual** | OpenAI GPT-4 or Claude 3 |
| **Need ultra-low latency** | Keep Groq (best in class) |

### Migration Guide (Groq → OpenAI)

**Current (Groq):**
```python
from groq import Groq
client = Groq(api_key="gsk_...")
response = client.chat.completions.create(
    model="llama-3.1-8b-instant",
    messages=[...]
)
```

**New (OpenAI):**
```python
from openai import OpenAI
client = OpenAI(api_key="sk-...")
response = client.chat.completions.create(
    model="gpt-3.5-turbo",  # or "gpt-4-turbo"
    messages=[...]
)
```

**Only change needed:** API key and model name!

---

## Next Steps

- **[Memory System](memory-system.md)** - How Q&A caching works
- **[RAG Explained](rag-explained.md)** - Context retrieval
- **[Architecture](architecture.md)** - Full system design

---

## References

- [Groq Documentation](https://console.groq.com/docs)
- [Llama 3.1 Paper](https://arxiv.org/abs/2407.21783)
- [LPU Architecture](https://wow.groq.com/lpu-inference-engine/)
- [Prompt Engineering Guide](https://www.promptingguide.ai/)

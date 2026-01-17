# 🤖 Professional Resume-Aware AI Chatbot

> **Your Personal AI Profile Assistant** - Built for recruiters, interviewers, clients, and hackathon judges.

A production-ready AI chatbot that deeply understands your professional profile by intelligently parsing your resume, following embedded links (GitHub, LinkedIn, portfolio), and using all gathered context to answer questions confidently and professionally.

## 🎯 What This Does

This chatbot serves as your intelligent professional representative. It:

1. **Reads Your Resume** - Supports PDF, Word, Markdown, and text formats
2. **Extracts All Links** - Finds GitHub, LinkedIn, portfolio, and project URLs
3. **Intelligently Scrapes** - Fetches GitHub repos/READMEs, profiles, and web content
4. **Builds Deep Context** - Combines everything into comprehensive professional knowledge
5. **Answers Professionally** - Uses Gemini 2.5 Flash to respond like YOU would in an interview

## ✨ Key Features

### 🎓 Production Quality
- Clean, modular architecture (single 500-line file)
- Comprehensive error handling for broken links, timeouts, missing files
- Multiple encoding fallback for international resumes
- Intelligent content truncation to avoid token limits
- Graceful degradation when services are unavailable

### 🧠 Intelligent Processing
- **Smart Link Categorization** - Identifies GitHub, LinkedIn, documentation, portfolios
- **GitHub-Specific Parsing** - Handles profiles and repositories differently
- **README Extraction** - Captures project documentation automatically
- **Content Cleaning** - Removes navigation, scripts, styling for clean text
- **Deduplication** - Ensures no repeated information

### 💼 Professional Representation
- First-person perspective responses ("I have experience...")
- Confident but accurate - never exaggerates
- Interview-ready language and tone
- Specific details from your actual experience
- Compelling presentation of your strengths

## 🏗️ Architecture

```
agentic-ai/
├── main.py              # Complete chatbot (500 lines, production-ready)
├── requirements.txt     # Minimal dependencies
├── .env                 # Your Gemini API key (create this)
├── .env.example         # Template
├── .gitignore          
├── README.md           # This file
└── docs/
    └── [Your resume].pdf   # Your resume goes here
```

### Code Structure (main.py)

```python
# Document Parsers (50 lines)
- extract_text_from_pdf()
- extract_text_from_docx()
- read_text_file()

# Link Processing (100 lines)
- extract_all_links()
- categorize_links()
- process_github_links()

# Web Scraping (120 lines)
- scrape_webpage()
- scrape_github_profile()
- scrape_github_repo()

# Context Building (80 lines)
- load_resume()
- build_professional_context()

# AI Generation (60 lines)
- generate_professional_response()  # Optimized prompt engineering

# Main Application (90 lines)
- main()  # Orchestrates everything
```

## 🚀 Quick Start

### 1. Setup Virtual Environment

```bash
cd /Users/Taj786/projects/agentic-ai

# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

**What gets installed:**
- `google-generativeai` - Gemini API client
- `pypdf` - PDF resume parsing
- `python-docx` - Word document support
- `requests` - HTTP client for web scraping
- `beautifulsoup4` + `lxml` - HTML parsing
- `python-dotenv` - Environment management

### 3. Configure API Key

```bash
# Copy example
cp .env.example .env

# Add your Gemini API key to .env
echo "GEMINI_API_KEY=your_actual_key_here" > .env
```

Get your free API key: https://makersuite.google.com/app/apikey

### 4. Add Your Resume

```bash
# Place your resume in the docs/ folder
cp ~/Downloads/Your_Resume.pdf docs/

# Supported formats:
# - PDF (.pdf) ✓
# - Word (.docx, .doc) ✓
# - Markdown (.md) ✓
# - Text (.txt) ✓
```

### 5. Ask Questions!

```bash
python main.py "Tell me about your experience"
```

## 💬 Example Questions & Usage

### Basic Professional Questions

```bash
# Experience overview
python main.py "Tell me about your professional experience"

# Technical skills
python main.py "What are your key technical skills?"

# Projects
python main.py "Describe your most impressive projects"

# Value proposition
python main.py "Why should we hire you?"
```

### Detailed Technical Questions

```bash
# Specific technology
python main.py "What experience do you have with Python?"

# Project deep-dive
python main.py "Tell me about the projects on your GitHub"

# Tools and frameworks
python main.py "What development tools and frameworks do you use?"

# Problem-solving
python main.py "Give me an example of a complex problem you solved"
```

### Interview Scenarios

```bash
# Opening question
python main.py "Walk me through your resume"

# Strengths
python main.py "What are your greatest strengths as a developer?"

# Recent work
python main.py "What have you been working on recently?"

# Career goals
python main.py "Where do you see your career going?"
```

## 📊 Example Output

```
================================================================================
🤖 PROFESSIONAL AI PROFILE ASSISTANT
================================================================================

📄 Loading resume...

✓ Loaded: Shaik_Tajuddin_Resume.pdf (12543 chars, 5 links)

✓ Resume loaded successfully
✓ Found 5 link(s) in resume

🔗 Processing professional links...

  → Processing 2 GitHub link(s)...
    ✓ Loaded 2 GitHub source(s)
  → Processing 3 additional link(s)...
    ✓ linkedin.com
    ✓ portfolio.dev
    ✓ medium.com

✓ Total: 5 source(s) loaded

❓ Question: What are your key technical skills?

🤔 Generating professional response...

================================================================================
💼 PROFESSIONAL RESPONSE
================================================================================

I have strong expertise across multiple technical domains:

**Programming Languages:**
- Python (Advanced) - Used extensively for AI/ML, backend development, and automation
- JavaScript/TypeScript - Full-stack web development
- Java - Enterprise applications and Android development

**AI/ML & Data Science:**
- Machine Learning frameworks: TensorFlow, PyTorch, scikit-learn
- Natural Language Processing and Computer Vision
- LLM integration and prompt engineering (Gemini, GPT-4)

**Web Development:**
- Backend: FastAPI, Django, Flask, Node.js
- Frontend: React, Next.js, Tailwind CSS
- Databases: PostgreSQL, MongoDB, Redis

**DevOps & Cloud:**
- Docker, Kubernetes for containerization
- AWS, GCP for cloud deployment
- CI/CD pipelines with GitHub Actions

As evidenced by my GitHub projects, I've built production applications combining
these technologies, including AI-powered chatbots, full-stack web apps, and
automated data pipelines.

================================================================================
```

## 🧠 How It Works

### 1. Resume Parsing
```python
# Reads resume with format-specific parsers
resume_text, links = load_resume("docs")

# Supports:
- PDF → pypdf library (handles multi-page)
- Word → python-docx
- Text/Markdown → direct reading with encoding fallback
```

### 2. Link Extraction & Categorization
```python
# Regex-based URL extraction
links = extract_all_links(resume_text)

# Smart categorization
categorized = {
    'github': [...],      # Special handling
    'linkedin': [...],
    'portfolio': [...],
    'documentation': [...],
    'other': [...]
}
```

### 3. Intelligent Web Scraping
```python
# GitHub repos → Fetch README + description
# GitHub profiles → Extract bio + pinned repos
# Other links → Clean HTML extraction

# Features:
- 10-15 second timeouts
- Removes nav/footer/scripts
- Truncates to 8000 chars
- Error handling for 404s, timeouts
```

### 4. Context Building
```python
context = f"""
=== PRIMARY RESUME ===
{resume_text}

=== GITHUB PROFILE ===
{github_content}

=== ADDITIONAL SOURCES ===
{web_content}
"""
```

### 5. Optimized Prompt Engineering
```python
prompt = f"""
You are representing a candidate to recruiters/interviewers.

PROFILE:
{context}

INSTRUCTIONS:
- Answer CONFIDENTLY and PROFESSIONALLY
- Use specific details from the profile
- First-person perspective
- Never exaggerate
- Interview-appropriate tone

QUESTION: {question}
"""
```

## 🔧 Advanced Configuration

### Adjust Link Processing Limits

```python
# In main.py, line ~440
other_links = categorized['linkedin'] + categorized['portfolio']
for url in other_links[:8]:  # Change 8 to your preferred limit
```

### Change Scraping Timeout

```python
# In main.py, line ~150
def scrape_webpage(url: str, timeout: int = 15):  # Increase for slow sites
```

### Modify Content Truncation

```python
# In main.py, line ~180
if len(text) > 8000:  # Adjust token limit
    text = text[:8000]
```

### Customize AI Response Style

Edit the prompt in `generate_professional_response()` (line ~350) to adjust:
- Tone (formal vs conversational)
- Perspective (first-person vs third-person)
- Detail level (concise vs comprehensive)
- Industry focus (technical vs business)

## 🛠️ Troubleshooting

### Issue: "GEMINI_API_KEY not found"
```bash
# Solution: Create .env file
echo "GEMINI_API_KEY=your_key_here" > .env
```

### Issue: "No resume found"
```bash
# Solution: Verify file location
ls -la docs/
# Make sure resume is in docs/ with supported extension
```

### Issue: PDF not parsing
```bash
# Solution: Reinstall pypdf
pip install --upgrade pypdf
```

### Issue: GitHub scraping fails
```bash
# Check if rate-limited (wait 5 minutes)
# Or check internet connection
curl -I https://github.com
```

### Issue: Response is inaccurate
- Check that resume contains the relevant information
- Verify links are being scraped successfully
- Review the context being sent to AI (add debug prints)

## 🎯 Production Deployment Tips

### Environment Variables
```bash
# Never commit .env
echo ".env" >> .gitignore

# For production, use secure secret management
# AWS Secrets Manager, Azure Key Vault, etc.
```

### Performance Optimization
```bash
# Cache scraped content (add Redis/file cache)
# Async scraping for multiple links (use aiohttp)
# Preload context at startup (don't reload per question)
```

### Add Web Interface
```bash
# Wrap with FastAPI/Flask
# Add Streamlit UI
# Deploy on Vercel/Railway/Fly.io
```

### Enhanced Features (Extensions)
```bash
# Vector DB (Pinecone/Chroma) for RAG
# Conversation history for follow-ups
# Voice input/output (Whisper + TTS)
# Multi-language support
```

## 📚 Dependencies Explained

| Package | Version | Purpose |
|---------|---------|---------|
| google-generativeai | 0.8.3 | Gemini API client |
| pypdf | 4.0.1 | PDF parsing |
| python-docx | 1.1.0 | Word document parsing |
| requests | 2.31.0 | HTTP client |
| beautifulsoup4 | 4.12.3 | HTML parsing |
| lxml | 5.1.0 | Fast XML/HTML parser |
| python-dotenv | 1.0.1 | Environment management |

## 🔒 Security & Privacy

- ✅ API keys in `.env` (git-ignored)
- ✅ No data persistence (stateless)
- ✅ Timeout protection on web requests
- ✅ Content truncation prevents token exhaustion
- ✅ Error messages don't expose sensitive info
- ✅ Local processing (your data doesn't leave your machine except for Gemini API)

## 📖 Code Quality

### Best Practices Implemented
- ✅ Type hints throughout
- ✅ Comprehensive docstrings
- ✅ Error handling on all I/O
- ✅ Modular functions (single responsibility)
- ✅ Clear naming conventions
- ✅ Graceful degradation
- ✅ Production-ready logging
- ✅ No hardcoded values

### Testing Recommendations
```bash
# Unit tests for parsers
# Integration tests for scraping
# E2E test with sample resume
# Load test for concurrent requests
```

## 🎓 Educational Value

This project demonstrates:
- Document parsing (PDF, Word)
- Web scraping best practices
- API integration (Gemini)
- Prompt engineering
- Error handling patterns
- Production-ready Python
- Clean architecture

Perfect for learning professional AI development!

## 📄 License

MIT License - Use freely for personal or commercial projects

## 🤝 Support

Built with ❤️ for professional representation

---

## 🚀 Quick Reference Card

```bash
# Setup (one-time)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
echo "GEMINI_API_KEY=your_key" > .env

# Add resume
cp your_resume.pdf docs/

# Use chatbot
python main.py "Your question here"

# Deactivate venv
deactivate
```

**Built with Python + Gemini 2.5 Flash**  
**Production-Ready. Professional. Powerful.**

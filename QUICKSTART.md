# 🚀 QUICK START GUIDE

## Your Resume-Aware AI Chatbot is Ready!

This is your **personal AI profile assistant** - production-ready and optimized for representing you to recruiters, interviewers, and clients.

---

## ⚡ 3-Minute Setup

### Option 1: Automated Setup (Recommended)

```bash
cd /Users/Taj786/projects/agentic-ai

# Run the setup script
./setup.sh

# Add your Gemini API key
nano .env  # Or use your preferred editor

# Test it!
source venv/bin/activate
python main.py "Tell me about your experience"
```

### Option 2: Manual Setup

```bash
cd /Users/Taj786/projects/agentic-ai

# 1. Create virtual environment
python3 -m venv venv

# 2. Activate it
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Add API key
echo "GEMINI_API_KEY=your_actual_key_here" > .env

# 5. Run chatbot
python main.py "What are your technical skills?"
```

---

## 📋 What You Have

### Files Structure
```
agentic-ai/
├── main.py                    # 500-line production chatbot
├── requirements.txt           # Dependencies
├── README.md                  # Full documentation
├── SAMPLE_QUESTIONS.md        # 100+ example questions
├── setup.sh                   # Automated setup script
├── .env                       # Your API key (create this)
├── .gitignore                # Git safety
└── docs/
    └── Shaik_Tajuddin_Resume.pdf  # Your resume ✓
```

### What It Does
1. ✅ Reads your resume (PDF/Word/Text)
2. ✅ Extracts all embedded links
3. ✅ Scrapes GitHub repos + READMEs
4. ✅ Fetches LinkedIn, portfolio content
5. ✅ Builds comprehensive context
6. ✅ Answers questions professionally using Gemini 2.5 Flash

---

## 💬 Example Usage

```bash
# Activate environment first
source venv/bin/activate

# Ask questions
python main.py "Tell me about yourself"
python main.py "What are your key projects?"
python main.py "What technologies do you specialize in?"
python main.py "Why should we hire you?"
python main.py "Walk me through your GitHub projects"
```

### Expected Output
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

✓ Total: 5 source(s) loaded

❓ Question: What are your key technical skills?

🤔 Generating professional response...

================================================================================
💼 PROFESSIONAL RESPONSE
================================================================================

[Professional, detailed response about your skills]

================================================================================
```

---

## 🎯 Try These Questions

### Interview Questions
```bash
python main.py "Tell me about your professional experience"
python main.py "What's your most impressive project?"
python main.py "What are your greatest strengths?"
```

### Technical Questions
```bash
python main.py "What programming languages do you know?"
python main.py "Tell me about your GitHub projects"
python main.py "What frameworks do you use?"
```

### See `SAMPLE_QUESTIONS.md` for 100+ more examples!

---

## 🔧 Configuration

### Get Gemini API Key (Free)
1. Go to: https://makersuite.google.com/app/apikey
2. Click "Create API Key"
3. Copy the key
4. Add to `.env` file:
   ```
   GEMINI_API_KEY=AIzaSy...your_key_here
   ```

### Add More Documents
```bash
# Just add files to docs/
cp ~/Downloads/portfolio.pdf docs/
cp ~/Documents/projects.md docs/

# The chatbot will automatically read them all
```

---

## 🛠️ Troubleshooting

### "GEMINI_API_KEY not found"
```bash
# Make sure .env exists and has your key
cat .env
# Should show: GEMINI_API_KEY=AIza...
```

### "No resume found"
```bash
# Check docs folder
ls -la docs/
# Add your resume if missing
cp ~/Downloads/resume.pdf docs/
```

### Virtual environment issues
```bash
# Recreate venv
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Imports failing
```bash
# Reinstall dependencies
pip install --upgrade -r requirements.txt
```

---

## 📚 Documentation

- **README.md** - Complete technical documentation
- **SAMPLE_QUESTIONS.md** - 100+ example questions organized by category
- **This file** - Quick start guide

---

## 🎓 Key Features

### Production Quality
- ✅ Clean, modular code (500 lines)
- ✅ Comprehensive error handling
- ✅ Type hints throughout
- ✅ Detailed docstrings
- ✅ Graceful degradation

### Intelligent Processing
- ✅ Multi-format resume support (PDF, Word, Text)
- ✅ Smart link categorization
- ✅ GitHub-specific parsing (profiles + repos)
- ✅ README extraction
- ✅ Content cleaning and truncation

### Professional Responses
- ✅ First-person perspective
- ✅ Interview-appropriate tone
- ✅ Specific details from your profile
- ✅ Confident but accurate
- ✅ Cites sources

---

## 🚀 Next Steps

### Immediate
1. ✅ Your resume is already in `docs/`
2. Add your Gemini API key to `.env`
3. Run the chatbot and test it!

### Extensions (Optional)
- Add conversation history for follow-up questions
- Build web interface (Streamlit/Flask)
- Add vector database for RAG (Pinecone/Chroma)
- Deploy to cloud (Vercel/Railway)
- Add voice input/output

---

## 💡 Pro Tips

1. **Keep resume updated** - The chatbot is only as good as your resume
2. **Include links** - GitHub, LinkedIn, portfolio for richer context
3. **Test thoroughly** - Try various question types
4. **Customize prompts** - Edit `generate_professional_response()` for your style
5. **Monitor API usage** - Gemini has free tier limits

---

## 📞 Support

For issues or questions:
1. Check `README.md` for detailed docs
2. Review `SAMPLE_QUESTIONS.md` for usage examples
3. Check the code comments in `main.py`

---

## ✨ You're All Set!

Your professional AI assistant is ready to represent you to:
- 🎯 Recruiters
- 💼 Interviewers  
- 🏢 Clients
- 🏆 Hackathon judges

**Run it now:**
```bash
source venv/bin/activate
python main.py "Tell me about your experience"
```

---

**Built with Python + Gemini 2.5 Flash**  
**Production-Ready • Professional • Powerful**

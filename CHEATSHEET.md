# 🎯 COMMAND CHEAT SHEET

## Quick Reference for Resume-Aware AI Chatbot

---

## 🚀 Initial Setup (One-Time)

```bash
# Navigate to project
cd /Users/Taj786/projects/agentic-ai

# Run automated setup
./setup.sh

# OR manual setup:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Add your API key
echo "GEMINI_API_KEY=your_actual_key_here" > .env
```

---

## 💻 Daily Usage

```bash
# Activate virtual environment
source venv/bin/activate

# Run chatbot
python main.py "Your question here"

# Exit virtual environment when done
deactivate
```

---

## 📝 Example Commands

### Professional Questions
```bash
python main.py "Tell me about yourself"
python main.py "What is your professional background?"
python main.py "Walk me through your resume"
python main.py "Why should we hire you?"
```

### Technical Questions
```bash
python main.py "What programming languages do you know?"
python main.py "What are your technical skills?"
python main.py "Tell me about your GitHub projects"
python main.py "What frameworks do you use?"
```

### Project Questions
```bash
python main.py "Describe your most impressive projects"
python main.py "What's your most challenging project?"
python main.py "Show me your problem-solving skills"
```

---

## 🔧 Maintenance Commands

### Update Dependencies
```bash
source venv/bin/activate
pip install --upgrade -r requirements.txt
```

### Check Installation
```bash
pip list | grep -E "google-generativeai|pypdf|requests|beautifulsoup4"
```

### View API Key
```bash
cat .env
```

### Check Resume
```bash
ls -lh docs/*.pdf
```

---

## 🧪 Testing

### Run Test Suite
```bash
source venv/bin/activate
python test_chatbot.py
```

### Quick Test
```bash
python main.py "What are your key skills?"
```

---

## 🐛 Troubleshooting Commands

### Problem: Virtual environment issues
```bash
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Problem: Missing dependencies
```bash
source venv/bin/activate
pip install pypdf python-docx requests beautifulsoup4 lxml google-generativeai python-dotenv
```

### Problem: API key not found
```bash
# Check if .env exists
ls -la .env

# Create if missing
echo "GEMINI_API_KEY=your_key_here" > .env

# Verify content
cat .env
```

### Problem: No resume found
```bash
# Check docs folder
ls -la docs/

# Add resume
cp ~/Downloads/your_resume.pdf docs/
```

### Problem: Permission denied
```bash
chmod +x setup.sh
chmod +x test_chatbot.py
```

---

## 📂 File Operations

### Add New Resume
```bash
cp ~/path/to/new_resume.pdf docs/
# Chatbot automatically uses latest
```

### View Main Code
```bash
head -n 50 main.py  # View first 50 lines
wc -l main.py       # Count total lines
```

### Check Project Structure
```bash
tree -L 2 -I 'venv|__pycache__|*.pyc'
# Or without tree:
find . -maxdepth 2 -type f -not -path './venv/*'
```

---

## 🔍 Monitoring & Debugging

### Check Python Version
```bash
python3 --version  # Should be 3.8+
```

### Test Imports
```bash
python3 -c "import google.generativeai; print('Gemini: OK')"
python3 -c "from pypdf import PdfReader; print('PDF: OK')"
python3 -c "import requests; print('Requests: OK')"
```

### Verbose Run (for debugging)
```bash
# Add debug output to main.py or run with python -v
python -v main.py "test question" 2>&1 | head -50
```

---

## 📊 Performance Checks

### Time a Query
```bash
time python main.py "What are your skills?"
```

### Check Memory Usage
```bash
/usr/bin/time -l python main.py "test" 2>&1 | grep "maximum resident"
```

### Monitor Network Calls
```bash
# Run in one terminal
python main.py "Tell me about your GitHub"

# Watch network in another
sudo tcpdump -i any host api.generativeai.google.com
```

---

## 🔐 Security Commands

### Verify .env is Ignored
```bash
git status  # Should not show .env
cat .gitignore | grep .env
```

### Check File Permissions
```bash
ls -la .env  # Should be readable only by you
chmod 600 .env  # Make it secure if needed
```

---

## 📦 Backup & Export

### Backup Project (without venv)
```bash
tar -czf resume-chatbot-backup.tar.gz \
  --exclude='venv' \
  --exclude='__pycache__' \
  --exclude='.env' \
  .
```

### Export Requirements with Versions
```bash
pip freeze > requirements-locked.txt
```

---

## 🚀 Advanced Usage

### Run with Different Python
```bash
python3.11 -m venv venv311
source venv311/bin/activate
pip install -r requirements.txt
```

### Batch Questions (create script)
```bash
cat > batch_test.sh << 'EOF'
#!/bin/bash
source venv/bin/activate
for q in "What are your skills?" "Tell me about projects" "Why hire you?"; do
    echo "Q: $q"
    python main.py "$q"
    echo ""
done
EOF
chmod +x batch_test.sh
./batch_test.sh
```

### Profile Performance
```bash
python -m cProfile -s cumtime main.py "test question" 2>&1 | head -30
```

---

## 📱 Quick Copy-Paste Commands

### Full Setup (copy entire block)
```bash
cd /Users/Taj786/projects/agentic-ai && \
python3 -m venv venv && \
source venv/bin/activate && \
pip install -r requirements.txt && \
echo "Setup complete! Add your API key to .env"
```

### Quick Test (copy entire block)
```bash
source venv/bin/activate && \
python main.py "What are your key technical skills?"
```

### Full Reset (copy entire block)
```bash
rm -rf venv && \
python3 -m venv venv && \
source venv/bin/activate && \
pip install -r requirements.txt && \
echo "Environment rebuilt!"
```

---

## 🎯 Most Common Commands

```bash
# 1. Daily startup
source venv/bin/activate

# 2. Ask question
python main.py "your question"

# 3. Exit
deactivate
```

---

## 💡 Pro Tips

### Alias for Quick Access
```bash
# Add to ~/.zshrc or ~/.bashrc
alias resume-ai='cd /Users/Taj786/projects/agentic-ai && source venv/bin/activate'

# Usage:
resume-ai
python main.py "your question"
```

### Create Function for Questions
```bash
# Add to ~/.zshrc or ~/.bashrc
ask-resume() {
    cd /Users/Taj786/projects/agentic-ai
    source venv/bin/activate
    python main.py "$*"
    deactivate
}

# Usage from anywhere:
ask-resume What are your key skills?
```

---

## 📖 Documentation Quick Access

```bash
# View README
less README.md

# View quick start
less QUICKSTART.md

# View sample questions
less SAMPLE_QUESTIONS.md

# View architecture
less ARCHITECTURE.md
```

---

## 🎓 Learning Commands

### Count Lines of Code
```bash
wc -l main.py
# Shows ~500 lines
```

### View Function List
```bash
grep "^def " main.py
```

### View Docstrings
```bash
grep -A 3 "def " main.py | head -50
```

---

**Keep this cheat sheet handy for quick reference!** 📌

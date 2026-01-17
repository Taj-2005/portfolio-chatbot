# Deployment Configurations for Free Tiers

## Render.com (Free Tier)

### render.yaml
```yaml
services:
  - type: web
    name: resume-chatbot
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: python main.py
    envVars:
      - key: GROQ_API_KEY
        sync: false
      - key: SEARCHAPI_KEY
        sync: false
        optional: true
```

### Setup Instructions:
1. Create account at https://render.com
2. Connect GitHub repository
3. Create new Web Service
4. Set environment variables:
   - `GROQ_API_KEY` (required)
   - `SEARCHAPI_KEY` (optional)
5. Deploy

---

## Fly.io (Free Tier)

### fly.toml
```toml
app = "resume-chatbot"
primary_region = "iad"

[build]
  builder = "paketobuildpacks/builder:base"

[env]
  PYTHON_VERSION = "3.11"

[[services]]
  http_checks = []
  internal_port = 8000
  processes = ["app"]
  protocol = "tcp"
  script_checks = []

  [services.concurrency]
    hard_limit = 25
    soft_limit = 20
    type = "connections"

  [[services.ports]]
    force_https = true
    handlers = ["http"]
    port = 80

  [[services.ports]]
    handlers = ["tls", "http"]
    port = 443

  [[services.tcp_checks]]
    grace_period = "1s"
    interval = "15s"
    restart_limit = 0
    timeout = "2s"
```

### Setup Instructions:
1. Install Fly CLI: `curl -L https://fly.io/install.sh | sh`
2. Login: `fly auth login`
3. Launch: `fly launch`
4. Set secrets:
   ```bash
   fly secrets set GROQ_API_KEY=your_key
   fly secrets set SEARCHAPI_KEY=your_key  # optional
   ```

---

## Railway (Free Tier)

### railway.json
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "python main.py",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

### Setup Instructions:
1. Create account at https://railway.app
2. New Project → Deploy from GitHub
3. Add environment variables:
   - `GEMINI_API_KEY`
   - `SEARCHAPI_KEY` (optional)
4. Deploy

---

## Hugging Face Spaces (CPU - Free)

### app.py (for Hugging Face Spaces)
```python
import os
import sys
from main import main

if __name__ == "__main__":
    # Hugging Face Spaces provides environment variables
    # Just run the main function
    if len(sys.argv) > 1:
        sys.argv = ['main.py'] + sys.argv[1:]
    else:
        sys.argv = ['main.py', 'What are your key skills?']
    main()
```

### README.md (for Hugging Face)
```markdown
---
title: Resume AI Chatbot
emoji: 🤖
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
---

# Resume-Aware AI Chatbot

Professional AI assistant for resume questions.

## Environment Variables
- GEMINI_API_KEY (required)
- SEARCHAPI_KEY (optional)
```

### Setup Instructions:
1. Create account at https://huggingface.co
2. Create new Space → Docker
3. Upload files
4. Set secrets in Space settings:
   - `GEMINI_API_KEY`
   - `SEARCHAPI_KEY` (optional)

---

## Dockerfile (Universal)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .
COPY memory.json* ./

ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]
```

---

## Environment Variables

All platforms require:

```bash
GROQ_API_KEY=your_groq_key_here
SEARCHAPI_KEY=your_searchapi_key_here  # Optional
```

Get keys:
- Groq: https://console.groq.com/keys
- SearchAPI: https://www.searchapi.io/ (free tier: 100 requests/month)

---

## Quick Deploy Commands

### Render
```bash
# Just push to GitHub, Render auto-deploys
git push origin main
```

### Fly.io
```bash
fly launch
fly secrets set GROQ_API_KEY=your_key
fly deploy
```

### Railway
```bash
railway login
railway init
railway up
```

### Hugging Face
```bash
# Upload via web interface or:
huggingface-cli upload your-username/resume-chatbot .
```

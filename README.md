# Portfolio Chatbot API

API on Vercel: send a question, get the answer in JSON.

## Deploy to Vercel

1. Push this repo to GitHub.
2. Go to [vercel.com](https://vercel.com) → **Add New** → **Project** → import your repo.
3. Add environment variable: **`GROQ_API_KEY`** (from [console.groq.com/keys](https://console.groq.com/keys)).
4. **Deploy**.

Vercel will redeploy on every push.

## API

**Endpoint:** `/api/question` (or `/api` or `/`)

**GET:**
```bash
curl "https://YOUR_PROJECT.vercel.app/api/question?question=What%20are%20your%20skills?"
```

**POST:**
```bash
curl -X POST https://YOUR_PROJECT.vercel.app/api/question \
  -H "Content-Type: application/json" \
  -d '{"question": "Tell me about your projects"}'
```

**Response:**
```json
{
  "question": "...",
  "answer": "..."
}
```

## Local

- Put your resume in `docs/` (PDF, DOCX, TXT, MD, TEX).
- CLI: `python main.py "What are your skills?"`

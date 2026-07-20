# Knowledge Base — Shaik Tajuddin

This directory is the **single source of truth** for the chatbot's retrieval. Nothing outside
`knowledge-base/` is indexed.

## Contents

| File | Loaded by | What it covers |
| --- | --- | --- |
| `profile.md` | `KnowledgeBaseLoader` | Identity, current roles, deplo.ai, all canonical links |
| `RESUME.md` | `ResumeLoader` | Full resume: summary, education, experience, internships, projects, skills |
| `Resume-Shaik-Tajuddin.pdf` | — (skipped) | Downloadable copy; skipped during indexing because `RESUME.md` carries the same content |
| `projects.json` | `ProjectLoader` | Every portfolio project with description, tech, GitHub, and live links |
| `portfolio-features.md` | `KnowledgeBaseLoader` | How the portfolio web app itself is built (pages, routes, APIs) |
| `techstacks.ts` | `KnowledgeBaseLoader` | Tech-stack list rendered on the portfolio |

## Quick facts

- **Name:** Shaik Tajuddin
- **Now:** Founder of **deplo.ai** (https://www.deplo.in) · Product & Software Engineer at
  Maverick Secure LLC (Florida, USA — remote)
- **Education:** B.Tech, Artificial Intelligence — Newton School of Technology, Rishihood
  University (2024 – 2028)
- **Portfolio:** https://www.taju.dev
- **GitHub:** https://github.com/Taj-2005 · **LinkedIn:** https://www.linkedin.com/in/tajuddinshaik786/
- **Email:** tajuddinshaik786r@gmail.com

## Updating

1. Edit the relevant file above — do not add facts to the chatbot's Python source.
2. The featured project the assistant leads with is controlled by
   `FEATURED_PROJECT_NAMES` in `src/config/settings.py` (override with the
   `FEATURED_PROJECT_NAMES` env var, comma-separated). It currently resolves to **deplo.ai**.
3. Redeploy — the loaders re-read this directory on cold start.

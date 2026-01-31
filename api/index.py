"""
Vercel serverless function for Portfolio Chatbot API
Accepts questions via GET (query params) or POST (JSON body)
"""

import os
import json
import sys
import traceback
from pathlib import Path
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Ensure project root is on path (Vercel runs from /var/task)
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

# Lazy import to surface import errors inside request
_main = None


def _get_main():
    global _main
    if _main is None:
        from main import (
            load_resume,
            load_project_json,
            categorize_links,
            process_github_links,
            select_relevant_context,
            should_use_web_augmentation,
            fetch_searchapi_context,
            call_groq_llm,
        )
        _main = {
            "load_resume": load_resume,
            "load_project_json": load_project_json,
            "categorize_links": categorize_links,
            "process_github_links": process_github_links,
            "select_relevant_context": select_relevant_context,
            "should_use_web_augmentation": should_use_web_augmentation,
            "fetch_searchapi_context": fetch_searchapi_context,
            "call_groq_llm": call_groq_llm,
        }
    return _main


# Cache resume + project data per instance
_sections = None
_links = None
_full_resume = None
_web_content = None
_project_data = None


def load_resume_data():
    global _sections, _links, _full_resume, _web_content, _project_data
    if _sections is None:
        try:
            m = _get_main()
            docs_dir = str(_root / "docs")
            _sections, _links, _full_resume = m["load_resume"](docs_dir)
            _project_data = m["load_project_json"](docs_dir)
            _web_content = []
            if _links:
                cat = m["categorize_links"](_links)
                if cat.get("github"):
                    _web_content = m["process_github_links"](cat["github"])
            if not _sections or all(not v for v in _sections.values()):
                _sections = {}
                _links = set()
                _full_resume = ""
        except Exception as e:
            traceback.print_exc()
            _sections = {}
            _links = set()
            _full_resume = ""
            _web_content = []
            _project_data = None
    return _sections, _links, _full_resume, _web_content, _project_data


def _send_json(self, status, data):
    body = json.dumps(data).encode("utf-8")
    self.send_response(status)
    self.send_header("Content-Type", "application/json")
    self.send_header("Access-Control-Allow-Origin", "*")
    self.send_header("Content-Length", str(len(body)))
    self.end_headers()
    self.wfile.write(body)
    try:
        self.wfile.flush()
    except Exception:
        pass


class handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        try:
            self._handle()
        except Exception as e:
            traceback.print_exc()
            _send_json(self, 500, {"error": str(e)})

    def do_POST(self):
        try:
            self._handle()
        except Exception as e:
            traceback.print_exc()
            _send_json(self, 500, {"error": str(e)})

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _handle(self):
        if getattr(self, "command", "GET") == "OPTIONS":
            self.do_OPTIONS()
            return

        path = getattr(self, "path", "") or ""
        parsed = urlparse(path)
        query = parse_qs(parsed.query)

        if getattr(self, "command", "GET") == "GET":
            question = (query.get("question") or [""])[0].strip()
        else:
            cl = int(self.headers.get("Content-Length", 0) or 0)
            raw = self.rfile.read(cl) if cl else b""
            try:
                body = json.loads(raw.decode("utf-8")) if raw else {}
            except Exception:
                body = {}
            question = (body.get("question") or "").strip()

        if not question:
            _send_json(
                self,
                400,
                {"error": "Question is required. Use ?question=... or {\"question\": \"...\"}"},
            )
            return

        groq_key = os.environ.get("GROQ_API_KEY")
        if not groq_key:
            _send_json(self, 500, {"error": "GROQ_API_KEY not configured"})
            return

        m = _get_main()
        sections, links, full_resume, web_content, project_data = load_resume_data()

        if not sections or all(not v for v in sections.values()):
            _send_json(self, 500, {"error": "Resume not found in docs/"})
            return

        initial_context = m["select_relevant_context"](
            sections, web_content, question,
            full_resume=full_resume, project_data=project_data
        )
        should_search, search_query, _ = m["should_use_web_augmentation"](
            question, initial_context, sections, links
        )
        searchapi_key = os.environ.get("SEARCHAPI_API_KEY") or os.environ.get("SEARCHAPI_KEY")
        searchapi_content = None
        if should_search and searchapi_key:
            searchapi_content = m["fetch_searchapi_context"](search_query, searchapi_key)

        relevant_context = m["select_relevant_context"](
            sections, web_content, question, searchapi_content,
            full_resume=full_resume, project_data=project_data
        )
        answer = m["call_groq_llm"](question, relevant_context, groq_key)

        _send_json(self, 200, {"question": question, "answer": answer})

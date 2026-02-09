"""
Vercel Serverless Function for Portfolio Chatbot API.

Accepts questions via GET (query params) or POST (JSON body)
and returns AI-generated answers about the resume/portfolio.

Endpoints:
    GET  /api/question?question=...
    POST /api/question with {"question": "..."}

Response:
    {"question": "...", "answer": "..."}
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

# Lazy import to surface errors inside request
_chatbot_instance = None


def _get_chatbot():
    """
    Get or create chatbot instance (cached per serverless instance).
    
    Returns:
        PortfolioChatbot: Initialized chatbot instance.
    """
    global _chatbot_instance
    
    if _chatbot_instance is None:
        from src.core import PortfolioChatbot
        from src.config import settings
        
        groq_key = os.environ.get("GROQ_API_KEY")
        if not groq_key:
            raise ValueError("GROQ_API_KEY not configured in environment")
        
        searchapi_key = os.environ.get("SEARCHAPI_API_KEY") or os.environ.get("SEARCHAPI_KEY")
        
        # Initialize chatbot with docs directory
        docs_dir = str(_root / "docs")
        _chatbot_instance = PortfolioChatbot(
            docs_dir=docs_dir,
            groq_api_key=groq_key,
            searchapi_key=searchapi_key
        )
    
    return _chatbot_instance


def _send_json(handler, status: int, data: dict):
    """
    Send JSON response.
    
    Args:
        handler: HTTP request handler.
        status: HTTP status code.
        data: Data to serialize as JSON.
    """
    body = json.dumps(data).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)
    try:
        handler.wfile.flush()
    except Exception:
        pass


class handler(BaseHTTPRequestHandler):
    """Vercel serverless function handler."""
    
    def log_message(self, format, *args):
        """Override to suppress request logging."""
        pass
    
    def do_GET(self):
        """Handle GET requests."""
        try:
            self._handle()
        except Exception as e:
            traceback.print_exc()
            _send_json(self, 500, {"error": str(e)})
    
    def do_POST(self):
        """Handle POST requests."""
        try:
            self._handle()
        except Exception as e:
            traceback.print_exc()
            _send_json(self, 500, {"error": str(e)})
    
    def do_OPTIONS(self):
        """Handle OPTIONS requests (CORS preflight)."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
    
    def _handle(self):
        """Main request handler for GET and POST."""
        # Handle OPTIONS
        if getattr(self, "command", "GET") == "OPTIONS":
            self.do_OPTIONS()
            return
        
        # Parse request
        path = getattr(self, "path", "") or ""
        parsed = urlparse(path)
        query = parse_qs(parsed.query)
        
        # Extract question from GET or POST
        if getattr(self, "command", "GET") == "GET":
            question = (query.get("question") or [""])[0].strip()
        else:
            # POST request - read JSON body
            cl = int(self.headers.get("Content-Length", 0) or 0)
            raw = self.rfile.read(cl) if cl else b""
            try:
                body = json.loads(raw.decode("utf-8")) if raw else {}
            except json.JSONDecodeError:
                _send_json(self, 400, {"error": "Invalid JSON in request body"})
                return
            question = (body.get("question") or "").strip()
        
        # Validate question
        if not question:
            _send_json(
                self,
                400,
                {"error": 'Question is required. Use ?question=... or {"question": "..."}'},
            )
            return
        
        # Get chatbot instance
        try:
            chatbot = _get_chatbot()
        except ValueError as e:
            _send_json(self, 500, {"error": str(e)})
            return
        except Exception as e:
            traceback.print_exc()
            _send_json(self, 500, {"error": f"Failed to initialize chatbot: {str(e)}"})
            return
        
        # Generate answer
        try:
            answer = chatbot.answer_question(question)
            _send_json(self, 200, {"question": question, "answer": answer})
        except Exception as e:
            traceback.print_exc()
            _send_json(self, 500, {"error": f"Error generating answer: {str(e)}"})

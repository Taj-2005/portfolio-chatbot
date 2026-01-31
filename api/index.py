"""
Vercel serverless function for Portfolio Chatbot API
Accepts questions via GET (query params) or POST (JSON body)
No security - freely accessible
"""

import os
import json
import sys
from pathlib import Path
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Add parent directory to path to import main
sys.path.append(str(Path(__file__).parent.parent))

from main import (
    load_resume, categorize_links, process_github_links,
    select_relevant_context, should_use_web_augmentation,
    fetch_searchapi_context, call_groq_llm
)

# Cache resume data (loaded once per serverless instance)
_sections = None
_links = None
_full_resume = None
_web_content = None


def load_resume_data():
    """Load resume data (cached per serverless instance)"""
    global _sections, _links, _full_resume, _web_content
    
    if _sections is None:
        try:
            _sections, _links, _full_resume = load_resume("docs")
            _web_content = []
            if _links:
                categorized = categorize_links(_links)
                if categorized['github']:
                    _web_content = process_github_links(categorized['github'])
            
            if not _sections or all(not v for v in _sections.values()):
                _sections = {}
                _links = set()
                _full_resume = ""
        except Exception as e:
            print(f"Error loading resume: {e}")
            _sections = {}
            _links = set()
            _full_resume = ""
            _web_content = []
    
    return _sections, _links, _full_resume, _web_content


class handler(BaseHTTPRequestHandler):
    """
    Vercel serverless function handler
    Supports GET and POST requests
    """
    
    def do_GET(self):
        """Handle GET requests"""
        self.handle_request()
    
    def do_POST(self):
        """Handle POST requests"""
        self.handle_request()
    
    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def handle_request(self):
        """Main request handler"""
        # Handle CORS preflight
        if self.command == 'OPTIONS':
            self.do_OPTIONS()
            return
        
        try:
            # Parse query string for GET requests
            parsed_path = urlparse(self.path)
            query_params = parse_qs(parsed_path.query)
            
            # Get question from query params (GET) or body (POST)
            if self.command == 'GET':
                question = query_params.get('question', [''])[0].strip()
            else:
                # POST - read and parse JSON body
                content_length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_length).decode('utf-8')
                try:
                    body_data = json.loads(body) if body else {}
                    question = body_data.get('question', '').strip()
                except:
                    question = ''
            
            if not question:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'error': 'Question is required. Use ?question=... for GET or {"question": "..."} for POST'
                }).encode('utf-8'))
                return
            
            # Get API keys
            groq_key = os.getenv('GROQ_API_KEY')
            if not groq_key:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'error': 'GROQ_API_KEY not configured'
                }).encode('utf-8'))
                return
            
            searchapi_key = os.getenv('SEARCHAPI_API_KEY') or os.getenv('SEARCHAPI_KEY')
            
            # Load resume data
            sections, links, full_resume, web_content = load_resume_data()
            
            # Check if resume is loaded
            if not sections or all(not v for v in sections.values()):
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'error': 'Resume not found in docs/ directory'
                }).encode('utf-8'))
                return
            
            # Build context
            initial_context = select_relevant_context(sections, web_content, question, full_resume=full_resume)
            should_search, search_query, search_reason = should_use_web_augmentation(
                question, initial_context, sections, links
            )
            
            searchapi_content = None
            if should_search and searchapi_key:
                searchapi_content = fetch_searchapi_context(search_query, searchapi_key)
            
            relevant_context = select_relevant_context(
                sections, web_content, question, searchapi_content, full_resume=full_resume
            )
            
            # Generate response
            response = call_groq_llm(question, relevant_context, groq_key)
            
            # Send success response
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                'question': question,
                'answer': response
            }).encode('utf-8'))
        
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                'error': str(e)
            }).encode('utf-8'))

#!/bin/bash
#
# Setup script for Resume-Aware AI Chatbot
# Run this once to set up your environment
#

set -e

echo "=================================="
echo "🤖 Resume AI Chatbot Setup"
echo "=================================="
echo ""

# Check if venv exists
if [ -d "venv" ]; then
    echo "✓ Virtual environment already exists"
else
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
fi

echo ""
echo "📥 Installing dependencies..."
source venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo "✓ All dependencies installed"

echo ""
echo "🔑 Checking for API key..."
if [ -f ".env" ]; then
    if grep -q "GEMINI_API_KEY=.*[A-Za-z0-9]" .env; then
        echo "✓ API key found in .env"
    else
        echo "⚠️  .env file exists but API key may be missing"
        echo "   Please add your Gemini API key to .env"
    fi
else
    echo "📝 Creating .env file..."
    echo "# Get your API key from: https://makersuite.google.com/app/apikey" > .env
    echo "GEMINI_API_KEY=your_api_key_here" >> .env
    echo "✓ Created .env file - Please add your API key"
fi

echo ""
echo "📄 Checking for resume..."
if [ -z "$(ls -A docs/*.pdf 2>/dev/null)" ]; then
    echo "⚠️  No PDF resume found in docs/"
    echo "   Please add your resume to the docs/ folder"
else
    echo "✓ Resume found in docs/"
fi

echo ""
echo "=================================="
echo "✅ Setup Complete!"
echo "=================================="
echo ""
echo "Next steps:"
echo "1. Add your Gemini API key to .env"
echo "2. Ensure your resume is in docs/"
echo "3. Activate environment: source venv/bin/activate"
echo "4. Run: python main.py 'Your question here'"
echo ""
echo "Example:"
echo "  python main.py 'Tell me about your experience'"
echo ""

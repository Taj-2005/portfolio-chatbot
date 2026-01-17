#!/usr/bin/env python3
"""
Test script for Resume-Aware AI Chatbot
Runs a series of test questions to verify functionality
"""

import subprocess
import sys
from pathlib import Path

# Test questions to verify functionality
TEST_QUESTIONS = [
    "What are your key technical skills?",
    "Tell me about your experience",
    "What projects have you built?",
]

def run_test(question: str) -> bool:
    """Run a single test question."""
    print(f"\n{'='*70}")
    print(f"Testing: {question}")
    print('='*70)
    
    try:
        result = subprocess.run(
            [sys.executable, "main.py", question],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print("✓ SUCCESS")
            print("\nResponse preview:")
            lines = result.stdout.split('\n')
            # Find and show response section
            in_response = False
            preview_lines = []
            for line in lines:
                if "PROFESSIONAL RESPONSE" in line:
                    in_response = True
                elif in_response and line.strip():
                    preview_lines.append(line)
                    if len(preview_lines) >= 5:  # Show first 5 lines
                        break
            
            if preview_lines:
                print('\n'.join(preview_lines[:5]))
                print("...")
            
            return True
        else:
            print("✗ FAILED")
            print(f"Error: {result.stderr[:200]}")
            return False
            
    except subprocess.TimeoutExpired:
        print("✗ TIMEOUT (>30s)")
        return False
    except Exception as e:
        print(f"✗ ERROR: {e}")
        return False


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("🧪 RESUME AI CHATBOT - TEST SUITE")
    print("="*70)
    
    # Check if we're in the right directory
    if not Path("main.py").exists():
        print("\n❌ Error: main.py not found")
        print("Please run this script from the project directory")
        sys.exit(1)
    
    # Check if resume exists
    if not any(Path("docs").glob("*.pdf")):
        print("\n⚠️  Warning: No PDF resume found in docs/")
        print("Tests may not work correctly without a resume")
    
    # Run tests
    results = []
    for question in TEST_QUESTIONS:
        results.append(run_test(question))
    
    # Summary
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    passed = sum(results)
    total = len(results)
    print(f"\nPassed: {passed}/{total}")
    
    if passed == total:
        print("✅ All tests passed!")
    else:
        print(f"⚠️  {total - passed} test(s) failed")
    
    print("\n" + "="*70 + "\n")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())

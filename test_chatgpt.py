#!/usr/bin/env python3
"""
Test script for ChatGPT API integration.
"""
import sys
import os
from datetime import datetime
from models import Game
from chatgpt_research import ChatGPTResearcher
from dotenv import load_dotenv

def main():
    """Test ChatGPT research on a sample game."""
    print("=" * 60)
    print("ChatGPT API Test")
    print("=" * 60)
    print()
    
    # Load environment variables
    load_dotenv(".env.local")
    load_dotenv()
    
    # Check API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not set!")
        print()
        print("Add it to .env.local:")
        print("  OPENAI_API_KEY=sk-your_key_here")
        return
    
    print(f"✓ API key found (length: {len(api_key)})")
    
    # Check model
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    print(f"✓ Using model: {model}")
    print()
    
    # Create test game
    test_game = Game(
        game_id="TEST-001",
        team_a="Los Angeles Lakers",
        team_b="Golden State Warriors",
        league="NBA",
        start_time=datetime(2025, 11, 19, 19, 30)  # Nov 19, 2025 7:30 PM
    )
    
    print(f"Researching: {test_game.team_a} vs {test_game.team_b}")
    print(f"League: {test_game.league}")
    print(f"Game Time: {test_game.start_time}")
    print()
    print("Querying ChatGPT API...")
    print()
    
    # Initialize researcher
    researcher = ChatGPTResearcher(model=model)
    
    # Research game
    try:
        analysis = researcher.research_game(test_game)
        
        if analysis:
            print("=" * 60)
            print("CHATGPT ANALYSIS")
            print("=" * 60)
            print()
            print("SUMMARY:")
            print("-" * 60)
            print(analysis.summary)
            print()
            
            if analysis.key_factors:
                print("KEY FACTORS:")
                print("-" * 60)
                for i, factor in enumerate(analysis.key_factors, 1):
                    print(f"{i}. {factor}")
                print()
            
            if analysis.prediction:
                print("PREDICTION:")
                print("-" * 60)
                print(analysis.prediction)
                print()
            
            if analysis.confidence:
                print(f"CONFIDENCE: {analysis.confidence}")
                print()
            
            print("=" * 60)
            print("✓ Test completed successfully!")
        else:
            print("✗ No analysis returned from ChatGPT API")
            print("  Check your API key and credits")
            
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()


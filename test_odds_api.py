"""
Test script to verify The Odds API integration.
"""
import sys
from config import load_config
from kalshi_client import KalshiClient
from odds_client import OddsClient
from models import Game
from datetime import datetime
from pytz import utc

def test_odds_api():
    """Test The Odds API integration."""
    print("=" * 60)
    print("Testing The Odds API Integration")
    print("=" * 60)
    print()
    
    config = load_config()
    kalshi = KalshiClient(config)
    odds = OddsClient(config)
    
    # Check if API key is set
    if not odds.api_key:
        print("⚠️  THE_ODDS_API_KEY not found in environment variables")
        print()
        print("To use real odds:")
        print("  1. Get your API key from https://the-odds-api.com/")
        print("  2. Add to .env file:")
        print("     THE_ODDS_API_KEY=your_api_key_here")
        print()
        print("The bot will use mock odds until the key is set.")
        return
    
    print(f"✓ API key found: {odds.api_key[:10]}...")
    print()
    
    # Fetch real markets
    print("Fetching real markets from Kalshi...")
    markets = kalshi.fetch_sports_markets()
    print(f"✓ Found {len(markets)} markets")
    
    if not markets:
        print("No markets found. Cannot test.")
        return
    
    # Filter for future games
    now_utc = datetime.now(utc)
    future_markets = []
    for m in markets:
        if m.start_time.tzinfo:
            if m.start_time > now_utc:
                future_markets.append(m)
        else:
            m_start = utc.localize(m.start_time)
            if m_start > now_utc:
                future_markets.append(m)
    
    print(f"✓ Found {len(future_markets)} future markets")
    print()
    
    if not future_markets:
        print("No future games found. Cannot test.")
        return
    
    # Take first few games
    test_games = []
    for market in future_markets[:5]:
        # Extract opponent
        if " vs " in market.event_name:
            parts = market.event_name.replace(" Winner?", "").split(" vs ")
            if market.team in parts[0] or market.team[:3].lower() in parts[0].lower():
                opponent = parts[1].strip() if len(parts) > 1 else "Unknown"
            else:
                opponent = parts[0].strip()
        else:
            opponent = "Unknown"
        
        game = Game(
            game_id=market.game_id,
            team_a=market.team,
            team_b=opponent,
            league=market.league,
            start_time=market.start_time
        )
        test_games.append(game)
    
    print(f"Testing odds fetching for {len(test_games)} games...")
    print()
    
    # Fetch odds
    ref_odds = odds.fetch_reference_odds(test_games)
    
    print("=" * 60)
    print("Results:")
    print("=" * 60)
    
    for game in test_games:
        if game.game_id in ref_odds:
            odds_obj = ref_odds[game.game_id]
            source = odds_obj.source
            team_a_odds = odds_obj.team_a_american_odds
            team_b_odds = odds_obj.team_b_american_odds
            
            print(f"\n{game.team_a} vs {game.team_b} ({game.league})")
            print(f"  Source: {source}")
            print(f"  Team A odds: {team_a_odds:+d}")
            print(f"  Team B odds: {team_b_odds:+d}")
            
            if source == "the-odds-api":
                print(f"  ✓ Real odds from The Odds API!")
            else:
                print(f"  ⚠️  Using mock odds (game not found in API)")
        else:
            print(f"\n{game.team_a} vs {game.team_b} ({game.league})")
            print(f"  ✗ No odds found")
    
    print()
    print("=" * 60)
    print("Test complete!")
    print("=" * 60)

if __name__ == "__main__":
    test_odds_api()


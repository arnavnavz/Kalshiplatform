"""
Test script to verify Kalshi API integration.
"""
import sys
from config import load_config
from kalshi_client import KalshiClient

def test_api_connection():
    """Test basic API connection and authentication."""
    print("=" * 60)
    print("Testing Kalshi API Integration")
    print("=" * 60)
    
    try:
        config = load_config()
        print(f"\n✓ Config loaded")
        print(f"  Mode: {config.mode}")
        print(f"  Base URL: {config.kalshi_base_url}")
        print(f"  API Key: {'Set' if config.kalshi_api_key else 'Not set'}")
        print(f"  API Secret: {'Set' if config.kalshi_api_secret else 'Not set'}")
        
        client = KalshiClient(config)
        print(f"\n✓ KalshiClient initialized")
        
        # Test balance fetch (only in LIVE mode, or will use mock in SHADOW)
        print(f"\n--- Testing Balance Fetch ---")
        try:
            balance = client.get_account_balance()
            print(f"✓ Balance: ${balance:,.2f}")
        except Exception as e:
            print(f"✗ Balance fetch failed: {e}")
        
        # Test market fetch
        print(f"\n--- Testing Market Fetch ---")
        try:
            markets = client.fetch_sports_markets()
            print(f"✓ Fetched {len(markets)} markets")
            if markets:
                print(f"\nSample markets:")
                for i, market in enumerate(markets[:3], 1):
                    print(f"  {i}. {market.title}")
                    print(f"     Market ID: {market.market_id}")
                    print(f"     League: {market.league}")
                    print(f"     Team: {market.team}")
                    print(f"     Yes Price: {market.best_yes_price:.4f}")
                    print(f"     Volume: {market.volume:,}")
            else:
                print("  No markets found (this is normal if no sports markets are active)")
        except Exception as e:
            print(f"✗ Market fetch failed: {e}")
            import traceback
            traceback.print_exc()
        
        # Test positions fetch
        print(f"\n--- Testing Positions Fetch ---")
        try:
            positions = client.get_positions()
            print(f"✓ Fetched {len(positions)} positions")
        except Exception as e:
            print(f"✗ Positions fetch failed: {e}")
        
        print(f"\n{'=' * 60}")
        print("API Test Complete!")
        print(f"{'=' * 60}")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    test_api_connection()


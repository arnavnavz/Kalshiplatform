"""
Script to search for and display available sports markets from Kalshi.
"""
import sys
from config import load_config
from kalshi_client import KalshiClient
from datetime import datetime

def search_markets():
    """Search for and display available sports markets."""
    print("=" * 80)
    print("Searching for Sports Markets on Kalshi")
    print("=" * 80)
    
    try:
        config = load_config()
        print(f"\nAPI: {config.kalshi_base_url}")
        print(f"Mode: {config.mode}\n")
        
        client = KalshiClient(config)
        
        # Fetch markets
        print("Fetching markets...")
        markets = client.fetch_sports_markets()
        
        print(f"\n{'=' * 80}")
        print(f"Found {len(markets)} sports markets")
        print(f"{'=' * 80}\n")
        
        if not markets:
            print("No sports markets found.")
            print("\nPossible reasons:")
            print("  - No active sports markets at this time")
            print("  - Markets may be filtered out by category")
            print("  - API endpoint or parameters may need adjustment")
            print("\nTrying to fetch all markets (not just sports)...")
            
            # Try fetching all markets to see what's available
            try:
                print("Making API request to /markets endpoint...")
                params = {"status": "open", "limit": 50}
                print(f"Request params: {params}")
                
                # Check if we can make the request
                if not client._private_key:
                    print("⚠ Warning: No private key loaded, cannot make authenticated requests")
                    return
                
                data = client._request("GET", "/markets", params=params)
                print(f"API Response received: {type(data)}")
                print(f"Response keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                print(f"Full response: {data}")
                
                if not data:
                    print("⚠ Empty response from API")
                    return
                
                # Try different response formats
                all_markets = data.get("markets", [])
                if not all_markets:
                    all_markets = data.get("data", {}).get("markets", [])
                if not all_markets and isinstance(data, list):
                    all_markets = data
                
                if all_markets:
                    print(f"\nFound {len(all_markets)} total open markets")
                    print("\nSample market categories:")
                    categories = {}
                    for m in all_markets[:20]:  # Check first 20
                        cat = m.get("category", "unknown")
                        categories[cat] = categories.get(cat, 0) + 1
                    
                    for cat, count in sorted(categories.items()):
                        print(f"  - {cat}: {count} markets")
                    
                    print("\nSample markets:")
                    for i, m in enumerate(all_markets[:5], 1):
                        print(f"\n  {i}. {m.get('title', 'N/A')}")
                        print(f"     Category: {m.get('category', 'N/A')}")
                        print(f"     Ticker: {m.get('ticker', 'N/A')}")
                        print(f"     Status: {m.get('status', 'N/A')}")
            except Exception as e:
                print(f"Error fetching all markets: {e}")
            
            return
        
        # Display markets
        for i, market in enumerate(markets, 1):
            print(f"{i}. {market.title}")
            print(f"   Market ID: {market.market_id}")
            print(f"   League: {market.league}")
            print(f"   Team: {market.team}")
            print(f"   Yes Price: {market.best_yes_price:.4f} ({market.best_yes_price*100:.2f}%)")
            print(f"   No Price: {market.best_no_price:.4f} ({market.best_no_price*100:.2f}%)")
            print(f"   Spread: {market.spread:.4f} ({market.spread*100:.2f}%)")
            print(f"   Volume: {market.volume:,}")
            print(f"   Start Time: {market.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print()
        
        print(f"{'=' * 80}")
        print(f"Total: {len(markets)} markets")
        print(f"{'=' * 80}")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    search_markets()


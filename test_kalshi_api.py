#!/usr/bin/env python3
"""
Test script to verify Kalshi API connectivity and authentication.
"""
import sys
from config import load_config
from kalshi_client import KalshiClient

def test_kalshi_api():
    """Test Kalshi API connection and authentication."""
    print("=" * 60)
    print("KALSHI API TEST")
    print("=" * 60)
    print()
    
    # Load config
    print("1. Loading configuration...")
    try:
        config = load_config()
        print(f"   ✓ Config loaded")
        print(f"   - Mode: {config.mode}")
        print(f"   - Base URL: {config.kalshi_base_url}")
        print(f"   - API Key: {config.kalshi_api_key[:8]}..." if config.kalshi_api_key and len(config.kalshi_api_key) > 8 else "   - API Key: NOT SET")
        print(f"   - API Secret: {'SET' if config.kalshi_api_secret else 'NOT SET'}")
        if config.kalshi_api_secret:
            secret_len = len(config.kalshi_api_secret)
            print(f"     (Secret length: {secret_len} chars)")
        print()
    except Exception as e:
        print(f"   ✗ Error loading config: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Check if API keys are configured
    if not config.kalshi_api_key or not config.kalshi_api_secret:
        print("   ✗ Missing API credentials!")
        print("   Please check your .env.local file and ensure:")
        print("     - KALSHI_API_KEY or KALSHI_API_KEY_ID is set")
        print("     - KALSHI_API_SECRET or KALSHI_PRIVATE_KEY is set")
        print()
        print("   Note: Kalshi uses:")
        print("     - API Key ID (for authentication)")
        print("     - Private Key (RSA-PSS key for signing)")
        return False
    
    # Initialize client
    print("2. Initializing Kalshi client...")
    try:
        kalshi = KalshiClient(config)
        print("   ✓ Client initialized")
        print()
    except Exception as e:
        print(f"   ✗ Error initializing client: {e}")
        return False
    
    # Test authentication by fetching balance
    print("3. Testing authentication (fetching balance)...")
    try:
        balance = kalshi.get_account_balance()
        if balance is not None:
            print(f"   ✓ Authentication successful!")
            print(f"   - Balance: ${balance:.2f}")
            print()
        else:
            print("   ✗ Authentication failed - balance is None")
            print()
            return False
    except Exception as e:
        print(f"   ✗ Authentication failed: {e}")
        print()
        
        # Check if private key was loaded
        if hasattr(kalshi, '_private_key') and kalshi._private_key:
            print("   ✓ Private key was loaded successfully")
        else:
            print("   ✗ Private key was NOT loaded - this is likely the issue!")
            print("   Check that your private key in .env.local is in PEM format:")
            print("   -----BEGIN PRIVATE KEY-----")
            print("   ...")
            print("   -----END PRIVATE KEY-----")
            print()
        
        print("   Common issues:")
        print("     1. Wrong environment:")
        print(f"        - Your base URL: {config.kalshi_base_url}")
        print("        - Demo API keys work with: https://api.demo.kalshi.com/trade-api/v2")
        print("        - Production API keys work with: https://api.elections.kalshi.com/trade-api/v2")
        print("        → Make sure your API keys match the base URL!")
        print()
        print("     2. Invalid/expired API keys")
        print("        → Generate new keys from Kalshi dashboard")
        print()
        print("     3. Incorrect private key format")
        print("        → Should be PEM format with BEGIN/END markers")
        print("        → Should include all newlines (use \\n in .env or actual newlines)")
        print()
        print("   To fix:")
        print("     1. Check which environment your API keys are for (demo or production)")
        print("     2. Set KALSHI_BASE_URL in .env.local to match:")
        print("        - Demo: KALSHI_BASE_URL=https://api.demo.kalshi.com/trade-api/v2")
        print("        - Production: KALSHI_BASE_URL=https://api.elections.kalshi.com/trade-api/v2")
        print("     3. Verify your private key is correctly formatted")
        print()
        return False
    
    # Test fetching markets
    print("4. Testing market fetching...")
    try:
        markets = kalshi.fetch_sports_markets()
        print(f"   ✓ Successfully fetched {len(markets)} markets")
        print()
        
        if markets:
            print("   Sample markets:")
            for i, market in enumerate(markets[:5], 1):
                print(f"   {i}. {market.event_name}")
                print(f"      Market ID: {market.market_id}")
                print(f"      Team: {market.team}")
                print(f"      League: {market.league}")
                print(f"      Start Time: {market.start_time}")
                print(f"      Best YES Price: {market.best_yes_price:.4f}")
                print()
            
            # Check for mock markets
            mock_markets = [m for m in markets if m.market_id.startswith("market_")]
            if mock_markets:
                print(f"   ⚠ WARNING: Found {len(mock_markets)} mock markets (market_0, market_1, etc.)")
                print("   This suggests the API is not returning real data.")
                print()
            else:
                print("   ✓ All markets appear to be real (no mock IDs)")
                print()
        else:
            print("   ⚠ No markets returned")
            print()
    except Exception as e:
        print(f"   ✗ Error fetching markets: {e}")
        print()
        return False
    
    # Test fetching positions
    print("5. Testing position fetching...")
    try:
        positions = kalshi.get_positions()
        print(f"   ✓ Successfully fetched {len(positions)} positions")
        if positions:
            print("   Sample positions:")
            for i, pos in enumerate(positions[:3], 1):
                print(f"   {i}. {pos.market_id}: {pos.quantity} contracts")
        print()
    except Exception as e:
        print(f"   ⚠ Error fetching positions (may be normal if no positions): {e}")
        print()
    
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print("✓ Kalshi API is working correctly!")
    print("  - Authentication: OK")
    print("  - Market fetching: OK")
    print("  - Ready to use")
    print()
    return True

if __name__ == "__main__":
    success = test_kalshi_api()
    sys.exit(0 if success else 1)


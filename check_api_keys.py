"""
Helper script to check and format Kalshi API keys.
"""
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("KALSHI_API_KEY") or os.getenv("KALSHI_API_KEY_ID", "")
api_secret = os.getenv("KALSHI_API_SECRET") or os.getenv("KALSHI_PRIVATE_KEY", "")

print("=" * 60)
print("Kalshi API Key Check")
print("=" * 60)

print(f"\nAPI Key ID:")
if api_key:
    print(f"  ✓ Set (length: {len(api_key)} chars)")
    print(f"  First 20 chars: {api_key[:20]}...")
else:
    print(f"  ✗ Not set")

print(f"\nAPI Secret/Private Key:")
if api_secret:
    print(f"  ✓ Set (length: {len(api_secret)} chars)")
    print(f"  First 50 chars: {api_secret[:50]}...")
    print(f"  Last 50 chars: ...{api_secret[-50:]}")
    
    # Check format
    if "BEGIN PRIVATE KEY" in api_secret:
        print(f"  ✓ Format: PEM (PKCS#8)")
    elif "BEGIN RSA PRIVATE KEY" in api_secret:
        print(f"  ✓ Format: PEM (RSA)")
    elif "-----" in api_secret:
        print(f"  ⚠ Format: Looks like PEM but missing BEGIN/END markers")
    else:
        print(f"  ⚠ Format: Doesn't appear to be PEM format")
        print(f"\n  Your private key should be in PEM format:")
        print(f"  -----BEGIN PRIVATE KEY-----")
        print(f"  ...key content...")
        print(f"  -----END PRIVATE KEY-----")
        print(f"\n  If Kalshi gave you the key in a different format,")
        print(f"  you may need to convert it or check the Kalshi API docs.")
else:
    print(f"  ✗ Not set")

print(f"\n{'=' * 60}")
print("Next Steps:")
print("=" * 60)
if api_key and api_secret:
    if "BEGIN PRIVATE KEY" in api_secret or "BEGIN RSA PRIVATE KEY" in api_secret:
        print("✓ Your API keys appear to be correctly formatted!")
        print("  You can now test the API connection with: python3 test_api.py")
    else:
        print("⚠ Your private key may not be in the correct format.")
        print("  Please check:")
        print("  1. The key should include '-----BEGIN PRIVATE KEY-----' at the start")
        print("  2. The key should include '-----END PRIVATE KEY-----' at the end")
        print("  3. All newlines should be preserved in your .env file")
        print("\n  In your .env file, the private key should look like:")
        print("  KALSHI_API_SECRET=\"-----BEGIN PRIVATE KEY-----\\n...\\n-----END PRIVATE KEY-----\"")
else:
    print("✗ Please set KALSHI_API_KEY and KALSHI_API_SECRET in your .env file")


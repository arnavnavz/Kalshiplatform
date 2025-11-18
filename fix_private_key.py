"""
Helper script to fix private key format by adding PEM headers if missing.
"""
import os
import re
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

def fix_private_key_format(key_content: str) -> str:
    """Add PEM headers if missing."""
    # Remove any existing headers/footers
    key_content = key_content.strip()
    key_content = re.sub(r'-----BEGIN.*?-----', '', key_content, flags=re.DOTALL)
    key_content = re.sub(r'-----END.*?-----', '', key_content, flags=re.DOTALL)
    key_content = key_content.strip()
    
    # Add PEM headers
    return f"-----BEGIN PRIVATE KEY-----\n{key_content}\n-----END PRIVATE KEY-----"

# Read current .env file
env_file = Path(".env")
if not env_file.exists():
    print("✗ .env file not found")
    exit(1)

with open(env_file, 'r') as f:
    env_content = f.read()

# Check if private key needs fixing
api_secret = os.getenv("KALSHI_API_SECRET") or os.getenv("KALSHI_PRIVATE_KEY", "")

if not api_secret:
    print("✗ No API secret found in .env")
    exit(1)

if "BEGIN PRIVATE KEY" in api_secret or "BEGIN RSA PRIVATE KEY" in api_secret:
    print("✓ Private key already has PEM headers")
    exit(0)

print("⚠ Private key missing PEM headers. Fixing...")

# Find the line with the secret
lines = env_content.split('\n')
fixed_lines = []
fixed = False

for line in lines:
    if line.startswith("KALSHI_API_SECRET=") or line.startswith("KALSHI_PRIVATE_KEY="):
        # Extract the key value
        if '=' in line:
            key_name, value = line.split('=', 1)
            # Remove quotes if present
            value = value.strip().strip('"').strip("'")
            
            # Fix the format
            fixed_value = fix_private_key_format(value)
            
            # Write back with quotes and proper escaping
            # For .env files, we can use triple quotes or escape newlines
            fixed_line = f'{key_name}="{fixed_value}"'
            fixed_lines.append(fixed_line)
            fixed = True
            print(f"✓ Fixed {key_name}")
        else:
            fixed_lines.append(line)
    else:
        fixed_lines.append(line)

if fixed:
    # Backup original
    backup_file = Path(".env.backup")
    with open(backup_file, 'w') as f:
        f.write(env_content)
    print(f"✓ Created backup: {backup_file}")
    
    # Write fixed version
    with open(env_file, 'w') as f:
        f.write('\n'.join(fixed_lines))
    print(f"✓ Updated .env file")
    print(f"\n⚠ Note: If the key has newlines, you may need to manually format it.")
    print(f"   The key should be on multiple lines in your .env file:")
    print(f"   KALSHI_API_SECRET=\"-----BEGIN PRIVATE KEY-----")
    print(f"   ...key content...")
    print(f"   -----END PRIVATE KEY-----\"")
else:
    print("✗ Could not find KALSHI_API_SECRET or KALSHI_PRIVATE_KEY in .env")


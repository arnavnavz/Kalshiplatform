# Real API Integration Guide

## Kalshi API Setup

To use real Kalshi data instead of mock data, you need to:

### 1. Get Your API Credentials

1. Log into your Kalshi account
2. Go to API settings
3. Generate an API Key ID and Private Key
4. The Private Key should be in PEM format (starts with `-----BEGIN PRIVATE KEY-----`)

### 2. Update Your `.env` File

Add your credentials to `.env`:

```env
# Kalshi API Configuration
# Option 1: Use KALSHI_API_KEY and KALSHI_API_SECRET
KALSHI_API_KEY=your_api_key_id_here
KALSHI_API_SECRET=-----BEGIN PRIVATE KEY-----
...your private key content...
-----END PRIVATE KEY-----

# Option 2: Or use KALSHI_API_KEY_ID and KALSHI_PRIVATE_KEY
# KALSHI_API_KEY_ID=your_api_key_id_here
# KALSHI_PRIVATE_KEY=-----BEGIN PRIVATE KEY-----
# ...your private key content...
# -----END PRIVATE KEY-----

# Use production API (not demo)
KALSHI_BASE_URL=https://api.kalshi.com/trade-api/v2

# Set mode to LIVE when ready (start with SHADOW for testing)
MODE=SHADOW
```

**Important Notes:**
- The private key must be in PEM format
- Keep your private key secure - never commit it to git
- The `.env` file is already in `.gitignore`

### 3. Install Cryptography Library

The real API integration requires the `cryptography` library:

```bash
pip install -r requirements.txt
```

This will install `cryptography>=41.0.0` which is needed for RSA-PSS signature authentication.

### 4. Test the Integration

1. **Start in SHADOW mode first** to test without placing real orders:
   ```bash
   MODE=SHADOW python runner.py
   ```

2. Check the logs to see if markets are being fetched:
   ```bash
   tail -f logs/bot.log
   ```

3. Once verified, switch to LIVE mode:
   ```bash
   MODE=LIVE python runner.py
   ```

## Reference Odds Integration

Currently, the bot uses mock reference odds. To use real odds:

### Option 1: The Odds API

1. Sign up at https://the-odds-api.com/
2. Get your API key
3. Add to `.env`:
   ```env
   THE_ODDS_API_KEY=your_odds_api_key
   ```

4. Update `odds_client.py` to use The Odds API (implementation needed)

### Option 2: SportsDataIO

1. Sign up at https://sportsdata.io/
2. Get your API key
3. Add to `.env`:
   ```env
   SPORTSDATA_API_KEY=your_sportsdata_key
   ```

### Option 3: Other Providers

You can integrate any odds provider by:
1. Adding API key to `.env`
2. Implementing the `fetch_reference_odds()` method in `odds_client.py`
3. Mapping Kalshi markets to external game IDs

## Troubleshooting

### Authentication Errors

If you see authentication errors:
- Verify your API key ID is correct
- Verify your private key is in PEM format
- Check that the private key includes the full header/footer lines
- Ensure you're using the correct base URL (demo vs production)

### No Markets Found

If no markets are returned:
- Check that there are active sports markets on Kalshi
- Verify the API endpoint is correct
- Check the logs for specific error messages
- The bot filters for sports markets - ensure markets have the "sport" category

### Market Parsing Issues

The market parsing logic may need adjustment based on:
- Actual Kalshi market title formats
- Event ticker formats
- League naming conventions

You may need to update:
- `_extract_league_from_ticker()` in `kalshi_client.py`
- `_parse_market_info()` in `kalshi_client.py`
- `extract_games_from_markets()` in `runner.py`
- `map_market_to_game_and_team()` in `runner.py`

## Next Steps

1. ✅ Real Kalshi API integration (markets, balance, positions, orders)
2. ⏳ Real reference odds integration
3. ⏳ Market parsing refinement based on actual data
4. ⏳ Testing with real markets


# The Odds API Setup Guide

## Issue: Reference Odds Showing as "N/A"

If you're seeing "N/A" for reference odds in the dashboard, it's likely because:

1. **API Key is Invalid/Expired** (Most Common)
   - The Odds API returned a 401 Unauthorized error
   - Your API key may have expired or been revoked

2. **API Key Not Set**
   - Check that `THE_ODDS_API_KEY` is in your `.env.local` file

3. **API Quota Exhausted**
   - Free tier has limited requests per month
   - Check your usage at https://the-odds-api.com/

## How to Fix

### Step 1: Get a New API Key

1. Go to https://the-odds-api.com/
2. Sign up or log in
3. Go to your dashboard: https://the-odds-api.com/dashboard
4. Copy your API key

### Step 2: Add to .env.local

Add this line to your `.env.local` file:

```bash
THE_ODDS_API_KEY=your_api_key_here
```

### Step 3: Verify It Works

Test the API key:

```bash
python3 test_odds_api.py
```

Or test manually:

```bash
curl "https://api.the-odds-api.com/v4/sports/basketball_nba/odds?apiKey=YOUR_KEY&regions=us&markets=h2h&oddsFormat=american"
```

## API Limits

- **Free Tier**: 500 requests/month
- **Paid Plans**: Start at $10/month for 5,000 requests

## Troubleshooting

### 401 Unauthorized Error
- Your API key is invalid or expired
- Get a new key from https://the-odds-api.com/

### No Games Matched
- The Odds API may not have odds for all games
- Some games may be too far in the future
- Team name matching may fail (check logs)

### Quota Exhausted
- Check your usage: https://the-odds-api.com/dashboard
- Upgrade your plan if needed
- The bot will continue to work without reference odds (using Kalshi prices only)

## Alternative: Continue Without Reference Odds

The bot will still work without reference odds:
- It will use Kalshi prices as the baseline
- Research-based recommendations will still work
- You just won't see odds arbitrage opportunities



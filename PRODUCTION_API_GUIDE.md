# Switching to Production API - What Changes

## Current Setup (Demo API)

**Base URL:** `https://api.demo.kalshi.com/trade-api/v2`

- **Purpose:** Testing and development environment
- **Markets:** May have limited or test markets
- **Balance:** Demo/test balance (often $0 or test funds)
- **Orders:** Test orders (not real money)
- **Data:** May not reflect real market conditions

## Production API

**Base URL:** `https://api.kalshi.com/trade-api/v2`

### What Changes:

1. **Real Markets**
   - ✅ Access to all live, real sports markets on Kalshi
   - ✅ Real-time prices and volumes
   - ✅ Actual market liquidity

2. **Real Account Data**
   - ✅ Your actual account balance
   - ✅ Your real positions
   - ✅ Real P&L

3. **Real Orders** (when MODE=LIVE)
   - ⚠️ **REAL MONEY** - Orders will use your actual funds
   - ⚠️ **IRREVERSIBLE** - Trades are real and binding
   - ⚠️ **RISK** - You can lose real money

4. **API Credentials**
   - ✅ Same API keys work for both demo and production
   - ✅ Same authentication method
   - ✅ No code changes needed

## How to Switch

### Step 1: Update `.env` File

Change this line:
```env
# From:
KALSHI_BASE_URL=https://api.demo.kalshi.com/trade-api/v2

# To:
KALSHI_BASE_URL=https://api.kalshi.com/trade-api/v2
```

### Step 2: Test in SHADOW Mode First

**CRITICAL:** Always test in SHADOW mode first!

```env
MODE=SHADOW
```

This will:
- ✅ Fetch real markets from production
- ✅ See your real balance
- ✅ Calculate real trades
- ✅ **BUT:** Won't place any real orders (just logs them)

### Step 3: Verify Everything Works

```bash
python3 test_api.py
```

You should see:
- Real markets (if any are active)
- Your actual account balance
- Successful API connections

### Step 4: Monitor in SHADOW Mode

Run the bot and watch the logs:
```bash
python3 runner.py
```

Check:
- Are markets being fetched correctly?
- Are the calculations reasonable?
- Are the trade decisions making sense?

### Step 5: Only Then Switch to LIVE

**ONLY** after thorough testing in SHADOW mode:

```env
MODE=LIVE
```

⚠️ **WARNING:** This will place REAL orders with REAL money!

## Important Considerations

### 1. Account Balance
- Production API shows your **real** account balance
- Make sure you have sufficient funds
- Start with small position sizes

### 2. Market Availability
- Production has real markets (may be more or fewer than demo)
- Markets depend on what's actually trading on Kalshi
- Some markets may have different liquidity

### 3. API Rate Limits
- Production API may have different rate limits
- Be mindful of request frequency
- The bot already has retry logic built in

### 4. Risk Management
- Your risk limits still apply (MAX_PER_BET_PCT, etc.)
- But now they're protecting **real money**
- Double-check your risk settings before going LIVE

## Safety Checklist Before Switching to Production

- [ ] Tested thoroughly in SHADOW mode with demo API
- [ ] Verified markets are being fetched correctly
- [ ] Checked that trade logic makes sense
- [ ] Reviewed and confirmed risk limits are appropriate
- [ ] Understand that LIVE mode uses real money
- [ ] Have sufficient account balance
- [ ] Ready to monitor the bot closely
- [ ] Know how to stop the bot if needed

## Recommended Workflow

1. **Demo API + SHADOW Mode** (Current)
   - Test the integration
   - Verify API connection works

2. **Production API + SHADOW Mode** (Next Step)
   - See real markets
   - Verify calculations with real data
   - No risk - no real orders

3. **Production API + LIVE Mode** (Final)
   - Real trading
   - Real money at risk
   - Monitor closely

## Quick Switch Command

To quickly test production API in SHADOW mode:

```bash
# Edit .env to change:
# KALSHI_BASE_URL=https://api.kalshi.com/trade-api/v2
# MODE=SHADOW

# Then test:
python3 test_api.py
```

## Reverting Back

If you want to go back to demo:

```env
KALSHI_BASE_URL=https://api.demo.kalshi.com/trade-api/v2
```

No other changes needed - same code, same keys, just different endpoint.


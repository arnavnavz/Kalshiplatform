# What is "Edge" and How Does It Work?

## Simple Explanation

**Edge = How much better your probability estimate is compared to what Kalshi is offering**

Think of it like this:
- **Fair Probability**: What the market (sportsbooks) thinks the true probability is (e.g., 73.4% for Burnley to win)
- **Kalshi Price**: What Kalshi is offering (e.g., 19.0% for Burnley to win)
- **Edge**: The difference = 73.4% - 19.0% = **54.4% edge**

## What Edge Means

**Positive Edge (e.g., +54.4%):**
- Kalshi is **undervaluing** the team
- You can buy at 19% when the true value is 73.4%
- This is a **good bet** - you're getting better odds than the market

**Negative Edge (e.g., -10%):**
- Kalshi is **overvaluing** the team
- You'd be paying more than the true value
- This is a **bad bet** - avoid it

**Zero Edge:**
- Kalshi price matches fair value
- No advantage either way
- Usually skip these

## Example: Burnley vs Crystal Palace

**What you're seeing:**
- **Kalshi Price**: 19.0% (what Kalshi offers for Burnley to win)
- **Fair Probability**: 73.4% (what sportsbooks think Burnley's true win probability is)
- **Edge**: 54.4% (the difference)

**What this means:**
- Sportsbooks think Burnley has a **73.4% chance** to win
- Kalshi is only charging **19%** for that bet
- You're getting **54.4% more value** than you should pay
- This is a **very good bet** (if research confirms Burnley should win)

## Important: Which Team's Market?

For a game like "Burnley vs Crystal Palace", Kalshi has **TWO separate markets**:
1. **Market 1**: "Burnley to win" - YES price = 19% (means 19% chance Burnley wins)
2. **Market 2**: "Crystal Palace to win" - YES price = 81% (means 81% chance Crystal Palace wins)

**The edge calculation:**
- If we're looking at **Burnley's market** (19% Kalshi price):
  - Fair value from sportsbooks: 73.4%
  - Edge = 73.4% - 19% = **+54.4%** ✅ Good bet on Burnley

- If we're looking at **Crystal Palace's market** (81% Kalshi price):
  - Fair value from sportsbooks: 26.6% (100% - 73.4%)
  - Edge = 26.6% - 81% = **-54.4%** ❌ Bad bet (Kalshi overpriced)

## Why You Might See Low Kalshi Prices

If you see a very low Kalshi price (like 9% or 19%), it could mean:
1. ✅ **Good opportunity**: Kalshi is undervaluing the team (like Burnley at 19%)
2. ❌ **Wrong market**: We're showing the opponent's market instead (e.g., showing Crystal Palace's 19% when we meant Burnley)

## How to Verify

Check the "Team to Bet" column:
- If it says "Burnley (YES)" and Kalshi Price is 19%, that's correct
- If it says "Burnley (YES)" but Kalshi Price is 81%, that's wrong (showing opponent's market)

## The Fix

The bot should:
1. ✅ Filter out TIE markets (already done)
2. ✅ Show the market for the team with the best edge
3. ✅ Make sure "Team to Bet" matches the Kalshi Price shown

If you see mismatches, it means we're showing the wrong team's market.


